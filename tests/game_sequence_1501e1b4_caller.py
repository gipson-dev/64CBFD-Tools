"""Connect the retail sequence-time caller prefix to the candidate."""
import itertools,struct
from tools.experiments import game_sequence_1501e1b4_match as match
from tools.tests import game_sequence_1501e1b4_oracle as o
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.match_progress import load_elf_functions

def run(s):
 entry,end=0x1501e400,0x1501e470;rom=s['rom'];caller=struct.unpack_from('>28I',rom,0x4b8b0)
 live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 assert tuple(live['func_1501E400'])==struct.unpack_from('>80I',rom,0x4b8b0)
 class Connected(o.Oracle):
  def __init__(self,initial,c,body):
   self.case=c;connected=dict(zip(range(o.ENTRY,o.ENTRY+324,4),body))
   o.g.Oracle.__init__(self,caller,initial,c,entry=entry,connected=connected);self.r[4]=c.slot;self.before=self.r[:]
  def record_call(self,t):
   if t==o.ENTRY:self.calls.append((t,tuple(map(o.g.u32,self.arguments(1)))))
   else:super().record_call(t)
 count=0
 for slot,state,pred,gap,query,phase in itertools.product(range(2),(0,1,2),range(2),(90,91),range(3),(0,8)):
  c=o.Case(slot,state,1,pred,gap,query,30,30,phase);initial=o.fixture(c);o.put(initial,0x800c3a58,2,1);o.put(initial,0x800c35b8+4*slot,0xabcdef98)
  expected=dict(initial);o.put(expected,0x800c3a58,1,1);o.put(expected,0x800c35b8+4*slot,o.read(expected,o.CURRENT+4*slot));expected,calls=o.reference(expected,c)
  for code in (s['raw_words'],s['retail_words']):
   m=Connected(initial,c,code);m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run();raise AssertionError('caller did not stop')
   except WindowBoundary:pass
   assert o.public(m.memory)==expected,c
   assert m.calls==[(o.ENTRY,(slot,))]+calls,(c,m.calls,calls)
  count+=1
 return dict(cases=count,bodies=2,caller='byte-exact original sequence-time prefix',helpers='modeled')
