"""Signed timer wrap, staged single-precision updates and ordered expiry providers."""
from dataclasses import dataclass
import itertools,math,struct
from tools.experiments import game_damped_record_lifetime_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
ENTRY,FREE,RELEASE=source.ENTRY,0x10004074,0x1516972C
ACTOR,OTHER,RECORDS,SECOND=0x220000,0x221000,0x230000,0x240000
CLOCK,REGISTRY,DEPTH,SLOTS=0x800BE9E4,0x8008B4A8,0x800DD190,0x800DD198
SCAN,ADAPTER,UNLINK,CALLBACK=0x151696DC,0x15169804,0x15168B10,0x17001234
INTMASK,FREE_HEAD=0x10024880,0x800380B8
FREE_TAIL,BEST_BLOCK,BEST_SIZE=0x800380BC,0x800380B0,0x8002AC30
u32=lambda n:n&0xFFFFFFFF
half=lambda n:((n&65535)^32768)-32768
signed=lambda n:(u32(n)^0x80000000)-0x80000000
def f32(v):
    try:return bits(v)
    except OverflowError:return 0xFF800000 if v<0 else 0x7F800000
add=lambda a,b:f32(floating(a)+floating(b))
sub=lambda a,b:f32(floating(a)-floating(b))
mul=lambda a,b:f32(floating(a)*floating(b))
def div(a,b):
    x,y=floating(a),floating(b)
    return f32(x/y if y else math.nan if not x else math.copysign(math.inf,x*math.copysign(1.,y)))
@dataclass(frozen=True)
class Case:
    age:int=0
    lifetime:int=10
    ticks:int=1
    pattern:int=0
    phase:int=0
    mutation:int=0
    connected:int=0
    payload:int=RECORDS
    category:int=6
    depth:int=2
    callback:int=0
    seed:int=0
def symbols():return dict(D_800BE9E4=CLOCK,func_10004074=FREE,func_1516972C=RELEASE)
def record_values(c,i):
    if c.pattern==0:return(0,10, bits(1.+i*.125),bits(2.-i*.25))
    if c.pattern==1:return(-5+i%3,3+i%4,bits(-2.+i*.25),bits(.5+i))
    if c.pattern==2:return(7,7,(0x7FA12345,0x7FC12345,0x7F800000,1)[i%4],0x80000000)
    if c.pattern==3:return((32766,-1,0,5)[i%4],(32767,0,-2,3)[i%4],bits(3.),bits(-.25))
    return(-1,9,(0,0x80000000,1,0x80000001,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345,bits(3.),bits(-3.),bits(.1))[i],bits(1.))
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;home=STACK+c.phase;m={home+i:(i*17+c.seed*13+165)&255 for i in range(-1024,512)}
    for a in(ACTOR,OTHER):
        m.update({a+i:(i*13+c.seed+90)&255 for i in range(0x200)});m[a]=c.category;put(m,a+8,a+0x400);put(m,a+0xA4,c.payload);put(m,a+0xA8,c.age,2);put(m,a+0xAA,c.lifetime,2)
    for p in(RECORDS,SECOND):
        m.update({p+i:(i*7+c.seed+89)&255 for i in range(-12,0x790)})
        for i in range(12):
            elapsed,duration,step,total=record_values(c,i);at=p+160*i;put(m,at+0x94,elapsed,2);put(m,at+0x96,duration,2);put(m,at+0x8C,step);put(m,at+0x90,total)
        put(m,p-12,0);put(m,p-8,0);put(m,p-4,0x01000780)
    put(m,s['D_800BE9E4'],c.ticks);put(m,FREE_HEAD,0);put(m,FREE_TAIL,0);put(m,BEST_BLOCK,0);put(m,BEST_SIZE,0x1000 if c.seed&1 else 0);m[DEPTH]=c.depth&255
    for i in range(4):put(m,SLOTS+4*i,ACTOR if i%2==0 else OTHER)
    for category in set((c.category,6,0,1,2)):
        put(m,REGISTRY+0x28+52*category,CALLBACK if c.callback else 0)
    return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-1024<=p<STACK+c.phase+512}
def observe(m,s):return(read(m,ACTOR+0xA4),half(read(m,ACTOR+0xA8,2)),half(read(m,ACTOR+0xAA,2)),read(m,s['D_800BE9E4'])if all(s['D_800BE9E4']+i in m for i in range(4))else None)
def effect(m,c,s,target,args,home):
    if target==s['func_10004074']:
        if c.mutation&1:put(m,ACTOR+0xA4,SECOND)
        if c.mutation&2:put(m,ACTOR+0xA8,-123,2);put(m,s['D_800BE9E4'],0x12345678)
        if c.mutation&4:put(m,home,OTHER)
    else:m[args[0]+31]^=0xA5
