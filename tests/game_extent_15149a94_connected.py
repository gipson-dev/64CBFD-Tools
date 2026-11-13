from pathlib import Path
import itertools,struct,sys
from tools.experiments import game_extent_15149a94_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_extent_15149a94_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
def run():
 start,end=0x1513d070,0x1513d0a8;rom=(root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>14I',rom,start-0x15000000+0x2d4b0)
 assert window[0]==0x90820071 and window[8]==0x0320f809
 class Connected(g.Machine):
  def __init__(self,words,case,initial):
   self.c=case;code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));code[end]=0
   FactoryOracle.__init__(self,window,initial,case,entry=start,s=g.SYMS,arguments=(g.ACTOR,),connected=code)
   self.r[7]=0;self.code=WindowCode(self.code,self);self.code.ends=(end,)
  def record_call(self,target):
   if target==g.ENTRY:self.calls.append((target,tuple(self.arguments(1))))
   else:super().record_call(target)
 programs=[bound_blob(*payload(out/x,g.NAME),g.SYMS) for x in ('retail.o','after.o','generated.o','generic.o')];count=0
 for flags,timer,x,y,factor,mutation in itertools.product((0,2,8,10),(-1,5),(0.,4.),(0.,8.),(0.5,1.),(0,1)):
  c=g.Case(flags,timer,x,y,factor,mutation);initial=g.fixture(c);initial[g.ACTOR+0x71]=14;put(initial,0x80089d98,g.ENTRY);expected,calls=g.reference(initial,c)
  for p in programs:
   machine=Connected(p,c,initial.copy())
   try:machine.run();raise AssertionError('caller boundary not reached')
   except WindowBoundary:pass
   actual={a:b for a,b in machine.memory.items() if not g.STACK-512<=a<g.STACK+512}
   assert actual==expected and machine.calls==[(g.ENTRY,(g.ACTOR,))]+calls and machine.r[7]==0,(c,machine.calls)
  count+=1
 print(count,'original callback-dispatch windows per stream passed with table index 14')
