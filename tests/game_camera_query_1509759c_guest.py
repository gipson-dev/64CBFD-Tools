"""Camera query guest semantics, literal private state and connected vector code."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,math,struct,sys
from tools.experiments import game_camera_query_1509759c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY,SIZE,WORLD,OTHER,ACTOR,POINTS,PARAMS=0x1509759C,508,0x30000,0x40000,0x50000,0x60000,0x70000
BASE,LIMIT,FLAGS,POINTBASE,ANGLE,TABLE=0x800DBFF0,0x80082FA0,0x800D2DC0,0x800DC020,0x8009DF4C,0x8009DF38
LOOKUP,SIN,COS,DELTA,DOT=0x1505EEF4,0x15047D60,0x15047C00,0x15048F90,0x150AD900
SYMS=dict(D_800DBFF0=BASE,D_80082FA0=LIMIT,D_800D2DC0=FLAGS,D_800DC020=POINTBASE,D_8009DF4C=ANGLE,jtbl_8009DF38_game=TABLE,jtbl_8009DF38=TABLE,func_1505EEF4=LOOKUP,sinf=SIN,cosf=COS,func_15048F90=DELTA,func_150AD900=DOT)
SYMS['.rodata']=TABLE
TABLE_WORDS=(0x15097648,0x15097628,0x15097608,0x15097668,0x150976D4)
u32=lambda n:n&0xFFFFFFFF
# target XYZ, actor XYZ, packed point X/Z, value37C, value390, heading, sin/cos contracts
PATTERNS=((2.,9.,5.,3.,-4.,9.,-3,1,-.25,.5,0.,.5,.75),
 (0.,0.,0.,0.,0.,0.,0,0,0.,-0.,-1.5707963705062866,0.,1.),
 (-12.25,100.,.5,4.5,-200.,-9.,-32768,32767,1.125,-2.5,1.,-.5,.25),
 (math.nan,1.,2.,4.,5.,6.,1,-1,.25,-.75,math.nan,math.nan,.5),
 (-0.,0.,-0.,0.,0.,0.,0,0,-.125,.125,-.5,-0.,-1.),
 (1.,2.,3.,4.,5.,6.,1,3,math.nan,math.inf,0.,1.,0.))
@dataclass(frozen=True)
class Case:
 view:int=0;limit:int=3;command:int=33;key:int=1;pattern:int=0;outcome:int=1;mutation:int=0;phase:int=0;params:int=PARAMS

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+256}
def op(a,b,kind):
 x,y=floating(a),floating(b)
 return bits(x+y if kind=='add'else x-y if kind=='sub'else x*y)
def truncate(v):
 f=floating(v)
 return u32(int(f))if math.isfinite(f)and -2147483648.<=f<2147483648. else 0x80000000
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,256)};p=PATTERNS[c.pattern]
 for base,n in((WORLD,0x9A0),(OTHER,0x9A0),(ACTOR,0x100),(c.params,0x80)):
  m.update({base+i:(i*29+0x35)&255 for i in range(n)})
 for b in(WORLD,OTHER):
  for at,v in zip((0x2F8,0x2FC,0x300,0x37C,0x390,0x39C),(*p[:3],*p[8:11])):put(m,b+at,bits(v))
 for i,v in enumerate(p[3:6]):put(m,ACTOR+0x14+4*i,bits(v))
 index=u32(c.key)&0xFFF;point=POINTS+24*index
 m.update({point+i:0x35 for i in range(24)});put(m,point,p[6]&65535,2);put(m,point+2,12345,2);put(m,point+4,p[7]&65535,2)
 m[u32(FLAGS+36*u32(c.key))]=0x87
 put(m,BASE,u32(WORLD-u32(c.view*0x9A0)));put(m,LIMIT,c.limit);put(m,POINTBASE,POINTS);put(m,ANGLE,0x3FC90FDB)
 for i,v in enumerate(TABLE_WORDS):put(m,TABLE+4*i,v)
 for i,v in enumerate((c.view,c.command,c.key,0x12345678)):put(m,c.params+4*i,v)
 return m
def effects(m,c,t):
 if t==LOOKUP:
  if c.mutation&1:put(m,BASE,OTHER)
  if c.mutation&2:put(m,WORLD+0x39C,bits(-.75))
  if c.mutation&4:put(m,ANGLE,bits(.25))
  if c.mutation&8:put(m,c.params+8,0xFFFFFFFF)
 if t==SIN and c.mutation&16:
  put(m,WORLD+0x2F8,bits(7.25));put(m,WORLD+0x39C,bits(9.))
 if t==COS and c.mutation&32:put(m,WORLD+0x300,bits(-6.5))
def delta(m,a,b,d):
 for i in(0,4,8):put(m,d+i,op(read(m,b+i),read(m,a+i),'sub'))
def dot(m,a,b):
 x=op(read(m,a),read(m,b),'mul');y=op(read(m,a+4),read(m,b+4),'mul');z=op(read(m,a+8),read(m,b+8),'mul')
 return op(op(x,y,'add'),z,'add')
def reference(initial,c):
 m=dict(initial);calls=[];p=WORLD;d=STACK+c.phase-80+0x30;f=d+12
 if signed(c.limit)<signed(u32(c.view)):return public(m),calls,0
 if c.command in(30,31):return public(m),calls,truncate(op(read(m,p+(0x37C if c.command==30 else 0x390)),bits(65536.),'mul'))
 if c.command==29:return public(m),calls,m[u32(FLAGS+36*u32(c.key))]
 if c.command==32:
  point=POINTS+24*(u32(c.key)&0xFFF);x=op(read(m,p+0x2F8),bits(float(((read(m,point,2)^32768)-32768))),'sub');z=op(read(m,p+0x300),bits(float(((read(m,point+4,2)^32768)-32768))),'sub')
  squared=op(op(x,x,'mul'),op(z,z,'mul'),'add');return public(m),calls,truncate(bits(math.sqrt(floating(squared))))
 if c.command!=33:return public(m),calls,0
 calls.append((LOOKUP,(u32(c.key)&0xFFF,)));effects(m,c,LOOKUP)
 if not c.outcome:return public(m),calls,0xFFFFFFFF
 angle=op(read(m,p+0x39C),read(m,ANGLE),'add');calls.append((SIN,(angle,)));effects(m,c,SIN);put(m,f,bits(PATTERNS[c.pattern][11]));put(m,f+4,0)
 calls.append((COS,(angle,)));effects(m,c,COS);put(m,f+8,bits(PATTERNS[c.pattern][12]))
 calls.append((DELTA,(p+0x2F8,ACTOR+0x14,d)));delta(m,p+0x2F8,ACTOR+0x14,d);put(m,d+4,0)
 calls.append((DOT,(f,d)));answer=0xFFFFFFFF if 0.<=floating(dot(m,f,d))else 1
 return public(m),calls,answer
@lru_cache(maxsize=1)
def helper_code():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();code={}
 for entry,n in((DELTA,14),(DOT,12)):
  b=rom[entry-0x15000000+0x2D4B0:entry-0x15000000+0x2D4B0+4*n];at=elf_slot_offset(elf,entry,4*n);assert elf[at:at+4*n]==b
  code.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,b)))
 return code
class Machine(FactoryOracle):
 def __init__(self,words,c,m,connected=False):
  self.c=c;self.sqrt_visits=set();self.trunc_visits=set()
  super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(u32(c.view),u32(c.command),c.params),connected=helper_code()if connected else None)
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(4,13):
   value=self.f[w>>11&31]
   if w&63==4:self.f[w>>6&31]=bits(math.sqrt(floating(value)));self.sqrt_visits.add(self.current_pc)
   else:self.f[w>>6&31]=truncate(value);self.trunc_visits.add(self.current_pc)
   return
  super().execute(w)
 def record_call(self,t):
  a=(self.f[12],)if t in(SIN,COS)else tuple(self.arguments({LOOKUP:1,DELTA:3,DOT:2}[t]))
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  a=self.calls[-1][1];value=0;floating_result=False
  if t==LOOKUP:value=ACTOR if self.c.outcome else 0
  elif t in(SIN,COS):value=bits(PATTERNS[self.c.pattern][11 if t==SIN else 12]);floating_result=True
  elif t==DELTA:delta(self.memory,*a)
  elif t==DOT:value=dot(self.memory,*a);floating_result=True
  else:raise AssertionError(hex(t))
  effects(self.memory,self.c,t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  if floating_result:self.f[0]=value
  else:self.r[2]=value
def programs():return[bound_blob(*payload(p,'func_1509759C'),SYMS)for p in(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/generated_C3E20.c.o')]
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.current_pc,m.delay_of,m.sqrt_visits,m.trunc_visits)
def corpus():
 for command,view,limit,pattern,key,outcome in itertools.product((0,28,29,30,31,32,33,34,0xFFFFFFFF),(-1,0,3,4),(0,3),range(6),(0,1,0x1001,-1),(0,1)):
  yield Case(view=view,limit=limit,command=command,pattern=pattern,key=key,outcome=outcome)
 for mutation,pattern,phase in itertools.product(range(64),(0,1,3),(0,8)):yield Case(mutation=mutation,pattern=pattern,phase=phase)
def compare(streams,c,connected=False):
 initial=fixture(c);expected=reference(initial,c);machines=[]
 for words in streams:
  m=Machine(words,c,dict(initial),connected).run();assert(public(m.memory),m.calls,m.r[2])==expected,('model',c,m.calls,expected[1],hex(m.r[2]),hex(expected[2]))
  machines.append(m)
 assert state(machines[0])==state(machines[1])==state(machines[2]),c
 return machines[0]
def run():
 streams=programs();assert streams[0]==streams[1]==streams[2];coverage=set();count=0
 for c in corpus():
  m=compare(streams,c);coverage|={p for p in m.visits if ENTRY<=p<ENTRY+SIZE};count+=1
 assert coverage==set(range(ENTRY,ENTRY+SIZE,4)),sorted(set(range(ENTRY,ENTRY+SIZE,4))-coverage)
 seen=set();connected_count=0
 for pattern,outcome,mutation,phase in itertools.product(range(6),(0,1),(0,7,16,32,63),(0,8)):
  m=compare(streams,Case(pattern=pattern,outcome=outcome,mutation=mutation,phase=phase),True);seen|=m.visits&helper_code().keys();connected_count+=1
 assert seen==set(helper_code()),set(helper_code())-seen
 faults=0
 for c in(Case(view=4),Case(command=29),Case(command=32),Case(outcome=0),Case(mutation=63)):
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
 for label,index,word,c in(('wrong-limit',13,0x0098082A,Case()),('wrong-key-mask',80,0x308800FF,Case(key=0x101)),('wrong-dot-order',114,0x4608003E,Case(pattern=0))):
  changed=list(streams[0]);assert changed[index]!=word;changed[index]=word
  m=Machine(changed,c,fixture(c)).run();effective=(public(m.memory),m.calls,m.r[2])!=reference(fixture(c),c)
  assert effective,label;controls.append(label)
 # A table permutation changes semantic command ownership without changing text.
 c=Case(command=29);m=fixture(c);put(m,TABLE,TABLE_WORDS[2]);expected=reference(m,c);model=Machine(streams[0],c,m).run();assert(public(model.memory),model.calls,model.r[2])!=expected;controls.append('swapped-command-table')
 r={'cases_per_stream':count,'streams':3,'covered_words':len(coverage),'access_fault_prefixes':faults,'connected_helper_cases_per_stream':connected_count,'connected_helper_words':len(seen),'effective_controls':controls,
  'limits':'Lookup and sin/cos use explicit effectful contracts. Exact delta/dot instructions are additionally connected. Default single arithmetic, sqrt and indefinite truncation results are modeled; FCSR flags/exceptions/hardware/gameplay are outside scope. Sparse invalid native indices and invalid float casts are guest-only.','source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
