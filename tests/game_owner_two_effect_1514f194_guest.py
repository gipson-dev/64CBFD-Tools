"""Two-effect owner initializer: ordered ABI calls, private state and fault cuts."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,sys
from tools.experiments import game_owner_two_effect_1514f194_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_camera_state_flags_151236d0_guest import static_reachable
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,SIZE,OWNER,FIRST,SECOND,GATE,PRESET0,PRESET1=0x1514F194,372,0x30000,0x40000,0x41000,0x800BE616,0x800A5958,0x800A5964
CHANNEL,INIT,OPTIONAL,FLAGS,STATE,CREATE,ATTACH=0x151D0F60,0x151BB044,0x151BC074,0x151BD2F8,0x151B9F00,0x15160A58,0x1514EC1C
SYMS={f'func_{p:08X}':p for p in(CHANNEL,INIT,OPTIONAL,FLAGS,STATE,CREATE,ATTACH)}
SYMS.update(D_800BE616=GATE,D_800A5958=PRESET0,D_800A5964=PRESET1)
COUNTS={CHANNEL:4,INIT:1,OPTIONAL:1,FLAGS:3,STATE:3,CREATE:16,ATTACH:3}
@dataclass(frozen=True)
class Case:
 gate:int=0;first:int=1;second:int=1;mutation_step:int=0;mutation_value:int=0;alias:int=0;phase:int=0
def owner(c):return(OWNER,PRESET0,GATE-16,0)[c.alias]
def answer(c,i):return(0,FIRST,owner(c),SECOND)[c.first]if i==0 else(0,SECOND,owner(c),FIRST)[c.second]
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,256)}
 for b,n in((OWNER,96),(FIRST,64),(SECOND,64),(PRESET0,96),(GATE-32,96)):
  m.update({b+i:(i*29+0x35)&255 for i in range(n)})
 m[GATE]=c.gate;return m
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+256}
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def effect(m,c,ordinal,p=None):
 if p is None:p=owner(c)
 if p:put(m,p+16+4*(ordinal%3),0x12340000+ordinal)
 if ordinal==c.mutation_step:m[GATE]=c.mutation_value
def reference(initial,c):
 m=dict(initial);calls=[];observations=[];p=owner(c)
 def call(t,a):
  calls.append((t,a))
  if t==CREATE:observations.append((a,data(m,a[2],12)))
  effect(m,c,len(calls))
 call(CHANNEL,(p,1,255,1));call(CHANNEL,(p,2,255,1));call(INIT,(p,))
 if m[GATE]==0:call(OPTIONAL,(p,))
 call(FLAGS,(p,255,1));call(STATE,(p,255,1))
 call(CREATE,(p,1,PRESET0,2,300,12,255,255,255,2,0,0xFFFFFFFF,0,0,255,1))
 call(CREATE,(p,1,PRESET1,2,300,15,255,0,0,255,1,0xFFFFFFFF,0,0,255,1))
 result=answer(c,1)
 if result:call(ATTACH,(result,p,25))
 return public(m),calls,observations
class Machine(FactoryOracle):
 def __init__(self,words,c,m):
  self.c=c;self.observations=[];self.factories=0
  super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(owner(c),))
 def record_call(self,t):
  a=tuple(self.arguments(COUNTS[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==CREATE:self.observations.append((a,data(self.memory,a[2],12)))
 def hook(self,t):
  a=self.calls[-1][1];effect(self.memory,self.c,len(self.calls),a[1]if t==ATTACH else a[0]);value=0xA5000002
  if t==CREATE:value=answer(self.c,self.factories);self.factories+=1
  # A callee may overwrite its incoming argument homes, including stack args.
  for i in range(COUNTS[t]):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def programs():return[bound_blob(*payload(p,'func_1514F194'),SYMS)for p in(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/generated_179F30.c.o')]
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.observations,m.current_pc,m.delay_of)
def corpus():
 for gate,first,second in itertools.product(range(256),(0,1),(0,1)):yield Case(gate=gate,first=first,second=second)
 for step,value,alias,phase,first,second in itertools.product(range(1,9),(0,1,128,255),range(4),(0,8),range(4),(0,1)):
  yield Case(gate=1,first=first,second=second,mutation_step=step,mutation_value=value,alias=alias,phase=phase)
 for first,second in itertools.product(range(4),range(4)):yield Case(first=first,second=second)
def compare(streams,c):
 initial=fixture(c);expected=reference(initial,c);machines=[]
 for w in streams:
  m=Machine(w,c,dict(initial)).run();assert(public(m.memory),m.calls,m.observations)==expected,('model',c,m.calls,expected[1])
  assert m.r[29]==STACK+c.phase
  for reg in(*range(16,24),30):assert m.r[reg]==m.before[reg],('saved',reg,c)
  machines.append(m)
 assert state(machines[0])==state(machines[1])==state(machines[2]),c
 return machines[0]
def run():
 streams=programs();assert streams[0]==streams[1]==streams[2];coverage=set();count=0
 for c in corpus():
  m=compare(streams,c);coverage.update((p-ENTRY)//4 for p in m.visits if ENTRY<=p<ENTRY+SIZE);count+=1
  if count%2000==0:print(json.dumps({'guest_cases':count}),flush=True)
 reachable=static_reachable(streams[0]);assert coverage==reachable,sorted(reachable-coverage)
 faults=0
 for c in(Case(),Case(gate=1,first=0,second=0),Case(gate=1,mutation_step=3,mutation_value=0,alias=2,phase=8)):
  full=compare(streams,c)
  for cut in range(full.all_accesses):
   states=[]
   for w in streams:
    m=Machine(w,c,fixture(c));m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(m))
   assert states[0]==states[1]==states[2];faults+=1
 controls=[]
 for label,old,new,c in(('second-channel',0x24050002,0x24050003,Case()),('attachment-key',0x24060019,0x24060018,Case()),('inverted-result-gate',0x10400004,0x14400004,Case(second=0))):
  changed=list(streams[0]);assert changed.count(old)==1;changed[changed.index(old)]=new
  initial=fixture(c);m=Machine(changed,c,dict(initial)).run();assert(public(m.memory),m.calls,m.observations)!=reference(initial,c),label;controls.append(label)
 r={'cases_per_stream':count,'streams':3,'covered_words':len(coverage),'static_unreachable_words':sorted(set(range(93))-reachable),'access_fault_prefixes':faults,
 'complete_memory_private_stack_registers_calls_ordered_accesses_equal':True,'all_16_argument_homes_clobbered_after_factory':True,'effective_controls':controls,
 'limits':'All seven helper interfaces use bounded side-effect contracts and aggressive ABI clobbers. Null/overlapping owners are guest ABI probes, not full helper or portable C acceptance. No full helper, hardware or gameplay claim.',
 'source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
