"""Independent signed-width animation model and bounded original lifecycle code."""
from dataclasses import dataclass,replace
import struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments import game_animation_state_tick_match as match
STATE,OTHER,DESC,DESC1=0x50000,0x60000,0x30000,0x30100
TABLE,DEPTH,SLOTS,CATALOG=0x8008CA20,0x800DD190,0x800DD198,0x8008B4A8
RELEASE,UNLINK,FALLBACK,PHYSICAL=0x1516972C,0x151696DC,0x15169804,0x15168B10
CALLBACK=0x18000000
u32=lambda v:v&0xFFFFFFFF
signed8=lambda v:((v&255)^128)-128
signed16=lambda v:((v&65535)^32768)-32768
def trunc256(v):return -(abs(v)//256)if v<0 else v//256
@dataclass(frozen=True)
class Case:
    rate:int=1
    remaining:int=128
    phase_value:int=255
    step:int=1
    count:int=3
    index:int=0
    mutation:int=0
    phase:int=0
    actor:int=STATE
    descriptor:int=DESC
    kind:int=3
    depth:int=2
def syms(table=TABLE,release=RELEASE):return dict(D_8008CA20=table,func_1516972C=release)
def cb(index):return CALLBACK+index*0x100
def fixture(c=Case(),s=None):
    s=s or syms();m={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
    for base,n in((STATE,128),(OTHER,128),(DESC,16),(DESC1,16),(s['D_8008CA20'],1024),(DEPTH-16,16),(SLOTS,64),(CATALOG,5252)):
        m.update({base+i:(i*29+91)&255 for i in range(n)})
    for i in range(256):put(m,s['D_8008CA20']+4*i,cb(i))
    for actor,descriptor in((c.actor,c.descriptor),(OTHER,DESC1)):
        m[actor]=c.kind;put(m,actor+8,0);put(m,actor+0x10,descriptor)
        put(m,actor+0x14,c.phase_value&65535,2);put(m,actor+0x16,c.step&65535,2)
        m[actor+0x22]=c.rate&255;m[actor+0x23]=c.remaining&255;m[actor+0x24]=c.index&255
    m[DESC+4]=c.count&255;m[DESC1+4]=c.count&255
    m[DEPTH]=c.depth&255
    for i in range(8):put(m,SLOTS+4*i,c.actor if i%2==0 else OTHER)
    for i in range(101):put(m,CATALOG+52*i+0x28,0)
    put(m,CATALOG+3*52,match.ENTRY)
    return m
def callback_effect(m,c,h,s):
    actor=c.actor
    if c.mutation&1:
        m[actor+0x22]=0xFE;m[actor+0x23]=129
        put(m,actor+0x14,0x02FF,2);put(m,actor+0x16,0x0101,2)
        m[read(m,actor+0x10)+4]=2
    if c.mutation&2:put(m,h,OTHER)
    if c.mutation&4:put(m,actor+0x10,DESC1);m[DESC1+4]=0
    if c.mutation&8:m[actor+0x24]=0;put(m,s['D_8008CA20']+4*c.index,cb((c.index+1)&255))
    if c.mutation&16:put(m,SLOTS+4*max(0,signed8(m[DEPTH])),0)
def release_effect(m,actor):m[actor+0x3F]=0xEE

def reference(initial,c,ra,s=None,h=None,connected=False):
    s=s or syms();h=STACK+c.phase if h is None else h;m=dict(initial);calls=[];actor=c.actor
    put(m,h-4,ra);index=m[actor+0x24]
    if index:
        target=read(m,s['D_8008CA20']+4*index);put(m,h,actor);calls.append((target,(actor,)))
        callback_effect(m,c,h,s);actor=read(m,h)
        for i in range(4):put(m,h-24+4*i,0xB5000000+i)
    rate=signed8(m[actor+0x22])
    if rate>0:
        remaining=m[actor+0x23]
        if rate<remaining:m[actor+0x23]=(remaining-rate)&255
        else:put(m,actor+0x14,m[read(m,actor+0x10)+4]<<8,2)
    elif rate<0:
        phase=signed16(read(m,actor+0x14,2));limit=m[read(m,actor+0x10)+4]-1
        if trunc256(phase)>=limit:
            remaining=m[actor+0x23];cost=-rate
            if cost<remaining:
                step=signed16(read(m,actor+0x16,2));m[actor+0x23]=(remaining-cost)&255;put(m,actor+0x14,(phase-step)&65535,2)
    phase=signed16(read(m,actor+0x14,2));step=signed16(read(m,actor+0x16,2));descriptor=read(m,actor+0x10)
    put(m,actor+0x14,(phase+step)&65535,2)
    if trunc256(signed16(read(m,actor+0x14,2)))>=m[descriptor+4]:
        calls.append((s['func_1516972C'],(actor,)))
        if connected:
            calls.append((UNLINK,(actor,)))
            for i in range(max(0,signed8(m[DEPTH]))):
                if read(m,SLOTS+4*i)==actor:put(m,SLOTS+4*i,read(m,actor+8))
            if m[actor]>=2:
                assert read(m,CATALOG+0x28+52*m[actor])==0
                calls.extend(((FALLBACK,(actor,)),(PHYSICAL,(actor,1))));release_effect(m,actor)
        else:release_effect(m,actor)
    return m,calls
def public(m):return{p:v for p,v in m.items()if not STACK-2048<=p<STACK+2048}

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=match.ENTRY,connected=None,arguments=None):
        self.s=s or syms();self.home=STACK+c.phase
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(c.actor,)if arguments is None else arguments)
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,False
    def record_call(self,t):
        if t==PHYSICAL:a=tuple(self.arguments(2))
        elif t in(match.ENTRY,self.s['func_1516972C'],UNLINK,FALLBACK)or CALLBACK<=t<CALLBACK+256*0x100:a=(self.r[4],)
        else:raise AssertionError(('Unbounded animation provider',hex(t)))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==match.ENTRY:self.home=self.r[29]
    def hook(self,t):
        if CALLBACK<=t<CALLBACK+256*0x100:callback_effect(self.memory,replace(self.case,actor=self.calls[-1][1][0],index=(t-CALLBACK)//0x100),self.home,self.s)
        elif t in(self.s['func_1516972C'],PHYSICAL):release_effect(self.memory,self.calls[-1][1][0])
        else:raise AssertionError(('Unexpected disconnected lifecycle helper',hex(t)))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xA5A50002
def connected_code(rom):
    code={}
    for entry,offset,n in((RELEASE,0x196BDC,28),(UNLINK,0x196B8C,20),(FALLBACK,0x196CB4,8)):
        code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code
