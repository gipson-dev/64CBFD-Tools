"""Connect the effect callback to original dispatcher windows and slot provider."""
import itertools,struct
from dataclasses import replace
from tools.experiments import game_random_point_15146e84_match as match
from tools.tests import game_random_point_15146e84_oracle as o
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.match_progress import load_elf_functions

def run(state):
 one,_=match.pad_both(state);bodies=(state['retail_words'],state['raw_words'],o.words(one));rom=state['rom'];table=0x8008a0b4;index=4;record=0x70000;count=0
 class Connected(o.Oracle):
  def __init__(self,entry,parent,initial,c,body):
   self.cc=c;self.obs=[];self.random_index=0;code=dict(zip(range(o.ENTRY,o.ENTRY+444,4),body));o.g.Oracle.__init__(self,parent,initial,c,entry=entry,connected=code);self.home=o.STACK+c.phase
  def record_call(self,t):
   if t==o.ENTRY:self.calls.append((t,tuple(map(o.g.u32,self.arguments(3)))));self.home=self.r[29]
   else:super().record_call(t)
 for which,mode,amount,active,answer,phase in itertools.product(range(2),(0,1,2,0xabcd00ff),(-32768,0,70,71,32767),(0,0x50000),(0,1),(0,8)):
  amount=0 if which==0 else amount;c=o.Case(mode=mode,amount=amount,active=active,answer=answer,phase=phase,randoms=(mode&1,123,456),mutation=(0,4,8,0)[mode&3]);initial=o.fixture(c)
  o.put(initial,table+index*8,o.ENTRY);o.put(initial,table+index*8+4,80)
  for i in range(64):initial[record+i]=165
  o.put(initial,record+14,amount&0xffff,2);entry,off,num,end=(0x15141B4C,0x16EFFC,5,0x15141B60)if which==0 else(0x15141BAC,0x16F05C,8,0x15141BCC);parent=struct.unpack_from('>%dI'%num,rom,off);want,calls,obs=o.reference(initial,c)
  for code in bodies:
   m=Connected(entry,parent,initial,c,code);m.r[18]=c.actor;m.r[19]=o.g.u32(mode);m.r[16]=table;m.r[14]=table+index*8;m.r[12]=index;m.r[2]=record;m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run();raise AssertionError('window did not stop')
   except WindowBoundary:pass
   assert o.public(m.memory)==want,c;assert m.calls==[(o.ENTRY,(c.actor,o.g.u32(mode),o.g.u32(amount)))]+calls,(c,m.calls,calls);assert m.obs==obs,c
  count+=1
 return dict(cases=count,programs=3,table_entry=4,retail_count=80)

def provider(state):
 one,_=match.pad_both(state);bodies=(state['retail_words'],state['raw_words'],o.words(one));rom=state['rom'];addr=o.SLOT;query=0x150A29C8;romoff=0x2062d0
 code=struct.unpack_from('>19I',rom,romoff);live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');assert tuple(live['func_151D8E20'])==code
 connected=dict(zip(range(addr,addr+76,4),code));count=0;visits=set()
 class Provider(o.Oracle):
  def __init__(self,body,c,mode,answer):
   super().__init__(body,c);self.code.update(connected);self.query_answer=answer;o.put(self.memory,0x800BE9F0,mode);o.put(self.memory,0x800E0A10,c.slot,1)
  def record_call(self,t):
   if t==query:self.calls.append((t,tuple(map(o.g.u32,self.arguments(2)))))
   else:super().record_call(t)
  def hook(self,t):
   if t==query:
    for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
    for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
    self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=self.query_answer
   else:super().hook(t)
 for mode,answer,slot,branch,amount,phase in itertools.product((0,1),(0,1),(0,1,255),(0,1),(70,71),(0,8)):
  chosen=10 if mode==0 and answer==0 else slot;c=o.Case(slot=chosen,amount=amount,phase=phase,randoms=(branch,0xffffffff,0x87654321));initial=o.fixture(c);o.put(initial,0x800BE9F0,mode);o.put(initial,0x800E0A10,slot,1);want,calls,obs=o.reference(initial,c)
  if mode==0:calls.insert(2,(query,(0,28)))
  for body in bodies:
   m=Provider(body,replace(c,slot=slot),mode,answer).run();assert (o.public(m.memory),m.calls,m.obs)==(want,calls,obs),(mode,answer,slot,m.calls,calls);visits.update(k for k in m.visits if k in connected)
  count+=1
 return dict(cases=count,provider_words_visited=len(visits),provider_words=19,query='bounded return',source='retail provider checked against production ELF')
