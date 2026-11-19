"""Independent actor emission reference; caller ignores the non-total result."""
from pathlib import Path
from dataclasses import dataclass,replace
import hashlib,itertools,json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_actor_attached_emitter_150bb760_normalizer import derive
from tools.experiments import game_actor_attached_emitter_150bb760_match as s
ROOT=s.ROOT;PACKET=s.OUT;ENTRY=0x150bb760
RNG,REAL,SINE,FACTORY=0x150ada20,0x150ada68,0x151423d8,0x15132a4c
ACTOR,OUTPUT=0x10000,0x50000;GLOBALS=(0x8009fe94,0x8009fe98,0x8009fe9c,0x8009fea0,0x8009fea4)
COUNTS={RNG:0,REAL:0,SINE:1,FACTORY:6};u32=lambda n:n&0xffffffff;s16=lambda n:((n&65535)^32768)-32768
public=lambda m:{a:b for a,b in m.items()if not STACK-4096<=a<STACK+4096}
def unspecified(i):return 0x59<=i<0x5c or i in(0x69,0x6b,0x71)or 0x76<=i<0x7c
@dataclass(frozen=True)
class Case:
 seed:int=0;heading:int=0;gate:int=3;success:int=1;mutation:int=0;phase:int=0;actor:int=ACTOR
def cases():
 for seed,heading,gate,success,mutation,phase in itertools.product((0,1,127,255),(0,127,128,255),range(4),(0,1),range(4),(0,8)):
  yield Case(seed,heading,gate,success,mutation,phase)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-4096,4096)}
 for base,n in((c.actor,512),(OUTPUT,512)):m.update({base+i:(i*11+c.seed*7+7)&255 for i in range(n)})
 put(m,c.actor,0 if c.gate==1 else 1);m[c.actor+4]=31 if c.gate==0 else 32;put(m,c.actor+0x1d4,0 if c.gate==2 else 0x30000)
 m[c.actor+0x3b]=(c.seed^255)&255
 for at,v in((0x14,1.25),(0x18,-2.5),(0x1c,3.75),(0x3c,(0.,-0.,1.5,-2.25)[c.seed%4])):put(m,c.actor+at,bits(v))
 put(m,c.actor+0x76,(c.heading<<8)|(c.seed&255),2)
 for at,value in((0xe4,(-32768,0,17,32767)[c.seed%4]),(0xe6,(32767,-91,0,-32768)[c.seed%4])):put(m,c.actor+at,value,2)
 for i,a in enumerate(GLOBALS):put(m,a,bits((.125,-0.,-2.25,3.5,7.75)[(c.seed+i)%5]))
 return m
def randoms(c):
 v=(0,0xffffffff,0x80000000,0x7fffffff,31,32,63,64,127,128,255,0x12345678)
 return tuple(v[(c.seed+3*i)%12]for i in range(3))
def reals(c):return tuple(bits((0.,-0.,.125,.5,1.,-.5,1.25)[(c.seed+3*i)%7])for i in range(12))
def sine(c,a):a&=255;return bits(-0. if a==0 and c.seed&1 else((a^128)-128)/128.)
def effects(m,c,t,index):
 a=c.actor
 if c.mutation&1:
  if t==SINE and index==0:put(m,a+0x76,0xa531,2);put(m,a+0xe4,-19,2);put(m,a+0xe6,23,2)
  if t==RNG and index==1:put(m,a+0x76,0x7b19,2)
 if c.mutation&2:
  if t==SINE and index==1:put(m,a+0x3c,bits(4.25));m[a+0x3b]=17
  if t==REAL and index in(2,3):
   for i,g in enumerate(GLOBALS):put(m,g,bits((i+1)*(1.5 if index==2 else-1.25)))
  if t==REAL and index==7:
   for offset,value in((0x14,123.5),(0x18,456.25),(0x1c,-789.75)):put(m,a+offset,bits(value))
   put(m,a+0xe6,77,2)
  if t==FACTORY:put(m,a+0x3c,bits(-19.));m[a+0x3b]=99;put(m,GLOBALS[-1],bits(-8.5))
