from dataclasses import dataclass
from pathlib import Path
import itertools,sys
root=Path.cwd();sys.path.insert(0,str(root));out=root/'conker/build/game-query-list-1509dbbc-screen'
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY=0x1509DBBC;ROWS=0x800DCE50;TABLE=0x800A6060;NODES=0x60000;PACKET=0x30000
SYMS=dict(D_800DCE50=ROWS,D_800A6060=TABLE,func_150E36BC=0x150E36BC)
@dataclass(frozen=True)
class Case: key:int;mode:int;scenario:int;phase:int=0
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
 for base,n in ((ROWS,0x340),(TABLE,12),(NODES,18*0x60),(PACKET,16)):m.update({base+i:0 for i in range(n)})
 for i,value in enumerate((54,76,91)):put(m,TABLE+4*i,value)
 for slot in range(6):
  row,column=divmod(slot,3);cell=ROWS+row*0x1a0+(54,76,91)[column]*4
  if c.scenario==0 or c.scenario in range(1,7) and slot!=c.scenario-1:continue
  count=3 if c.scenario>=7 else 1
  put(m,cell,NODES+slot*0x120)
  for j in range(count):
   node=NODES+slot*0x120+j*0x60;put(m,node+8,node+0x60 if j+1<count else 0)
   m[node+0x48]=2 if c.scenario in range(1,7) or c.scenario==7 and slot==5 and j==2 else 1
 return m
class Machine(FactoryOracle):
 def __init__(self,words,c,m):self.c=c;super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(c.key&0xffffffff,c.mode&0xffffffff,PACKET))
 def record_call(self,target):raise AssertionError(('unexpected helper call',hex(target),self.c))
 def hook(self,target):raise AssertionError(('unexpected helper',hex(target)))
def public(m):return {a:b for a,b in m.items() if not STACK-512<=a<STACK+512}
def reference(c,m):return public(m),0 if c.key==25 and c.mode==4 and c.scenario in range(1,8) else 1 if c.key==25 and c.mode==4 else 4
programs=[bound_blob(*payload(out/x,'func_1509DBBC'),SYMS) for x in ('retail.o','typedshape06.o','generated.o','generic.o')];assert programs[0]==programs[2]==programs[3]
count=0;visited=set()
for vals in itertools.product((0,4,5,6,25,26,-1,0x7fffffff),(-1,0,1,4,5),range(9),(0,8)):
 c=Case(*vals);initial=fixture(c);expected=reference(c,initial)
 for index,p in enumerate(programs):
  try:m=Machine(p,c,initial.copy()).run()
  except Exception as exc:raise AssertionError((c,index,exc)) from exc
  assert (public(m.memory),m.r[2])==expected,(c,index)
  if p==programs[0]:visited.update(m.visits)
 count+=1
assert all(pc not in visited for pc in range(0x1509dccc,0x1509dcf8,4))
print(count,'guest cases per stream, including six list slots, multi-node paths and all key/mode branches; coordinate helper path unreachable in this corpus')
