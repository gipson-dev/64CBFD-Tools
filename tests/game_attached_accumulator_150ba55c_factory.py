"""Execute the original payload factory, allocation wrapper and byte-copy loop."""
from dataclasses import dataclass
import itertools,json,struct
from tools.experiments import game_attached_accumulator_150ba55c_match as s
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests import game_attached_accumulator_150ba55c_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
FACTORY,SPAWN,ALLOC,ZERO,COPY=0x150ba4c0,0x15149130,0x15167a68,0x100226f0,0x10022ec0
@dataclass(frozen=True)
class Case(g.Case):
 outcome:int=1;variant:int=0xabcd00ef;context:int=0x87654321
def random(c):return g.u32((0,0xffffffff,0x80000000,0x7fffffff,126,127,30,31)[c.seed%8])
class Machine(FactoryOracle):
 def __init__(self,words,children,initial,c):
  super().__init__(words,initial,c,entry=FACTORY,s={},connected=children,arguments=(g.ACTOR,c.variant,c.context))
  self.factory_calls=[];self.observations=[];self.saved={i:self.r[i]for i in(*range(16,24),28,29,30)};self.saved_fp=tuple(self.f[20:])
 def record_call(self,t):
  counts={g.RNG:0,SPAWN:9,ALLOC:6,ZERO:2,COPY:3};assert t in counts,hex(t)
  args=tuple(self.arguments(counts[t]));self.pending=(t,args);self.factory_calls.append((t,args))
  if t==COPY:self.observations.append(g.data(self.memory,args[1],args[2]))
 def hook(self,t):
  target,args=self.pending;assert target==t;c=self.case
  if t==g.RNG:
   value=random(c)
   if c.mutation:self.memory[g.ACTOR+59]^=85
  elif t==ALLOC:
   assert args==(35,c.context,52,1,c.variant&255,1);value=g.RECORD if c.outcome else 0
  elif t==ZERO:
   assert args==(g.RECORD+20,16)
   for i in range(16):self.memory[g.RECORD+20+i]=0
   value=0xdeadbeef
  else:raise AssertionError(('unexpected opaque factory service',hex(t)))
  for i in range(max(4,len(args))):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=value;self.hi=self.lo=0xdeadbeef
def run(state):
 rom=state['rom'];elf=(s.FROZEN/'conker/build/conker.us.elf').read_bytes()
 def retail(entry,size,offset):
  blob=rom[offset:offset+size];at=elf_slot_offset(elf,entry,size);assert elf[at:at+size]==blob
  return list(struct.unpack('>%dI'%(size//4),blob))
 factory=retail(FACTORY,156,0xe7970);spawn=retail(SPAWN,196,0x1765e0);copy=retail(COPY,44,0x22ec0)
 children={**dict(zip(range(SPAWN,SPAWN+196,4),spawn)),**dict(zip(range(COPY,COPY+44,4),copy))}
 seen=set();n=0;normalized=s.normalizer.derive(state['raw_words']);assert normalized==state['retail_words']
 streams=(('raw',state['raw_words']),('retail',state['retail_words']),('normalized',normalized))
 for seed,outcome,mutation,phase in itertools.product((0,1,64,126,127,128,254,255),(0,1),(0,1),(0,8)):
  c=Case(seed=seed,mutation=mutation,phase=phase,outcome=outcome,variant=g.u32(0xabcd0000|seed),context=g.u32(0x87654321+seed*0x1020304));initial=g.fixture(c)
  g.put(initial,g.DT,g.bits(3.));want=dict(initial);home=g.STACK+phase;packet=struct.pack('>I',g.ACTOR)+bytes((seed&255,))+g.data(initial,home-7,3)+b'\0'*4
  if mutation:want[g.ACTOR+59]^=85
  duration=random(c)%9+15;events=[(g.RNG,()),(SPAWN,(duration,0xffffffff,82,0xffffffff,1,63,12,c.variant&255,c.context)),(ALLOC,(35,c.context,52,1,c.variant&255,1))]
  if outcome:
   g.put(want,g.RECORD+14,duration,2)
   for at,v in((13,1),(16,255),(17,82),(18,255),(19,63)):want[g.RECORD+at]=v
   for i in range(16):want[g.RECORD+20+i]=0
   for i,b in enumerate(packet):want[g.RECORD+40+i]=b
   events.extend(((ZERO,(g.RECORD+20,16)),(COPY,(g.RECORD+40,home-12,12))))
  machine=Machine(factory,children,initial,c).run();seen|=machine.visits
  assert machine.factory_calls==events,('factory calls',c,machine.factory_calls,events)
  assert g.public(machine.memory)==g.public(want),('factory public',c)
  assert machine.observations==([packet]if outcome else[]),('payload',c,machine.observations,packet)
  assert all(machine.r[i]==v for i,v in machine.saved.items())and tuple(machine.f[20:])==machine.saved_fp
  if outcome:
   for kind,words in streams:
    expected,service,prefix=g.reference(machine.memory,c,'raw'if kind=='raw'else'retail');assert not prefix
    child=g.Oracle(words,machine.memory,c).run()
    assert g.public(child.memory)==g.public(expected)and child.service.calls==service.calls,('callback seam',c,kind)
  n+=1
 spans={name:dict(words=size//4,visited=len(seen&set(range(entry,entry+size,4))),unvisited_offsets=[hex(i)for i in range(0,size,4)if entry+i not in seen])for name,entry,size in(('factory',FACTORY,156),('allocation_wrapper',SPAWN,196),('copy',COPY,44))}
 assert spans['factory']['unvisited_offsets']==spans['copy']['unvisited_offsets']==[]
 assert spans['allocation_wrapper']['unvisited_offsets']==['0x34','0x38']
 assert spawn[10]==0x33190002 and spawn[11]==0x13200003
 report=dict(passes=True,cases=n,callback_programs=3,complete_original_functions=spans,wrapper_flag_always_one_from_this_factory=True,two_alternate_flag_words_unreachable_from_this_caller=True,production_children_literal=True,copied_payload_bytes=12,retained_payload_padding_bytes=3,allocation_and_zero_services_modeled=True,source_installed=s.installed(),c_match_credit=0)
 (s.OUT/'factory-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
