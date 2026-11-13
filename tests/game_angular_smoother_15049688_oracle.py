from pathlib import Path
from dataclasses import dataclass
import itertools,struct,subprocess,sys
from tools.experiments import game_angular_smoother_15049688_match as packet
root=packet.ROOT;out=packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_scalar_velocity_smoothing_oracle import corpus,fixture,public
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY=0x15049688;DELTA=0x15048a70;NORMALIZE=0x15048758;SYMS={'func_15048A70':DELTA,'func_15048758':NORMALIZE}
@dataclass(frozen=True)
class Case:phase:int=0
class Machine(FactoryOracle):
 def __init__(self,ws,m,args,phase,code):super().__init__(ws,m,Case(phase),entry=ENTRY,s=SYMS,arguments=args,connected=code)
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==5:
   self.f[(w>>6)&31]=self.f[(w>>11)&31]&0x7fffffff
  else:super().execute(w)
 def record_call(self,t):
  assert t in (DELTA,NORMALIZE),hex(t);self.calls.append((t,(self.f[12],self.f[14])if t==DELTA else (self.r[4],)))
 def hook(self,t):raise AssertionError(('unconnected',hex(t)))
def words(path):
 raw,refs=payload(path,'func_15049688');return bound_blob(raw,refs,SYMS)
def helper_code():
 rom=(root/'conker/conker.us.bin').read_bytes();code={}
 for va,n in ((DELTA,24),(NORMALIZE,32)):
  off=0x2d4b0+va-0x15000000;code.update(zip(range(va,va+n*4,4),struct.unpack_from('>%dI'%n,rom,off)))
 return code
code=helper_code()
def programs():return [words(out/x)for x in ('retail.o','after.o','generated.o','generic.o')]
