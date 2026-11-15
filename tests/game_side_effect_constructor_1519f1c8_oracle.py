"""Independent constructor model, full packet provenance and original helpers."""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_side_effect_constructor_1519f1c8_match as s
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests import game_perpendicular_offset_1519ef90_oracle as offset
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import test_game_actor_burst_consumer_match as faults
STATE,ACTOR,ALT,OUT,PAYLOAD=0x30000,0x31000,0x32000,0x80000,0x800A0
COLOR,QUERY,FACTORY,COPY,ALLOCATE,ZERO,CHECK=0x151D8E20,0x1519EF90,0x15147A80,0x10022EC0,0x15167A68,0x100226F0,0x150A29C8
HEADING,SAMPLE=offset.HEADING,offset.SAMPLE
COUNTS={COLOR:0,QUERY:3,FACTORY:11,COPY:3,ALLOCATE:6,ZERO:2,CHECK:2,HEADING:1,SAMPLE:1,s.ENTRY:2,0x151A0928:1}

@dataclass(frozen=True)
class Case:
    mode:int=6
    hit:int=1
    success:int=1
    color:int=10
    effects:int=0
    phase:int=0
    seed:int=0
    alias:int=0
    rule:str='left'

def destination(c):return (PAYLOAD,STATE+0x10,ACTOR+0x10,s.symbols()['D_800AB414']+8)[c.alias]
def data(m,p,n):return bytes(m[p+i] for i in range(n))
def public(m,c):return {p:v for p,v in m.items() if not STACK+c.phase-2048<=p<STACK+c.phase+2048}
def public_trace(q,c):return [v for v in q.trace if not STACK+c.phase-2048<=v[1]<STACK+c.phase+2048]

def fixture(c):
    home=STACK+c.phase;m={home+i:(i*17+c.seed*29+0xA5)&255 for i in range(-2048,2048)}
    for p,n in ((STATE,0x100),(ACTOR,0x240),(ALT,0x240),(OUT,0x240),(s.symbols()['D_800AB414'],768)):
        assert p+n<=home-2048 or p>=home+2048,('public fixture overlaps stack window',hex(p),n)
        m.update({p+i:(i*13+c.seed*31+0x53)&255 for i in range(n)})
    for p,v in offset.helper_data()[1].items():put(m,p,v)
    for p in (ACTOR,ALT):
        for d,v in ((0x14,bits(1.25 if p==ACTOR else -3.0)),(0x18,bits(4.5)),(0x1C,bits(-2.0 if p==ACTOR else 9.0)),(0x118,bits(-9500.)),(0x1D4,c.hit)):
            put(m,p+d,v)
        put(m,p+0x7A,(c.seed*17&255)<<8,2)
    put(m,STATE+0x18,ACTOR);put(m,STATE+0x68,bits(2.5))
    put(m,OUT+0x98,destination(c))
    put(m,s.symbols()['D_800A8CE8'],0x3E800000);put(m,s.symbols()['D_800A8CEC'],0x3F000000)
    return m

def color_effect(m,c):
    if c.effects&1:
        put(m,STATE+0x18,ALT);put(m,ACTOR+0x14,bits(11.));put(m,ACTOR+0x1C,bits(-17.))
        put(m,s.symbols()['D_800A8CE8'],0x80000000);put(m,s.symbols()['D_800A8CEC'],0x7FC12345)
    if c.effects&2:
        for i in range(768):m[s.symbols()['D_800AB414']+i]=(255-i+c.seed)&255

def query_effect(m,c,packet,point):
    if c.effects&4:
        put(m,packet+8,0xDEADBEEF);put(m,STATE+0x18,ACTOR)
        for i in range(768):m[s.symbols()['D_800AB414']+i]^=0x55
    if c.hit:
        for i,v in enumerate((bits(-3.25),0x80000000,0x7FC54321)):put(m,point+4*i,v)

