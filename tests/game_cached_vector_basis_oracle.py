"""Live cached flags, partial writes, scalar rounding and original vector helpers."""
from dataclasses import dataclass
import itertools,math,struct
from tools.experiments import game_cached_vector_basis_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
ENTRY,NORM,BASIS,CROSS=source.ENTRY,0x15145128,0x15146078,0x151450B4
STATE=0x220000
u32=lambda v:v&0xFFFFFFFF
def f32(v):
    try:return bits(v)
    except OverflowError:return 0xFF800000 if v<0 else 0x7F800000
add=lambda a,b:f32(floating(a)+floating(b))
sub=lambda a,b:f32(floating(a)-floating(b))
mul=lambda a,b:f32(floating(a)*floating(b))
def symbols():return dict(func_15145128=NORM,func_15146078=BASIS)
@dataclass(frozen=True)
class Case:
    flags:int=0
    vectors:tuple=(0x3F800000,0x40000000,0x40400000,0x40800000,0x40A00000,0x40C00000,0x40E00000,0x41000000,0x41100000)
    outcomes:tuple=(1,)
    mutation:int=0
    replacement:int=0xA0
    phase:int=0
    seed:int=0
    alias:int=0
    connected:int=0
def address(c):return(STATE,STACK+c.phase,STACK+c.phase+64)[c.alias]
def fixture(c=Case()):
    home=STACK+c.phase;m={home+i:(i*17+c.seed*13+165)&255 for i in range(-2048,1024)};p=address(c)
    for i in range(44):m[p+i]=(i*29+c.seed*11+90)&255
    m[p]=c.flags&255
    for i,v in enumerate(c.vectors):put(m,p+4+4*i,v)
    put(m,p+40,0x3F400000);return m
def data(m,p,n=44):return bytes(m[p+i]for i in range(n))
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-2048<=p<STACK+c.phase+1024}
def vec(m,p):return tuple(read(m,p+4*i)for i in range(3))
def store(m,p,vs):
    for i,v in enumerate(vs):put(m,p+4*i,v)
def outputs(n):return tuple(bits(v)for v in((n+1)*.125,-(n+2)*.25,(n+3)*.5))
def opaque(m,c,target,a,n):
    p=address(c)
    if target==NORM:store(m,a[1],outputs(n))
    else:store(m,a[1],outputs(n));store(m,a[2],outputs(n+1))
    if c.mutation&1:m[p]=c.replacement&255
    if c.mutation&2:store(m,p+4,outputs(n+2))
    if c.mutation&4:put(m,p+40,bits(n+.5))
    return u32(c.outcomes[(n-1)%len(c.outcomes)])
def normalize(m,a):
    values=vec(m,a[0]);length=add(add(mul(values[0],values[0]),mul(values[1],values[1])),mul(values[2],values[2]))
    if floating(length)==0:return 0
    length=f32(math.sqrt(floating(length)));inverse=f32(1./floating(length))
    if a[2]:put(m,a[2],length)
    if a[3]:put(m,a[3],inverse)
    for i in range(3):put(m,a[1]+4*i,mul(inverse,read(m,a[0]+4*i)))
    return 1
def cross(m,a):
    left,right=vec(m,a[0]),vec(m,a[1]);values=(sub(mul(left[1],right[2]),mul(left[2],right[1])),sub(mul(left[2],right[0]),mul(left[0],right[2])),sub(mul(left[0],right[1]),mul(left[1],right[0])))
    store(m,a[2],values)
def reference(initial,c=Case(),s=None,home=None):
    s=symbols()if s is None else s;home=STACK+c.phase if home is None else home;m=dict(initial);p=address(c);calls=[];obs=[];n=0
    def invoke(t,a):
        nonlocal n
        a=tuple(map(u32,a));calls.append((t,a));obs.append((t,vec(m,a[0]),data(m,p)))
        if t==s['func_15145128']and c.connected&1:return normalize(m,a)
        if t==CROSS:cross(m,a);return 0
        if t==s['func_15146078']and c.connected&2:
            d=vec(m,a[0]);zero=[floating(v)==0 for v in d]
            if all(zero):return 0
            if sum(zero)==2:
                axis=zero.index(False);basis=tuple(tuple(bits(float(i==j))for i in range(3))for j in range(3)if j!=axis);store(m,a[1],basis[0]);store(m,a[2],basis[1]);return 1
            i,j=(2,1)if zero[2]else(1,2);v=[bits(1.),0,0];v[i]=bits(1.);v[j]=sub(d[0]^0x80000000,f32(floating(d[i])/floating(d[j])));store(m,a[1],v)
            invoke(CROSS,(a[1],a[0],a[2]));invoke(CROSS,(a[2],a[0],a[1]));sp=home-32-72
            invoke(s['func_15145128'],(a[1],a[1],sp+0x34,sp+0x30));invoke(s['func_15145128'],(a[2],a[2],sp+0x34,sp+0x30));return 1
        n+=1;return opaque(m,c,NORM if t==s['func_15145128']else BASIS,a,n)
    if not m[p]&1:
        if not invoke(s['func_15145128'],(p+4,p+4,0,0)):return m,calls,obs,0
        values=tuple(mul(v,bits(1000.))for v in vec(m,p+4));m[p]|=1;store(m,p+4,values)
    if not m[p]&2:
        if not invoke(s['func_15146078'],(p+4,p+16,p+28)):return m,calls,obs,0
        m[p]|=6
    if not m[p]&4:
        if not invoke(s['func_15145128'],(p+16,p+16,0,0)):return m,calls,obs,0
        if not invoke(s['func_15145128'],(p+28,p+28,0,0)):return m,calls,obs,0
        m[p]|=4
    return m,calls,obs,1
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s;self.home=STACK+c.phase;self.n=0;self.observations=[];self.root_args=[]
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(address(c),)if arguments is None else arguments)
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63 in(2,4,7):
            rd,rt,fd=w>>11&31,w>>16&31,w>>6&31
            self.f[fd]=mul(self.f[rd],self.f[rt])if w&63==2 else f32(math.sqrt(floating(self.f[rd])))if w&63==4 else self.f[rd]^0x80000000
            return
        super().execute(w)
    def record_call(self,t):
        counts={ENTRY:1,self.s['func_15145128']:4,self.s['func_15146078']:3,CROSS:3};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==ENTRY:self.root_args.append(a);self.home=self.r[29]
        else:self.observations.append((t,vec(self.memory,a[0]),data(self.memory,address(self.case))))
    def hook(self,t):
        self.n+=1;a=self.calls[-1][1];value=opaque(self.memory,self.case,NORM if t==self.s['func_15145128']else BASIS,a,self.n)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def helper_code(rom,c):
    code={}
    for bit,entry,at,n in((1,NORM,0x1725D8,50),(2,BASIS,0x173528,148),(2,CROSS,0x172564,29)):
        if c.connected&bit:code.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,at)))
    return code
def cases():
    for flags in range(256):
        for outcomes in((1,),(0,),(1,0),(1,1,0),(0x80000000,0xFFFFFFFF,1)):yield Case(flags=flags,outcomes=outcomes,mutation=flags&7,replacement=flags^0x55,seed=flags%7)
    for flags,outcomes,mutation,replacement,phase in itertools.product(range(8),((1,),(0,),(1,0),(1,1,0)),range(8),(0,1,2,4,7,0x80,0xFF),(0,8)):yield Case(flags=flags,outcomes=outcomes,mutation=mutation,replacement=replacement,phase=phase)
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.all_accesses,m.visits,m.current_pc,m.delay_of,m.observations,m.root_args)
