"""Independent actor flags/scalars and bounded variadic packet dispatch."""
from dataclasses import dataclass
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY,HELPER,ACTOR,ACTOR_SIZE=0x150B2340,0x1509BE40,0x30000,0x9A0
PACKET,COUNT,TABLE=0x800D2F60,0x800D3840,0x80088498
OFFSETS=(0x84,0x190,0x348,0x34C,0x374,0x5F0)
CALLBACKS=(0x1509C7C8,0x15099C14,0x1509ED74,0x150A04D8,0x1509FE0C,0x1509E6F0,0x1509F33C,0x1509DEC4,0x1509759C,0x1509E8A0,0x150A0374,0x1509F800,0,0x1509DBBC,0x1509E3DC)
u32=lambda n:n&0xFFFFFFFF

@dataclass(frozen=True)
class Case:
    actor:int=ACTOR
    results:tuple=(5,1,0,1,1)
    flags:int=0x81234567
    status:int=0xFEDCBA98
    seed:int=0
    mutation:int=0
    phase:int=0

def addr(c,offset):return u32(c.actor+offset)
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def observation(m,c):return tuple(read(m,addr(c,o))for o in OFFSETS)+(read(m,addr(c,0x100),1),read(m,addr(c,ACTOR_SIZE-1),1))

def fixture(c=Case()):
    m={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
    for i in range(ACTOR_SIZE):m[addr(c,i)]=(i*29+c.seed*17+90)&255
    for o,v in zip(OFFSETS,(c.flags,0x80000000,0x7FC01234,0xFF800000,0x3F800000,c.status)):put(m,addr(c,o),v)
    for i in range(16):put(m,PACKET+i*4,0xABCD0000+i)
    put(m,COUNT,0x87654321)
    for i,value in enumerate(CALLBACKS):put(m,TABLE+i*4,value)
    return m

def effect(m,c,stage):
    if c.mutation&1:
        put(m,addr(c,0x84),0x12340000^(stage*0x01000100)^c.seed)
        put(m,addr(c,0x5F0),0x80000000^(stage*0x00000101)^c.seed)
    if c.mutation&2:
        put(m,addr(c,0x100),c.seed+stage*17,1);put(m,addr(c,ACTOR_SIZE-1),c.seed^stage,1)
    if c.mutation&4:
        for i,o in enumerate(OFFSETS[1:5]):put(m,addr(c,o),0xFFC01234^(stage*0x100+i))

def reference(initial,c=Case(),connected=False):
    m=dict(initial);calls=[];snapshots=[];nested=[];packet_snaps=[]
    def call(*args):
        stage=len(calls);args=tuple(map(u32,args));calls.append((HELPER,args));snapshots.append(data(m,c.actor,ACTOR_SIZE))
        if connected:
            count,flags,key=args[:3];old=read(m,COUNT);put(m,PACKET,flags&0xFFF);put(m,PACKET+4,key)
            for i,v in enumerate(args[3:]):put(m,PACKET+8+i*4,v)
            put(m,COUNT,count+2);target=read(m,TABLE+((((flags&0xF000)>>12)-1)*4));nested.append((target,(flags&0xFFF,key,PACKET)));packet_snaps.append((read(m,COUNT),data(m,PACKET,64),data(m,c.actor,ACTOR_SIZE)))
        effect(m,c,stage)
        if connected:put(m,COUNT,old)
        return u32(c.results[stage])
    flags=call(0,0x2007,0xB7)|0x2000;enabled=call(0,flags,0xBC);blocker=call(0,0x2000,0xBB)
    if call(0,0x5043,0x1A):
        if call(0,0x5045,0x1A):put(m,addr(c,0x84),read(m,addr(c,0x84))|0x4000)
        put(m,addr(c,0x84),read(m,addr(c,0x84))|0x400000);put(m,addr(c,0x190),0)
    elif call(1,0x4030,6,0x2000):put(m,addr(c,0x190),0x436B0000)
    else:
        for o,v in((0x348,0x42E40000),(0x34C,0x42E40000),(0x374,0x43C00000),(0x190,0x42700000)):put(m,addr(c,o),v)
    v=read(m,addr(c,0x5F0));put(m,addr(c,0x5F0),v|0x100 if enabled and blocker!=0xFFFFFFFF else v&0xFFFFFEFF)
    return public(m),calls,snapshots,nested,packet_snaps

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,helper=HELPER,connected=None,arguments=None):
        self.helper=helper;self.snapshots=[];self.nested=[];self.packet_snaps=[]
        super().__init__(words,memory,c,entry=entry,s={'func_1509BE40':helper},connected=connected,arguments=(u32(c.actor),)if arguments is None else arguments)
    def record_call(self,t):
        if t==self.helper:
            n=self.arguments(1)[0];assert n in(0,1),n;a=tuple(map(u32,self.arguments(3+n)));self.calls.append((t,a));self.snapshots.append(data(self.memory,self.case.actor,ACTOR_SIZE))
        elif t in CALLBACKS:
            a=tuple(map(u32,self.arguments(3)));self.nested.append((t,a));self.packet_snaps.append((read(self.memory,COUNT),data(self.memory,PACKET,64),data(self.memory,self.case.actor,ACTOR_SIZE)))
        else:raise AssertionError(('Unbounded actor-scalar provider',hex(t)))
    def hook(self,t):
        stage=len(self.calls)-1;assert 0<=stage<5
        effect(self.memory,self.case,stage)
        for i in range(4):self.put(u32(self.r[29]+4*i),0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(self.case.results[stage])

def cases():
    for enabled,blocker,path,mutation,phase in itertools.product((0,1,0x80000000,0xFFFFFFFF),(0,1,0x80000000,0xFFFFFFFF),range(4),(0,1,2,7),(0,8)):
        seed=(enabled^blocker^path*67^mutation*19)&255;first=(0,0x2000,0x80002005,0xFFFFFFFF)[path]
        primary=(1,0x80000000,0,0)[path];last=(0,0xFFFFFFFF,0,0x80000000)[path]
        yield Case(results=(first,enabled,blocker,primary,last),flags=(0,0xFFFFFFFF,0x4000,0x80000001)[path],status=(0,0xFFFFFFFF,0x100,0x80000000)[mutation%4],seed=seed,mutation=mutation,phase=phase)
