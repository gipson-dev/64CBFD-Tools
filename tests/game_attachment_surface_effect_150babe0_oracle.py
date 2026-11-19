"""Independent semantic contract and literal/private-cache MIPS qualification.

This private packet does not install source or guards and earns no matching credit.
"""
from pathlib import Path
from dataclasses import dataclass,replace
import hashlib,itertools,json,math,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.test_game_point_transform_match import put,read

from tools.experiments import game_attachment_surface_effect_150babe0_match as s
from tools.tests.game_attachment_surface_effect_150babe0_normalizer import derive
ROOT=s.ROOT;PACKET=s.OUT
ENTRY=0x150babe0
ACTOR,BASE,ALT,MARK,MODEL,EFFECT,QUEUE=0x60000,0x80000,0xa0000,0x70000,0x90000,0xb0000,0xc0000
BASE_PTR,INDEX,SCALE,QUEUE_PTR=0x800dbff0,0x80082fa4,0x8009fe70,0x80088750
MATRIX,COMMAND,EVENT,REAL,RNG,FINAL,PREP,QUERY,CREATE,APPEND,FREE=0x15142314,0x15143e94,0x15165f80,0x150ada68,0x150ada20,0x1514c678,0x1504715c,0x15046c80,0x1513c73c,0x1518abd0,0x1516972c
COUNTS={MATRIX:3,COMMAND:2,EVENT:9,REAL:0,RNG:0,FINAL:12,PREP:2,QUERY:4,CREATE:14,APPEND:3,FREE:1}
u32=lambda n:n&0xffffffff
short=lambda v:u32(((v&65535)^32768)-32768)
public=lambda m:{a:b for a,b in m.items()if not STACK-4096<=a<STACK+4096}
POINTS=((0.,-0.,0.),(-0.,0.,-0.),(17.75,-91.5,255.25),(-17.75,91.5,-255.25),(32768.5,-32769.5,65535.75),(-65536.5,1000000.25,-1000000.25))
@dataclass(frozen=True)
class Case:
 seed:int=0;gate:int=0;selector:int=0;context:int=255;hit:int=1;created:int=1;appended:int=1;mutation:int=0;phase:int=0

def cases():
 for seed in range(256):
  yield Case(seed,seed%5,0xabcd0000|(seed&1),u32(0xdead0000+seed),(0,1,256,0xffffffff)[seed%4],(seed>>2)&1,(seed>>3)&1,(seed>>4)&7,(seed&1)*8)
 for seed,selector,hit,created,appended,mutation,phase in itertools.product((0,127),(0,1),(0,1,256,0xffffffff),(0,1),(0,1),(0,1,2,4,7),(0,8)):
  yield Case(seed,0,0xabcd0000|selector,u32(0xdead0000+seed),hit,created,appended,mutation,phase)

