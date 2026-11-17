"""Execute the complete original 45-word record tick through its literal table."""
from pathlib import Path
from dataclasses import dataclass,replace
import importlib.util,itertools,json,struct,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_actor_accumulator_151ab9c8_recovery as source
from tools.tests import game_actor_accumulator_151ab9c8_oracle as g
R,P=source.ROOT,source.OUT
ENTRY=0x15149264;TABLE=0x8008a4e8;CLEAN=0x150ae790;FREE=0x1516972c;TICK=0x800be9e4
@dataclass(frozen=True)
class Case(g.Case):
 enabled:int=1;tick:int=0;life:int=1;delta:int=0;cleanup:int=0
def cases():
 for i,(seed,route,enabled,tick,cleanup,phase)in enumerate(itertools.product((0,255),range(4),(0,1),(0,1),(0,1,2),(0,8))):
  yield Case(seed,route,31,phase,i%5,enabled,tick,(0,1,-1,-32768,32767)[i%5],(0,1,0x7fffffff)[i%3],cleanup)
def fixture(c,table):
 m=g.fixture(c)
 for i,b in enumerate(table):m[TABLE+i]=b
 g.put(m,TABLE-40,CLEAN);g.put(m,TICK,c.delta)
 m[g.RECORD+13]=c.tick;m[g.RECORD+17]=14 if c.enabled else 255;m[g.RECORD+16]=0 if c.cleanup else 255;g.put(m,g.RECORD+14,c.life,2)
 return m
def half(v):return((v&65535)^32768)-32768
class Caller(g.Oracle):
 def __init__(self,words,parent,initial,c):
  connected=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));FactoryOracle.__init__(self,parent,initial,c,entry=ENTRY,s={},arguments=(g.RECORD,),connected=connected)
  self.service=g.Service(self.memory,c);self.target_calls=[];self.parent_calls=[];self.saved={i:self.r[i]for i in(*range(16,24),28,30)};self.saved_fp=tuple(self.f[20:])
 def record_call(self,t):
  if t==g.ENTRY:
   assert tuple(self.arguments(1))==(g.RECORD,);assert g.read(self.memory,g.ACTOR)==(0 if self.case.route==0 else 1),('actor-active',self.case,g.read(self.memory,g.ACTOR));self.target_calls.append(t)
  elif t in(CLEAN,FREE):assert tuple(self.arguments(1))==(g.RECORD,);self.parent_calls.append(t)
  else:super().record_call(t)
 def hook(self,t):
  if t not in(CLEAN,FREE):return super().hook(t)
  if t==CLEAN and self.case.cleanup==2:g.put(self.memory,g.RECORD+14,1,2)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xdeadbeef
def verify(words,parent,c,table):
 initial=fixture(c,table);expected=dict(initial)
 if c.tick:g.put(expected,g.RECORD+14,c.life-c.delta,2)
 if c.enabled:expected,calls,stopped=g.reference(expected,replace(c,phase=c.phase-24));assert not stopped
 else:calls=[]
 parent_calls=[]
 if half(g.read(expected,g.RECORD+14,2))<0 and c.cleanup:
  parent_calls.append(CLEAN)
  if c.cleanup==2:g.put(expected,g.RECORD+14,1,2)
 if half(g.read(expected,g.RECORD+14,2))<0:parent_calls.append(FREE)
 m=Caller(words,parent,initial,c).run()
 assert len(m.target_calls)==c.enabled and m.parent_calls==parent_calls and m.service.calls==calls,('calls',as_tuple(c),len(m.target_calls),m.parent_calls,parent_calls,m.service.calls,calls)
 assert g.public(m.memory)==g.public(expected),('public',as_tuple(c))
 assert all(m.r[i]==v for i,v in m.saved.items())and tuple(m.f[20:])==m.saved_fp
 return m
def as_tuple(c):return tuple(c.__dict__.values())
def main():
 rom=(R/'conker/conker.us.bin').read_bytes();elf=(R/'conker/build/conker.us.elf').read_bytes();parent=list(struct.unpack_from('>45I',rom,ENTRY-0x14fd2b50));table=rom[0x22efa8:0x22efa8+60]
 assert struct.unpack_from('>I',table,56)[0]==g.ENTRY
 at=elf_slot_offset(elf,TABLE,len(table));assert elf[at:at+len(table)]==table
 at=elf_slot_offset(elf,ENTRY,180);assert elf[at:at+180]==struct.pack('>45I',*parent)
 counts={};seen=set()
 for label,words in g.programs().items():
  n=0
  for c in cases():seen|=verify(words,parent,c,table).visits&set(range(ENTRY,ENTRY+180,4));n+=1
  counts[label]=n
 bad=bytearray(table);struct.pack_into('>I',bad,56,g.ENTRY+4)
 try:verify(g.programs()['raw'],parent,Case(),bytes(bad))
 except(AssertionError,KeyError,ValueError):control=True
 else:raise AssertionError('ineffective callback control')
 report=dict(cases_per_stream=counts,complete_original_caller_executed=True,caller_words=45,caller_words_visited=len(seen),caller_production_literal=True,callback_table_production_literal=True,effective_wrong_callback_control=control,bounded_cleanup_helpers=2,source_installed=source.installed(),c_match_credit=0)
 (P/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
