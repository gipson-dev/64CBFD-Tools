"""Modeled MIPS execution for bounded randomized path-node writes."""
from dataclasses import dataclass
import itertools,math
from tools.experiments import game_script_150793d8_match as match
from tools.tests import test_game_point_interval_effect_match as g
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob

ENTRY=0x150793d8;RNG=0x150ada20;VECTOR=0x1505a184;PLAYER=0x800cc2d0;CURRENT=0x800d154c;NODES=0x800d2104;CMD=0x800d1890
ACTORS=(0x30000,0x60000);TABLE=0x50000;PATHS=(0x51000,0x52000);STACK=g.STACK;put,read=g.put,g.read
@dataclass(frozen=True)
class Case:
 x:int;z:int;dx:int;dz:int;actor:int;path:int;index:int;phase:int
 mode:int=0;amount:int=0;fcsr:int=0

def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
 for base in (PLAYER,*ACTORS):m.update({base+i:(i*13+91)&255 for i in range(0x340)})
 for path in PATHS:m.update({path+i:(i*5+17)&255 for i in range(64)})
 for i,path in enumerate(PATHS):put(m,TABLE+4*i,path)
 for a in ACTORS:put(m,a+0x13f,c.path,1)
 put(m,PLAYER+0x14,g.bits(c.x+(-.25 if c.x<0 else .25)));put(m,PLAYER+0x1c,g.bits(c.z+(-.25 if c.z<0 else .25)))
 put(m,CURRENT,ACTORS[c.actor^1]);put(m,NODES,TABLE);put(m,CMD,c.index^1,1)
 return m

def public(m):return {k:v for k,v in m.items() if not STACK-1024<=k<STACK+1024}
def reference(initial,c):
 m=dict(initial);x,z=c.x,c.z
 if x< -1180 or x>1180 or z< -1180 or z>1180:x=z=0
 x=max(-1200,min(1200,x+c.dx));z=max(-1200,min(1200,z+c.dz))
 put(m,CURRENT,ACTORS[c.actor]);put(m,CMD,c.index,1);dest=PATHS[c.path]+8*(c.index+1)
 put(m,dest,x&65535,2);put(m,dest+4,z&65535,2)
 return public(m)

class Oracle(g.Oracle):
 def __init__(self,code,c):
  self.case=c;super().__init__(code,fixture(c),c,entry=ENTRY)
 def execute(self,w):
  if w>>26==17 and (w>>21&31)==16 and (w&63)==13:
   src=w>>11&31;dest=w>>6&31;value=g.floating(self.f[src]);assert math.isfinite(value) and -(2**31)<=value<2**31
   self.f[dest]=g.u32(math.trunc(value));self.r[0]=0
  else:super().execute(w)
 def record_call(self,target):
  assert target in (RNG,VECTOR),hex(target)
  args=() if target==RNG else tuple(map(g.u32,self.arguments(6)))
  if target==VECTOR:assert args[:3]==(0xabcd,g.bits(550.),0)
  self.calls.append((target,args))
 def hook(self,target):
  if target==VECTOR:
   a=self.calls[-1][1];put(self.memory,a[3],g.bits(self.case.dx));put(self.memory,a[4],g.bits(self.case.dz));put(self.memory,a[5],g.bits(123.))
   put(self.memory,CURRENT,ACTORS[self.case.actor]);put(self.memory,CMD,self.case.index,1)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=0x1234abcd

def words(path,state):
 raw,refs=match.payload(path);return tuple(bound_blob(raw,refs,state['symbols']))
def run(state):
 _,padded=match.pad_both(state);codes=(state['raw_words'],state['retail_words'],words(padded,state))
 assert codes[1]==codes[2];count=0;visits=set()
 for x,z,dx,dz,actor,path,index,phase in itertools.product((-1181,-1180,0,1180,1181),(-1181,-1180,0,1180,1181),(-300,0,300),(-300,0,300),range(2),range(2),range(2),(0,8)):
  c=Case(x,z,dx,dz,actor,path,index,phase);expected=reference(fixture(c),c)
  for code in codes:
   m=Oracle(code,c).run();assert public(m.memory)==expected,c
   assert len(m.calls)==2 and [k for k,_ in m.calls]==[RNG,VECTOR] and m.r[29]==STACK+c.phase
   visits.update(m.visits)
  count+=1
 return dict(cases=count,bodies=len(codes),words_visited=len(visits),scope='bounded finite inputs; helper outputs and mutations modeled')
