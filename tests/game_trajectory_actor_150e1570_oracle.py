import itertools,math,struct,sys
from pathlib import Path
from dataclasses import dataclass
from tools.experiments import game_trajectory_actor_150e1570_match as packet
root=packet.ROOT;out=packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x150E1570;TABLE=0x800CC2D0;PLAYER=0x800C3E78;SOURCE=0x40000;LOOK=0x15047390;TEST=0x15049440;EMIT=0x1505D1C4
S=dict(D_800CC2D0=TABLE,D_800C3E78=PLAYER,func_15047390=LOOK,func_15049440=TEST,func_1505D1C4=EMIT)
@dataclass(frozen=True)
class Case:
 phase:int=0;sourceSlot:int=0;excluded:int=0;flags:int=0;pattern:int=0

def score(i,p):return ((0,3,-2,7,-2)[(i+p)%5])
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-2048,2048)}
 for base,n in ((SOURCE,0x32c),(TABLE,25*0x32c),(PLAYER,1)):
  m.update({base+i:0 for i in range(n)})
 m[SOURCE+0x124]=c.sourceSlot;put(m,SOURCE+0x76,0xb135,2);m[PLAYER]=0xcd
 for i in range(25):
  a=TABLE+i*0x32c;put(m,a,0 if (c.flags&1 and i%4==0) else 1)
  m[a+0x1ca]=0 if (c.flags&2 and i%3==0) else 1
  m[a+0x125]=1 if (c.flags&4 and i%7==0) else 0
  for off,val in ((0x14,i+0.5),(0x18,100.0+i),(0x1c,-200.0-i)):put(m,a+off,bits(val))
  for off,val in ((0xd2,-i-1),(0xd4,i+2),(0xd6,i-10)):put(m,a+off,val&65535,2)
 return m
class Machine(FactoryOracle):
 def __init__(self,ws,c):
  self.c=c;self.scores=[]
  args=(SOURCE,bits(1.0),bits(2.0),bits(3.0),bits(4.0),bits(6.0),bits(3.0),c.excluded,18)
  super().__init__(ws,fixture(c),c,entry=ENTRY,s=S,arguments=args)
 def execute(self,w):
  if w>>26==17 and (w>>21&31)==16 and w&63==4:
   fs=w>>11&31;fd=w>>6&31;self.f[fd]=bits(math.sqrt(floating(self.f[fs])));return
  return super().execute(w)
 def record_call(self,t):
  if t in (LOOK,TEST):a=self.arguments(10)
  else:
   assert t==EMIT,hex(t);a=(self.f[12],self.f[14],self.r[6],self.r[7],*[self.get(self.r[29]+4*i,4) for i in range(4,8)])
  self.calls.append((t,tuple(a)))
 def hook(self,t):
  a=self.calls[-1][1];v=0
  if t==LOOK:
   for i in range(16):self.put(a[0]+4*i,bits(1.0 if i in (0,5,10,15) else 0.0),4)
  elif t==TEST:
   i=int(floating(a[1]));v=score(i,self.c.pattern)&0xffffffff;self.scores.append(i)
  else:
   assert t==EMIT;v=0xdeadbeef
   put(self.memory,SOURCE+0x76,0x6789,2)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=v

def external(m):return {a:b for a,b in m.items() if not STACK-2048<=a<STACK+2048}
def program(path):
 raw,refs=payload(path,'func_150E1570');return bound_blob(raw,refs,S)