def model_query(m,c,packet,point,calls):
    actor=read(m,read(m,packet)+0x18)
    if not read(m,actor+0x1D4):return 0
    op=lambda a,b,k:offset.fp(a,b,k,c.rule)
    dx=op(read(m,actor+0x14),read(m,packet+0x20),'sub');dz=op(read(m,actor+0x1C),read(m,packet+0x24),'sub')
    threshold=floating(read(m,s.symbols()['D_800A8CE0']))
    if threshold<abs(floating(dx)) or threshold<abs(floating(dz)):
        inv=op(bits(1.),offset.sqrt_word(op(op(dx,dx,'mul'),op(dz,dz,'mul'),'add')),'div')
        tx,tz=op(dz,inv,'mul'),op(dx,inv,'mul')
    else:
        heading=((read(m,actor+0x7A,2)>>8)+64)&255
        calls.extend(((HEADING,(actor,)),(SAMPLE,(heading,)),(SAMPLE,((heading-64)&255,))))
        tx,tz=offset.sample(m,heading),offset.sample(m,(heading-64)&255)
    distance=read(m,read(m,packet)+0x68)
    if c.mode&255!=6:distance^=0x80000000
    put(m,point,op(read(m,actor+0x14),op(distance,tx,'mul'),'add'))
    put(m,point+8,op(read(m,actor+0x1C),op(distance,tz,'mul'),'sub'))
    height=read(m,actor+0x118)
    put(m,point+4,read(m,actor+0x18) if floating(height)<floating(read(m,s.symbols()['D_800A8CE4'])) else height)
    return 1

def reference(initial,c,connected=False):
    m=initial.copy();home=STACK+c.phase;packet,request=home-0x70,home-0x20;actor=read(m,STATE+0x18)
    calls=[(COLOR,())];snap=[];color_effect(m,c)
    for p,v,n in ((request+14,0x42,2),(request+12,300,2),(request+21,10,1),(packet+46,200,2),(packet+64,3,1),
        (packet,STATE,4),(packet+4,6,1),(packet+65,0x55,1),(packet+66,3,1),(packet+67,0x55,1),(packet+68,0x88,1),(packet+69,0xC4,1),
        (packet+40,0,2),(packet+70,0,2),(packet+48,255,2),(packet+50,40,2),(packet+52,25,2),(packet+72,6,2),(packet+74,0x325,2),
        (packet+8,read(m,s.symbols()['D_800A8CE8']),4),(packet+56,read(m,s.symbols()['D_800A8CEC']),4),(packet+60,0x3F800000,4),
        (packet+12,0,4),(packet+28,0,4),(request+16,c.mode&255,4),(packet+76,0x3FC00000,4),
        (packet+32,read(m,actor+0x14),4),(packet+36,read(m,actor+0x1C),4)):put(m,p,v,n)
    calls.append((QUERY,(packet,c.mode&255,request)));snap.append(('query',data(m,packet,80),data(m,request,12)))
    hit=model_query(m,c,packet,request,calls) if connected else c.hit
    if not connected:query_effect(m,c,packet,request)
    if hit:
        for i in range(12):m[packet+16+i]=m[request+i]
        put(m,request+14,read(m,request+14,2)|4,2)
    for i in range(3):m[packet+42+i]=m[s.symbols()['D_800AB414']+(c.color&255)*3+i]
    a=(request,80,36,5,5,5,0,0,STATE+0x34,255,1);calls.append((FACTORY,a));snap.append(('factory',data(m,request,28)))
    if c.success:
        a=(read(m,OUT+0x98),packet,80);calls.append((COPY,a));snap.append(('copy',data(m,packet,80)))
        packet_bytes=data(m,packet,80)
        for i,v in enumerate(packet_bytes):m[a[0]+i]=v
    return m,calls,snap,OUT if c.success else 0

