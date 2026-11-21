"""Timed effect updater: complete guest state and bounded effectful callbacks."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
from tools.experiments import game_timed_effect_update_15188b74_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_camera_state_flags_151236d0_guest import static_reachable
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,SIZE,HEAD,DELTA,NODES=0x15188B74,396,0x800DF7C8,0x800BE9E4,(0x30000,0x30100,0x30200)
UPDATES,CLEANUP,FREE=(0x15188E48,0x15188F84),(0x151895A4,0x151895CC),0x10004074
SYMS=dict(D_800DF7C8=HEAD,D_800BE9E4=DELTA,D_8008D580=0x8008D580,D_8008D588=0x8008D588,func_10004074=FREE)
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
half=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 timer:int=1;opacity:int=20;delta:int=1;list:int=0;count:int=3;phase:int=0;mutation:int=0;pattern:int=0
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,256)}
 for b,n in((HEAD-8,24),(DELTA-4,12),*( (p-8,48)for p in NODES)):
  m.update({b+i:(i*29+c.pattern*11+0x35)&255 for i in range(n)})
 put(m,HEAD,NODES[0]if c.count and c.list==0 else 0);put(m,HEAD+4,NODES[0]if c.count and c.list==1 else 0)
 put(m,DELTA,c.delta)
 for i,p in enumerate(NODES):
  m[p]=(c.pattern+i)&1;m[p+3]=(c.opacity+((17*i)if c.pattern&2 else 0))&255
  put(m,p+6,c.timer if i==0 or not c.pattern&1 else(1,0,-1)[i],2)
  put(m,p+12,NODES[i+1]if i+1<c.count else 0);put(m,p+16,0)
 for base,values in((0x8008D580,UPDATES),(0x8008D588,CLEANUP)):
  for i,v in enumerate(values):put(m,base+4*i,v)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+256}
def effect(m,c,t,p):
 if t in UPDATES:
  if c.mutation&1:put(m,p+6,0,2)
  if c.mutation&2:m[p+3]=(1,0,255)[NODES.index(p)]
  if c.mutation&4:put(m,p+12,0)
  if c.mutation&8:m[p]^=1
  if c.mutation&16:put(m,DELTA,3)
  if c.mutation&32:put(m,HEAD+4*c.list,0)
 elif t==FREE:m[p+2]=0xA7
 elif t in CLEANUP:m[p+1]^=0x53
 else:raise AssertionError(hex(t))
def reference(initial,c):
 m=dict(initial);calls=[];head=HEAD+4*c.list;p=read(m,head);previous=0
 def call(t,p):calls.append((t,(p,)));effect(m,c,t,p)
 while p:
  following=read(m,p+12);timer=half(read(m,p+6,2))
  if timer:put(m,p+6,timer-read(m,DELTA),2)
  if half(read(m,p+6,2))<0:put(m,p+6,0,2)
  call(UPDATES[m[p]],p);opacity=m[p+3]
  if read(m,p+6,2):
   if opacity!=255:
    opacity=signed(opacity+read(m,DELTA)*16)
    if opacity>=256:opacity=255
    m[p+3]=opacity&255
   previous=p
  elif opacity:
   opacity=signed(opacity-read(m,DELTA)*8)
   if opacity<0:opacity=0
   if opacity==0:
    put(m,previous+12 if previous else head,following)
    call(CLEANUP[m[p]],p);call(FREE,p)
   else:m[p+3]=opacity&255;previous=p
  p=following
 return public(m),calls
class Machine(FactoryOracle):
 def __init__(self,words,c,m):
  self.c=c;super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(c.list,))
 def record_call(self,t):
  assert t in(*UPDATES,*CLEANUP,FREE),hex(t)
  a=tuple(self.arguments(1));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  effect(self.memory,self.c,t,self.calls[-1][1][0])
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def programs():return[bound_blob(*payload(p,'func_15188B74'),SYMS)for p in(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/generated_1B5CC0.c.o')]
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.current_pc,m.delay_of)
def corpus():
 for timer,opacity in itertools.product((-32768,-1,0,1,2,32767),range(256)):yield Case(timer=timer,opacity=opacity,count=1)
 for timer,opacity,delta,list_,phase in itertools.product((-32768,-1,0,1,32767),(0,1,7,8,20,239,240,254,255),(-1,0,1,2,16,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1),(0,8)):
  yield Case(timer=timer,opacity=opacity,delta=delta,list=list_,phase=phase,pattern=(opacity^delta)&3)
 for mutation,count,pattern in itertools.product(range(64),(0,1,3),range(4)):yield Case(timer=2,opacity=8,mutation=mutation,count=count,pattern=pattern)
 for c in(Case(count=0),Case(timer=0,opacity=0),Case(timer=0,opacity=20),Case(timer=0,opacity=1),Case(timer=1,opacity=255),Case(timer=32767,opacity=240)):
  yield c
def compare(streams,c):
 initial=fixture(c);expected=reference(initial,c);machines=[]
 for w in streams:
  m=Machine(w,c,dict(initial)).run()
  assert(public(m.memory),m.calls)==expected,('model',c,m.calls,expected[1])
  assert m.r[29]==STACK+c.phase
  for reg in range(16,24):assert m.r[reg]==m.before[reg],('saved',reg,c)
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
 for c in(Case(count=0),Case(timer=2,opacity=240),Case(timer=0,opacity=8,mutation=12),Case(timer=0,opacity=0)):
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
 for label,old,new,c in(('fade-in-rate',0x000C6900,0x000C68C0,Case(timer=2,opacity=1)),('fade-out-rate',0x000E78C0,0x000E7880,Case(timer=0,opacity=8)),('timer-clamp-field',0xA6000006,0xA6000008,Case(timer=-1))):
  changed=list(streams[0]);assert changed.count(old)==1;changed[changed.index(old)]=new
  initial=fixture(c);m=Machine(changed,c,dict(initial)).run();assert(public(m.memory),m.calls)!=reference(initial,c),label;controls.append(label)
 r={'cases_per_stream':count,'streams':3,'covered_words':len(coverage),'static_unreachable_words':sorted(set(range(99))-reachable),'access_fault_prefixes':faults,
 'complete_memory_private_stack_registers_calls_ordered_accesses_equal':True,'effective_controls':controls,
 'limits':'Two verified callback-table selectors and free use bounded side-effect contracts with caller clobbers. Original full callbacks, full caller, hardware and gameplay are not claimed. All tick bit patterns are guest machine evidence; native C uses its defined arithmetic domain.',
 'source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