def reference(initial,c,home=None):
 m=dict(initial);d=(STACK+c.phase if home is None else home)-0x7c;calls=[];obs=[];counts={RNG:0,REAL:0,SINE:0}
 if m[c.actor+4]!=32 or c.actor==0 or read(m,c.actor)==0 or read(m,c.actor+0x1d4)==0:return m,calls,obs
 def field(i,v,n=4):put(m,d+i,v,n)
 def call(t,arg=None):
  index=counts[t];counts[t]+=1;args=()if arg is None else(arg&255,);calls.append((t,args))
  answer=randoms(c)[index]if t==RNG else reals(c)[index]if t==REAL else sine(c,arg)
  effects(m,c,t,index);return answer
 def mul(a,b):return fp(a,b,'mul','left')
 def add(a,b):return fp(a,b,'add','left')
 width=bits(float(s16(read(m,c.actor+0xe4,2))));height=bits(float(s16(read(m,c.actor+0xe6,2))))
 hs=call(SINE,read(m,c.actor+0x76,2)>>8);hc=call(SINE,(read(m,c.actor+0x76,2)>>8)+64)
 speed=read(m,c.actor+0x3c);dx=mul(mul(speed,hs),bits(.5));dz=mul(mul(speed,hc),bits(.5))
 for i,v,n in((0x56,1,2),(0x50,0x29e9,4),(0x58,0,1),(0x5c,0,4),(0x60,255,1),(0x61,1,1),(0x62,0,1),(0x63,2,1),(0x64,0,1),(0x65,0,1),(0x66,0,1),(0x67,0,1),(0x68,0,1),(0x6a,1,1),(0x6c,c.actor,4),(0x48,0,4),(0x4c,bits(-1.),4),(0x70,m[c.actor+0x3b],1),(0x72,32,2),(0x74,7,2)):field(i,v,n)
 for i in range(3):field(0x1c+4*i,bits(1.))
 angle=call(RNG)&255;rs=call(SINE,angle);rc=call(SINE,angle-64);radius=mul(call(REAL),width);ox=mul(rs,radius);oz=mul(rc^0x80000000,radius)
 random=call(RNG);angle=((read(m,c.actor+0x76,2)>>8)-(random&63)-32)&255;ss=call(SINE,angle);sc=call(SINE,angle-64)
 speed=add(mul(call(REAL),bits(5.)),bits(3.));vx=mul(sc,speed);vz=mul(ss,speed)
 sample=call(REAL);first=add(mul(sample,read(m,GLOBALS[0])),read(m,GLOBALS[1]))
 sample=call(REAL);second=add(mul(sample,read(m,GLOBALS[2])),read(m,GLOBALS[3]));field(8,first);field(12,second);field(0,mul(add(first,second),bits(.5)))
 for i in range(3):field(0x10+4*i,mul(call(REAL),bits(360.)))
 field(0x28,add(read(m,c.actor+0x14),ox));sample=call(REAL);field(0x2c,add(add(mul(sample,height),read(m,c.actor+0x18)),bits(4.)));field(0x30,add(read(m,c.actor+0x1c),oz));field(0x34,add(vx,dx))
 field(0x38,add(mul(call(REAL),bits(5.)),bits(3.)));field(0x3c,add(vz,dz))
 field(0x40,fp(bits(25.),mul(call(REAL),bits(50.)),'sub','left'));field(0x44,fp(bits(25.),mul(call(REAL),bits(50.)),'sub','left'));field(0x54,(call(RNG)&31)+60,2)
 sample=call(REAL);field(4,add(mul(sample,read(m,GLOBALS[4])),bits(.25)))
 calls.append((FACTORY,(d,3,255,0,255,0)));obs.append(tuple(m[d+i]for i in range(124)))
 if c.success:
  for i in range(124):m[OUTPUT+16+i]=m[d+i]
 effects(m,c,FACTORY,0);return m,calls,obs
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,arguments=None,connected=None):
  super().__init__(words,initial,c,entry=entry,s={},arguments=(c.actor,)if arguments is None else arguments,connected=connected)
  self.cc=c;self.indices={RNG:0,REAL:0,SINE:0};self.obs=[];self.calls=[];self.r[2]=0x13579bdf
  self.saved={i:self.r[i]for i in(*range(16,24),28,29,30)};self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2,3):self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul','div')[fn],'left');return
  if op==17 and fmt==16 and fn==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000;return
  return super().execute(w)
 def record_call(self,t):
  assert t in COUNTS,hex(t);a=tuple(self.arguments(COUNTS[t]));self.calls.append((t,a))
  if t==FACTORY:self.obs.append(tuple(self.memory[a[0]+i]for i in range(124)))
 def hook(self,t):
  c=self.cc;a=self.calls[-1][1];value=0xdeadbeef;floating=None
  if t==FACTORY:
   if c.success:
    for i in range(124):self.memory[OUTPUT+16+i]=self.memory[a[0]+i]
   effects(self.memory,c,t,0);value=OUTPUT if c.success else 0
  else:
   index=self.indices[t];self.indices[t]+=1
   if t==RNG:value=randoms(c)[index]
   else:floating=reals(c)[index]if t==REAL else sine(c,a[0])
   effects(self.memory,c,t,index)
  for i in range(6 if t==FACTORY else 4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=u32(value);self.hi=self.lo=0xdeadbeef
  if floating is not None:self.f[0]=floating
def state():return s.state()
def run(supplied=None):
 code=state()if supplied is None else supplied;seen=set();count=0
 rows=list(cases())+[Case(actor=0,gate=3),Case(actor=0,gate=0)]
 for c in rows:
  initial=fixture(c);expected,calls,obs=reference(initial,c);returns=[]
  for label,words in ((k,v)for k,v in code.items()if k.endswith('_words')):
   m=Oracle(words,initial,c).run();assert(public(m.memory),m.calls,m.obs)==(public(expected),calls,obs),(label,c,m.calls,calls)
   assert all(m.r[i]==v for i,v in m.saved.items())and tuple(m.f[20:])==m.saved_fp
   if label=='retail_words':seen|=m.visits
   returns.append(m.r[2])
  assert len(set(returns))==1;count+=1
 assert len(seen)==255,len(seen)
 for label,words in ((k,v)for k,v in code.items()if k.endswith('_words')):
  c=Case(actor=0);initial=fixture(c);del initial[4];m=Oracle(words,initial,c)
  try:m.run()
  except AssertionError as e:assert e.args[0]==('unmapped read',4,1),e
  else:raise AssertionError('missing actor byte4 did not fault')
  assert ENTRY+0x10 in m.visits and ENTRY+0x28 not in m.visits and not m.calls
  bad=list(words);assert bad[4]==0x920e0004;bad[4]=0x240e0020
  control=Oracle(bad,initial,c).run();assert not control.calls and ENTRY+0x28 in control.visits
 report=dict(passes=True,cases=count,ordinary_cases=count-2,programs=3,executions=count*3,retail_words_visited=255,mapped_null_guest_cases=2,unmapped_null_fault_controls=3,effective_missing_read_controls=3,descriptor_bytes=124,unspecified_bytes=12,return_used_by_known_caller=False,raw_private_fault_equivalence_claimed=False,c_match_credit=0)
 (PACKET/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report

def caller(supplied=None):
 from tools.match_progress import load_elf_functions
 code=state()if supplied is None else supplied;entry=0x1506efc8;rom=(s.FROZEN/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>15I',rom,0x9c478)
 live,_,_=load_elf_functions(str(s.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');assert tuple(live['func_1506EFC8'])==words
 class Caller(Oracle):
  def record_call(self,t):
   if t==ENTRY:self.calls.append((t,tuple(self.arguments(1))))
   else:super().record_call(t)
 rows=[Case(seed,heading,gate,success,mutation,phase)for seed,heading,gate,success,mutation,phase in itertools.product((0,127),(0,255),range(4),(0,1),range(4),(0,8))]
 rows += [Case(seed,gate=3,success=success,phase=phase)for seed,success,phase in itertools.product((0,127),(0,1),(0,8))]
 seen=set()
 for ordinal,c in enumerate(rows):
  initial=fixture(c);put(initial,0x800d154c,c.actor);skip=ordinal>=len(rows)-8
  if skip:initial[c.actor+4]=0x8c;expected,calls,obs=dict(initial),[],[]
  else:expected,calls,obs=reference(initial,c,home=STACK+c.phase-24);calls=[(ENTRY,(c.actor,))]+calls
  for label,body in ((k,v)for k,v in code.items()if k.endswith('_words')):
   connected=dict(zip(range(ENTRY,ENTRY+len(body)*4,4),body));m=Caller(words,initial,c,entry=entry,arguments=(0xdeadbeef,),connected=connected).run()
   assert(public(m.memory),m.calls,m.obs)==(public(expected),calls,obs),('caller',label,c,m.calls,calls)
   assert all(m.r[i]==v for i,v in m.saved.items())and tuple(m.f[20:])==m.saved_fp;seen|=m.visits&set(range(entry,entry+60,4))
 assert len(seen)==15
 report=dict(passes=True,cases=len(rows),programs=3,actual_complete_caller_words=15,caller_words_visited=15,production_caller_literal=True,identity_0x8c_skips_target=True,return_value_ignored=True,full_higher_parent_qualified=False)
 (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');return report

def factory(supplied=None):
 from tools.match_progress import load_elf_functions
 code=state()if supplied is None else supplied;rom=(s.FROZEN/'conker/conker.us.bin').read_bytes();backend=0x1513264c;words=struct.unpack_from('>15I',rom,0x15fefc)
 live,_,_=load_elf_functions(str(s.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');assert tuple(live['func_15132A4C'])==words
 connected=dict(zip(range(FACTORY,FACTORY+60,4),words));seen=set();count=0
 class Connected(Oracle):
  def record_call(self,t):
   if t==backend:self.calls.append((t,tuple(self.arguments(7))))
   else:super().record_call(t)
  def hook(self,t):
   if t!=backend:return super().hook(t)
   Oracle.hook(self,FACTORY);self.put(self.r[29]+24,0xb5000006,4)
 for seed,heading,success,mutation,phase in itertools.product((0,127),(0,127,128,255),(0,1),range(4),(0,8)):
  c=Case(seed,heading,3,success,mutation,phase);initial=fixture(c);expected,calls,obs=reference(initial,c);d=STACK+phase-0x7c
  calls=calls+[(backend,(d,3,255,0,0,255,0))]
  for label,body in ((k,v)for k,v in code.items()if k.endswith('_words')):
   m=Connected(body,initial,c,connected=connected).run();assert(public(m.memory),m.calls,m.obs)==(public(expected),calls,obs),('wrapper',label,c,m.calls,calls)
   assert all(m.r[i]==v for i,v in m.saved.items())and tuple(m.f[20:])==m.saved_fp;seen|=m.visits&set(connected)
  count+=1
 assert len(seen)==15
 report=dict(passes=True,cases=count,programs=3,actual_wrapper_words=15,wrapper_words_visited=15,all7_backend_argument_words_checked=True,production_wrapper_literal=True,descriptor_copy_bytes=124,backend='opaque modeled service',full_backend_qualified=False,full_allocator_qualified=False)
 (s.OUT/'factory-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
