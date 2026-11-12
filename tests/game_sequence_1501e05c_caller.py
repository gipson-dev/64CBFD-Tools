"""Connect the retail transition-handler call site to its predicate."""
import itertools,struct
from tools.experiments import game_sequence_1501e05c_match as match
from tools.tests import game_sequence_1501e05c_oracle as o
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.match_progress import load_elf_functions

def run(s):
 entry,end=0x1501e1e8,0x1501e1f0;rom=s['rom'];caller=struct.unpack_from('>2I',rom,0x4b698)
 live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 assert tuple(live['func_1501E1B4'])==struct.unpack_from('>81I',rom,0x4b664)
 class Connected(o.Oracle):
  def __init__(self,initial,c,body):
   self.case=c;connected=dict(zip(range(o.ENTRY,o.ENTRY+344,4),body))
   o.g.Oracle.__init__(self,caller,initial,c,entry=entry,connected=connected);self.r[4]=c.slot;self.r[29]=o.STACK+c.phase-32;self.before=self.r[:]
  def record_call(self,t):
   if t==o.ENTRY:self.calls.append((t,tuple(map(o.g.u32,self.arguments(1)))))
   else:super().record_call(t)
 count=0
 for slot,scene,trigger,event,buttons,override,force,answer,mut in itertools.product(range(2),(29,33,17),(0,0x80),(4,5),(0x20,0x1000),range(2),range(2),range(2),range(2)):
  c=o.Case(slot,scene,trigger,event,buttons,1,0,override,force,answer,mut,8 if slot else 0,301);initial=o.fixture(c);expected,calls,result=o.reference(initial,c)
  for body in (s['raw_words'],s['retail_words']):
   m=Connected(initial,c,body);m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run();raise AssertionError('caller did not stop')
   except WindowBoundary:pass
   assert (o.public(m.memory),m.calls,m.r[2])==(expected,[(o.ENTRY,(slot,))]+calls,result),c
  count+=1
 return dict(cases=count,bodies=2,caller='byte-exact original transition call site',helper='modeled')

def real_helper(s):
 rom=s['rom'];live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 words=struct.unpack_from('>33I',rom,0x4a774);assert tuple(live['func_1501D2C4'])==words
 connected=dict(zip(range(o.HELPER,o.HELPER+132,4),words));count=0;seen=set()
 class Connected(o.Oracle):
  def __init__(self,body,c,initial):super().__init__(body,c);self.memory=dict(initial);self.code.update(connected)
 for slot,event,force,phase in itertools.product(range(2),(4,5),range(2),(0,8)):
  c=o.Case(slot,17,0,event,0x20,0,0,0,force,1,0,phase,301);initial=o.fixture(c);o.put(initial,0x800c3670,1,1);expected,calls,result=o.reference(initial,c)
  for body in (s['raw_words'],s['retail_words']):
   m=Connected(body,c,initial).run();assert (o.public(m.memory),m.calls,m.r[2])==(expected,calls,result),c
   seen.update(pc for pc in m.visits if pc in connected)
  count+=1
 return dict(cases=count,helper_words_visited=len(seen),helper_words=len(words),scope='retail helper override branch only')