def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);calls=[];obs=[];home=STACK+c.phase
    def call(t,a):calls.append((t,tuple(map(u32,a))));obs.append(observe(m,s))
    if half(read(m,ACTOR+0xA8,2))<0:
        p=read(m,ACTOR+0xA4);put(m,home,ACTOR);call(s['func_10004074'],(p,))
        if c.connected&1:
            if p:
                call(INTMASK,(1,));m[p-4]=0;put(m,p,0);put(m,p+4,0);put(m,FREE_HEAD,p-12);put(m,FREE_TAIL,p-12)
                if read(m,p-4)>read(m,BEST_SIZE):put(m,BEST_SIZE,read(m,p-4));put(m,BEST_BLOCK,p-12)
                call(INTMASK,(0x300,))
        else:effect(m,c,s,s['func_10004074'],(p,),home)
        actor=read(m,home)if not c.connected&1 and c.mutation&4 else ACTOR;call(s['func_1516972C'],(actor,))
        if c.connected&2:
            call(SCAN,(actor,));depth=((m[DEPTH]^128)-128)
            for i in range(max(0,depth)):
                if read(m,SLOTS+4*i)==actor:put(m,SLOTS+4*i,read(m,actor+8))
            if m[actor]>=2:
                callback=read(m,REGISTRY+0x28+52*m[actor])
                if callback:call(callback,(actor,));effect(m,c,s,callback,(actor,),home)
                else:call(ADAPTER,(actor,));call(UNLINK,(actor,1));effect(m,c,s,UNLINK,(actor,),home)
        else:effect(m,c,s,s['func_1516972C'],(actor,),home)
        return m,calls,obs
    age=half(read(m,ACTOR+0xA8,2)+read(m,s['D_800BE9E4']));limit=half(read(m,ACTOR+0xAA,2));put(m,ACTOR+0xA8,age,2)
    if age>limit:put(m,ACTOR+0xA8,-10,2)
    elif age>=0:
        for offset in range(0,1920,160):
            p=u32(read(m,ACTOR+0xA4)+offset);elapsed,duration=(half(read(m,p+i,2))for i in(0x94,0x96))
            if elapsed<duration:
                put(m,p+0x94,elapsed+read(m,s['D_800BE9E4']),2);p=u32(read(m,ACTOR+0xA4)+offset);elapsed,duration=(half(read(m,p+i,2))for i in(0x94,0x96))
                if elapsed>duration:put(m,p+0x94,duration,2);p=u32(read(m,ACTOR+0xA4)+offset)
                elapsed,duration=(half(read(m,p+i,2))for i in(0x94,0x96));step,total=read(m,p+0x8C),read(m,p+0x90);amount=sub(step,div(mul(div(step,bits(3.)),f32(float(elapsed))),f32(float(duration))));put(m,p+0x90,add(total,amount))
    return m,calls,obs
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s;self.home=STACK+c.phase;self.observations=[];self.root_args=[]
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(ACTOR,)if arguments is None else arguments)
    def execute(self,w):
        op,fmt,fn,fs,ft,fd=w>>26,w>>21&31,w&63,w>>11&31,w>>16&31,w>>6&31
        if op==17 and fmt==16 and fn in(0,1,2,3):self.f[fd]=(add,sub,mul,div)[fn](self.f[fs],self.f[ft]);return
        if op==17 and fmt==20 and fn==32:self.f[fd]=f32(float(signed(self.f[fs])));return
        super().execute(w)
    def record_call(self,t):
        counts={ENTRY:1,self.s['func_10004074']:1,self.s['func_1516972C']:1,SCAN:1,ADAPTER:1,UNLINK:2,CALLBACK:1,INTMASK:1};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.root_args.append(a);self.home=self.r[29]
        else:self.observations.append(observe(self.memory,self.s))
    def hook(self,t):
        a=self.calls[-1][1];value=0x300 if t==INTMASK and a[0]==1 else 0xA5000002
        if t!=INTMASK:effect(self.memory,self.case,self.s,t,a,self.home)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value;self.hi,self.lo=0xA5000010,0xA5000011
def helper_code(rom,c):
    code={}
    for bit,entry,offset,n in((1,FREE,0x4074,119),(2,RELEASE,0x196BDC,28),(2,SCAN,0x196B8C,20),(2,ADAPTER,0x196CB4,8)):
        if c.connected&bit:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code
def cases():
    for age,lifetime,ticks,pattern in itertools.product((-32768,-10,-1,0,1,32760,32767),(-32768,-1,0,1,10,32767),(0,1,-1,2,20,65535,65536,0x7FFFFFFF,0x80000000),range(4)):yield Case(age=age,lifetime=lifetime,ticks=ticks,pattern=pattern)
    for mutation,age,phase,payload in itertools.product(range(8),(-32768,-1),(0,8),(0,RECORDS)):yield Case(age=age,mutation=mutation,phase=phase,payload=payload)
    for ticks,phase in itertools.product((0,1,-1,2,32767,65535),(0,8)):yield Case(ticks=ticks,pattern=4,phase=phase)
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of,m.observations,m.root_args)
