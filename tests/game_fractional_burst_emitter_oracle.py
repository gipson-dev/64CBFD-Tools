"""Rounded phase reference, mutable providers and retained 64-bit random helper."""
from dataclasses import dataclass
import struct
from tools.experiments import game_fractional_burst_emitter_match as match
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_random_selector_outputs_match import RandomOutputsOracle,next_seed,SEEDS
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
ACTOR,OTHER,RATE,STEP,RNG,EMIT,SEED,SCALE=0x30000,0x60000,0x800A8D10,0x800BE9A4,0x150ADA68,0x1514C678,0x800885B0,0x8009F740
PARENT,RELEASE,DESTRUCTOR,TABLE,TICKS=0x15149264,0x1516972C,0x150AE790,0x8008A4E8,0x800BE9E4
RANDOMS=(0,0x3E800000,0x3F000000,0x3F800000,0xBF800000,0x7FC12345,0x7F800000)
class CallLimit(Exception):pass
@dataclass(frozen=True)
class Case:
    phase_value:int=0x40480000
    step:int=0x3F800000
    rate:int=0x3E333334
    tag:int=0xFE
    context:int=0x81
    mode:int=0
    random:int=0
    phase:int=0
    actor:int=ACTOR
    alias:int=0
    offset:int=0
def syms():return dict(D_800A8D10=RATE,D_800BE9A4=STEP,func_150ADA68=RNG,func_1514C678=EMIT)
def actor(c,s):return c.actor if not c.alias else s['D_800A8D10'if c.alias==1 else'D_800BE9A4']-c.offset
def mul(a,b):return bits(floating(a)*floating(b))
def add(a,b):return bits(floating(a)+floating(b))
def sub(a,b):return bits(floating(a)-floating(b))
def fixture(c=Case(),s=None):
    s=s or syms();a=actor(c,s);m={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
    m.update({a+i:(i*13+89)&255 for i in range(64)})
    for at,v in((0x28,bits(1.25)),(0x2C,bits(-2.5)),(0x30,0x80000000),(0x38,c.phase_value)):put(m,a+at,v)
    m[a+0x34]=c.tag;m[a+0xC]=c.context;put(m,s['D_800A8D10'],c.rate);put(m,s['D_800BE9A4'],c.step)
    put(m,SEED,0x123456789ABCDEF0,8);put(m,SCALE,0x37800080);return m
def effect(m,c,s,kind,n,home):
    a=actor(c,s)
    if kind=='random'and n==1:
        if c.mode&1:
            for i in range(3):put(m,a+0x28+4*i,bits(100.+i))
            m[a+0x34]=0x80;m[a+0xC]=0xFF;put(m,a+0x38,bits(3.75))
        if c.mode&2:put(m,s['D_800A8D10'],bits(4.));put(m,s['D_800BE9A4'],bits(8.))
        if c.mode&16:put(m,home,OTHER)
    if kind=='emit'and n==1:
        if c.mode&4:put(m,a+0x38,bits(.25))
        if c.mode&8:
            for i in range(3):put(m,a+0x28+4*i,bits(200.+i))
            m[a+0x34]=0xFF;m[a+0xC]=0x80
def public(m):return{p:v for p,v in m.items()if not STACK-2048<=p<STACK+2048}
def reference(initial,c=Case(),s=None,connected_rng=False,home=None,saved=None):
    s=s or syms();a=actor(c,s);m=dict(initial);calls=[];h=STACK+c.phase if home is None else home
    saved=saved or(0x5A000010,0x5A000011,0xDEAD0000)
    for at,value in((-12,saved[0]),(-8,saved[1]),(-4,saved[2])):put(m,h+at,value)
    put(m,a+0x38,add(read(m,a+0x38),mul(read(m,s['D_800A8D10']),read(m,s['D_800BE9A4']))))
    n=0
    while floating(read(m,a+0x38))>1.:
        n+=1
        if n>16:raise CallLimit
        calls.append((s['func_150ADA68'],()))
        if connected_rng:
            seed=next_seed(read(m,SEED,8));put(m,SEED,seed,8);value=mul(bits(float(seed&65535)),read(m,SCALE))
        else:value=RANDOMS[(c.random+n-1)%len(RANDOMS)];effect(m,c,s,'random',n,h)
        packet=(*(read(m,a+0x28+4*i)for i in range(3)),add(mul(value,bits(25.)),bits(15.)),0,255,5,4,m[a+0x34],0,0,m[a+0xC])
        calls.append((s['func_1514C678'],packet));effect(m,c,s,'emit',n,h)
        put(m,a+0x38,sub(read(m,a+0x38),bits(1.)))
    return m,calls
class Oracle(RandomOutputsOracle,FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=match.ENTRY,connected=None,limit=16):
        self.s=s or syms();self.home=STACK+c.phase;self.n=0;self.emission_limit=limit;self.packets=[]
        FactoryOracle.__init__(self,words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(actor(c,self.s),))
    def record_call(self,t):
        if t==self.s['func_150ADA68']:
            if self.n>=self.emission_limit:raise CallLimit
            self.n+=1;a=()
        elif t==self.s['func_1514C678']:
            a=(self.f[12],self.f[14],self.r[6]&0xFFFFFFFF,self.r[7]&0xFFFFFFFF,*(read(self.memory,self.r[29]+16+4*i)for i in range(8)));self.packets.append(a)
        elif t==match.ENTRY:a=(self.r[4],);self.home=self.r[29]
        elif t in(RELEASE,DESTRUCTOR):a=(self.r[4],)
        else:raise AssertionError(('Unbounded fractional burst provider',hex(t)))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        if t==self.s['func_150ADA68']:effect(self.memory,self.case,self.s,'random',self.n,self.home)
        elif t==self.s['func_1514C678']:effect(self.memory,self.case,self.s,'emit',self.n,self.home)
        elif t==RELEASE:self.memory[self.calls[-1][1][0]+0x3F]=0xEE
        elif t!=DESTRUCTOR:raise AssertionError(('Unexpected fractional burst hook',hex(t)))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0xA5A50002;self.hi,self.lo=0xA5000010,0xA5000011
        if t==self.s['func_150ADA68']:self.f[0]=RANDOMS[(self.case.random+self.n-1)%len(RANDOMS)]
def rng_code(rom):return dict(zip(range(RNG,RNG+100,4),struct.unpack_from('>25I',rom,0xDAF18)))
