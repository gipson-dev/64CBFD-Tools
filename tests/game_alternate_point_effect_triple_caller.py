"""Modeled effect callbacks connected to original dispatcher windows."""
import itertools,struct
from tools.experiments import game_alternate_point_effect_triple_match as match
from tools.tests import game_alternate_point_effect_triple_oracle as oracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
def run(state):
 g=vars(oracle)
 one,_=match.pad_both(state)
 bodies=[(state['retail_words'][n],state['raw_words'][n],oracle.words(one,n)) for n in match.NAMES]
 class Connected(g['Oracle']):
  def __init__(self,entry,parent,initial,c,body):
   self.cc=c;self.obs=[];target=g['ENTRIES'][c.kind];connected=dict(zip(range(target,target+352,4),body));g['g'].Oracle.__init__(self,parent,initial,c,entry=entry,connected=connected);self.home=g['STACK']+c.phase
  def record_call(self,t):
   if t==g['ENTRIES'][self.cc.kind]:
    a=tuple(map(g['g'].u32,self.arguments(3)));self.calls.append((t,a));self.home=self.r[29]
   else:super().record_call(t)
 rom=state['rom'];table=0x8008a0b4;indices=(6,15,16);record=0x70000;n=[0,0,0]
 for kind,which,mode,amount,active,answer,phase in itertools.product(range(3),range(2),(0,1,2,0xabcd00ff),(-32768,0,114,115,32767),(0,0x50000),(0,1),(0,8)):
  amount=0 if which==0 else amount;c=g['Case'](kind=kind,mode=mode,amount=amount,active=active,answer=answer,phase=phase);initial=g['fixture'](c);index=indices[kind];target=g['ENTRIES'][kind];g['put'](initial,table+index*8,target);g['put'](initial,table+index*8+4,130)
  for i in range(64):initial[record+i]=165
  g['put'](initial,record+14,amount&0xffff,2);entry,off,num,end=(0x15141B4C,0x16EFFC,5,0x15141B60)if which==0 else(0x15141BAC,0x16F05C,8,0x15141BCC);parent=struct.unpack_from('>%dI'%num,rom,off);want,calls,obs=g['reference'](initial,c)
  for code in bodies[kind]:
   m=Connected(entry,parent,initial,c,code);m.r[18]=c.actor;m.r[19]=mode;m.r[16]=table;m.r[14]=table+index*8;m.r[12]=index;m.r[2]=record;m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run();raise AssertionError('window did not stop')
   except WindowBoundary:pass
   assert g['public'](m.memory)==want,c;assert m.calls==[(target,(c.actor,mode,amount&0xffffffff))]+calls,(c,m.calls,calls);assert m.obs==obs,c
  n[kind]+=1
 return dict(cases_per_target=n,programs=3,parent_windows=['0x15141B4C','0x15141BAC'],table_entries=indices,retail_counts=[130,130,130])

def run_providers(state):
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 from tools.match_progress import load_elf_functions
 root=match.ROOT
 g=vars(oracle)
 one,_=match.pad_both(state)
 bodies=[(state['retail_words'][n],state['raw_words'][n],oracle.words(one,n)) for n in match.NAMES]
 rom=state['rom'];elf=(root/'conker/build/conker.us.elf').read_bytes();live,_,_=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');names=('func_151D97A8','func_151D99C8','func_151D9ADC');counts=(30,22,22);tables=(0x800AB350,0x800AB3A8,0x800AB3CC);nums=(7,3,3);RNG=0x150ADA20
 providers=[];tablebytes=[]
 for n,addr,count,table,num in zip(names,g['PROVIDERS'],counts,tables,nums):
  offset=addr-0x15000000+0x2d4b0;ws=struct.unpack_from('>%dI'%count,rom,offset);assert tuple(live[n])==ws,(n,len(live[n]));providers.append(dict(zip(range(addr,addr+count*4,4),ws)));at=elf_slot_offset(elf,table,num*4);tablebytes.append(elf[at:at+num*4])
 class Connected(g['Oracle']):
  def __init__(self,code,c,random):
   super().__init__(code,c);self.random=random;self.connected=providers[c.kind];self.code.update(self.connected);table=tables[c.kind];self.memory.update({table+i:b for i,b in enumerate(tablebytes[c.kind])})
  def execute(self,w):
   if w>>26==0 and w&63==27:
    a=self.r[w>>21&31];b=self.r[w>>16&31];assert b;self.lo=a//b;self.hi=a%b;self.r[0]=0
   else:super().execute(w)
  def record_call(self,t):
   if t==RNG:self.calls.append((t,()))
   else:super().record_call(t)
  def hook(self,t):
   if t==RNG:
    for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
    for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
    self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=self.random
   else:super().hook(t)
 count=[0,0,0];seen=[set(),set(),set()]
 for kind,mode,amount,phase,random in itertools.product(range(3),(0,1,2,255),(114,115),(0,8),(0,1,2,3,6,7,0xffffffff)):
  vals=struct.unpack('>%dI'%nums[kind],tablebytes[kind]);value=vals[random%nums[kind]]&255;c=g['Case'](kind=kind,mode=mode,amount=amount,phase=phase,provider_return=value);initial=g['fixture'](c);initial.update({tables[kind]+i:b for i,b in enumerate(tablebytes[kind])});want,calls,obs=g['reference'](initial,c);at=next(i for i,(target,_) in enumerate(calls) if target==g['PROVIDERS'][kind]);calls.insert(at+1,(RNG,()))
  for code in bodies[kind]:
   m=Connected(code,c,random).run();assert (g['public'](m.memory),m.calls,m.obs)==(want,calls,obs),(c,random,m.calls,calls);seen[kind].update(addr for addr in m.visits if addr in providers[kind])
  count[kind]+=1
 return dict(cases_per_target=count,provider_words=list(map(len,seen)),rng='modeled return',source='retail bytes checked against live ELF')
