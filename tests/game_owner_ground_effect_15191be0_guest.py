"""Ground-effect packet: complete guest words, copied padding, ABI and fault cuts."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
from tools.experiments import game_owner_ground_effect_15191be0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_camera_state_flags_151236d0_guest import static_reachable
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,SIZE,OWNER,POSITION,OUTPUT,MARK=0x15191BE0,372,0x30000,0x31000,0x50000,0x70000
SURFACE,FACTORY,COPY,ALLOCATE,ZERO=0x1504715C,0x15149130,0x10022EC0,0x15167A68,0x100226F0
SYMS={'func_1504715C':SURFACE,'func_15149130':FACTORY,'memcpy':COPY}
COUNTS={ENTRY:18,SURFACE:2,FACTORY:9,COPY:3,ALLOCATE:6,ZERO:2}
u32=lambda n:n&0xFFFFFFFF
s16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 seed:int=0;life:int=-1;channel:int=255;priority:int=255;outcome:int=1;mutation:int=0;alias:int=0;null:int=0;phase:int=0

def args(c):
 values=[OWNER if not c.null else 0,OWNER if c.alias else POSITION,c.channel,0x80000000,0x7FC12345,c.life,
         0x3F800000,0xBF800000,0xABCD8001,0x12347FFF,0xAA00FF80,0xBB00AAFF,
         0x00000001,0x7F800000,0xFF800000,0xCC00AA81,c.priority,0x13579BDF]
 if c.seed:
  for i in (3,4,6,7,8,9,10,11,12,13,14,15,17):values[i]=u32(c.seed*0x1020304+i*0x1234567)
 return tuple(map(u32,values))
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2304)}
 for b,n in ((OWNER-32,640),(POSITION-32,96),(OUTPUT-32,256),(MARK,32)):
  m.update({b+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 m[OWNER+0x3B]=c.seed&255
 return m
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m):return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def surface(m,c,p,owner,home):
 for i in range(9):put(m,p+4*i,u32(0x12345678+c.seed*0x10203+i*0x11111111))
 if c.mutation&1:
  m[owner+0x3B]^=0x55
  for i in range(3):put(m,(OWNER if c.alias else POSITION)+4*i,0xDEAD0000+i)
 if c.mutation&2:
  for i in range(5,18):put(m,home+4*i,u32(0x87654321+i*0x10203))
def factory_effect(m,c):
 put(m,MARK,0x13579BDF)
 if c.mutation&4:
  m[OWNER+0x3B]^=0xAA
  for i in range(3):put(m,(OWNER if c.alias else POSITION)+4*i,0xFACE0000+i)
def initialize(m,a):
 put(m,OUTPUT+14,a[0],2)
 for off,index in ((13,4),(16,1),(17,2),(18,3),(19,5)):m[OUTPUT+off]=a[index]&255
 for i in range(16):m[OUTPUT+20+i]=0
def reference(initial,c,arguments=None,home=None,connected=False):
 m=dict(initial);a=args(c)if arguments is None else arguments;home=STACK+c.phase if home is None else home
 calls=[];observations=[];packet=home-108
 if not a[0]:return public(m),calls,0,observations
 put(m,packet,a[0]);m[packet+4]=m[a[0]+0x3B]
 source=data(m,a[1],12)
 for i,b in enumerate(source):m[packet+8+i]=b
 for off,v in ((20,(a[2]&255)<<6),(24,0),(28,a[3]),(32,a[4])):put(m,packet+off,v)
 calls.append((SURFACE,(packet+36,a[0])));surface(m,c,packet+36,a[0],home)
 fresh=list(a)
 if c.mutation&2:
  for i in range(5,18):fresh[i]=read(m,home+4*i)
 for off,i in ((72,6),(76,7),(88,12),(92,13),(96,14)):put(m,packet+off,fresh[i])
 for off,i in ((80,8),(82,9)):put(m,packet+off,fresh[i],2)
 for off,i in ((84,10),(85,11),(100,15)):m[packet+off]=fresh[i]&255
 lifetime=s16(fresh[5]);factory=(u32(300 if lifetime==-1 else lifetime),0xFFFFFFFF,29,0xFFFFFFFF,int(lifetime!=-1),29,104,fresh[16]&255,fresh[17])
 calls.append((FACTORY,factory))
 if connected:calls.append((ALLOCATE,(35,fresh[17],144,1,fresh[16]&255,1)))
 factory_effect(m,c)
 result=OUTPUT if c.outcome else 0
 if result:
  initialize(m,factory)
  if connected:calls.append((ZERO,(result+20,16)))
  calls.append((COPY,(result+40,packet,104)));snapshot=data(m,packet,104);observations.append((snapshot,result+40,104))
  for i,b in enumerate(snapshot):m[result+40+i]=b
 return public(m),calls,result,observations
class Machine(FactoryOracle):
 def __init__(self,words,c,m,connected=None):
  self.c=c;self.observations=[]
  super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=args(c),connected=connected)
 def record_call(self,t):
  a=tuple(map(u32,self.arguments(COUNTS[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==COPY:self.observations.append((data(self.memory,a[1],a[2]),a[0],a[2]))
 def hook(self,t):
  a=self.calls[-1][1];c=self.c
  if t==SURFACE:surface(self.memory,c,a[0],a[1],self.target_home);value=0xDEADBEEF
  elif t in(FACTORY,ALLOCATE):
   factory_effect(self.memory,c);value=OUTPUT if c.outcome else 0
   if t==FACTORY and value:initialize(self.memory,a)
  elif t==ZERO:
   assert a[1]==16
   for i in range(a[1]):self.memory[a[0]+i]=0
   value=0xDEADBEEF
  else:
   assert t==COPY and a[2]==104
   snapshot=data(self.memory,a[1],a[2])
   for i,b in enumerate(snapshot):self.memory[a[0]+i]=b
   value=a[0]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def programs():return[bound_blob(*payload(p,'func_15191BE0'),SYMS)for p in(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/generated_1BF090.c.o')]
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.observations,m.current_pc,m.delay_of)
def corpus():
 for life,channel,priority,outcome,mutation,alias,phase in itertools.product((-32768,-2,-1,0,1,32767,0xABCDFFFF),(0,1,128,255,0xABCDEF80),(0,255,0xABCDEF81),(0,1),range(8),range(2),(0,8)):
  yield Case(seed=(channel+life)&15,life=life,channel=channel,priority=priority,outcome=outcome,mutation=mutation,alias=alias,phase=phase)
 for n in range(256):yield Case(seed=n,life=n,channel=n,priority=n,null=1)
def helpers():
 rom=(root/'conker/conker.us.bin').read_bytes();code={}
 for address,offset,n in ((FACTORY,0x1765E0,49),(COPY,0x22EC0,11)):
  code.update(zip(range(address,address+n*4,4),struct.unpack_from('>%dI'%n,rom,offset)))
 return code
def compare(streams,c,connected=False):
 initial=fixture(c);expected=reference(initial,c,connected=connected);machines=[]
 for words in streams:
  m=Machine(words,c,dict(initial),helpers()if connected else None).run()
  assert(public(m.memory),m.calls,m.r[2],m.observations)==expected,('model',c,m.calls,expected[1])
  assert m.r[29]==STACK+c.phase
  for reg in(*range(16,24),30):assert m.r[reg]==m.before[reg]
  machines.append(m)
 assert state(machines[0])==state(machines[1])==state(machines[2]),c
 return machines[0]
def run():
 streams=programs();assert streams[0]==streams[1]==streams[2];coverage=set();count=0
 for c in corpus():
  m=compare(streams,c);coverage.update((p-ENTRY)//4 for p in m.visits if ENTRY<=p<ENTRY+SIZE);count+=1
  if count%4000==0:print(json.dumps({'guest_cases':count}),flush=True)
 reachable=static_reachable(streams[0]);assert coverage==reachable,sorted(reachable-coverage)
 connected=0
 for life,mutation,outcome,alias,phase in itertools.product((-32768,-1,0,32767),range(8),(0,1),(0,1),(0,8)):
  compare(streams,Case(life=life,mutation=mutation,outcome=outcome,alias=alias,phase=phase),True);connected+=1
 faults=0
 for c in(Case(),Case(life=0,outcome=0,mutation=3),Case(null=1),Case(alias=1,mutation=7,phase=8)):
  full=compare(streams,c)
  for cut in range(full.all_accesses):
   states=[]
   for words in streams:
    m=Machine(words,c,fixture(c));m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(m))
   assert states[0]==states[1]==states[2];faults+=1
 controls=[]
 for label,old,new,c in(('wrong-identity',0x90EF003B,0x90EF003A,Case()),('wrong-kind',0x2406001D,0x2406001C,Case()),('wrong-default-duration',0x2403012C,0x2403012D,Case()),('wrong-payload-size',0x24060068,0x24060064,Case())):
  changed=list(streams[0]);assert changed.count(old)==1;changed[changed.index(old)]=new
  try:
   m=Machine(changed,c,fixture(c)).run();assert(public(m.memory),m.calls,m.r[2],m.observations)!=reference(fixture(c),c),label
  except AssertionError as e:
   if str(e)==label:raise
  controls.append(label)
 r={'cases_per_stream':count,'streams':3,'covered_words':len(coverage),'static_unreachable_words':sorted(set(range(93))-reachable),'connected_factory_and_copy_cases_per_stream':connected,'access_fault_prefixes':faults,'complete_memory_private_stack_registers_calls_ordered_accesses_equal':True,'effective_controls':controls,'limits':'Surface helper uses an explicit 36-byte write contract and caller-home/owner/position mutations. Original factory and copy are connected separately; the current memcpy is non-exact and is bounded by its byte-copy contract. Portable C padding, hardware and gameplay are not claimed.','source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':run()