def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-4096,4096)}
 for at,n in((ACTOR,512),(BASE,3*0x9a0),(ALT,3*0x9a0),(MARK,4),(EFFECT,64),(QUEUE,16),(BASE_PTR,4),(INDEX,4),(SCALE,4),(QUEUE_PTR,4)):
  m.update({at+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 put(m,ACTOR,0 if c.gate==2 else 8 if c.gate==3 else 5)
 put(m,ACTOR+468,0 if c.gate==4 else MODEL);put(m,ACTOR+384,bits(POINTS[c.seed%6][1]))
 put(m,BASE_PTR,BASE);put(m,INDEX,c.seed%3);put(m,SCALE,bits((1.,-.5,.25,2.)[c.seed%4]));put(m,QUEUE_PTR,QUEUE)
 for base in(BASE,ALT):
  for i in range(3):put(m,base+i*0x9a0+0x380,bits((c.seed-128)*256.+i*17.25))
 return m

def random(c,n):return(0,0xffffffff,0x80000000,0x7fffffff,10,11,22,2001)[(c.seed+n)%8]
def sample(c,n):return bits(((c.seed*37+n*19)%257)/256.)
def canonical(t,args):
 a=list(args)
 if t==EVENT:a[7]&=255
 if t==FINAL:
  for i in(4,5,6):a[i]=short(a[i])
  a[7]&=255;a[11]&=255
 if t==CREATE:
  for i in(1,2,9,10,12):a[i]&=255
 if t==APPEND:a[2]&=255
 return tuple(a)

class Service:
 def __init__(self,m,c):self.m=m;self.c=c;self.calls=[];self.position=None;self.surface=None;self.probe=None;self.descriptor=None
 def invoke(self,t,args):
  m,c=self.m,self.c;n=len(self.calls);args=canonical(t,args);a=list(args);observed=()
  if t==MATRIX:
   assert args[:2]==(MODEL,17 if(c.selector&255)==0 else 26);self.position=args[2];a[2]='position'
  elif t==PREP:self.surface=args[0];a[0]='surface';assert args[1]==ACTOR
  elif t==QUERY:self.probe=args[0];assert args[1]==0 and args[3]==self.surface;a[0]='probe';a[3]='surface';observed=tuple(read(m,self.probe+4*i)for i in range(3))
  elif t==CREATE:
   self.descriptor=args[0];assert args[3]==self.surface+4;a[0]='descriptor';a[3]='vertices'
   observed=tuple(m[self.descriptor+i]for i in range(40))
  if self.position is not None:observed+=tuple(read(m,self.position+4*i)for i in range(3))
  if self.surface is not None:observed+=tuple(read(m,self.surface+4*i)for i in range(9))
  self.calls.append((t,tuple(a),observed))
  # All mutations remain in provider-visible objects or globals. Private cached
  # angles and unused stack bytes are never exposed to these services.
  if c.mutation&1 and self.position is not None:
   for i in range(3):put(m,self.position+4*i,bits((c.seed-100)*.125+n*.25+i))
   put(m,ACTOR+384,bits((c.seed-100)*.125+n*.25+1))
  if c.mutation&2:
   put(m,BASE_PTR,ALT if n&1 else BASE);put(m,INDEX,(c.seed+n)%3);put(m,SCALE,bits(.25 if n&1 else -1.25))
   for base in(BASE,ALT):
    for i in range(3):put(m,base+i*0x9a0+0x380,bits((c.seed-128)*256.+(n+1)*32.+i*.125))
  if c.mutation&4 and self.surface is not None:
   put(m,self.surface,bits(-25.5+n*.25))
   for i in range(1,9):put(m,self.surface+4*i,u32(0xabcdef00+n*0x010203+i*0x070b11+c.seed))
  put(m,MARK,u32(0x13579bdf+n*0x10203+t))
  if t==MATRIX:
   for i,v in enumerate(POINTS[c.seed%6]):put(m,args[2]+4*i,bits(v))
  if t==PREP:
   put(m,args[0],bits(-12.75))
   for i in range(1,9):put(m,args[0]+4*i,u32(0x12340000+c.seed*0x10203+i*0x112233))
  if t==QUERY:return c.hit
  if t==COMMAND:return(c.seed+n)&1
  if t==RNG:return random(c,n)
  if t==REAL:return sample(c,n)
  if t==CREATE:return EFFECT if c.created else 0
  if t==APPEND:return c.appended
  return u32(0xdeadbeef+n)

def reference(initial,c):
 m=dict(initial);service=Service(m,c);home=STACK+c.phase;position,surface,probe,descriptor=home-12,home-56,home-68,home-108
 angle=u32(math.trunc(floating(fp(read(m,read(m,BASE_PTR)+read(m,INDEX)*0x9a0+0x380),read(m,SCALE),'mul','left'))))
 if c.gate==1 or read(m,ACTOR)in(0,8)or not read(m,ACTOR+468):return m,service
 service.invoke(MATRIX,(MODEL,17 if(c.selector&255)==0 else 26,position));put(m,position+4,read(m,ACTOR+384))
 service.invoke(COMMAND,(5,0x4022));x,y,z=(read(m,position+4*i)for i in range(3))
 service.invoke(EVENT,(0xffffffff,u32(math.trunc(floating(x))),u32(math.trunc(floating(fp(y,bits(6.),'add','left')))),u32(math.trunc(floating(z))),25,18,0,c.context&255,1))
 real=service.invoke(REAL,());rng=service.invoke(RNG,())
 service.invoke(FINAL,(*(read(m,position+4*i)for i in range(3)),fp(fp(real,bits(50.),'mul','left'),bits(40.),'add','left'),short(angle+60),short(angle-60),rng%11+30,5,0,0,0,c.context&255))
 service.invoke(PREP,(surface,ACTOR));x,y,z=(read(m,position+4*i)for i in range(3))
 for i,v in enumerate((x,fp(y,bits(100.),'add','left'),z)):put(m,probe+4*i,v)
 if service.invoke(QUERY,(probe,0,fp(y,bits(100.),'sub','left'),surface)):
  size=service.invoke(REAL,());size=fp(fp(size,bits(200.),'mul','left'),bits(200.),'add','left')
  # Keep the constructor's copied-but-unspecified tail; initialize exactly the
  # retail bytes, never memset the descriptor or fill its padding for a match.
  for at,value,n in((6,42,1),(7,0,1),(0,0x7340,4),(4,300,2),(8,0,4)):put(m,descriptor+at,value,n)
  put(m,descriptor+12,service.invoke(RNG,())%2001+2000)
  for at,value,n in((16,255,1),(17,255,1),(18,0,1),(19,0,1),(20,0,1),(21,255,1),(22,0,1),(23,13,1),(32,255,1),(28,0,4),(24,0x170002,4)):put(m,descriptor+at,value,n)
  first=service.invoke(RNG,());second=service.invoke(RNG,());third=service.invoke(RNG,())
  effect=service.invoke(CREATE,(descriptor,0,0,surface+4,read(m,position),read(m,surface),read(m,position+8),size,size,first&255,(third&1)+((second&1)<<1),4,c.context&255,0))
  if effect and not service.invoke(APPEND,(read(m,QUEUE_PTR),effect,1)):service.invoke(FREE,(effect,))
 real=service.invoke(REAL,());rng=service.invoke(RNG,())
 service.invoke(FINAL,(*(read(m,position+4*i)for i in range(3)),fp(fp(real,bits(40.),'mul','left'),bits(60.),'add','left'),short(angle+60),short(angle-60),rng%7+6,6,0,0,0,c.context&255))
 return m,service

class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,arguments=None,connected=None):
  super().__init__(words,initial,c,entry=entry,s={},arguments=(0 if c.gate==1 else ACTOR,c.selector,c.context)if arguments is None else arguments,connected=connected)
  self.service=Service(self.memory,c);self.saved={i:self.r[i]for i in(*range(16,24),28,29,30)};self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2,3):self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul','div')[fn],'left');return
  return super().execute(w)
 def record_call(self,t):
  assert t in COUNTS,hex(t);a=tuple(self.arguments(COUNTS[t]))
  if t==FINAL:a=(self.f[12],self.f[14],*a[2:])
  self.pending=t,a
 def hook(self,t):
  target,args=self.pending;assert t==target;answer=self.service.invoke(t,args)
  for i in range(max(4,COUNTS[t])):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=answer;self.hi=self.lo=0xdeadbeef
  if t==REAL:self.f[0]=answer

