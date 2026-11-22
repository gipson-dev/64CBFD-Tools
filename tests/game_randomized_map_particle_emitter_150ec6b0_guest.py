"""Execute raw C and retail streams against a bounded independent packet model."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,sys
from tools.experiments import game_randomized_map_particle_emitter_150ec6b0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_interpolated_particle_emitter_150d1204_guest as fp
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
bits,floating,u32=fp.bits,fp.floating,fp.u32
ENTRY=0x150EC6B0;FRNG=0x150ADA68;RNG=0x150ADA20;FACTORY=0x15130280;COPY=0x10022EC0
RECORD=0x30000;OUTPUT=0x60000;STEP=0x800BE9A4
LITERALS=(0x44D44000,0x38D1B717,0x3F7870B9,0x3F82B114,0x3DC8B43A,0x3E3020C5)
@dataclass(frozen=True)
class Case:
    accumulator:int=bits(2.25)
    timestep:int=bits(.25)
    float_draws:tuple=(bits(.5),bits(.25),bits(.75),bits(0.),bits(1.))
    integer_draws:tuple=(0,1,4,5,50,51,100,101,0x80000000,0xFFFFFFFF)
    float_flags:object=None
    allocation_mask:int=0xFF
    mode:int=0
    phase:int=0
    fcsr:int=0
    priority:int=0xAB
    context:int=0xCD

def addresses(home):return home-272+0x9C,home-272+0x8C
def fixture(c):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    m.update({RECORD+i:0xA5 for i in range(72)})
    for off,v in ((0x28,bits(1.)),(0x2C,bits(-2.)),(0x30,bits(3.)),(0x34,c.accumulator)):put(m,RECORD+off,v)
    m[RECORD+0xC]=c.priority;m[RECORD+1]=c.context
    for i,v in enumerate(LITERALS):put(m,0x800A1578+4*i,v)
    put(m,STEP,c.timestep)
    m.update({OUTPUT+i:0xA5 for i in range(8*192)})
    return m
def public(m):return {a:v for a,v in m.items()if not STACK-2048<=a<STACK+512}
def snapshot(m,home,fcsr):
    d,e=addresses(home)
    return (tuple(m[d+i] for i in range(112)),tuple(m[e+i]for i in range(16)),
            tuple(m[RECORD+i]for i in range(56)),read(m,STEP),fcsr)
def provider(m,c,t,args,ordinal,home):
    d,e=addresses(home)
    if t==FRNG:
        if ordinal==1 and c.mode&1:
            put(m,STEP,bits(.5));put(m,RECORD+0x34,bits(2.5))
        return c.float_draws[(ordinal-1)%len(c.float_draws)]
    if t==RNG:
        if c.mode&8:
            m[RECORD+0xC]=(c.priority+ordinal)&255;m[RECORD+1]=(c.context^ordinal)&255
        return c.integer_draws[(ordinal-1)%len(c.integer_draws)]
    if t==FACTORY:
        assert args==(d,0,0,16,m[RECORD+0xC],m[RECORD+1]),args
        if c.mode&2:m[d+0x14]=(m[d+0x14]+1)&255
        answer=OUTPUT+192*(ordinal-1)if c.allocation_mask&(1<<(ordinal-1))else 0
        if answer:
            for i in range(112):m[answer+16+i]=m[d+i]
            m[answer+0x9C]=0
        return answer
    assert t==COPY and args[1:]==(e,16),args
    for i in range(16):m[args[0]+i]=m[e+i]
    if c.mode&2:m[e]=(m[e]+1)&255
    if c.mode&4 and ordinal==1:put(m,RECORD+0x34,bits(.5))
    return args[0]

def reference(initial,c,home=None):
    m=dict(initial);home=STACK+c.phase if home is None else home;d,e=addresses(home)
    calls=[];observations=[];counts={};fcsr=c.fcsr
    def calc(a,b,op):
        nonlocal fcsr
        value,flags=fp.arithmetic(a,b,op,fcsr&3);fcsr=(fcsr&~0x3F000)|flags;return value
    def call(t,*args):
        nonlocal fcsr
        args=tuple(map(u32,args));counts[t]=counts.get(t,0)+1
        calls.append((t,args));observations.append(snapshot(m,home,fcsr))
        answer=provider(m,c,t,args,counts[t],home)
        if t==FRNG and c.float_flags is not None:fcsr=(fcsr&~0x3F000)|c.float_flags[(counts[t]-1)%len(c.float_flags)]
        return answer
    draw=call(FRNG)
    increment=calc(calc(calc(bits(1352.),calc(draw,LITERALS[0],2),0),LITERALS[1],2),read(m,STEP),2)
    put(m,RECORD+0x34,calc(read(m,RECORD+0x34),increment,0))
    if floating(read(m,RECORD+0x34))>1.:
        m[e]=m[e+1]=0;put(m,e+12,LITERALS[2])
        for off,value,size in ((0,0x200005,4),(4,0,4),(8,0x5103,2),(12,0,4),(16,0,4),
            (0x1C,255,1),(0x1D,108,1),(0x1E,70,2),(0x20,3,2),(0x22,70,2),
            (0x24,LITERALS[3],4),(0x58,0x80DE07,4),(0x60,8,1),(0x61,6,1),
            (0x62,22,1),(0x63,255,1),(0x64,255,1),(0x65,0,1)):put(m,d+off,value,size)
        for i,v in enumerate((71,194,0,255,192,73,0)):m[d+0x14+i]=v
        for i in range(12):m[d+0x30+i]=m[RECORD+0x28+i]
        for i in range(0x3C,0x54):m[d+i]=0
        for iteration in range(8):
            m[e+2]=call(RNG)%5+4;m[e+3]=call(RNG)%5+4
            put(m,e+4,calc(call(FRNG),bits(11.),2));put(m,e+8,calc(call(FRNG),bits(11.),2))
            parameter=calc(call(FRNG),LITERALS[5],2)
            put(m,d+0x58,read(m,d+0x58)&~0xC0)
            put(m,d+0x54,calc(parameter,LITERALS[4],0))
            first=0x80 if call(RNG)&1 else 0
            second=0x40 if call(RNG)&1 else 0
            put(m,d+0x58,read(m,d+0x58)|first|second)
            m[d+0x1B]=call(RNG)%101+100;put(m,d+0xA,call(RNG)%51+80,2)
            extent=calc(calc(call(FRNG),bits(80.),2),bits(92.),0)
            put(m,d+0x2C,extent);put(m,d+0x28,extent)
            answer=call(FACTORY,d,0,0,16,m[RECORD+0xC],m[RECORD+1])
            if answer:call(COPY,answer+0xA8,e,16)
            put(m,RECORD+0x34,calc(read(m,RECORD+0x34),bits(1.),1))
            if not floating(read(m,RECORD+0x34))>1.:break
        else:raise AssertionError('bounded particle count exceeded')
    return m,calls,observations,fcsr

class Oracle(fp.Oracle):
    def __init__(self,words,c,entry=ENTRY,connected=None,memory=None):
        self.c=c;self.home=STACK+c.phase
        FactoryOracle.__init__(self,words,fixture(c)if memory is None else memory,c,entry=entry,arguments=(RECORD,),connected=connected)
        self.initial=dict(self.memory);self.before_f=self.f[:];self.fcsr=c.fcsr
        self.counts={};self.observations=[]
    def record_call(self,t):
        args=tuple(map(u32,self.arguments({ENTRY:1,FRNG:0,RNG:0,FACTORY:6,COPY:3}[t])))
        if t==ENTRY:self.home=self.r[29]
        self.calls.append((t,args));self.events.append(('CALL',t,args))
        self.counts[t]=self.counts.get(t,0)+1
        self.observations.append(snapshot(self.memory,self.home,self.fcsr))
    def clobber(self,value):
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
    def hook(self,t):
        value=provider(self.memory,self.c,t,self.calls[-1][1],self.counts[t],self.home)
        self.clobber(value)
        if t==FRNG:
            self.f[0]=value
            if self.c.float_flags is not None:self.fcsr=(self.fcsr&~0x3F000)|self.c.float_flags[(self.counts[t]-1)%len(self.c.float_flags)]

def check(words,c,capture_failure=True):
    m=Oracle(words,c).run();expected,calls,observations,fcsr=reference(m.initial,c)
    assert m.calls==calls,(c,'calls',m.calls,calls)
    if m.observations!=observations:
        first=next((i,a,b)for i,(a,b)in enumerate(zip(m.observations,observations))if a!=b)
        if capture_failure:(out/'guest-failure.json').write_text(json.dumps({'case':str(c),'observation':first},indent=2))
        raise AssertionError((c,'ordered snapshots',first[0]))
    assert public(m.memory)==public(expected),(c,'public memory')
    assert m.fcsr==fcsr,(c,'FCSR',m.fcsr,fcsr)
    assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
    return m

def cases():
    for a,step,mask,mode,phase,rm in itertools.product((0.,1.,1.0000001192092896,2.25,4.25),
        (0.,.25),(0,0x55,0xFF),(0,3,4,8),(0,8),range(4)):
        yield Case(accumulator=bits(a),timestep=bits(step),allocation_mask=mask,mode=mode,phase=phase,fcsr=rm)
    for value in (0,1,4,5,50,51,100,101,0x7FFFFFFF,0x80000000,0xFFFFFFFF):
        yield Case(integer_draws=(value,)*8)
    for zero,rm in itertools.product((0,0x80000000),range(4)):
        yield Case(accumulator=zero,timestep=zero,float_draws=(zero,),fcsr=rm)

def main():
    raw=json.loads((out/'early-payload/words.json').read_text())
    retail=list(struct.unpack_from('>238I',(root/'conker/conker.us.bin').read_bytes(),0x119B60))
    visits=[set(),set()];count=0
    for c in cases():
        machines=[check(words,c)for words in(raw,retail)]
        assert public(machines[0].memory)==public(machines[1].memory)
        for v,m in zip(visits,machines):v.update(m.visits)
        count+=1
    r={'cases_per_stream':count,'streams':2,'raw_words':237,'retail_words':238,
       'executed_words':[sum(ENTRY+4*i in v for i in range(n))for v,n in zip(visits,(237,238))],
       'ordered_packet_snapshots_equal':True,'all_four_rounding_modes':True,
       'null_success_multiple_emissions':True,'escaped_packet_mutations':True,
       'saved_registers_preserved':True,'finite_bounded_model':True,
       'original_helpers_executed':False,'access_fault_prefix_qualified':False,
       'source_installed':packet.installed(),'matching_credit':0}
    (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
