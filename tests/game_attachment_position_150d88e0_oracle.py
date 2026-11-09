"""Attachment positions: defined C selectors and literal default-stack inputs."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
ENTRY,MATRIX,OWNER,OUTPUT,ALT_OUTPUT,MATRICES,ALT_MATRICES=0x150D88E0,0x150A7960,0x30000,0x50000,0x51000,0x70000,0x71000
OFFSETS={3:(18,0xC0E00000,0x41F00000),4:(21,0xC0800000,0x420C0000),5:(15,0x40A00000,0x41A00000),6:(24,0x40A00000,0x41F80000)}
u32=lambda v:v&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    selector:int=3
    owner:int=OWNER
    output:int=OUTPUT
    base:int=MATRICES
    seed:int=0
    mutation:int=0
    phase:int=0
    stale_joint:int=7
    stale_x:int=0x3F800001
    stale_z:int=0xC0700000
    results:tuple=(0x3FA00000,0xC0200000,0x40700000)
    connected:bool=False

def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def seed_locals(m,c,home=None):
    home=STACK+c.phase if home is None else home
    for off,v in((-4,c.stale_joint),(-8,c.stale_x),(-16,c.stale_z)):put(m,u32(home+off),v)
def fixture(c=Case()):
    m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2048)}
    for base,size in((c.owner,0x240),(OUTPUT-16,48),(ALT_OUTPUT-16,48)):
        for i in range(size):m[u32(base+i)]=(i*29+c.seed*17+90)&255
    for base in(MATRICES,ALT_MATRICES):
        for j in range(32):
            for k in range(16):
                value=((j*7+k*3+c.seed)%19-9)*0.25
                if 12<=k<=14:value=j*4+(k-12)*3-c.seed*0.125
                put(m,base+j*64+k*4,bits(value))
    put(m,u32(c.owner+0x1D4),c.base);put(m,u32(c.owner+0x180),0x41280000)
    put(m,0x800A0B30,0x3DCCCCCD);put(m,0x800A0B34,0x3CF5C28F);seed_locals(m,c)
    return m

def transform(m,address,x,y,z):
    result=[]
    for axis in range(3):
        a,b,c,d=(read(m,u32(address+axis*4+k*16))for k in range(4))
        left=bits(floating(bits(floating(a)*floating(x)))+floating(bits(floating(b)*floating(y))))
        right=bits(floating(bits(floating(c)*floating(z)))+floating(d))
        result.append(bits(floating(left)+floating(right)))
    return tuple(result)

def reference(initial,c=Case(),home=None,helper=MATRIX):
    home=STACK+c.phase if home is None else home;m=dict(initial)
    put(m,home,c.output);put(m,home+4,c.owner);put(m,home+8,c.selector)
    joint,x,z=OFFSETS[c.selector&255]if c.selector&255 in OFFSETS else(read(m,home-4),read(m,home-8),read(m,home-16))
    if c.selector&255 in OFFSETS:
        for off,v in((-4,joint),(-8,x),(-16,z)):put(m,home+off,v)
    put(m,home-12,0)
    address=u32(read(m,u32(c.owner+0x1D4))+u32(joint<<6));args=(address,x,0,z,home-8,home-12,home-16)
    snapshot=(args,tuple(read(m,p)for p in args[4:]),data(m,c.output,12))
    results=transform(m,address,x,0,z)if c.connected else c.results
    for p,v in zip(args[4:],results):put(m,p,v)
    if not c.connected:
        if c.mutation&1:put(m,u32(c.owner+0x1D4),ALT_MATRICES)
        if c.mutation&2:put(m,home,ALT_OUTPUT)
        if c.mutation&4:put(m,home-8,read(m,home-8)^0x00400000);put(m,home-12,read(m,home-12)^0x80000000)
        if c.mutation&8:put(m,u32(c.owner+0x180),0xC0B00000)
    destination=read(m,home)
    # Reload each source immediately before its ordered destination store.
    for source,target in((home-8,destination),(home-12,u32(destination+4)),(home-16,u32(destination+8))):put(m,target,read(m,source))
    return m,[(helper,args)],[snapshot],1,destination

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,helper=MATRIX,connected=None,arguments=None):
        self.helper=helper;self.snapshots=[];self.position_home=STACK+c.phase
        super().__init__(words,memory,c,entry=entry,s={'func_150A7960':helper},connected=connected,arguments=(c.output,c.owner,u32(c.selector))if arguments is None else arguments)
        self.before=self.r[:];self.before_f=self.f[:]
    def record_call(self,t):
        assert t==self.helper,hex(t);a=tuple(map(u32,self.arguments(7)));self.calls.append((t,a));self.snapshots.append((a,tuple(read(self.memory,p)for p in a[4:]),data(self.memory,self.case.output,12)))
    def hook(self,t):
        c=self.case;a=self.calls[-1][1]
        for p,v in zip(a[4:],c.results):put(self.memory,p,v)
        if c.mutation&1:put(self.memory,u32(c.owner+0x1D4),ALT_MATRICES)
        if c.mutation&2:put(self.memory,self.position_home,ALT_OUTPUT)
        if c.mutation&4:put(self.memory,a[4],read(self.memory,a[4])^0x00400000);put(self.memory,a[5],read(self.memory,a[5])^0x80000000)
        if c.mutation&8:put(self.memory,u32(c.owner+0x180),0xC0B00000)
        for i in range(4):self.put(u32(self.r[29]+i*4),0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF

def cases():
    for selector,phase,seed in itertools.product(range(256),(0,8),(0,1)):
        yield Case(selector=selector,phase=phase,seed=seed,mutation=(selector^seed)&15,stale_joint=(selector+seed)%32,stale_x=0x80000000 if seed else 0x3F800001,results=(0x7FC01234 if selector&1 else 0x80000000,0x3FA00000,0xC0700000))
    for selector,mutation,phase in itertools.product((3,4,5,6,0xAABBCC03,0x80000006,0xFFFFFFFF),range(16),(0,8)):
        yield Case(selector=selector,mutation=mutation,phase=phase,seed=mutation,stale_joint=0x81234567,stale_x=0x7FC01234,stale_z=0x80000000)
