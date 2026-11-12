"""Bounded finite-float reference for the resource motion callback."""
from dataclasses import dataclass

from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY,OBJ,TIME,INV,TICKS=0x15157AA8,0x30000,0x800BE9A4,0x800BE9A8,0x800BE9E4
@dataclass(frozen=True)
class Case:
 flags:int;ticks:int;time:int;inverse:int;pattern:int;phase:int
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-2048,512)}
 m.update({OBJ+i:(i*13+0x5a)&255 for i in range(-16,0x170)})
 for addr in (TIME,INV,TICKS):m.update({addr+i:0 for i in range(4)})
 for off,vals in ((0x54,(10.0,-5.0,3.0)),(0x120,(2.0,3.0,-4.0)),
                  (0x130,(2.5,-3.0,1.5)),(0x13c,(1.0,-0.5,0.25))):
  for i,v in enumerate(vals):put(m,OBJ+off+i*4,bits(v+c.pattern*.125))
 put(m,OBJ+0x148,bits(-.75));put(m,OBJ+0x14c,bits((0.5,1.0)[c.pattern%2]));m[OBJ+0x150]=c.flags
 put(m,TIME,c.time);put(m,INV,c.inverse);put(m,TICKS,c.ticks)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-2048<=a<STACK+512}
def add(a,b):return bits(floating(a)+floating(b))
def sub(a,b):return bits(floating(a)-floating(b))
def mul(a,b):return bits(floating(a)*floating(b))
def reference(c):
 m=fixture(c);flag=m[OBJ+0x150]
 if flag&1:
  previous=[read(m,OBJ+0x130+i*4) for i in range(3)]
  if flag&8:
   for _ in range(c.ticks):
    put(m,OBJ+0x130,mul(read(m,OBJ+0x130),read(m,OBJ+0x14c)))
    put(m,OBJ+0x138,mul(read(m,OBJ+0x138),read(m,OBJ+0x14c)))
  accelY=read(m,OBJ+0x148) if flag&4 else bits(0.0)
  if flag&4:put(m,OBJ+0x134,add(read(m,OBJ+0x134),mul(accelY,read(m,TIME))))
  accelX=mul(sub(read(m,OBJ+0x130),previous[0]),read(m,INV))
  accelZ=mul(sub(read(m,OBJ+0x138),previous[2]),read(m,INV))
  for i,accel in enumerate((accelX,accelY,accelZ)):
   inner=add(previous[i],mul(mul(bits(.5),accel),read(m,TIME)))
   put(m,OBJ+0x54+i*4,add(read(m,OBJ+0x54+i*4),mul(inner,read(m,TIME))))
 if m[OBJ+0x150]&2:
  for i in range(3):put(m,OBJ+0x120+i*4,add(read(m,OBJ+0x120+i*4),mul(read(m,OBJ+0x13c+i*4),read(m,TIME))))
 return public(m)
class Oracle(FactoryOracle):
 def __init__(self,words,c):super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(OBJ,))
 def record_call(self,target):raise AssertionError(('unexpected call',target))
 def hook(self,target):raise AssertionError(('unexpected helper',target))
