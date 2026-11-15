"""Independent six-provider vertex arcs, cached model pointer and live state."""
from dataclasses import dataclass
import itertools,json,math,struct
from tools.experiments import game_model_vertex_wave_1517725c_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
STATE,MODELS,VERTICES,ALTERNATE,MARK=0x8008d0b0,0x800dde88,0x50000,0x51000,0x70000
SIN,COS=0x150ad78c,0x150ad780
COEFFS=(0x800a71ac,0x800a71b0,0x800a71b4,0x800a71b8)
RETURNS=(0x3f000000,0xbf000000,0x3f800000,0xbf800000,0x3e800000,0xbe800000,0,0x80000000)
u32=lambda x:x&0xffffffff
mul=lambda a,b:bits(floating(a)*floating(b))
add=lambda a,b:bits(floating(a)+floating(b))
sub=lambda a,b:bits(floating(a)-floating(b))

@dataclass(frozen=True)
class Case:
    slot:int=7
    angle:int=0x43b38000
    speed:int=0x3f800000
    amplitude:int=0x42340000
    outer:int=0x420c0000
    inner:int=0x41a00000
    mode:int=0
    phase:int=0
    seed:int=0
    alias:int=0
    private_sine:bool=False
    flag:int=1

def address(c):return STATE+(c.slot&255)*56
def home(c):return STACK+c.phase
def vertices(c):return VERTICES if not c.alias else address(c)+0x24-0xa0
def values(c):return tuple(RETURNS[(c.seed+3*i)%len(RETURNS)]for i in range(6))

def cases():
    for slot,angle,mode,phase in itertools.product((0,7,10,255,0x87650007),(0.,359.5,360.,720.,-30.),(0,1,0x15,0x3f),(0,8)):
        yield Case(slot=slot,angle=bits(angle),speed=bits((1.,-2.,400.)[slot%3]),mode=mode,phase=phase,seed=slot%8)
    for seed in range(64):yield Case(slot=seed%11,seed=seed,outer=bits((-65535.75,-1.,0.,0.75,32768.75,65535.5)[seed%6]),inner=bits((0.,-32768.75,1.5,12345.75)[seed%4]),mode=seed&63)
    for alias,mode in itertools.product((1,),(0,1,63)):yield Case(alias=alias,mode=mode,seed=0)

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,512)}
    for base,n in ((STATE-32,256*56+64),(MODELS-32,256*20+64),(VERTICES-32,576),(ALTERNATE-32,576),(MARK,4)):
        for i in range(n):m[base+i]=(i*29+c.seed*11+0x59)&255
    p=address(c)
    for off,v in ((0x18,bits(13.)),(0x1c,c.speed),(0x24,c.angle),(0x28,c.amplitude),(0x30,c.outer),(0x34,c.inner)):put(m,p+off,v)
    put(m,MODELS+(c.slot&255)*20,vertices(c));put(m,home(c),u32(c.slot));put(m,MARK,0)
    for p in COEFFS:put(m,p,0x3c8efa35)
    m[0x800ddf6f]=c.flag&255
    return m

def effects(m,c,stage,h):
    put(m,MARK,u32((SIN if stage in (0,1,3,4) else COS)^((stage+1)*0x1020304)))
    if c.mode>>stage&1:
        p=address(c)
        for off,v in ((0x24,bits(30.+stage*70.)),(0x28,bits(20.+stage)),(0x30,bits(32.+stage)),(0x34,bits(16.+stage)),(0x1c,bits(-1.+stage))):put(m,p+off,v)
        put(m,MODELS+(c.slot&255)*20,ALTERNATE)
        for i,p in enumerate(COEFFS):put(m,p,bits((stage+i+1)/128.))
        put(m,h,0x76540003)
    if c.private_sine and stage in (2,5):put(m,h-8,0x3e800000)

def trunc(v):
    f=floating(v);assert math.isfinite(f) and -2147483647<=math.trunc(f)<=2147483647,hex(v)
    return math.trunc(f)

