"""Execute the actual wrapper, mode-zero factory and byte-copy helper."""
from pathlib import Path
import importlib.util,itertools,json,struct,sys
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests import game_inverse_motion_151a4638_oracle as g
O=g.O;R=g.R
BASE,ALLOCATE=0x15130280,0x15167A68
ROM=(R/'conker/conker.us.bin').read_bytes();ELF=(R/'conker/build/conker.us.elf').read_bytes()
HELPERS={}
for entry,offset,n in((g.FACTORY,0x15D824,18),(BASE,0x15D730,61),(g.COPY,0x22EC0,11)):
 raw=ROM[offset:offset+4*n];at=elf_slot_offset(ELF,entry,len(raw));assert ELF[at:at+len(raw)]==raw
 HELPERS.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,raw)))

class Machine(g.Machine):
 def __init__(self,words,m,c):
  a=g.inputs(c);g.base.Machine.__init__(self,words,m,c,connected=HELPERS,entry=g.ENTRY,args=(0xBAD00004,0xBAD00005,a[2],a[3]));self.f[12],self.f[14]=a[:2];self.ri=0;self.homes=[];self.forwardings=[];self.allocations=[]
 def record_call(self,t):
  if t==BASE:self.forwardings.append(tuple(self.arguments(6)));return
  if t==ALLOCATE:self.allocations.append(tuple(self.arguments(6)));return
  if t==g.COPY and self.arguments(3)[2]==112:
   a=tuple(self.arguments(3));assert a[1]==self.target_home-112
   self.calls.append((t,(a[0],'packet',112),g.data(self.memory,a[1],112)));return
  return super().record_call(t)
 def hook(self,t):
  if t!=ALLOCATE:return super().hook(t)
  g.mutate(self.memory,self.c,g.FACTORY,0)
  for i in range(6):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=g.output(self.c)if self.c.success else 0

def main(label='v37'):
 streams=g.programs([label]);seen=set();n=0
 for seed,flips,success,alias,mutation in itertools.product((0,1,127,128,254,255),range(4),(0,1),(0,1),(0,16)):
  c=g.Case(seed=seed,flips=flips,success=success,alias=alias,mutation=mutation,pattern=seed%4)
  initial=g.fixture(c);expected,calls,answer,ops=g.reference(initial,c);packet=next(v[2]for v in calls if v[0]==g.FACTORY);slot=next(v[1][3]for v in calls if v[0]==g.FACTORY)
  if success:
   calls.insert(-1,(g.COPY,(g.output(c)+16,'packet',112),packet))
   for i,v in enumerate(packet):expected[g.output(c)+16+i]=v
   expected[g.output(c)+0x9C]=0
  for name,words in streams.items():
   q=Machine(words,initial,c).run();assert(g.public(q.memory),q.calls,q.r[2],q.fp_ops)==(g.public(expected),calls,answer,ops),(name,c,'connected bytes/calls/return/FP')
   assert q.forwardings==[(q.target_home-112,0,0,12,slot,1)],q.forwardings
   assert q.allocations==[(0x2B,1,0xB4,1,slot,1)],q.allocations
   seen.update(pc for pc in q.visits if pc in HELPERS)
  n+=1
 report=dict(cases_per_stream=n,streams=len(streams),actual_wrapper_words=18,actual_base_factory_words=61,actual_memcpy_words=11,helper_words_visited=len(seen),mode_zero_allocation_arguments=True,all112_descriptor_bytes_copied=True,all12_payload_bytes_copied=True,failure_skips_both_copies=True,output_alias_and_owner_mutation=True,uncovered_factory_modes_and_optional_vector_path=True,deep_allocator='bounded hook',source_installed=False,c_match_credit=0)
 (O/'connected-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main(sys.argv[1]if len(sys.argv)>1 else'v37')
