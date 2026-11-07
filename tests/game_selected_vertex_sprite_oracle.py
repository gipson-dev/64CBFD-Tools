"""Byte reference for descriptor fields, eight vertices and bounded allocation."""
from dataclasses import dataclass
import itertools,math,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
ENTRY,COLOR,CREATE,RANDOM,ALLOCATE,COPY=0x1518C57C,0x1516865C,0x15168800,0x150ADA20,0x15167A68,0x10023A10
ACTOR,OWNER,OTHER,POSITIONS,OUTPUT,PACKET,TEXTURES,HEADER,SEED=0x220000,0x230000,0x231000,0x240000,0x250000,0x260000,0x8008CA4C,0x270000,0x800885B0
u32=lambda n:n&0xFFFFFFFF
half=lambda n:((n&65535)^32768)-32768
byte=lambda n:((n&255)^128)-128
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
@dataclass(frozen=True)
class Case:
    index:int=0
    height:int=bits(17.75)
    random:int=0xFFFFFFFF
    phase:int=0
    seed:int=1
    mutation:int=0
    connected:int=0
    outcome:int=1
    width:int=47
    tall:int=31
    flags:int=0
    texture:int=18
    rgba:tuple=(255,129,17,0)
def symbols():return dict(func_150ADA20=RANDOM,func_1516865C=COLOR,func_15168800=CREATE,D_8008CA4C=TEXTURES)
def arguments(c):return(ACTOR,bits(3.25),bits(-4.5),bits(7.75),c.height,ACTOR+0x64)
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,512)}
    for p,n in((ACTOR,256),(OWNER,64),(OTHER,64),(OUTPUT-16,216),(PACKET-16,200),(HEADER,16)):m.update({p+i:(i*7+c.seed*11+90)&255 for i in range(n)})
    m[ACTOR+0x2D]=c.index&255;m[ACTOR+12]=201;m[ACTOR+1]=135;put(m,ACTOR+0x94,POSITIONS);put(m,ACTOR+0x98,OWNER)
    for i in range(-128,128):
        for j,v in enumerate((i*257+.75,-3.5,-i*131-.5,0.,1.)):put(m,POSITIONS+i*20+j*4,bits(v))
    for i in range(256):put(m,s['D_8008CA4C']+4*i,HEADER)
    put(m,HEADER+6,c.width,2);put(m,HEADER+8,c.tall,2);put(m,SEED,c.seed,8);put(m,PACKET+0x98,c.flags,2);m[PACKET+0xA0]=c.texture
    return m
def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+512}
def initialize(m,p,rgba,s):
    header=read(m,s['D_8008CA4C']+4*m[p+0xA0]);highV=half((read(m,header+8,2)+256)*32);highU=half((read(m,header+6,2)+256)*32);lowV=lowU=8192
    for i in range(8):
        put(m,p+16*i+6,0,2)
        for j,v in enumerate(rgba):m[p+16*i+12+j]=v&255
    flags=read(m,p+0x98,2)
    if flags&128:highV=8192;lowV=half((read(m,read(m,s['D_8008CA4C']+4*m[p+0xA0])+8,2)+256)*32)
    if flags&256:highU=8192;lowU=half((read(m,read(m,s['D_8008CA4C']+4*m[p+0xA0])+6,2)+256)*32)
    for i,(u,v)in enumerate(((highU,highV),(lowU,highV),(lowU,lowV),(highU,lowV))*2):put(m,p+16*i+8,u,2);put(m,p+16*i+10,v,2)
    for off in(0x88,0x9C,0x9E):put(m,p+off,0,2)
def effect(m,c,stage):
    if c.mutation&1 and stage==0:put(m,ACTOR+0x94,POSITIONS+20);m[ACTOR+0x2D]=127
    if c.mutation&2 and stage==1:m[ACTOR+12]=17;m[ACTOR+1]=255;put(m,ACTOR+0x98,OTHER)
    if c.mutation&4 and stage==2:put(m,ACTOR+0x98,OTHER)
