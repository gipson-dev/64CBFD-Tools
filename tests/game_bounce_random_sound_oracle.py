"""Bounce callback ABI, independent float effects and original helper execution."""
from dataclasses import dataclass
import math,struct
from tools.experiments import game_bounce_random_sound_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
from tools.tests import test_game_actor_burst_consumer_match as faults
ACTOR,MARK,TABLE,SEED,AUDIO_BASE=0x30000,0x50000,0x80089934,0x800885B0,0x10010E78
u32=lambda n:n&0xFFFFFFFF
s16=lambda n:(n&65535)-65536 if n&32768 else n&65535
bits=lambda f:struct.unpack('>I',struct.pack('>f',f))[0]
floating=lambda n:struct.unpack('>f',struct.pack('>I',n))[0]
rounded=lambda f:floating(bits(f))
COORDS=((0.0,-0.0,0.0),(1.75,-1.75,17.5),(32767.75,-32768.75,65535.75),(-65536.75,65536.75,123.25),(1073741824.0,-1073741824.0,2147483520.0))
@dataclass(frozen=True)
class Case:
    gate:int=1
    sample:int=0
    position:int=1
    phase:int=0
    scale:int=0
    velocity:int=0
    mutation:int=0
    seed:int=1
    actual_rng:bool=False

def symbols():return dict(func_15133B98=source.BOUNCE,func_150ADA20=source.RANDOM,func_10010F88=source.AUDIO)
def arguments(c):return(ACTOR,*map(bits,COORDS[c.position]),bits(17.25),ACTOR+0x114)
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+2048}
def fixture(c=Case()):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,2048)}
    for base,size in((ACTOR,0x200),(MARK,16),(TABLE,60),(SEED,8)):
        for i in range(size):m[base+i]=(i*29+0xA5)&255
    put(m,ACTOR+0x10,bits(10.5));put(m,ACTOR+0x14,bits((0.0,0.5,1.0,-1.0)[c.scale]))
    for i,v in enumerate((1.75,(0.0,3.999,4.0,-4.0,8.0)[c.velocity],-2.5,3.25,-4.5,5.75,6.25)):put(m,ACTOR+0x44+4*i,bits(v))
    put(m,ACTOR+0x60,0xFEDCBAFF);m[ACTOR+0x73]=12;put(m,ACTOR+0x110,bits(17.25));put(m,TABLE+48,source.ENTRY);put(m,SEED,c.seed,8)
    return m

def bounce(m,args):
    a,_,_,_,height,_=args;scale=floating(read(m,a+0x14));yspeed=rounded(floating(read(m,a+0x48))*(-scale))
    values=[rounded(floating(read(m,a+off))*scale)for off in(0x44,0x4C,0x50,0x54,0x58)]
    put(m,a+0x48,bits(yspeed));put(m,a+0x3C,bits(rounded(floating(read(m,a+0x10))+floating(height))))
    for off,v in zip((0x44,0x4C,0x50,0x54,0x58),values):put(m,a+off,bits(v))
    if abs(yspeed)<4.0:
        put(m,a+0x60,read(m,a+0x60)&0xFFFFFF96)
        for off in range(0x44,0x60,4):put(m,a+off,0)

def effect(m,c,stage,home):
    if c.mutation==stage:
        for i,v in enumerate((123.75,-234.5,32767.75)):put(m,home+4+i*4,bits(v))
        put(m,ACTOR+0x90,stage)

def observe(m):return tuple(read(m,ACTOR+i)for i in(0x3C,0x44,0x48,0x4C,0x50,0x54,0x58,0x5C,0x60,0x90))+ (read(m,MARK),)
def audio_effect(m,args):put(m,MARK,sum(args)&0xFFFFFFFF);put(m,ACTOR+0x80,0xACED1234)

def reference(initial,c=Case(),s=None,connected=False,home=None,args=None):
    s=symbols()if s is None else s;m=dict(initial);args=arguments(c)if args is None else args;home=STACK+c.phase if home is None else home;calls=[];observations=[]
    for i in range(1,4):put(m,home+4*i,args[i])
    def call(t,a):calls.append((t,tuple(map(u32,a))));observations.append((t,observe(m)))
    call(s['func_15133B98'],args);bounce(m,args);effect(m,c,1,home)
    def rng(index):
        call(s['func_150ADA20'],());effect(m,c,index+2,home)
        if c.actual_rng:
            value=next_seed(read(m,SEED,8));put(m,SEED,value,8);return u32(value)
        return u32((c.gate,c.sample)[index])
    if rng(0)&1:
        sound=rng(1)%9+0x2DE
        audio=(sound,0x2EE0,0,0,0,*[u32(math.trunc(floating(read(m,home+4*i))))for i in range(1,4)],500,1000)
        call(s['func_10010F88'],audio)
        if connected:
            base=(0,*audio[:5],*[s16(v)for v in audio[5:]]);call(AUDIO_BASE,base);audio_effect(m,base)
        else:audio_effect(m,audio)
    return m,calls,observations

class BounceSoundOracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None,args=None):
        self.case=c;self.syms=symbols()if s is None else s;self.home=STACK+c.phase;self.rng_count=0
        super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=arguments(c)if args is None else args,connected=connected)
        self.trace=[];self.observations=[];self.all_accesses=0;self.cut=None
    def access(self):
        if self.own_instruction:
            if self.all_accesses==self.cut:raise faults.AccessBoundary
            self.all_accesses+=1
    def get(self,a,n):
        v=super().get(a,n)
        if self.own_instruction:self.trace.append(('R',a,n,v))
        return v
    def put(self,a,v,n):
        super().put(a,v,n)
        if self.recording and self.own_instruction:self.trace.append(('W',a,n,v&((1<<(8*n))-1)))
    def execute(self,w):
        op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if op in(55,63):
            self.own_instruction=True
            try:
                a=u32(self.r[rs]+s16(w));assert a%8==0
                if op==55:self.r[rt]=self.get(a,8)
                else:self.put(a,self.r[rt],8)
            finally:self.own_instruction=False
        elif op==0 and fn in(56,58,60,62,63):
            v=self.r[rt]&((1<<64)-1)
            if fn in(56,60):v<<=sh+(32 if fn==60 else 0)
            elif fn in(58,62):v>>=sh+(32 if fn==62 else 0)
            else:v=(v if v<1<<63 else v-(1<<64))>>(sh+32)
            self.r[rd]=v&((1<<64)-1)
        elif op==0 and fn in(37,38) and source.RANDOM<=self.current_pc<source.RANDOM+72:
            self.r[rd]=(self.r[rs]|self.r[rt])if fn==37 else(self.r[rs]^self.r[rt])
        elif op==17 and rs==16 and fn in(5,7):
            self.f[w>>6&31]=(self.f[w>>11&31]&0x7FFFFFFF)if fn==5 else(self.f[w>>11&31]^0x80000000)
        elif op==32:
            self.own_instruction=True
            try:v=self.get(u32(self.r[rs]+s16(w)),1);self.r[rt]=u32((v^128)-128)
            finally:self.own_instruction=False
        else:
            before=self.r[:]
            if op==0 and fn==27:self.r[rs]=u32(self.r[rs]);self.r[rt]=u32(self.r[rt])
            super().execute(w)
            # Retain original 64-bit RNG temporaries through its ordinary LUI/ANDI.
            if source.RANDOM<=self.current_pc<source.RANDOM+72:
                dest=rt if op in(9,12,13,15,35)else rd if op==0 else None
                for i,v in enumerate(before):
                    if i!=dest and v>0xFFFFFFFF:self.r[i]=v
        self.r[0]=0
    def record_call(self,t):
        s=self.syms;counts={source.ENTRY:6,s['func_15133B98']:6,s['func_150ADA20']:0,s['func_10010F88']:10,AUDIO_BASE:11}
        assert t in counts,('Unbounded bounce sound provider',hex(t));args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args));self.observations.append((t,observe(self.memory)))
        if t==s['func_150ADA20']:
            effect(self.memory,self.case,self.rng_count+2,self.home);self.rng_count+=1
    def hook(self,t):
        s=self.syms;args=self.calls[-1][1];value=0xABCD
        if t==s['func_15133B98']:bounce(self.memory,args);effect(self.memory,self.case,1,self.home)
        elif t==s['func_150ADA20']:assert not self.case.actual_rng;value=u32((self.case.gate,self.case.sample)[self.rng_count-1])
        elif t in(s['func_10010F88'],AUDIO_BASE):audio_effect(self.memory,args)
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

HELPERS=((source.BOUNCE,0x161048,48),(source.AUDIO,0x10F88,29))
def helper_code(rom,actual_rng=False):
    result={}
    for entry,offset,n in HELPERS+(((source.RANDOM,0xDAED0,18),)if actual_rng else()):result.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return result
WINDOWS=((0x15132FDC,19,(0x15133024,0x15133028,0x151332C8)),(0x1513397C,17,(0x151339C0,)))
def caller_machine(rom,words,c=Case(),window=0,index=12):
    from tools.tests.test_game_character_effect_pair import WindowCode
    entry,n,ends=WINDOWS[window];initial=fixture(c);initial[ACTOR+0x73]=index;home=STACK+c.phase
    args=arguments(c)
    for i in range(1,4):put(initial,home+(0x370 if window==0 else 0x3C)+i*4,args[i])
    code=helper_code(rom,c.actual_rng);code.update(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));code.update({pc:0 for pc in ends})
    body=struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2D4B0)
    m=BounceSoundOracle(body,initial,c,entry=entry,connected=code,args=args);m.r[16]=ACTOR;m.r[4]=ACTOR;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=ends
    expected=dict(initial);calls=[];observations=[];called=window==1 or index!=0
    if called:
        expected,calls,observations=reference(initial,c,connected=True,home=home,args=args);calls=[(source.ENTRY,args)]+calls;observations=[(source.ENTRY,observe(initial))]+observations
    return m,(expected,calls,observations),called
