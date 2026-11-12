"""Original script dispatcher window with the target handler connected."""
import itertools,struct
from tools.experiments import game_script_15079fbc_match as match
from tools.tests import game_script_15079fbc_oracle as o
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.match_progress import load_elf_functions

def run(state):
 _,padded=match.pad_both(state);bodies=(state['retail_words'],state['raw_words'],o.words(padded));rom=state['rom'];entry,end=0x1507bd20,0x1507bd74;parent=struct.unpack_from('>21I',rom,0xa91d0);table=0x80086730;index=196;record=0x70000;count=0
 live,_,addr=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');assert tuple(live['func_1507BC14'])==struct.unpack_from('>103I',rom,0xa90c4);assert struct.unpack_from('>I',rom,0x22b500)[0]==o.ENTRY
 class Connected(o.Oracle):
  def __init__(self,initial,c,code):
   self.cc=c;connected=dict(zip(range(o.ENTRY,o.ENTRY+324,4),code));o.g.Oracle.__init__(self,parent,initial,c,entry=entry,connected=connected)
  def record_call(self,t):
   if t==o.ENTRY:self.calls.append((t,()))
   else:super().record_call(t)
 for actor,active,value,chased,mutation,phase in itertools.product((o.ACTOR,o.PLAYER),(0,1),(4.,5.,16.75,20.),(0,1),range(4),(0,8)):
  c=o.Case(actor=actor,active=active,value=o.g.bits(value),chased=chased,mutation=mutation,phase=phase);initial=o.fixture(c);o.put(initial,actor+0x218,record);o.put(initial,table+index*4,o.ENTRY)
  for i,v in enumerate((index,13,c.cmd,0x19,0xff)):o.put(initial,record+i,v,1)
  want,calls=o.reference(initial,c);o.put(want,actor+0x218,o.g.u32(o.read(want,actor+0x218)+5))
  for code in bodies:
   m=Connected(initial,c,code);m.r[2]=record;m.r[16]=actor;m.r[17]=o.CMD;m.r[18]=o.CMD+1;m.r[19]=o.CMD+2;m.r[20]=o.CMD+3;m.r[21]=table;m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run();raise AssertionError('window did not stop')
   except WindowBoundary:pass
   assert (o.public(m.memory),m.calls)==(want,[(o.ENTRY,())]+calls),(c,m.calls,calls)
  count+=1
 return dict(cases=count,programs=3,window='0x1507BD20..0x1507BD74',table='D_80086730[196]',caller='retail caller matches live ELF')


def lookup(state):
 rom=state['rom'];live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');entry=o.LOOKUP;code=struct.unpack_from('>59I',rom,0xa8fd8);assert tuple(live['func_1507BB28'])==code;connected=dict(zip(range(entry,entry+236,4),code));_,padded=match.pad_both(state);bodies=(state['retail_words'],state['raw_words'],o.words(padded));resource=0x71010;local=0x72000;fallback=0x80086a88;count=0;seen=set()
 class Connected(o.Oracle):
  def __init__(self,code,c,initial):super().__init__(code,c);self.memory=dict(initial);self.code.update(connected)
 for actor,mode,cmd,phase in itertools.product((o.ACTOR,o.PLAYER),range(6),(0,1,127,255),(0,8)):
  c=o.Case(actor=actor,active=0,cmd=cmd,phase=phase);initial=o.fixture(c);identity=o.read(initial,actor+4,1);o.put(initial,0x800d1588+identity*4,0 if mode==0 else resource)
  o.put(initial,resource-16,0 if mode==1 else local);o.put(initial,local,0 if mode in (4,5) else o.SCRIPT);o.put(initial,local+4,cmd if mode==2 else (cmd+1)&255,1);o.put(initial,local+8,o.SCRIPT);o.put(initial,local+12,cmd,1)
  o.put(initial,fallback,o.SCRIPT);o.put(initial,fallback+4,cmd if mode==4 else (cmd+1)&255,1);o.put(initial,fallback+8,o.SCRIPT);o.put(initial,fallback+12,cmd,1)
  want,calls=o.reference(initial,c)
  if mode in (0,1):o.put(want,actor+0x218,0x8009a120-5)
  for body in bodies:
   m=Connected(body,c,initial).run();assert (o.public(m.memory),m.calls)==(want,calls),(c,mode,m.calls,calls);seen.update(pc for pc in m.visits if pc in connected)
  count+=1
 return dict(cases=count,helper_words_visited=len(seen),helper_words=59,source='retail lookup checked against production ELF',includes=['null resource','null table','local first and second','fallback first and second'])
