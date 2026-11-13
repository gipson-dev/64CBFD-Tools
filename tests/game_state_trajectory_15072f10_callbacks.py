from pathlib import Path
from importlib.machinery import SourceFileLoader
import struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests import game_state_trajectory_15072f10_oracle as G
from tools.tests.test_game_point_transform_match import put
class Stub(FactoryOracle):
 def __init__(self,ws,m,c,seed):
  super().__init__(ws,m,c,entry=0x1507304c,s={},arguments=(0x12345678,));self.r[2]=seed;self.before[2]=seed
 def record_call(self,t):raise AssertionError(('unexpected call',t))
 def hook(self,t):raise AssertionError(('unexpected helper',t))
def run():
 rom=(G.root/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x22b090)[0]==G.ENTRY;assert struct.unpack_from('>I',rom,0x22b09c)[0]==0x1507304c
 for phase in (0,8):
  for seed in (0,1,0xffffffff,0xdeadbeef):
   c=G.Case(phase=phase);initial=G.fixture(c);results=[]
   for kind in ('retail.o','generated.o','generic.o'):
    words=G.words(G.out/kind);assert words[-2:]==(0x03e00008,0) or list(words[-2:])==[0x03e00008,0];m=Stub(words[-2:],initial.copy(),c,seed).run();assert m.memory==initial and m.r[2]==seed and not m.calls;results.append((m.memory,m.r))
   assert results.count(results[0])==3
 print('callback table indices 177 and 180; restored no-op executed for 8 register/stack cases')
