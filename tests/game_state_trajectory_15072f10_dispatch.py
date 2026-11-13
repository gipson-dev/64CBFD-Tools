from pathlib import Path
from importlib.machinery import SourceFileLoader
import struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import game_state_trajectory_15072f10_oracle as G
TABLE=0x8008630c;RESOURCE=0x38000;HOLDER=0x39000;BEGIN=0x1505e39c;END=0x1505e3bc
rom=(G.root/'conker/conker.us.bin').read_bytes();start=0x2d4b0+BEGIN-0x15000000;window=struct.unpack_from('>8I',rom,start)
class Window(FactoryOracle):
 def __init__(self,c,m):
  super().__init__(window,m,c,entry=BEGIN,s={},arguments=(0,));self.r[7]=RESOURCE;self.r[16]=HOLDER;self.before=self.r[:];self.code=WindowCode(self.code,self);self.code.ends=(END,)
 def record_call(self,t):raise AssertionError(('unexpected call',t))
 def hook(self,t):raise AssertionError(('unexpected helper',t))
def run():
 for index,expected in ((177,G.ENTRY),(180,0x1507304c)):
  for phase in (0,8):
   c=G.Case(phase=phase);m=G.fixture(c);G.put(m,RESOURCE+2,index,2);target=struct.unpack_from('>I',rom,0x22adcc+index*4)[0];assert target==expected;G.put(m,TABLE+index*4,target);G.put(m,HOLDER,0)
   machine=Window(c,m)
   try:machine.run();raise AssertionError('window returned without boundary')
   except WindowBoundary:pass
   assert G.read(machine.memory,HOLDER)==expected
 print('original dispatch lookup selected indices 177 and 180 in four cases')
