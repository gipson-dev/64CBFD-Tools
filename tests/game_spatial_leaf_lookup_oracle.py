"""Read-only spatial graph contract, word wrapping and relative-offset fixtures."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_spatial_leaf_lookup_match as source
from tools.experiments import game_spatial_leaf_lookup_candidates as candidate
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
BASE,ROOT=0x30000,0x30040
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
half=lambda n:((n&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
    x:int=0
    z:int=0
    plan:int=1
    radius:int=10
    cx:int=0
    cz:int=0
    phase:int=0

@dataclass(frozen=True)
class Node:
    next:int=0
    radius:int=10
    x:int=0
    z:int=0
    child:int=0

def symbols():return {'D_800DBE48':0x800DBE48}

def nodes(c):
    n=Node(radius=c.radius,x=half(c.cx),z=half(c.cz));other=Node(radius=65535,x=half(c.cx+20),z=half(c.cz-20))
    plans={
      0:{},1:{ROOT:n},
      2:{ROOT:Node(0,c.radius,n.x,n.z,32),ROOT+32:n},
      3:{ROOT:Node(32,c.radius,n.x,n.z,-64),BASE:n,ROOT+32:other},
      4:{ROOT:Node(32,c.radius,n.x,n.z),ROOT+32:n},
      5:{ROOT:Node(-32,c.radius,n.x,n.z,32),ROOT-32:other,ROOT+32:Node(32,0,half(c.cx+1),half(c.cz+1)),ROOT+64:n},
      6:{ROOT:Node(0,65535,n.x,n.z,16),ROOT+16:Node(32,c.radius,n.x,n.z,16),ROOT+32:n,ROOT+48:other},
      7:{ROOT:Node(-32,0,half(c.cx+1),half(c.cz+1)),ROOT-32:n},
    }
    return plans[c.plan]

def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+i:(i*17+165)&255 for i in range(-64,128)}
    m.update({BASE+i:(i*29+123)&255 for i in range(160)})
    for p,n in nodes(c).items():
        for off,value in((4,n.next),(6,n.radius),(8,n.x),(10,n.z),(12,n.child)):put(m,p+off,value,2)
    put(m,s['D_800DBE48'],ROOT if c.plan else 0);return m

def inside(value,center,radius):
    delta=u32(value-half(center));magnitude=u32(-delta)if delta&0x80000000 else delta
    return signed(magnitude)<=radius

def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;p=read(initial,s['D_800DBE48']);visited=set()
    while p:
        if p in visited:raise ValueError('Cyclic spatial test fixture')
        visited.add(p);child=half(read(initial,p+12,2));radius=read(initial,p+6,2)
        hit=inside(c.x,read(initial,p+8,2),radius)and inside(c.z,read(initial,p+10,2),radius)
        if hit and not child:return p
        offset=child if hit else half(read(initial,p+4,2))
        p=u32(p+offset)if offset else 0
    return 0

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(u32(c.x),u32(c.z))if arguments is None else arguments)
    def record_call(self,target):
        if target!=source.ENTRY:raise AssertionError(('Unexpected spatial lookup call',hex(target)))
        a=tuple(map(u32,self.arguments(2)));self.calls.append((target,a));self.events.append(('CALL',target,a))
    def hook(self,target):raise AssertionError(('Unbounded spatial lookup helper',hex(target)))

def bound(obj,s):
    raw,bindings=source.function_blob(obj);words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
    for at,rows in bindings.items():
        if len(rows)!=1:raise ValueError('Spatial lookup binding count changed')
        kind,name=rows[0];value=s[name]
        if kind=='R_MIPS_HI16':part=(value+0x8000)>>16&65535
        elif kind=='R_MIPS_LO16':part=value&65535
        else:raise ValueError('Spatial lookup binding kind changed')
        words[at//4]=(words[at//4]&0xFFFF0000)|part
    return words

def cases():
    for plan,radius,center,phase in itertools.product(range(8),(0,1,10,32767,65535),(-32768,0,32767),(0,8)):
        for delta,axis in itertools.product((-radius-1,-radius,-1,0,1,radius,radius+1,0x80000000,0x7FFFFFFF),(0,1)):
            x=u32(center+(delta if axis==0 else 0));z=u32(-center+(delta if axis else 0))
            yield Case(x,z,plan,radius,center,half(-center),phase)

def controls():
    b=candidate.SELECTED
    return dict(exclusive=b.replace('<= *(u16 *)','< *(u16 *)'),signed_radius=b.replace('<= *(u16 *)','<= *(s16 *)'),
        unsigned_center=b.replace('(u32)*(s16 *)(node + 8)','(u32)*(u16 *)(node + 8)'),
        unsigned_child=b.replace('child = *(s16 *)','child = *(u16 *)'),unsigned_next=b.replace('offset = *(s16 *)','offset = *(u16 *)'),
        wrong_axis=b.replace('(u32)z -','(u32)x -'),first_leaf=b.replace('return node;','return NULL;'),
        wrap_abs=b.replace('(s32)(0u - (u32)(value))','((value) == (s32)0x80000000u ? 0x7FFFFFFF : (s32)(0u - (u32)(value)))'))
