"""Two-bank wave effects, live reads, narrowing, single wrap and real sine."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,math,os,struct
from tools.experiments import game_wave_vertices_15179db0_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests import test_game_trig_match as trig
SINE,RES,STATE,INDICES,FACTOR=0x15047d60,0x800dde80,0x8008d0b0,0x800a7210,0x800a7218
FIRST,SECOND,ALT=0x50000,0x60000,0x70000
u32=lambda v:v&0xffffffff
half=lambda v:((v&65535)^32768)-32768
class ConversionBoundary(Exception):pass

@dataclass(frozen=True)
class Case:
    index:int=8
    phases:tuple=(0x43af0000,0x43b40000)
    steps:tuple=(0x41200000,0x3f800000)
    amplitude:int=0x41a80000
    samples:tuple=(0x3e800000,0xbe800000)
    indices:tuple=(4,9,13,14,15,17,19)
    factor:int=0x3c8efa35
    alias:int=0
    mutation:int=0
    phase:int=0
    seed:int=0
    real:bool=False

def address(c):return STATE+(c.index&255)*56
def resource(c):return RES+(c.index&255)*20
def banks(c):return (FIRST if c.alias==1 else FIRST+16 if c.alias==2 else SECOND),FIRST
def mul(a,b):return bits(floating(a)*floating(b))
def add(a,b):return bits(floating(a)+floating(b))
def sub(a,b):return bits(floating(a)-floating(b))

def cases():
    phase_pairs=((0.,0.),(350.,360.),(-1.,720.),(359.5,1080.),(360.,-360.))
    step_pairs=((0.,0.),(10.,1.),(-2.,720.),(.5,-.5))
    for i,(pair,step,amplitude,samples,alias,mutation,phase) in enumerate(itertools.product(
            phase_pairs,step_pairs,(21.,-21.5,65536.),((.25,-.25),(1.,-1.)),range(3),(0,1,3),(0,8))):
        indices=(4,9,13,14,15,17,19) if i%2 else (2,3,6,8,0,19,2)
        yield Case(0xabcd0000|(8+i%2),tuple(map(bits,pair)),tuple(map(bits,step)),bits(amplitude),
                   tuple(map(bits,samples)),indices,alias=alias,mutation=mutation,phase=phase,seed=i)
    for v in range(256):
        yield Case(index=0x12340000|v,seed=v)
        yield Case(indices=(v,)*7,seed=v)
    for sample in (0x7f800000,0xff800000,0x7fc01234,0x4f000000):
        yield Case(samples=(sample,bits(.25)))
        yield Case(samples=(bits(.25),sample))

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,512)}
    for base in (FIRST,SECOND,ALT):m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(512)})
    p=address(c);q=resource(c)
    m.update({p+i:(i*19+c.seed+0xa5)&255 for i in range(56)})
    m.update({q+i:(i*23+c.seed+0x5a)&255 for i in range(20)})
    second,first=banks(c);put(m,q+4,first);put(m,q+8,second)
    for i,value in enumerate(c.steps):put(m,p+0x18+4*i,value)
    for i,value in enumerate(c.phases):put(m,p+0x20+4*i,value)
    put(m,p+0x28,c.amplitude)
    for i,value in enumerate(c.indices):m[INDICES+i]=value
    put(m,FACTOR,c.factor)
    for base in (first,second):
        for idx in c.indices:
            for k in range(2):m.setdefault(base+idx*16+k,0xa5)
    if c.real:
        for a,v in trig.GLOBALS.items():put(m,a,v)
    return m

def digest(m,c):
    values=[m[base+i] for base in (FIRST,SECOND,ALT) for i in range(512)]
    values += [m[address(c)+i] for i in range(56)]+[m[resource(c)+i] for i in range(20)]
    values += [m[INDICES+i] for i in range(7)]+[m[FACTOR+i] for i in range(4)]
    h=2166136261
    for v in values:h=u32((h^v)*16777619)
    return h

def effects(m,c,ordinal,home):
    if c.mutation&1:
        p=address(c);q=resource(c)
        put(m,p+0x28,bits(-21.5+ordinal*.5))
        put(m,p+0x20+ordinal*4,bits(720.+ordinal+.5))
        put(m,p+0x18,bits(30.+ordinal));put(m,p+0x1c,bits(-1.25+ordinal))
        put(m,FACTOR,bits(2.+ordinal));put(m,q+4,ALT);put(m,q+8,ALT)
        for i,v in enumerate((2,3,6,8,19,1,17)):m[INDICES+i]=v
        m[FIRST+0x1f1]^=ordinal+1;m[SECOND+0x1f2]^=ordinal+1
    if c.mutation&2:put(m,home,0x87650007)

def reference(initial,c):
    m=dict(initial);p=address(c);q=resource(c);factor=read(m,FACTOR)
    selected=(read(m,q+8),read(m,q+4));calls=[];observations=[]
    for i,base in enumerate(selected):
        argument=mul(read(m,p+0x20+4*i),factor);calls.append((SINE,(argument,)));observations.append(digest(m,c))
        sample=trig.reference(argument) if c.real else c.samples[i]
        effects(m,c,i,STACK+c.phase);product=floating(mul(sample,read(m,p+0x28)))
        if not math.isfinite(product) or not -2147483648<=product<2147483648:
            return m,calls,observations,i
        value=half(math.trunc(product))
        put(m,base+0x20,value&65535,2);put(m,base+0x30,value&65535,2)
        edge=-(value>>1)
        for j in range(7):put(m,base+m[INDICES+j]*16,edge&65535,2)
        put(m,base+0x60,(edge+18)&65535,2);put(m,base+0x80,(edge-18)&65535,2)
        at=p+0x20+4*i;put(m,at,add(read(m,at),read(m,p+0x18+4*i)))
        if floating(read(m,at))>=360.:put(m,at,sub(read(m,at),bits(360.)))
    return m,calls,observations,None

class Oracle(FactoryOracle):
    def __init__(self,words,initial,c,entry=source.ENTRY,connected=None):
        self.observed=[]
        super().__init__(words,initial,c,entry=entry,arguments=(u32(c.index),),connected=connected)
        self.before_r,self.before_f=self.r[:],self.f[:]
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63==7:
            self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
        elif w>>26==17 and w>>21&31==16 and w&63==13:
            value=floating(self.f[w>>11&31])
            if not math.isfinite(value) or not -2147483648<=value<2147483648:raise ConversionBoundary
            self.f[w>>6&31]=u32(math.trunc(value))
        else:super().execute(w)
    def record_call(self,target):
        if target==source.ENTRY:
            assert self.r[4]&255==self.case.index&255;return
        assert target==SINE,hex(target);a=(self.f[12],)
        self.calls.append((target,a));self.events.append(('CALL',target,a));self.observed.append(digest(self.memory,self.case))
    def hook(self,target):
        assert target==SINE;ordinal=len(self.calls)-1;effects(self.memory,self.case,ordinal,self.target_home)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.f[0]=self.case.samples[ordinal]
        self.hi,self.lo=0xa5000010,0xa5000011

def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def verify(m,initial,c):
    expected,calls,obs,boundary=reference(initial,c)
    assert (public(m.memory),m.calls,m.observed)==(public(expected),calls,obs),c
    if boundary is None:
        assert m.r[16:24]==m.before_r[16:24] and m.f[20:]==m.before_f[20:] and m.r[29]==m.before_r[29]
def state(m):return m.memory,m.r,m.f,m.calls,m.observed,m.trace,m.hi,m.lo
def load():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD
    programs=[source.bound(*payload(out/f,source.NAME)) for f in ('retail.o','selected.o','guarded.o')]
    assert programs[0]==programs[2];return root,out,programs

def main():
    root,out,programs=load();n=prefixes=0;seen=set()
    for c in cases():
        initial=fixture(c);boundary=reference(initial,c)[3];models=[]
        for words in programs:
            m=Oracle(words,initial,c)
            try:m.run();assert boundary is None
            except ConversionBoundary:assert boundary is not None
            verify(m,initial,c);models.append(m)
        assert state(models[0])==state(models[2]);seen.update(models[0].visits)
        if boundary is None:n+=1
        else:prefixes+=1
    assert len(seen)==140,len(seen)
    cuts=0
    for c in (Case(mutation=3),Case(alias=1)):
        initial=fixture(c);m=Oracle(programs[0],initial,c);m.run()
        for cut in range(m.all_accesses):
            models=[]
            for words in (programs[0],programs[2]):
                m=Oracle(words,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing fired memory boundary')
                models.append(m)
            assert state(models[0])==state(models[1]);cuts+=1
    rom=(root/'conker/conker.us.bin').read_bytes();pc=0x15183f4c;window=struct.unpack_from('>7I',rom,0x1b13fc)
    caller_cases=0
    for slot,flag,mutation,phase in itertools.product((8,9),(0,1,255),(0,1),(0,8)):
        c=Case(index=slot,mutation=mutation,phase=phase);initial=fixture(c);initial[0x800ddf68+slot]=flag
        for words in programs:
            code=dict(zip(range(source.ENTRY,source.ENTRY+source.SIZE,4),words));ends=(0x15183f68,0x15183f6c)
            code.update({end:0 for end in ends});m=Oracle(window,initial,c,entry=pc,connected=code)
            m.r[16],m.r[17],m.r[18]=slot-8,0x800ddf68+slot-8,1;m.before_r=m.r[:]
            m.code=WindowCode(m.code,m);m.code.ends=ends
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing caller continuation')
            if flag==1:verify(m,initial,c)
            else:assert public(m.memory)==public(initial) and not m.calls
        caller_cases+=1
    helper=dict(zip(range(SINE,SINE+416,4),struct.unpack_from('>104I',rom,0x75210)))
    from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
    elf=(root/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,SINE,416)
    assert elf[at:at+416]==rom[0x75210:0x753b0]
    real_cases=0
    for slot,angle,alias,phase in itertools.product((8,9),(0.,45.,90.,359.,360.,720.,-45.),range(3),(0,8)):
        c=Case(index=slot,phases=(bits(angle),bits(angle+1)),alias=alias,phase=phase,real=True);initial=fixture(c)
        for words in programs:
            m=Oracle(words,initial,c,connected=helper);m.run();verify(m,initial,c)
        real_cases+=1
    controls={'wrong_bank_snapshot':(26,0x8c590008),'wrong_wrap_limit':(29,0x3c0143b3),
              'wrong_seventh_index':(103,0x90480002),'wrong_positive_edge':(99,0x246d0011)}
    killed=[]
    for label,(at,word) in controls.items():
        words=programs[0][:];assert words[at]!=word;words[at]=word;failed=False
        for c in (Case(),Case(phases=(bits(350.),bits(350.))),Case(mutation=1),Case(alias=1)):
            initial=fixture(c)
            try:m=Oracle(words,initial,c);m.run();verify(m,initial,c)
            except (AssertionError,KeyError):failed=True;break
        assert failed,label;killed.append(label)
    report=dict(valid_cases=n,conversion_prefixes=prefixes,observed_words=len(seen),caller_cases=caller_cases,
                full_state_prefixes=cuts,provider_mutations=True,alias_layouts=3,
                real_sine_cases=real_cases,native_index_domain='8,9',raw_private_frame_explicit=True,
                negative_controls=killed,original_sine_bytes_reverified=True)
    (out/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=='__main__':main()
