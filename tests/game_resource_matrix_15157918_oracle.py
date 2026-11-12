"""Bounded guest reference for the two-slot resource matrix callback."""
from dataclasses import dataclass

from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY,OBJ,INDEX,HELPER=0x15157918,0x30000,0x800BE9C0,0x150A8050
@dataclass(frozen=True)
class Case:
 index:int; mutation:int; scale:int; pattern:int; phase:int
def fixture(c):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-2048,512)}
 m.update({OBJ+i:(i*13+0x5a)&255 for i in range(-16,0x150)})
 m[INDEX]=c.index
 for i,v in enumerate((1.5,-2.0,3.25)):
  put(m,OBJ+0x54+i*4,bits(v));put(m,OBJ+0x120+i*4,bits(v+0.5))
 put(m,OBJ+0x12c,c.scale)
 return m
def matrix_effect(m,c,address):
 for i in range(16):put(m,address+i*4,bits((i-c.pattern*3)*0.25))
 if c.mutation:
  m[INDEX]^=1
  for i,v in enumerate((-4.0,5.5,6.25)):put(m,OBJ+0x54+i*4,bits(v))
  put(m,OBJ+0x12c,bits(-0.5))
def public(m):return {a:v for a,v in m.items() if not STACK-2048<=a<STACK+512}
def reference(c):
 m=fixture(c);start=m[INDEX];address=OBJ+0x7c+start*64
 args=(address,read(m,OBJ+0x120),read(m,OBJ+0x124),read(m,OBJ+0x128))
 matrix_effect(m,c,address)
 for i in range(3):put(m,OBJ+0xac+m[INDEX]*64+i*4,read(m,OBJ+0x54+i*4))
 for row in range(3):
  for col in range(3):
   address=OBJ+0x7c+m[INDEX]*64+row*16+col*4
   put(m,address,bits(floating(read(m,address))*floating(read(m,OBJ+0x12c))))
 return public(m),[(HELPER,args)]
class Oracle(FactoryOracle):
 def __init__(self,words,c):super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(OBJ,))
 def record_call(self,target):
  assert target==HELPER,hex(target);self.calls.append((target,tuple(self.r[4:8])))
 def hook(self,target):
  assert target==HELPER;matrix_effect(self.memory,self.case,self.r[4])
  for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