def reference(initial,c,h=None):
    m=dict(initial);h=home(c)if h is None else h;p=address(c);v=read(m,MODELS+(c.slot&255)*20);calls=[]
    def call(target,arg):
        stage=len(calls);calls.append((target,(arg,)));effects(m,c,stage,h);return values(c)[stage]
    wave=mul(call(SIN,mul(read(m,p+0x24),read(m,COEFFS[0]))),read(m,p+0x28));put(m,p+0x18,wave)
    angle=mul(wave,read(m,COEFFS[1]));sine=call(SIN,angle);cosine=call(COS,angle)
    if c.private_sine:sine=0x3e800000
    radius=read(m,p+0x30);x=trunc(mul(radius,cosine));y=trunc(mul(radius,sine))
    for off,val in ((0xa0,-x),(0xb0,-x),(0x110,x),(0x120,x),(0x112,y),(0x122,y),(0xa2,y),(0xb2,y)):put(m,v+off,val&65535,2)
    wave=mul(call(SIN,mul(sub(read(m,p+0x24),bits(30.)),read(m,COEFFS[2]))),read(m,p+0x28));put(m,p+0x18,wave)
    angle=mul(wave,read(m,COEFFS[3]));sine=call(SIN,angle);cosine=call(COS,angle)
    if c.private_sine:sine=0x3e800000
    radius=read(m,p+0x34);x=trunc(mul(radius,cosine));y=trunc(mul(radius,sine))
    for off,val in ((0xe0,-x),(0x130,x),(0xe2,y),(0x132,y)):put(m,v+off,val&65535,2)
    angle=add(read(m,p+0x24),read(m,p+0x1c));put(m,p+0x24,angle)
    if floating(angle)>=360.:put(m,p+0x24,sub(angle,bits(360.)))
    return m,calls

class Oracle(FactoryOracle):
    def __init__(self,words,initial,c,entry=source.ENTRY,connected=None):
        super().__init__(words,initial,c,entry=entry,arguments=(u32(c.slot),),connected=connected)
        self.entered=home(c);self.entries=[];self.before_r=self.r[:];self.before_f=self.f[:];self.call_ra=self.r[31]
    def record_call(self,t):
        if t==source.ENTRY:self.entered=self.r[29];self.call_ra=self.r[31];self.entries.append(self.r[4]);return
        assert t==(SIN if len(self.calls)in(0,1,3,4)else COS)
        a=(self.f[12],);self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        stage=len(self.calls)-1;effects(self.memory,self.case,stage,self.entered)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.f[0]=values(self.case)[stage]
        self.hi,self.lo,self.condition=0xa5000010,0xa5000011,True

def public(m):return {a:v for a,v in m.items()if not STACK-512<=a<STACK+512}
def state(m):return m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of
def verify(m,initial,c):
    want,calls=reference(initial,c,m.entered)
    assert (public(m.memory),m.calls)==(public(want),calls),c
    assert m.r[16:24]==m.before_r[16:24] and m.r[29:31]==m.before_r[29:31] and m.r[31]==m.call_ra and m.f[20:]==m.before_f[20:]

def main():
    programs=[source.bound(*payload(source.OUT/n,source.NAME))for n in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2]
    seen=set();count=0
    for c in cases():
        initial=fixture(c);models=[]
        for w in programs:m=Oracle(w,initial,c);m.run();verify(m,initial,c);models.append(m)
        assert state(models[0])==state(models[2]);seen.update(models[0].visits);count+=1
    private=0
    for mode,phase,seed in itertools.product((0,63),(0,8),range(8)):
        c=Case(mode=mode,phase=phase,seed=seed,private_sine=True);initial=fixture(c)
        for w in (programs[0],programs[2]):m=Oracle(w,initial,c);m.run();verify(m,initial,c)
        private+=1
    prefixes=0
    for c in (Case(),Case(mode=63),Case(alias=1),Case(private_sine=True)):
        initial=fixture(c);full=Oracle(programs[0],initial,c);full.run()
        for cut in range(full.all_accesses):
            models=[]
            for w in (programs[0],programs[2]):
                m=Oracle(w,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing target memory boundary')
                models.append(m)
            assert state(models[0])==state(models[1]);prefixes+=1
    assert seen==set(range(source.ENTRY,source.ENTRY+source.SIZE,4))
    report=dict(cases=count,streams=3,private_sine_cases=private,full_state_prefixes=prefixes,visited_words=len(seen),raw_fault_order_claimed=False)
    (source.OUT/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
