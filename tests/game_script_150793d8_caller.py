"""Original dispatcher window connected to the path-node candidate."""
import itertools,struct
from tools.experiments import game_script_150793d8_match as match
from tools.tests import game_script_150793d8_oracle as o
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.match_progress import load_elf_functions

def run(state):
 rom=state['rom'];entry,end=0x1507bd20,0x1507bd74;parent=struct.unpack_from('>21I',rom,0xa91d0)
 live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 assert tuple(live['func_1507BC14'])==struct.unpack_from('>103I',rom,0xa90c4)
 table=0x80086730;index=180;record=0x70000
 assert struct.unpack_from('>I',rom,0x22b4c0)[0]==o.ENTRY
 class Connected(o.Oracle):
  def __init__(self,initial,c,body):
   self.case=c;connected=dict(zip(range(o.ENTRY,o.ENTRY+408,4),body))
   o.g.Oracle.__init__(self,parent,initial,c,entry=entry,connected=connected)
  def record_call(self,t):
   if t==o.ENTRY:self.calls.append((t,()))
   else:super().record_call(t)
 count=0
 for x,z,delta,actor,path,idx,phase in itertools.product((-1181,0,1180),(-1181,0,1180),(-300,300),range(2),range(2),range(2),(0,8)):
  c=o.Case(x,z,delta,-delta,actor,path,idx,phase);initial=o.fixture(c);original=o.ACTORS[actor^1]
  o.put(initial,original+0x218,record);o.put(initial,table+index*4,o.ENTRY)
  for i,v in enumerate((index,idx^1,0x13,0x29,0xff)):o.put(initial,record+i,v,1)
  for i in range(4):o.put(initial,o.CMD+i,0x77,1)
  expected=dict(initial)
  for i,v in enumerate((idx^1,0x13,0x29,0xff)):o.put(expected,o.CMD+i,v,1)
  expected=o.reference(expected,c);o.put(expected,original+0x218,(o.read(expected,original+0x218)+5)&0xffffffff)
  for body in (state['raw_words'],state['retail_words']):
   m=Connected(initial,c,body);m.r[2]=record;m.r[16]=original;m.r[17]=o.CMD;m.r[18]=o.CMD+1;m.r[19]=o.CMD+2;m.r[20]=o.CMD+3;m.r[21]=table
   m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run();raise AssertionError('dispatcher did not stop')
   except WindowBoundary:pass
   assert o.public(m.memory)==expected,c
   assert [t for t,_ in m.calls]==[o.ENTRY,o.RNG,o.VECTOR]
  count+=1
 return dict(cases=count,bodies=2,table_index=index,helper='modeled',dispatcher='retail dispatcher window validated against production ELF')
