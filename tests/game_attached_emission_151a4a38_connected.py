"""Couple the recovery to the original emitter, allocation wrapper and memcpy."""
from pathlib import Path
import importlib.util,itertools,json,struct,sys
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests import game_attached_emission_151a4a38_oracle as g
O=g.O
BASE,ALLOCATE,COPY,REAL,TRIG,OUTPUT=0x15130280,0x15167A68,0x10022EC0,0x150ADA68,0x151423D8,0x90000
ROM=(g.R/'conker/conker.us.bin').read_bytes();ELF=(g.R/'conker/build/conker.us.elf').read_bytes();HELPERS={}
for entry,offset,n in((g.EMIT,0x180AE4,224),(BASE,0x15D730,61),(COPY,0x22EC0,11)):
 raw=ROM[offset:offset+4*n];at=elf_slot_offset(ELF,entry,len(raw));assert ELF[at:at+len(raw)]==raw
 HELPERS.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,raw)))
class Machine(g.Machine):
 def __init__(self,words,m,c,success,alias):
  g.base.Machine.__init__(self,words,m,c,connected=HELPERS,entry=g.ENTRY,args=(g.E,0xBAD00005,0xBAD00006,0xBAD00007));self.ri=0;self.homes=[];self.output_home=None;self.forwardings=[];self.allocations=[];self.success=success;self.output=g.E if alias else OUTPUT
 def record_call(self,t):
  if t in(g.EMIT,g.RNG,g.TRANSFORM):return super().record_call(t)
  if t==BASE:self.forwardings.append(tuple(self.arguments(6)));return
  if t==ALLOCATE:self.allocations.append(tuple(self.arguments(6)));return
  if t==COPY:
   a=tuple(self.arguments(3));assert a[2]in(4,112);self.calls.append((t,(a[0],'descriptor'if a[2]==112 else'parameter',a[2]),g.data(self.memory,a[1],a[2])));self.raw_calls.append((t,a));return
  assert t in(REAL,TRIG),hex(t);a=tuple(self.arguments(0 if t==REAL else 1));self.calls.append((t,a,b''));self.raw_calls.append((t,a))
 def hook(self,t):
  if t in(g.RNG,g.TRANSFORM):return super().hook(t)
  assert t in(REAL,TRIG,ALLOCATE),hex(t);value=0xA5000002;fpword=None
  if t==ALLOCATE:value=self.output if self.success else 0
  elif t==REAL:fpword=g.bits(.25)
  else:fpword=g.bits(((self.raw_calls[-1][1][0]&255)-128)/256.)
  for i in range(6 if t==ALLOCATE else 4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=value
  if fpword is not None:self.f[0]=fpword
def main(label='v13'):
 streams=g.programs(label);seen=set();n=0;allocation_counts=set()
 for seed,flips,success,alias,mutation,phase in itertools.product((1,2,255),range(4),(0,1),(0,1),(0,1,2,12,16),(0,8)):
  c=g.Case(seed=seed,flips=flips,mutation=mutation,phase=phase,pattern=3);initial=g.fixture(c)
  initial.update({OUTPUT+i:(i*19+seed)&255 for i in range(256)});results=[]
  for name,words in streams.items():
   q=Machine(words,initial,c,success,alias).run();results.append((q.memory,q.calls,q.forwardings,q.allocations,tuple(q.r),tuple(q.f),q.hi,q.lo,q.fp_ops));seen.update(pc for pc in q.visits if pc in HELPERS)
   emitter=next(call for call in q.calls if call[0]==g.EMIT);slot,context=emitter[1][2:]
   for a in q.allocations:assert a==(0x2B,context,0xAC,1,slot,1),a
   for a in q.forwardings:assert a==(q.target_home-280,0,0,4,slot,context),a
   assert len([call for call in q.calls if call[0]==COPY])==(2*len(q.allocations)if success else 0)
   allocation_counts.add(len(q.allocations))
  assert all(v==results[0]for v in results[1:]),(c,success,alias,'actual emitter chain');n+=1
 report=dict(cases_per_stream=n,streams=len(streams),actual_emitter_words=224,actual_base_factory_words=61,actual_memcpy_words=11,helper_words_visited=len(seen),allocations_per_callback=sorted(allocation_counts),all_public_and_private_bytes_and_registers_equal=True,zero_count_and_allocation_failure_and_output_owner_alias=True,mode_zero_NULL_vector_contract=True,transform_trig_random_and_allocator_bounded_hooks=True,source_installed=False,c_match_credit=0)
 (O/'connected-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main(sys.argv[1]if len(sys.argv)>1 else'v13')