def callers():
 rom=(s.FROZEN/'conker/conker.us.bin').read_bytes()
 lookup={n:f[1]for _,n,f,_ in symbol_rows((s.FROZEN/'conker/build/conker.us.elf').read_bytes())}
 target=bound_blob(*payload(s.OUT/'padded-generated.o',s.NAME),lookup)
 connected=dict(zip(range(ENTRY,ENTRY+1036,4),target));seen=set();count=0
 for entry,offset,selector in((0x1506f11c,0x9c5cc,0),(0x1506f14c,0x9c5fc,1)):
  words=list(struct.unpack_from('>12I',rom,offset))
  for seed,gate,hit,created,appended,mutation,phase in itertools.product((0,127),range(5),(0,1),(0,1),(0,1),(0,7),(0,8)):
   c=Case(seed,gate,selector,255,hit,created,appended,mutation,phase)
   initial=fixture(c);put(initial,0x800d154c,0 if gate==1 else ACTOR)
   expected,service=reference(initial,replace(c,phase=phase-24))
   machine=Oracle(words,initial,c,entry=entry,arguments=(0x12345678,),connected=connected)
   base=machine.record_call
   def record(t):
    if t==ENTRY:assert tuple(machine.arguments(3))==(0 if gate==1 else ACTOR,selector,255)
    else:base(t)
   machine.record_call=record;machine.run()
   assert public(machine.memory)==public(expected)and machine.service.calls==service.calls,('caller',hex(entry),c)
   assert all(machine.r[i]==v for i,v in machine.saved.items())and tuple(machine.f[20:])==machine.saved_fp
   seen|=machine.visits&set(range(entry,entry+48,4));count+=1
 assert len(seen)==24
 report=dict(passes=True,cases=count,complete_callers=2,caller_words_visited=24,
             actor_global='D_800D154C',selector_low_bytes=[0,1],context_byte=255,
             target_return_ignored=True,full_higher_parents_qualified=False)
 (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');return report

def constructor_prefix():
 # Execute the complete 50-word retail constructor around opaque allocation,
 # initialization and deletion services. This qualifies its o32 argument
 # forwarding and failure cleanup, not those deeper service implementations.
 rom=(s.FROZEN/'conker/conker.us.bin').read_bytes();entry=CREATE;offset=0x169bec
 words=list(struct.unpack_from('>50I',rom,offset));seen=set();count=0
 allocate,initialize=0x1513c350,0x1513e2ac
 class Constructor(FactoryOracle):
  def __init__(self,args,c,allocated,initialized):
   m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-4096,4096)}
   super().__init__(words,m,c,entry=entry,s={},arguments=args)
   self.args=args;self.allocated=allocated;self.initialized=initialized;self.observed=[]
   self.saved={i:self.r[i]for i in(*range(16,24),28,29,30)};self.saved_fp=tuple(self.f[20:])
  def record_call(self,t):
   n={allocate:11,initialize:9,FREE:1}[t];self.pending=t,tuple(self.arguments(n))
  def hook(self,t):
   target,a=self.pending;assert target==t;self.observed.append((t,a))
   for i in range(max(4,len(a))):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xdeadbeef
   self.r[2]=EFFECT if t==allocate and self.allocated else self.initialized if t==initialize else 0
 for seed,allocated,initialized,phase in itertools.product(range(16),(0,1),(0,1),(0,8)):
  args=(0x50000,0xabcdef00|seed,0x123400ff-seed,0x50004,
        *tuple(bits(v)for v in POINTS[seed%6]),bits(200.25),bits(400.5),
        0x87650000|seed,0x76540000|(seed&3),4,0x987600ff-seed,0)
  c=Case(seed=seed,phase=phase);machine=Constructor(args,c,allocated,initialized).run()
  expected=[(allocate,(args[0],0,args[1]&255,args[2]&255,args[10]&255,0,0,0,args[11],args[12]&255,args[13]))]
  if allocated:
   expected.append((initialize,(EFFECT,0,args[3],*args[4:9],args[9]&255)))
   if not initialized:expected.append((FREE,(EFFECT,)))
  assert machine.observed==expected,('constructor ABI',seed,allocated,initialized,machine.observed,expected)
  assert machine.r[2]==(EFFECT if allocated and initialized else 0)
  assert all(machine.r[i]==v for i,v in machine.saved.items())and tuple(machine.f[20:])==machine.saved_fp
  seen|=machine.visits;count+=1
 assert len(seen)==50,(len(seen),50)
 report=dict(passes=True,cases=count,original_constructor_words=50,words_visited=50,
             complete_wrapper_executed=True,o32_arguments=14,descriptor_copy_size=40,
             deeper_allocation_initialization_deletion_qualified=False)
 (s.OUT/'constructor-abi-report.json').write_text(json.dumps(report,indent=2)+'\n');return report