def reference(initial,c=Case(),s=None,helper=False):
    s=symbols()if s is None else s;m=dict(initial);calls=[];packets=[]
    if helper:initialize(m,PACKET,c.rgba,s);return m,calls,packets,None
    home=STACK+c.phase;p=home-168;owner=read(m,ACTOR+0x98);positions=read(m,ACTOR+0x94);i=byte(m[ACTOR+0x2D]);x=math.trunc(floating(read(m,positions+i*20)));z=math.trunc(floating(read(m,positions+i*20+8)));height=math.trunc(floating(c.height))
    for off,v,n in((0x80,0,4),(0x8A,256,2),(0x8C,x,2),(0x8E,height,2),(0x90,z,2)):put(m,p+off,v,n)
    calls.append((s['func_150ADA20'],()))
    if c.connected&4:r=next_seed(read(m,SEED,8));put(m,SEED,r,8)
    else:r=c.random;effect(m,c,0)
    lifetime=u32(r)%21+35
    for off,v,n in((0x92,lifetime,2),(0x94,lifetime,2),(0x96,height,2),(0x98,12,2),(0xA0,18,1),(0xA1,0,1),(0xA2,255,1)):put(m,p+off,v,n)
    calls.append((s['func_1516865C'],(p,255,255,255,255)));initialize(m,p,(255,)*4,s)
    if not c.connected&1:effect(m,c,1)
    calls.append((s['func_15168800'],(p,m[ACTOR+12],m[ACTOR+1])));packets.append(data(m,p,168))
    if c.connected&2:calls.append((ALLOCATE,(14,m[ACTOR+1],184,1,m[ACTOR+12],1)))
    effect(m,c,2)
    if c.outcome:
        if c.connected&2:calls.append((COPY,(p,OUTPUT+16,168)))
        for i,b in enumerate(packets[-1]):m[OUTPUT+16+i]=b
    m[owner+32]=4
    return m,calls,packets,1
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,helper=False,arguments_override=None):
        self.s=symbols()if s is None else s;self.packets=[];self.helper=helper
        a=(PACKET,*c.rgba)if helper else arguments(c)
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=a if arguments_override is None else arguments_override)
    def execute(self,w):
        op,rs,rt,rd,shift,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;mask=(1<<64)-1
        if op==0 and fn==27:
            assert u32(self.r[rt]);self.lo,self.hi=divmod(u32(self.r[rs]),u32(self.r[rt]))
        elif op in(55,63):
            at=u32(self.r[rs]+half(w));assert at%8==0
            if op==55:self.r[rt]=self.get(at,8)
            else:self.put(at,self.r[rt],8)
        elif op==0 and fn in(37,38,56,58,60,62,63):
            v=self.r[rt]&mask
            if fn in(37,38):v=self.r[rs]|v if fn==37 else self.r[rs]^v
            elif fn in(56,60):v<<=shift+(32 if fn==60 else 0)
            elif fn in(58,62):v>>=shift+(32 if fn==62 else 0)
            else:v=(v if v<1<<63 else v-(1<<64))>>(shift+32)
            self.r[rd]=v&mask
        else:
            before=self.r[:];super().execute(w);dest=rt if op in(9,12,13,15,33,35,36,37)else rd if op==0 and fn in(0,2,3,33,35,36,42,43)else None
            for i,v in enumerate(before):
                if i!=dest and v>0xFFFFFFFF:self.r[i]=v
        self.r[0]=0
    def record_call(self,t):
        counts={ENTRY:6,self.s['func_150ADA20']:0,self.s['func_1516865C']:5,self.s['func_15168800']:3,ALLOCATE:6,COPY:3};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==self.s['func_15168800']:self.packets.append(data(self.memory,a[0],168))
    def hook(self,t):
        c=self.case;a=self.calls[-1][1];value=0xA5000002
        if t==self.s['func_150ADA20']:value=c.random;effect(self.memory,c,0)
        elif t==self.s['func_1516865C']:initialize(self.memory,a[0],a[1:],self.s);effect(self.memory,c,1)
        elif t==self.s['func_15168800']:
            effect(self.memory,c,2);value=OUTPUT if c.outcome else 0
            if value:
                for i,b in enumerate(data(self.memory,a[0],168)):self.memory[OUTPUT+16+i]=b
        elif t==ALLOCATE:effect(self.memory,c,2);value=OUTPUT if c.outcome else 0
        elif t==COPY:
            assert a[2]==168
            for i,b in enumerate(data(self.memory,a[0],a[2])):self.memory[a[1]+i]=b
        else:raise AssertionError(('unconnected helper',hex(t)))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def helper_code(rom,c,s=None,color_words=None):
    s=symbols()if s is None else s;code={}
    for bit,entry,off,n in((1,s['func_1516865C'],0x195B0C,105),(2,s['func_15168800'],0x195CB0,28),(4,s['func_150ADA20'],0xDAED0,18)):
        if c.connected&bit:
            w=color_words if bit==1 and color_words is not None else struct.unpack_from('>%dI'%n,rom,off);code.update(zip(range(entry,entry+4*n,4),w))
    return code
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of,m.packets)
def cases():
    for i in range(256):yield Case(index=i,random=u32(i*1664525+1013904223),height=bits((-1 if i&1 else 1)*(i*311+.75)),mutation=i%8,outcome=i&1,phase=8*(i&1))
    for r,h,outcome,mutation in itertools.product((0,1,20,21,22,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(-65536.75,-32768.5,-.75,0.,32767.75,65536.5),(0,1),(0,7)):yield Case(index=-3,random=r,height=bits(h),outcome=outcome,mutation=mutation)
    for connected,seed,outcome in itertools.product((1,2,3,4,7),SEEDS,(0,1)):yield Case(connected=connected,seed=seed,outcome=outcome)
