"""Connect the original dispatcher window to the candidate path handler."""
import itertools,struct
from tools.experiments import game_script_1507602c_match as match
from tools.tests import game_script_1507602c_oracle as o
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.match_progress import load_elf_functions

def run(state):
 rom=state['rom'];entry,end=0x1507bd20,0x1507bd74;parent=struct.unpack_from('>21I',rom,0xa91d0)
 live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 assert tuple(live['func_1507BC14'])==struct.unpack_from('>103I',rom,0xa90c4)
 table=0x80086730;index=16;record=0x70000
 assert struct.unpack_from('>I',rom,0x22b230)[0]==o.ENTRY
 class Connected(o.Oracle):
  def __init__(self,initial,c,body):
   self.case=c;connected=dict(zip(range(o.ENTRY,o.ENTRY+412,4),body))
   o.g.Oracle.__init__(self,parent,initial,c,entry=entry,connected=connected);self.fcsr=0x800004
  def record_call(self,t):
   if t==o.ENTRY:self.calls.append((t,()))
   else:super().record_call(t)
 count=0
 for actor,path,index2,speed,phase in itertools.product(range(2),range(2),range(2),(.5,2.,10.,100.),(0,8)):
  c=o.Case(actor,path,index2,speed,phase);initial=o.fixture(c);original=o.ACTORS[actor^1]
  o.put(initial,original+0x218,record);o.put(initial,table+index*4,o.ENTRY)
  for i,v in enumerate((index,13,index2,0x19,0xff)):o.put(initial,record+i,v,1)
  for i in range(4):o.put(initial,o.CMD-1+i,0x77,1)
  expected=dict(initial)
  for i,v in enumerate((13,index2,0x19,0xff)):o.put(expected,o.CMD-1+i,v,1)
  expected=o.reference(expected,c)
  o.put(expected,original+0x218,(o.read(expected,original+0x218)+5)&0xffffffff)
  for body in (state['retail_words'],state['raw_words']):
   m=Connected(initial,c,body);m.r[2]=record;m.r[16]=original;m.r[17]=o.CMD-1;m.r[18]=o.CMD;m.r[19]=o.CMD+1;m.r[20]=o.CMD+2;m.r[21]=table
   m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run();raise AssertionError('dispatcher did not stop')
   except WindowBoundary:pass
   actual=o.public(m.memory)
   assert actual==expected,(c,[(hex(k),expected.get(k),actual.get(k)) for k in sorted(set(actual)|set(expected)) if actual.get(k)!=expected.get(k)][:12])
   assert m.calls==[(o.ENTRY,()),(o.HELPER,())] and m.fcsr==0x800004
  count+=1
 return dict(cases=count,bodies=2,table_index=index,helper='modeled',dispatcher='retail window validated against production ELF')

def helper(state):
 rom=state['rom'];live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 connected={}
 for name,start,end in [('func_15075548',0x15075548,0x15075650),('func_15075498',0x15075498,0x15075548)]:
  words=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2d4b0)
  assert tuple(live[name])==words
  connected.update(zip(range(start,end,4),words))
 class OriginalHelper(o.Oracle):
  def __init__(self,code,c,initial):
   super().__init__(code,c);self.memory=dict(initial);self.code.update(connected)
  def record_call(self,t):
   assert t in (0x15075548,0x15075498),hex(t)
   self.calls.append((t,()))
 count=0;seen=set()
 for actor,path,index,speed,phase in itertools.product(range(2),range(2),range(2),(.5,2.,10.,100.),(0,8)):
  c=o.Case(actor,path,index,speed,phase);initial=o.fixture(c);active=o.ACTORS[actor]
  o.put(initial,o.CURRENT,active);o.put(initial,active+0x44,o.b(speed))
  for address,value in ((o.CMD-1,0),(o.CMD+1,255),(o.CMD+2,0x7f)):o.put(initial,address,value,1)
  o.put(initial,0x800be616,0,1)
  expected=dict(initial);o.put(expected,active+0x223,0,1);o.put(expected,active+0x21c,0,2)
  o.put(expected,active+0xf4,o.read(expected,active+0xf4)&~0x143e)
  expected=o.reference(expected,c)
  for code in (state['raw_words'],state['retail_words']):
   m=OriginalHelper(code,c,initial).run()
   assert o.public(m.memory)==expected,c
   assert m.calls==[(0x15075548,()),(0x15075498,())] and m.fcsr==0x800004
   seen.update(pc for pc in m.visits if pc in connected)
  count+=1
 return dict(cases=count,bodies=2,helper_words_visited=len(seen),helper_words=len(connected),scope='original helper, command rate sentinel and disabled actor override')
