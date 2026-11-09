"""Independent dispatch model and literal MIPS checks; no production writes."""
import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_camera_transition_dispatch_15128540_match as match
root=match.ROOT;out=root/match.BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object

ENTRY,ADDRESS=0x15128540,0x30000
PREDICATE,BUSY,FIRST,SECOND,THIRD,FOURTH,INITIALIZE,UPDATE,FINISH,FALLBACK=(
 0x151253CC,0x15128030,0x1512A360,0x1512E4B0,0x151219D0,0x1512D380,
 0x151256BC,0x151236D0,0x151284C4,0x15126378)
HELPERS=(PREDICATE,BUSY,FIRST,SECOND,THIRD,FOURTH,INITIALIZE,UPDATE,FINISH,FALLBACK)
SYMS={'func_%08X'%v:v for v in HELPERS}
u32=lambda v:v&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 flags:int=0
 first:int=0
 busy:int=0
 fallback:int=0
 mutation:int=0
 override:int=0
 phase:int=0
 address:int=ADDRESS
 pattern:int=0

def fixture(c):
 m={u32(STACK+i):(i*17+0xA5)&255 for i in range(-2048,2048)}
 m.update({u32(c.address+i):(i*29+c.pattern*37+0x5A)&255 for i in range(0x810)})
 put(m,u32(c.address+0x2C),c.flags)
 words=(0x7FA12345,0x80000000,0xFFFFFFFF)if c.pattern&1 else(0x3F800001,0x80000001,0x87654321)
 for i,w in enumerate(words):put(m,u32(c.address+0x2A4+i*4),w)
 return m

def snapshot(m,c,t):
 return(t,tuple(read(m,u32(c.address+offset))for offset in(0x2C,0x2A4,0x2A8,0x2AC,0x2BC,0x2C0,0x2C4,0x300)))

def effect(m,c,t,home):
 a=c.address
 if (t==PREDICATE and c.mutation&1)or(t==BUSY and c.mutation&2):put(m,u32(a+0x2C),c.override)
 if t==FIRST:
  if c.mutation&4:
   for i,w in enumerate((0xFFFFFFFF,0x7F800001,0x80000000)):put(m,u32(a+0x2A4+i*4),w)
  if c.mutation&64:
   for i in range(3):put(m,u32(a+0x2BC+i*4),0x12345678+i)
 if t==UPDATE and c.mutation&8:
  put(m,u32(a+0x2C),0xFFFFFFFF);put(m,u32(a+0x2C0),0xABCDEF01)
 if t==FINISH and c.mutation&16:put(m,u32(a+0x2C4),0x7FA12345)
 if c.mutation&32:
  for i in range(4):put(m,u32(home+i*4),0xB1000000+i)
 put(m,u32(a+0x300),u32(t^c.mutation))

