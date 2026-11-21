"""Camera pair translation: bounded contracts and connected exact vector helpers."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,math,struct,sys
from tools.experiments import game_camera_origin_shift_15097798_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_camera_state_flags_151236d0_guest import static_reachable
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY,SIZE,BASE,GATE,SCALE,WORLD,OTHER=0x15097798,372,0x800DBFF0,0x800D2DB4,0x800D2E30,0x30000,0x50000
DELTA,NORMALIZE,LENGTH=0x15048F90,0x1504917C,0x150AD930
SYMS=dict(D_800DBFF0=BASE,D_800D2DB4=GATE,D_800D2E30=SCALE,func_15048F90=DELTA,func_1504917C=NORMALIZE)
u32=lambda n:n&0xFFFFFFFF
PATTERNS=((1.,2.,3.,4.,6.,3.),(0.,0.,0.,0.,0.,0.),(-3.,7.,-.5,2.,-1.,4.),(1.25,-2.5,3.75,7.5,1.125,-9.25),(-0.,0.,-0.,0.,-0.,0.),(1e-20,-1e-20,2e-20,2e-20,3e-20,-2e-20))
@dataclass(frozen=True)
class Case:
 gate:int=1;view:int=0;scale:int=1;pattern:int=0;mutation:int=0;alias:int=0;phase:int=0
def camera(c):
 a=u32(SCALE+4*c.view)
 return u32(a-(0x2A4 if c.alias==1 else 0x2AC))if c.alias in(1,2)else STACK-48+0x20-0x2A4 if c.alias==3 else WORLD
def selected(c):return u32(camera(c)+c.phase)if c.alias==3 else camera(c)
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,256)};p=selected(c)
 for b in(p,u32(p+0x9A0),OTHER):
  m.update({u32(b+i):(i*29+0x35)&255 for i in range(0x9A0)})
  for at,v in zip((0x2A4,0x2A8,0x2AC,0x2F8,0x2FC,0x300),PATTERNS[c.pattern]):put(m,u32(b+at),bits(v))
 for k in range(-1,5):put(m,u32(SCALE+4*(c.view+k)),k+2)
 put(m,u32(SCALE+4*c.view),c.scale);put(m,BASE,u32(p-u32(c.view*0x9A0)));put(m,GATE,c.gate)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+256}
def coordinates(m,p):return tuple(read(m,u32(p+at))for at in(0x2A4,0x2A8,0x2AC,0x2F8,0x2FC,0x300))
def op(a,b,kind):
 x,y=floating(a),floating(b)
 if kind=='sub':v=x-y
 elif kind=='mul':v=x*y
 elif kind=='add':v=x+y
 else:raise AssertionError(kind)
 return bits(v)
def delta(m,a,b,d):
 for off in(0,4,8):put(m,u32(d+off),op(read(m,u32(b+off)),read(m,u32(a+off)),'sub'))
def length(m,a):
 x,y,z=(read(m,u32(a+i))for i in(0,4,8));s=op(op(op(x,x,'mul'),op(y,y,'mul'),'add'),op(z,z,'mul'),'add')
 return bits(math.sqrt(floating(s)))
def normalize(m,a,d):
 value=length(m,a);v=floating(value);factor=bits(1./v)if v!=0. else value
 for off in(0,4,8):put(m,u32(d+off),op(read(m,u32(a+off)),factor,'mul'))
def effect(m,c,stage):
 if stage==DELTA:
  if c.mutation&1:put(m,BASE,OTHER)
  if c.mutation&2:put(m,u32(SCALE+4*c.view),-3)
  if c.mutation&4:put(m,GATE,0)
  if c.mutation&8:put(m,u32(selected(c)+0x2A4),bits(9.5));put(m,u32(selected(c)+0x2FC),bits(-7.25))
 if stage==NORMALIZE and c.mutation&16:
  for i,v in enumerate((.125,-.25,.5)):put(m,STACK+c.phase-48+0x20+4*i,bits(v))
def reference(initial,c,connected=False):
 m=dict(initial);calls=[];p=u32(read(m,BASE)+u32(c.view*0x9A0));d=STACK+c.phase-48+0x20
 if read(m,GATE):
  a=(u32(p+0x2A4),u32(p+0x2F8),d);calls.append((DELTA,a));delta(m,*a)
  if not connected:effect(m,c,DELTA)
  calls.append((NORMALIZE,(d,d)))
  if connected:calls.append((LENGTH,(d,)))
  normalize(m,d,d)
  if not connected:effect(m,c,NORMALIZE)
  for at,i,scale in((0x2A4,0,-2.5),(0x2A8,4,-2.),(0x2AC,8,-2.5),(0x2F8,0,-2.5),(0x2FC,4,-2.),(0x300,8,-2.5)):
   movement=op(op(read(m,d+i),bits(scale),'mul'),bits(float(signed(read(m,u32(SCALE+4*c.view))))),'mul')
   put(m,u32(p+at),op(read(m,u32(p+at)),movement,'add'))
 return public(m),calls,coordinates(m,p)
@lru_cache(maxsize=1)
def helper_code():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();code={}
 for entry,n in((DELTA,14),(NORMALIZE,28),(LENGTH,11)):
  at=entry-0x15000000+0x2D4B0;b=rom[at:at+4*n];p=elf_slot_offset(elf,entry,4*n);assert elf[p:p+4*n]==b
  code.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,b)))
 return code
class Machine(FactoryOracle):
 def __init__(self,words,c,m,connected=False):
  self.c=c;self.sqrt_visits=set()
  super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(u32(c.view),),connected=helper_code()if connected else None)
 def execute(self,w):
  if w>>26==0x11 and w>>21&31==16 and w&63==4:
   self.f[w>>6&31]=bits(math.sqrt(floating(self.f[w>>11&31])));self.sqrt_visits.add(self.current_pc);return
  super().execute(w)
 def record_call(self,t):
  n={DELTA:3,NORMALIZE:2,LENGTH:1}[t];a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  a=self.calls[-1][1]
  if t==DELTA:delta(self.memory,*a)
  elif t==NORMALIZE:normalize(self.memory,*a)
  else:raise AssertionError(hex(t))
  effect(self.memory,self.c,t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def programs():return[bound_blob(*payload(p,'func_15097798'),SYMS)for p in(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/generated_C3E20.c.o')]
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.current_pc,m.delay_of,m.sqrt_visits)
def corpus():
 for gate,view,scale,pattern in itertools.product((0,1,0x80000000,0xFFFFFFFF),(-1,0,1,3,255),(0,1,-1,3,-7,0x7FFFFFFF,0x80000000),range(6)):yield Case(gate=gate,view=view,scale=scale,pattern=pattern)
 for mutation,view,phase,pattern in itertools.product(range(32),(0,3),(0,8),(0,1,3)):yield Case(mutation=mutation,view=view,phase=phase,pattern=pattern)
 for alias,scale,pattern,phase in itertools.product((1,2,3),(1,0x3F800000,-1),(0,1,3),(0,8)):yield Case(alias=alias,scale=scale,pattern=pattern,phase=phase)
def compare(streams,c,connected=False):
 initial=fixture(c);expected=reference(initial,c,connected);machines=[]
 for words in streams:
  m=Machine(words,c,dict(initial),connected).run();assert(public(m.memory),m.calls,coordinates(m.memory,selected(c)))==expected,('model',c,connected,m.calls,expected[1])
  assert m.r[29]==STACK+c.phase
  for reg in(*range(16,24),30):assert m.r[reg]==m.before[reg]
  machines.append(m)
 assert state(machines[0])==state(machines[1])==state(machines[2]),(c,connected)
 return machines[0]
def run():
 streams=programs();assert streams[0]==streams[1]==streams[2];coverage=set();count=0
 for c in corpus():
  m=compare(streams,c);coverage.update((p-ENTRY)//4 for p in m.visits if ENTRY<=p<ENTRY+SIZE);count+=1
  if count%1000==0:print(json.dumps({'guest_cases':count}),flush=True)
 reachable=static_reachable(streams[0]);assert coverage==reachable,sorted(reachable-coverage)
 connected_cases=0;seen=set();sqrt_seen=set();code=helper_code()
 for pattern,scale,view,phase in itertools.product(range(6),(0,1,-3,0x7FFFFFFF),(0,3),(0,8)):
  m=compare(streams,Case(pattern=pattern,scale=scale,view=view,phase=phase),True);seen|=m.visits&code.keys();sqrt_seen|=m.sqrt_visits;connected_cases+=1
 desired=set()
 for entry,n in((DELTA,14),(NORMALIZE,28),(LENGTH,11)):desired|={entry+4*i for i in static_reachable([code[entry+4*i]for i in range(n)])}
 assert seen==desired and sqrt_seen=={LENGTH+40},(desired-seen,sqrt_seen)
 faults=0
 for c in(Case(gate=0),Case(),Case(alias=1,scale=0x3F800000),Case(alias=3,phase=8)):
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
 for label,old,new,c in(('x-z-scale',0x3C01C020,0x3C01C000,Case()),('y-scale',0x3C01C000,0x3C01C020,Case()),('inverted-gate',0x13200049,0x17200049,Case(gate=0))):
  changed=list(streams[0]);assert changed.count(old)==1;changed[changed.index(old)]=new
  initial=fixture(c);m=Machine(changed,c,dict(initial)).run();assert(public(m.memory),m.calls,coordinates(m.memory,selected(c)))!=reference(initial,c),label;controls.append(label)
 r={'cases_per_stream':count,'streams':3,'covered_words':len(coverage),'static_unreachable_words':sorted(set(range(93))-reachable),'access_fault_prefixes':faults,
 'connected_helper_cases_per_stream':connected_cases,'connected_helper_words':len(code),'connected_helper_covered_words':len(seen),'sqrt_instruction_fired':sorted(sqrt_seen),
 'complete_memory_private_stack_registers_calls_ordered_accesses_equal':True,'effective_controls':controls,
 'limits':'Bounded effectful delta/normalizer contracts plus separate actual original/current 53-word helper execution without injected effects. Default rounded single arithmetic and sqrt are modeled; no FCSR exceptions/hardware/gameplay claim. Overlapping scale/camera/private-frame storage and extreme views are guest-only.',
 'source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