def run(state=None):
 obj=PACKET/'owner.o';raw,refs=payload(obj,'func_150BABE0');truth,trefs=payload(PACKET/'original.o','func_150BABE0');normal,rows=derive(raw,refs,truth,trefs)
 lookup={n:f[1]for _,n,f,_ in symbol_rows((s.FROZEN/'conker/build/conker.us.elf').read_bytes())}
 words=bound_blob(raw,refs,lookup);retail=bound_blob(truth,trefs,lookup);normalized=bound_blob(normal,refs,lookup)
 assert struct.pack('>259I',*retail)==(s.FROZEN/'conker/conker.us.bin').read_bytes()[0xe8090:0xe849c]
 seen=set();n=0
 for c in cases():
  initial=fixture(c);expected,service=reference(initial,c);a=Oracle(words,initial,c).run();b=Oracle(retail,initial,c).run()
  for label,machine in(('raw',a),('retail',b)):
   assert public(machine.memory)==public(expected),('public',label,c)
   assert machine.service.calls==service.calls,('calls',label,c,next(((i,x,y)for i,(x,y)in enumerate(zip(machine.service.calls,service.calls))if x!=y),None),len(machine.service.calls),len(service.calls))
   assert all(machine.r[i]==v for i,v in machine.saved.items())and tuple(machine.f[20:])==machine.saved_fp
  frame=STACK+c.phase-208
  def trace(machine,original):
   out=[]
   for kind,at,size,value in machine.trace:
    cell={0x44:'low',0x48:'high'}if original else{0x40:'low',0x44:'high'}
    out.append((kind,cell.get(at-frame,at),size,value))
   return out
  assert trace(a,False)==trace(b,True),('private cache trace',c)
  seen|=a.visits;n+=1
 unvisited=set(range(ENTRY,ENTRY+1036,4))-seen
 # Both actual callers select 0 or 1. The two other-selector instructions read
 # an uninitialized attachment home; they have static identity but no native
 # semantic promise, and are not credited as runtime coverage.
 assert unvisited=={ENTRY+0xa4,ENTRY+0xa8},sorted(hex(v-ENTRY)for v in unvisited)
 controls=0
 for i in range(259):
  bad=bytearray(raw);bad[4*i]^=1
  try:derive(bytes(bad),refs,truth,trefs)
  except AssertionError:controls+=1
  else:raise AssertionError(('accepted instruction corruption',i))
 for at in refs:
  bad={k:list(v)for k,v in refs.items()};kind,name=bad[at][0];bad[at][0]=(kind,name+'_wrong')
  try:derive(raw,bad,truth,trefs)
  except AssertionError:controls+=1
  else:raise AssertionError(('accepted binding corruption',at))
 report=dict(passes=True,cases=n,guest_executions=2*n,body_words=259,body_words_visited=len(seen),unvisited_static_only_offsets=sorted(hex(v-ENTRY)for v in unvisited),valid_selector_low_bytes=[0,1],raw_private_cache_trace_qualified=True,normalized_literal_retail=normalized==retail,derived_private_cache_words=len(rows),descriptor_bytes_observed=40,effective_instruction_binding_controls=controls,source_installed=s.installed(),c_match_credit=0,raw_sha256=hashlib.sha256(raw).hexdigest())
 (PACKET/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
 return report