def reference(initial,c,home=None):
 m=dict(initial);calls=[];snapshots=[];home=STACK+c.phase if home is None else home
 def call(t):
  calls.append((t,(u32(c.address),)));snapshots.append(snapshot(m,c,t));effect(m,c,t,home)
  return c.first if t==PREDICATE else c.busy if t==BUSY else c.fallback if t==FALLBACK else 0xDEADBEEF
 if call(PREDICATE):return m,calls,snapshots,1
 if call(BUSY):return m,calls,snapshots,0
 flags=read(m,u32(c.address+0x2C));picked=next((t for bit,t in zip((19,20,21,22),(FIRST,SECOND,THIRD,FOURTH))if flags&(1<<bit)),None)
 if picked is not None:
  call(picked)
  if picked==FIRST:
   words=[read(m,u32(c.address+0x2A4+i*4))for i in range(3)]
   for i,w in enumerate(words):put(m,u32(c.address+0x2BC+i*4),w)
   call(INITIALIZE)
  call(UPDATE);call(FINISH);return m,calls,snapshots,1
 if call(FALLBACK):call(FINISH);return m,calls,snapshots,1
 return m,calls,snapshots,0

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,syms=SYMS,connected=None,arguments=None):
  self.snapshots=[];self.targets={SYMS[k]:v for k,v in syms.items()}
  super().__init__(words,memory,c,entry=entry,s=syms,connected=connected,arguments=(u32(c.address),)if arguments is None else arguments)
 def record_call(self,t):
  actual={v:k for k,v in self.targets.items()}[t];args=tuple(map(u32,self.arguments(1)))
  self.calls.append((actual,args));self.snapshots.append(snapshot(self.memory,self.case,actual));self.events.append(('CALL',t,args))
 def hook(self,t):
  actual={v:k for k,v in self.targets.items()}[t];c=self.case
  effect(self.memory,c,actual,self.target_home)
  for i in range(4):self.put(u32(self.r[29]+i*4),0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  self.r[2]=u32(c.first if actual==PREDICATE else c.busy if actual==BUSY else c.fallback if actual==FALLBACK else 0xDEADBEEF)

def cases():
 for flags,first,busy,fallback,phase in itertools.product(range(16),(0,1,0x80000000,0xFFFFFFFF),(0,1,0x80000000),(0,1,0x80000000),(0,8)):
  yield Case(flags=(flags<<19)|0x800400A5,first=first,busy=busy,fallback=fallback,phase=phase,pattern=flags&1)
 for flags,mutation,phase in itertools.product((0,1,3,8,15),range(128),(0,8)):
  yield Case(flags=flags<<19,mutation=mutation,override=((flags^9)<<19)|0x40400,fallback=0xFFFFFFFF,phase=phase,pattern=mutation&1)
 for address,phase in itertools.product((0xFFFFFF00,STACK+0x40-0x2A4),(0,8)):
  for flags in(0,1,2,4,8,15):yield Case(flags=flags<<19,address=address,fallback=1,phase=phase,mutation=4)

def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+2048}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.snapshots,m.trace,m.current_pc,m.delay_of,m.dispatched_word)
def check(m,initial,c):
 expected,calls,snapshots,value=reference(initial,c)
 assert (public(m.memory),m.calls,m.snapshots,m.r[2])==(public(expected),calls,snapshots,value),c
 assert m.r[16]==m.before[16] and m.r[29]==STACK+c.phase and m.r[31]==m.before[31],c

def guest_checks():
 truth=list(struct.unpack_from('>80I',(root/'conker/conker.us.bin').read_bytes(),0x1559F0))
 text,fs,rs=parse_object(out/'qualified-owner.o');f=fs['func_15128540'];refs={a-f['value']:v for a,v in rs.items()if f['value']<=a<f['value']+f['size']}
 raw=bound_blob(text[f['value']:f['value']+f['size']],refs,SYMS);assert raw==truth
 visits=set();n=0;accesses=0
 for c in cases():
  initial=fixture(c);pair=[]
  for words in(truth,raw):
   m=Oracle(words,initial,c).run();check(m,initial,c);pair.append(m);visits.update((p-ENTRY)//4 for p in m.visits)
  assert state(pair[0])==state(pair[1]);n+=1;accesses+=pair[0].all_accesses
  if n%512==0:print('guest cases',n,flush=True)
 unreachable=sorted(set(range(80))-visits)
 assert unreachable==[16,74],unreachable
 faults=delay=0
 for c in(Case(),Case(flags=15<<19,mutation=127),Case(first=0x80000000),Case(busy=1),Case(fallback=1),Case(address=0xFFFFFF00,flags=1<<19)):
  initial=fixture(c);full=Oracle(truth,initial,c).run()
  for cut in range(full.all_accesses):
   pair=[]
   for words in(truth,raw):
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run();raise AssertionError('Missing fault')
    except AccessBoundary:pass
    pair.append(m)
   assert state(pair[0])==state(pair[1]);faults+=1;delay+=pair[0].delay_of is not None
 report=dict(cases_per_body=n,visited_words=len(visits),literal_words=80,unreachable_words=unreachable,accesses_per_body=accesses,
             fault_prefix_pairs=faults,delay_slot_faults=delay,all_predicate_return_signs=True,all_flag_combinations=True,
             helper_mutations=True,raw_float_bit_patterns=True,wrapped_and_stack_alias_guest_only=True,
             portable_native_or_whole_caller_claim=False)
 (out/'guest-contract.json').write_text(json.dumps(report,indent=2)+'\n');return report
