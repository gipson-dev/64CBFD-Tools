from dataclasses import dataclass
from pathlib import Path
import itertools,sys
root=Path.cwd();sys.path.insert(0,str(root));out=root/'conker/build/game-camera-condition-150be850-screen'
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY=0x1509BE40;PACKET=0x800D2F60;COUNT=0x800D3840;TABLE=0x80088498;CALLBACK=0x15140000
SYMS=dict(D_800D2F60=PACKET,D_800D2F64=PACKET+4,D_800D3840=COUNT,D_80088498=TABLE)
@dataclass(frozen=True)
class Case: count:int;flags:int;key:int;mutate:int;phase:int=0
def arguments(c):return (c.count&0xffffffff,c.flags,c.key,*[0x12340000+i for i in range(10)])
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
 for base,n in ((PACKET,128),(TABLE,64),(COUNT,4)):m.update({base+i:(i*29+0x35)&255 for i in range(n)})
 put(m,COUNT,0x87654321)
 for i in range(15):put(m,TABLE+4*i,CALLBACK+4*i)
 return m
class Machine(FactoryOracle):
 def __init__(self,words,c,m):self.c=c;super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=arguments(c))
 def record_call(self,target):
  a=tuple(self.arguments(3));self.calls.append((target,a,read(self.memory,COUNT),tuple(read(self.memory,PACKET+4*i) for i in range(2+max(0,self.c.count)))))
 def hook(self,target):
  if self.c.mutate:put(self.memory,COUNT,0xabcddcba);put(self.memory,PACKET+4,0x76543210)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010;self.r[2]=0x89abcdef
def public(m):return {a:b for a,b in m.items() if not STACK-512<=a<STACK+512}
def reference(c,m):
 m=m.copy();selector=c.flags&0xfff;index=((c.flags&0xf000)>>12)-1
 put(m,PACKET,selector);put(m,PACKET+4,c.key)
 for i in range(max(0,c.count)):put(m,PACKET+8+4*i,0x12340000+i)
 put(m,COUNT,c.count+2)
 call=(CALLBACK+4*index,(selector,c.key,PACKET),(c.count+2)&0xffffffff,tuple(read(m,PACKET+4*i) for i in range(2+max(0,c.count))))
 if c.mutate:put(m,COUNT,0xabcddcba);put(m,PACKET+4,0x76543210)
 put(m,COUNT,0x87654321)
 return public(m),[call],0x89abcdef
programs=[bound_blob(*payload(out/x,'func_1509BE40'),SYMS) for x in ('query-retail.o','query-shape08.o','query-generic.o')]
assert programs[0]==programs[2]
for values in itertools.product((-2,-1,0,1,2,3,4,5,7), (0x1001,0x2fff,0xfabc), (0,0x7fffffff,0xffffffff), (0,1)):
 c=Case(*values);initial=fixture(c);expected=reference(c,initial)
 for p in programs:
  m=Machine(p,c,initial.copy()).run();actual=(public(m.memory),m.calls,m.r[2]);assert actual==expected,(c,actual[1:],expected[1:])
print('162 cases per retail, raw and guarded helper; count, selector, stack arguments and callback mutation modeled')
