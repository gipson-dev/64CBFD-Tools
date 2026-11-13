from dataclasses import dataclass
from pathlib import Path
import itertools,sys
from tools.experiments import game_extent_15149a94_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
NAME='func_15149A94';ENTRY=0x15149A94;ACTOR=0x30000;HELPER=0x1513F680
SYMS={'D_800A578C':0x800A578C,'D_800A5790':0x800A5790,'func_1513F680':HELPER}
@dataclass(frozen=True)
class Case: flags:int;timer:int;x:float;y:float;factor:float;mutation:int;phase:int=0
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)};m.update({ACTOR+i:(i*29+0x35)&255 for i in range(0x200)})
 for a,v in ((0x2c,c.x),(0x30,c.y),(0x118,4.0),(0x130,8.0),(0x154,c.factor)):put(m,ACTOR+a,bits(v))
 put(m,ACTOR+0x1c,c.timer&65535,2);put(m,ACTOR+0x58,0x12345679);m[ACTOR+0x74]=c.flags;m[ACTOR+0x70]=7;m[ACTOR+0x72]=9;m[ACTOR+0x73]=11;m[ACTOR+0x158]=22
 put(m,SYMS['D_800A578C'],bits(0.75));put(m,SYMS['D_800A5790'],bits(0.75));return m
class Machine(FactoryOracle):
 def __init__(self,words,c,m):self.c=c;super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(ACTOR,))
 def record_call(self,t):assert t==HELPER;self.calls.append((t,tuple(self.arguments(5))))
 def hook(self,t):
  a=self.calls[-1][1]
  for i,v in enumerate(a[1:]):self.memory[a[0]+0x70+i]=v&255
  if self.c.mutation:put(self.memory,ACTOR+0x1c,3,2);self.memory[ACTOR+0x158]=23
  for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010
def reference(initial,c):
 m=initial.copy();calls=[];complete=1
 for flag,dest,target,factor in ((2,0x2c,0x118,'D_800A578C'),(8,0x30,0x130,'D_800A5790')):
  if not m[ACTOR+0x74]&flag:
   old=floating(read(m,ACTOR+dest));goal=floating(read(m,ACTOR+target));scale=floating(read(m,ACTOR+0x154))
   diff=floating(bits(goal-old));step=floating(bits(diff*scale));put(m,ACTOR+dest,bits(old+step))
   if floating(bits(goal*floating(read(m,SYMS[factor]))))<floating(read(m,ACTOR+dest)):m[ACTOR+0x74]|=flag
   else:complete=0
 def call(param):
  a=(ACTOR,m[ACTOR+0x70],param,m[ACTOR+0x72],m[ACTOR+0x73]);calls.append((HELPER,a))
  for i,v in enumerate(a[1:]):m[ACTOR+0x70+i]=v&255
  if c.mutation:put(m,ACTOR+0x1c,3,2);m[ACTOR+0x158]=23
 if complete:call(13)
 timer=read(m,ACTOR+0x1c,2);timer=timer-65536 if timer&32768 else timer
 if timer<5:
  call(m[ACTOR+0x158]);put(m,ACTOR+0x1c,100,2);put(m,ACTOR+0x58,read(m,ACTOR+0x58)&~1)
 return {a:b for a,b in m.items() if not STACK-512<=a<STACK+512},calls
def run():
 progs=[bound_blob(*payload(out/x,NAME),SYMS) for x in ('retail.o','after.o','generated.o','generic.o')];assert all(p==progs[0] for p in progs)
 count=0
 for flags,timer,x,y,factor,mutation in itertools.product((0,2,8,10),(-1,4,5,100),(0.,3.,4.),(0.,6.,8.),(0.,0.5,1.),(0,1)):
  c=Case(flags,timer,x,y,factor,mutation);initial=fixture(c);expected=reference(initial,c)
  for p in progs:
   machine=Machine(p,c,initial.copy()).run();actual=({a:b for a,b in machine.memory.items() if not STACK-512<=a<STACK+512},machine.calls)
   assert actual==expected,(c,actual[1],expected[1]);assert machine.r[2]==1
  count+=1
 print(count,'cases per stream across retail, raw C, and both padders passed independent state/call model')
if __name__=='__main__':run()
