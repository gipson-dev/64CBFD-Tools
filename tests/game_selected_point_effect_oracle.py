"""Point descriptor, original point helper and complete bounded consumer chain."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_selected_point_effect_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
ENTRY,POINT,CONSUMER=source.ENTRY,0x15146890,0x15150F90
RESOLVE,RNG32,RNGF,VECTOR,EMIT=0x15142314,0x150ADA20,0x150ADA68,0x15143794,0x1518A3C0
ACTOR,OTHER,MARK,TABLE=0x220000,0x230000,0x240000,0x8008A0B4
CONSTANTS=tuple(0x800A5708+4*i for i in range(6))
DEFAULT=(0x3CCCCCCC,0x3CA30553,0x40FF3B65,0xBECE5605,0x3E916873,0x3F741BDA)
FIXED={0:(4,5),4:(4,22),0x1C:(2,0),0x1E:(2,255),0x20:(2,-20),0x22:(2,14),0x24:(4,0x40C00000),0x28:(4,0x40400000),0x3C:(1,3),0x3E:(2,25),0x40:(2,25)}
GLOBAL_FIELDS=(0x14,0x18,0x2C,0x30,0x34,0x38)
HOLES=(0x3D,0x42,0x43)
PATTERNS=(0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x3F800000,0xBF800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7F812345)
u32=lambda v:v&0xFFFFFFFF
s16=lambda v:((v&65535)^32768)-32768
def symbols():return dict(func_15146890=POINT,func_15150F90=CONSUMER,**{'D_%08X'%a:a for a in CONSTANTS})
@dataclass(frozen=True)
class Case:
    active:int=0x250000
    context:int=1
    unused:int=85
    point:tuple=(0x3FA00000,0xC0200000,0x40700000)
    constants:tuple=DEFAULT
    mutation:int=0
    fill:bool=True
    answer:int=1
    connected:int=0
    random:int=0
    emit_mutation:int=0
    phase:int=0
    seed:int=0
    alias:int=0
def addresses(c,s=None):
    home=STACK+c.phase
    return(ACTOR,home-12-0x1D4,ACTOR,ACTOR)[c.alias]
def args(c,s=None):return(addresses(c,s),u32(c.context),u32(c.unused))
def descriptor(home):return home-80
def position(home):return home-12
def constants(c,s):
    vals=[s['D_%08X'%a]for a in CONSTANTS]
    if c.alias==2:vals[0]=STACK+c.phase-12
    if c.alias==3:vals[0]=STACK+c.phase+8
    return vals
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;o=addresses(c,s);home=STACK+c.phase;m={home+i:(i*17+c.seed*13+165)&255 for i in range(-2048,1024)}
    for base in(ACTOR,OTHER,0x250000,MARK):m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(0x340)})
    for a,v in zip(constants(c,s),c.constants):put(m,a,v)
    put(m,o+0x1D4,c.active);put(m,MARK,0)
    return m
def packet(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-2048<=p<STACK+c.phase+1024}
def helper_effect(m,c,s,home):
    if c.mutation&1:
        for i,a in enumerate(constants(c,s)):put(m,a,bits((i+1)*.125))
    if c.mutation&2:put(m,addresses(c,s)+0x1D4,0)
    if c.mutation&4:
        for i,v in enumerate((OTHER,0x123456FF,0xFEDCBA98)):put(m,home+4*i,v)
def fill(m,p,c):
    for i,v in enumerate(c.point):put(m,p+4*i,v)
def float32(op,a,b):return bits(op(floating(a),floating(b)))
add=lambda a,b:float32(lambda x,y:x+y,a,b)
mul=lambda a,b:float32(lambda x,y:x*y,a,b)
sub=lambda a,b:float32(lambda x,y:x-y,a,b)
def random32(c,n):return(0,1,0xFFFFFFFF,0x80000000,0x12345678,22)[(n+c.random)%6]
def randomf(c,n):return bits((0.,.25,.5,.75,.875)[(n+c.random)%5])
def vector_values(a,b,speed):return(bits(s16(a)*.5),bits(s16(b)*.25),speed)
def emit_effect(m,c,p,ordinal):
    put(m,MARK,ordinal)
    if c.emit_mutation&1:put(m,p,0);put(m,p+4,0)
    if c.emit_mutation&2:put(m,p+0x2C,bits(2.));put(m,p+8,bits(ordinal*.5))
    if c.emit_mutation&4:m[p+0x3C]=7;put(m,p+0x3E,8,2);put(m,p+0x40,3,2)
def consume(m,c,home,calls,emits):
    p=descriptor(home);sp=home-104-200;nr=nf=0;doubled=add(read(m,p+0x2C),read(m,p+0x2C))
    def ri():
        nonlocal nr
        calls.append((RNG32,()));v=random32(c,nr);nr+=1;return v
    def rf():
        nonlocal nf
        calls.append((RNGF,()));v=randomf(c,nf);nf+=1;return v
    count=u32(read(m,p)+ri()%u32(read(m,p+4)+1))
    for ordinal in range(count):
        rot=tuple(mul(rf(),bits(360.))for _ in range(3));a,b=ri(),ri();speed=add(mul(rf(),read(m,p+0x28)),read(m,p+0x24));yaw=s16(a%(s16(read(m,p+0x1E,2))+1)+s16(read(m,p+0x1C,2)));pitch=s16(b%(s16(read(m,p+0x22,2))+1)+s16(read(m,p+0x20,2)))
        calls.append((VECTOR,(u32(yaw),u32(pitch),speed,sp+0x9C)));vel=vector_values(yaw,pitch,speed)
        jitter0=sub(mul(rf(),doubled),read(m,p+0x2C));jitter2=sub(mul(rf(),doubled),read(m,p+0x2C));first,second=rf(),rf();life=ri()
        scale=add(mul(first,read(m,p+0x18)),read(m,p+0x14));value=add(mul(second,read(m,p+0x34)),read(m,p+0x30));life=life%(s16(read(m,p+0x40,2))+1)+s16(read(m,p+0x3E,2));a=(p+8,sp+0xA8,scale,sp+0x9C,sp+0xBC,value,read(m,p+0x38),m[p+0x3C],u32(life),0,0,255,1);calls.append((EMIT,a))
        emits.append((packet(m,p+8,12),struct.pack('>3I',*rot),struct.pack('>3I',*vel),struct.pack('>3I',jitter0,0,jitter2)))
        emit_effect(m,c,p,ordinal+1)
def reference(initial,c=Case(),s=None,home=None):
    s=symbols()if s is None else s;m=dict(initial);home=STACK+c.phase if home is None else home;o=addresses(c,s);p=descriptor(home);q=position(home);calls=[];obs=[];emits=[]
    for i,v in enumerate(args(c,s)):put(m,home+4*i,v)
    if not read(m,o+0x1D4):return m,calls,obs,emits
    calls.append((s['func_15146890'],(q,o,0,c.context&255)));helper_effect(m,c,s,home)
    if c.connected&1:
        if c.context&255 in(1,2):calls.append((RESOLVE,(read(m,o+0x1D4),19 if c.context&255==1 else 23,q)));fill(m,q,c)
    elif c.fill:fill(m,q,c)
    for at,(n,v)in FIXED.items():put(m,p+at,v,n)
    raw=packet(m,q,12)
    for i,v in enumerate(raw):m[p+8+i]=v
    for at,a in zip(GLOBAL_FIELDS,constants(c,s)):put(m,p+at,read(m,a))
    calls.append((s['func_15150F90'],(p,0,255,1)));obs.append(packet(m,p,68))
    if c.connected&2:consume(m,c,home,calls,emits)
    else:put(m,MARK,1)
    return m,calls,obs,emits
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s;self.home=STACK+c.phase;self.root_args=[];self.observations=[];self.emits=[];self.nr=self.nf=self.ne=0
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=args(c,self.s)if arguments is None else arguments)
    def record_call(self,t):
        counts={ENTRY:3,self.s['func_15146890']:4,self.s['func_15150F90']:4,RESOLVE:3,RNG32:0,RNGF:0,VECTOR:4,EMIT:13};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.root_args.append(a);self.home=self.r[29]
        if t==self.s['func_15146890']:helper_effect(self.memory,self.case,self.s,self.home)
        if t==self.s['func_15150F90']:self.observations.append(packet(self.memory,a[0],68))
        if t==EMIT:self.emits.append(tuple(packet(self.memory,a[i],12)for i in(0,1,3,4)))
    def hook(self,t):
        c=self.case;a=self.calls[-1][1];value=0xD00DFEED;fv=None
        if t==self.s['func_15146890']:
            if c.fill:fill(self.memory,a[0],c)
            value=u32(c.answer)
        elif t==RESOLVE:fill(self.memory,a[2],c)
        elif t==self.s['func_15150F90']:put(self.memory,MARK,1)
        elif t==RNG32:value=random32(c,self.nr);self.nr+=1
        elif t==RNGF:fv=randomf(c,self.nf);self.nf+=1
        elif t==VECTOR:
            for i,v in enumerate(vector_values(a[0],a[1],a[2])):put(self.memory,a[3]+4*i,v)
        else:assert t==EMIT;self.ne+=1;emit_effect(self.memory,c,descriptor(self.home),self.ne)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
        if fv is not None:self.f[0]=fv
def helper_code(rom,c):
    code={}
    for bit,entry,offset,n in((1,POINT,0x173D40,56),(2,CONSUMER,0x17E440,155)):
        if c.connected&bit:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code
def cases():
    for context in range(256):yield Case(context=context,unused=u32(context*0x81010101),answer=context&1,mutation=context&3,seed=context%7)
    for active,context,unused,mutation,answer,phase in itertools.product((0,1,0x250000,0x80000000),(1,2,0x101,0xABCD00FF),(0,85,0x80000000,0xFFFFFFFF),(0,1,2,3),(0,1),(0,8)):
        yield Case(active=active,context=context,unused=unused,mutation=mutation,answer=answer,phase=phase)
    for v in PATTERNS:
        for field in range(9):
            point=list(Case.point);const=list(DEFAULT)
            if field<3:point[field]=v
            else:const[field-3]=v
            yield Case(point=tuple(point),constants=tuple(const))
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of,m.observations,m.emits,m.root_args)
