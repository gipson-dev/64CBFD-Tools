from pathlib import Path
from dataclasses import dataclass
import itertools,struct,subprocess,sys
from tools.experiments import game_state_trajectory_15072f10_match as packet
root=packet.ROOT;out=packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY=0x15072f10;VECTOR=0x1505a184;SUBMIT=0x150e1570;CURRENT=0x800d154c;SCALE=0x8009a094;PLAYER=0x800c3e78;ACTOR=0x30000;ACTOR2=0x32000;STATE=0x35000;STATE2=0x36000;MARK=0x37000
SYMS=dict(D_800D154C=CURRENT,D_8009A094=SCALE,D_800C3E78=PLAYER,func_1505A184=VECTOR,func_150E1570=SUBMIT)
@dataclass(frozen=True)
class Case:
 phase:int=0;pitch:int=0;timer:int=0;angle:int=0;offset:int=0;mutation:int=0;output:int=0

def words(path):
 raw,refs=payload(path,'func_15072F10');return bound_blob(raw,refs,SYMS)
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-2048,2048)}
 for base,n in ((ACTOR,0x400),(ACTOR2,0x400),(STATE,0x100),(STATE2,0x100),(CURRENT,4),(SCALE,4),(PLAYER,1),(MARK,8)):
  m.update({base+i:(i*29+0x5a)&255 for i in range(n)})
 for actor,state,k in ((ACTOR,STATE,0),(ACTOR2,STATE2,1)):
  put(m,actor+0x31c,state);m[actor+0x1d1]=(c.pitch+k)&255;put(m,actor+0x7a,c.angle+k*13,2);put(m,state+0x12,c.offset-k*9,2);put(m,state+0x24,c.timer+k,2);put(m,actor+0xd6,-30+k*50,2)
  for off,val in zip((0x14,0x18,0x1c),((100.5,-25.25,300.75)if not k else(-200.5,75.25,-400.75))):put(m,actor+off,bits(val))
 put(m,CURRENT,ACTOR);put(m,SCALE,bits(.25));m[PLAYER]=0xd2;return m
class Machine(FactoryOracle):
 def __init__(self,ws,c,m):self.c=c;super().__init__(ws,m,c,entry=ENTRY,s=SYMS,arguments=(0x12345678,));self.draw=0
 def record_call(self,t):
  assert t in (VECTOR,SUBMIT),hex(t);self.calls.append((t,tuple(self.arguments(6 if t==VECTOR else 9))))
 def hook(self,t):
  a=self.calls[-1][1]
  if t==VECTOR:
   x,z,y=((11.25,-22.5,33.75)if not self.c.output else(-1.25,2.5,-3.75))
   for ptr,value in ((a[5],y),(a[3],x),(a[4],z)):put(self.memory,ptr,bits(value))
   if self.c.mutation&1:put(self.memory,CURRENT,ACTOR2)
   if self.c.mutation&2:put(self.memory,SCALE,bits(-.5))
   if self.c.mutation&4:self.memory[PLAYER]=0x6c
   value=0x99887766
  else:put(self.memory,MARK,0x13579bdf);value=0xdeadbeef
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value

def public(m,c):return {a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+2048}
def programs():return [words(out/x) for x in ('retail.o','after.o','generated.o','generic.o')]
