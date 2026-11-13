from pathlib import Path
import itertools,struct,sys
from tools.experiments import game_coordinate_table_1512abf8_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_coordinate_table_1512abf8_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
def run():
 rom=(root/'conker/conker.us.bin').read_bytes();start,end=0x15005440,0x15005448;window=struct.unpack_from('>2I',rom,0x328f0);assert window==(0x0d44aafe,0)
 class Connected(g.Machine):
  def __init__(self,words,case,initial):
   self.c=case;code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));code[end]=0
   FactoryOracle.__init__(self,window,initial,case,entry=start,s=g.SYMS,arguments=(),connected=code)
   self.code=WindowCode(self.code,self);self.code.ends=(end,)
  def record_call(self,t):
   if t==g.ENTRY:self.calls.append((t,()))
   else:super().record_call(t)
 programs=g.words();count=0
 for vals in itertools.product((-1,0,1,3,4),(0,27,30,31),(0,1)):
  c=g.Case(*vals);initial=g.fixture(c);expected,calls=g.reference(initial,c)
  for p in programs:
   machine=Connected(p,c,initial.copy())
   try:machine.run();raise AssertionError('caller boundary not reached')
   except WindowBoundary:pass
   public={a:b for a,b in machine.memory.items() if not g.STACK-512<=a<g.STACK+512}
   assert public==expected and machine.calls==[(g.ENTRY,())]+calls,(c,machine.calls)
  count+=1
 print(count,'original caller windows per stream passed')