class Machine(offset.Oracle):
    def __init__(self,words,m,c,connected=False,entry=None,arguments=None,code=None):
        self.c=c;self.snap=[];self.fp_ops=[];self.root_words=words
        FactoryOracle.__init__(self,words,m,BaseCase(phase=c.phase),entry=s.ENTRY if entry is None else entry,s={},arguments=(STATE,c.mode) if arguments is None else arguments,connected=code if code is not None else helpers() if connected else None)
    def execute(self,w):return offset.Oracle.execute(self,w)
    def record_call(self,t):
        a=tuple(x&0xFFFFFFFF for x in self.arguments(COUNTS[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==QUERY:self.snap.append(('query',data(self.memory,a[0],80),data(self.memory,a[2],12)))
        elif t==FACTORY:self.snap.append(('factory',data(self.memory,a[0],28)))
        elif t==COPY:self.snap.append(('copy',data(self.memory,a[1],a[2])))
    def hook(self,t):
        a=self.calls[-1][1];c=self.c
        if t==COLOR:color_effect(self.memory,c);value=c.color
        elif t==QUERY:query_effect(self.memory,c,a[0],a[2]);value=c.hit
        elif t==FACTORY:value=OUT if c.success else 0
        elif t==COPY:
            assert a[2]==80
            chunk=data(self.memory,a[1],a[2])
            for i,v in enumerate(chunk):self.memory[a[0]+i]=v
            value=a[0]
        elif t==ALLOCATE:value=OUT if c.success else 0
        elif t==ZERO:
            assert a==(OUT+0x84,16)
            for i in range(a[1]):self.memory[a[0]+i]=0
            value=0xDEADBEEF
        else:raise AssertionError(('unexpected hook',hex(t)))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value&0xFFFFFFFF

@lru_cache(None)
def helpers():
    rom=(s.ROOT/'conker/conker.us.bin').read_bytes();elf=(s.ROOT/'conker/build/conker.us.elf').read_bytes();code={}
    for entry,n in ((QUERY,94),(HEADING,7),(SAMPLE,27)):
        off=entry-0x15000000+0x2D4B0;raw=rom[off:off+n*4];at=elf_slot_offset(elf,entry,len(raw));assert elf[at:at+len(raw)]==raw
        code.update(zip(range(entry,entry+4*n,4),struct.unpack('>'+str(n)+'I',raw)))
    return code

@lru_cache(None)
def factory_helpers():
    rom=(s.ROOT/'conker/conker.us.bin').read_bytes();elf=(s.ROOT/'conker/build/conker.us.elf').read_bytes();code=dict(helpers())
    for entry,off,n in ((FACTORY,0x174F30,115),(COPY,0x22EC0,11)):
        if entry==FACTORY:off=entry-0x15000000+0x2D4B0
        raw=rom[off:off+4*n];at=elf_slot_offset(elf,entry,len(raw));assert elf[at:at+len(raw)]==raw,hex(entry)
        code.update(zip(range(entry,entry+4*n,4),struct.unpack('>'+str(n)+'I',raw)))
    return code

def connected_factory(streams):
    count=0;code=factory_helpers()
    for mode,hit,success,effects,phase in itertools.product((6,7),(0,1),(0,1),(0,1,2,4,7),(0,8)):
        c=Case(mode=mode,hit=hit,success=success,effects=effects,phase=phase);initial=fixture(c)
        expected,_,snap,value=reference(initial,c,True);observations=[]
        for w in streams.values():
            q=Machine(w,initial.copy(),c,code=code).run();assert q.r[2]==value
            assert [a for t,a in q.calls if t==ALLOCATE]==[(77,1,600,1,255,1)]
            assert q.snap[:2]==snap[:2]
            if success:
                assert data(q.memory,PAYLOAD,80)==data(expected,PAYLOAD,80)
                assert data(q.memory,OUT+0x10,28)==snap[1][1]
                assert data(q.memory,OUT+0x60,36)==data(expected,STATE+0x34,36)
                assert data(q.memory,OUT+0x2C,6)==bytes((0,0,0,5,5,5))
                assert data(q.memory,OUT+0x34,4)==bytes(4) and q.memory[OUT+0x38]==0
                assert data(q.memory,OUT+0x3C,36)==bytes(36)
                assert data(q.memory,OUT+0x84,16)==bytes(16)
                assert read(q.memory,OUT+0x94)==OUT+0xF0 and read(q.memory,OUT+0x98)==PAYLOAD
                assert [a for t,a in q.calls if t==ZERO]==[(OUT+0x84,16)]
            observations.append((public(q.memory,c),q.calls,q.snap))
        assert observations.count(observations[0])==3,c
        count+=1
    return count

def run(words,c,connected=False,cut=None):
    q=Machine(words,fixture(c),c,connected);q.cut=cut;return q.run()

def cases():
    for mode,hit,success,color,effects,phase,alias in itertools.product((0,6,7,0xFFFFFF06),(0,1),(0,1),(0,10,255),(0,1,2,4,7),(0,8),range(4)):
        yield Case(mode=mode,hit=hit,success=success,color=color,effects=effects,phase=phase,alias=alias,seed=color%7)

def check(words,c,connected=False):
    initial=fixture(c);expected,calls,snap,value=reference(initial,c,connected);q=Machine(words,initial,c,connected).run()
    assert (public(q.memory,c),q.calls,q.snap,q.r[2])==(public(expected,c),calls,snap,value),('constructor model',c,connected,q.calls,calls,q.snap,snap)
    return q

def boundaries(streams):
    count=0
    for c in (Case(),Case(hit=0,success=0,effects=3),Case(alias=1,effects=7),Case(alias=3,mode=0xFFFFFF06)):
        complete=[check(w,c) for w in streams.values()];totals=[]
        for label,w in streams.items():
            target=complete[0 if label=='retail' else 1 if label=='candidate' else 2];cuts=[]
            for cut in range(target.all_accesses):
                q=Machine(w,fixture(c),c);q.cut=cut
                try:q.run()
                except faults.AccessBoundary:pass
                else:raise AssertionError('Boundary did not fire')
                trace=public_trace(q,c)
                # Compare public effect prefixes, not private/scratch fault state.
                if trace:cuts.append((len(trace),trace,public(q.memory,c),q.calls,q.snap))
                count+=1
            totals.append({repr(x):x for x in cuts})
        assert set(totals[0])==set(totals[1])==set(totals[2]),('public boundary prefixes',c)
    return count

def main():
    streams=s.programs();count=0;visits={k:set() for k in streams}
    for c in cases():
        for label,w in streams.items():q=check(w,c);visits[label]|=q.visits
        count+=1
    connected=0
    for mode,hit,success,effects,seed in itertools.product((6,7),(0,1),(0,1),(0,1,2,3),range(16)):
        c=Case(mode=mode,hit=hit,success=success,effects=effects,seed=seed)
        for w in streams.values():check(w,c,True)
        connected+=1
    controls=[]
    for label,word,mask,c in (('flags',0x24180042,1,Case()),('allocation',0x24050050,4,Case()),('palette',0x904A0000,1,Case()),('snapshot',0xC4700014,8,Case(effects=1))):
        w=streams['retail'][:];assert w.count(word)==1;w[w.index(word)]^=mask
        try:check(w,c)
        except (AssertionError,KeyError):controls.append(label)
        else:raise AssertionError(('ineffective guest control',label))
    report=dict(cases_per_stream=count,streams=3,connected_query_cases_per_stream=connected,connected_factory_cases_per_stream=connected_factory(streams),public_boundary_cuts=boundaries(streams),
                visited_root_words={k:len([v for v in values if s.ENTRY<=v<s.ENTRY+s.SIZE]) for k,values in visits.items()},effective_controls=controls)
    (s.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
