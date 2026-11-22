"""Bounded ordered actor model, valid whole-record aliases and explicit FCSR."""
from pathlib import Path
from dataclasses import dataclass
from fractions import Fraction
import itertools,json,math,struct,sys
from tools.experiments import game_paired_actor_initializer_151951e0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
ENTRY=0x151951E0;ROM=0x1C2690;ACTOR=0x30000;PAIR=0x50000;MARK=0x70000;COEFF=0x800A8704;SIZE=812
TYPE=0x1507CD64;MODE=0x15194AB4;RNG=0x150ADA20;ALLOC=0x1505ED34;REGISTER=0x150838EC;TRANSITION=0x150D10E4
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 values:tuple=(0,1,2,3,4);kind:int=0;angle:int=32768;facing:int=0xABCD;mode:int=0;phase:int=0;seed:int=0;alias:int=0;coefficient:int=0x45AAAAAB;fcsr:int=0
def pointers(c):return ACTOR,ACTOR if c.alias==1 else ACTOR-256 if c.alias==2 else PAIR
def initialize(m,p,c,tag):
 for i in range(SIZE):m[p+i]=(i*29+c.seed*11+tag)&255
 for off,v in((0x14,10.+tag),(0x18,20.),(0x1C,-30.),(0x20,3.),(0x24,4.),(0x3C,7.),(0x40,90.),(0xB8,3.),(0xBC,4.),(0x148,5.),(0x14C,1.25),(0x150,1.5)):put(m,p+off,bits(v))
 put(m,p,1);m[p+4]=c.kind;put(m,p+0x76,c.angle,2);put(m,p+0x7A,c.facing,2)
 put(m,p+0x84,0x1234,2);put(m,p+0x4C,0xFFFFFFEF);put(m,p+0x9C,0x00100001);put(m,p+0xF8,0x12345678);m[p+0x1CA]=200
 for i in range(6):m[p+0x68+i]=(c.kind+7*i)&255
def fixture(c):
 a,p=pointers(c);m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-512,512)}
 for base in(a,p):
  for i in range(-32,SIZE+32):m[base+i]=(i*19+c.seed+0xA5)&255
 initialize(m,a,c,0);initialize(m,p,c,0x50)
 if p!=a:initialize(m,a,c,0)
 for i in range(32):m[MARK+i]=(i*11+3)&255
 put(m,COEFF,c.coefficient);return m
def effect(m,c,t,args,rng_index=0):
 a,p=pointers(c)
 if t==TYPE:
  if c.mode&1:
   m[a+4]^=0x55;m[a+0x1CA]=99
   for off,v in((0x14,42.),(0x18,-13.),(0x1C,17.)):put(m,a+off,bits(v))
 elif t==MODE:
  put(m,a+0x9C,read(m,a+0x9C)|0xFFFE)
  if c.mode&2:put(m,a+0x84,0xBEEF,2);put(m,a+0x4C,0x87654321);put(m,a+0x76,53000,2)
 elif t==ALLOC:
  initialize(m,p,c,0x71)
  if c.mode&4:
   for off,v in((0x14,123.),(0x1C,-82.),(0x14C,.75),(0x150,2.25)):put(m,a+off,bits(v))
 elif t==RNG:
  if c.mode&8:
   if rng_index==0:put(m,a+0x3C,bits(12.));put(m,a+0x14,bits(-32.))
   if rng_index==1:put(m,a+0xBC,bits(17.))
   if rng_index==4:put(m,a+0x76,60000,2);put(m,p+0x76,64000,2);put(m,COEFF,bits(5461.5))
 elif t==REGISTER:
  if c.mode&4:put(m,p+0xF8,0xFEDCBA98)
 elif t==TRANSITION:put(m,MARK+4*args[1],0xABCD0000+args[1])
 else:raise AssertionError(hex(t))
def fsub(a,b):return bits(floating(a)-floating(b))
def fadd(a,b):return bits(floating(a)+floating(b))
def unsigned_conversion(v):
 x=floating(v);return u32(math.trunc(x))if math.isfinite(x)and -1<x<4294967296 else 0xFFFFFFFF
def actors(m,c):
 a,p=pointers(c);return bytes(m[a+i]for i in range(SIZE)),bytes(m[p+i]for i in range(SIZE)),read(m,COEFF)
def reference(initial,c,capture=False):
 m=dict(initial);a,p=pointers(c);calls=[];snapshots=[];rng_index=0
 def call(t,*args):
  nonlocal rng_index
  args=tuple(map(u32,args));calls.append((t,args));pre=actors(m,c)
  effect(m,c,t,args,rng_index)
  value=c.values[rng_index]if t==RNG else p if t==ALLOC else 0x87654321
  if t==RNG:rng_index+=1
  if capture:snapshots.append(dict(target=t,args=args,before=pre,after=actors(m,c),answer=u32(value)))
  return value
 m[a+0x1CA]=0;call(TYPE,a,5);call(MODE,a);put(m,a,40);put(m,a+0x3C,bits(-3.))
 value=call(RNG);put(m,a+0xBC,fsub(bits(-10.),bits(float(value%5))))
 value=call(RNG);put(m,a+0x20,0);put(m,a+0x24,0);put(m,a+0x148,fsub(bits(float(value%10)),bits(5.)))
 assert call(ALLOC)==p;put(m,p,40);identity=m[a+4];m[p+0x125]=255;m[p+0x104]=255;m[p+4]=identity
 for off in(0x14,0x18,0x1C,0x40):put(m,p+off,read(m,a+off))
 for off in(0x76,0x7A):put(m,p+off,read(m,a+off,2),2)
 for off in(0xB8,0x14C,0x150):put(m,p+off,read(m,a+off))
 put(m,p+0x3C,bits(10.));value=call(RNG);put(m,p+0xBC,fadd(bits(float(value%5)),bits(10.)))
 value=call(RNG);put(m,p+0x148,fsub(bits(float(value%10)),bits(5.)))
 for i in range(6):m[p+0x68+i]=m[a+0x68+i]
 value=call(RNG)
 delta,sub_flags=fp_result(bits(float(value%0x2AAA)),read(m,COEFF),1,c.fcsr&3)
 angle,add_flags=fp_result(delta,bits(float(read(m,p+0x76,2))),0,c.fcsr&3)
 put(m,p+0x76,unsigned_conversion(angle),2)
 put(m,p+0x40,bits((read(m,a+0x76,2)+0x4000)*0.0054931640625))
 link=read(m,a+0xF8);put(m,p+0x9C,read(m,p+0x9C)|0x0FFF0000);put(m,p+0xF8,link)
 call(REGISTER,p,read(m,a+0x84,2),0,read(m,a+0x4C));call(TRANSITION,a,0);call(TRANSITION,p,1)
 if capture:snapshots[-1]['final_fcsr']=(c.fcsr&~0x3F000)|((sub_flags|add_flags)&0x7C)
 return m,calls,snapshots
def next_up(b):
 if b&0x7FFFFFFF==0:return 1
 return b-1 if b&0x80000000 else b+1
def next_down(b):
 if b&0x7FFFFFFF==0:return 0x80000001
 return b+1 if b&0x80000000 else b-1
def fp_result(a,b,fn,rm=0):
 x,y=floating(a),floating(b)
 if not math.isfinite(x)or not math.isfinite(y):
  z=x+y if fn==0 else x-y if fn==1 else x*y
  invalid=math.isnan(z)and not(math.isnan(x)or math.isnan(y))
  return bits(z),0x10040 if invalid else 0
 exact=Fraction(x)+Fraction(y)if fn==0 else Fraction(x)-Fraction(y)if fn==1 else Fraction(x)*Fraction(y)
 z=bits(float(exact));v=Fraction(floating(z))if math.isfinite(floating(z))else None
 if v is not None and v!=exact:
  if rm==1:z=next_down(z)if exact>0 and v>exact else next_up(z)if exact<0 and v<exact else z
  elif rm==2 and v<exact:z=next_up(z)
  elif rm==3 and v>exact:z=next_down(z)
 return z,0x1004 if not math.isfinite(floating(z))or Fraction(floating(z))!=exact else 0
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,connected=None):
  self.c=c;a,p=pointers(c)
  super().__init__(words,fixture(c),c,entry=entry,arguments=(a,),connected=connected)
  self.initial=dict(self.memory);self.before_f=self.f[:];self.rng_index=0;self.fcsr=c.fcsr;self.observations=[]
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==2:self.r[rt]=self.fcsr
  elif op==17 and fmt==6:self.fcsr=self.r[rt]
  elif op==17 and fmt==20 and fn==32:
   value=((self.f[fs]&0xFFFFFFFF)^0x80000000)-0x80000000;self.f[fd]=bits(float(value))
   flags=0x1004 if floating(self.f[fd])!=value else 0;self.fcsr=(self.fcsr&~0x3F000)|flags
  elif op==17 and fmt==16 and fn==36:
   value=floating(self.f[fs]);rm=self.fcsr&3
   converted=math.trunc(value)if rm==1 and math.isfinite(value)else math.ceil(value)if rm==2 and math.isfinite(value)else math.floor(value)if rm==3 and math.isfinite(value)else round(value)if math.isfinite(value)else None
   valid=converted is not None and -2147483648<=converted<2147483648
   self.f[fd]=u32(converted)if valid else 0x80000000
   flags=0x10040 if not valid else 0x1004 if converted!=value else 0;self.fcsr=(self.fcsr&~0x3F000)|flags
  elif op==17 and fmt==16 and fn in(0,1,2):
   self.f[fd],flags=fp_result(self.f[fs],self.f[rt],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3F000)|flags
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  counts={TYPE:2,MODE:1,RNG:0,ALLOC:0,REGISTER:4,TRANSITION:2,ENTRY:1};assert t in counts,hex(t)
  args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
  self.observations.append(actors(self.memory,self.c))
 def hook(self,t):
  effect(self.memory,self.c,t,self.calls[-1][1],self.rng_index)
  value=self.c.values[self.rng_index]if t==RNG else pointers(self.c)[1]if t==ALLOC else 0x87654321
  if t==RNG:self.rng_index+=1
  self.clobber(value)
 def clobber(self,value):
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def programs():
 lookup={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 paths=(out/'qualified-source/candidate.o',out/'image-qualification/padded.o',out/'image-qualification/retail.o')
 streams=[bound_blob(*payload(p,'func_151951E0'),lookup)for p in paths]
 truth=list(struct.unpack_from('>210I',(root/'conker/conker.us.bin').read_bytes(),ROM))
 assert streams[1]==streams[2]==truth and sum(a!=b for a,b in zip(streams[0],truth))==15
 return streams
def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+512}
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
def final_state(m):return(m.memory,m.r,m.f,m.fcsr,m.calls,m.observations,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
def check(words,c):
 m=Oracle(words,c).run();expected,calls,observed=reference(m.initial,c,True)
 assert m.calls==calls,(c,'calls',m.calls,calls)
 assert public(m.memory)==public(expected),(c,'memory',[(hex(a),v,expected.get(a))for a,v in public(m.memory).items()if expected.get(a)!=v][:8])
 assert m.observations==[v['before']for v in observed],(c,'call boundary snapshots')
 assert m.fcsr==observed[-1]['final_fcsr'],(c,'FCSR',m.fcsr,observed[-1]['final_fcsr'])
 assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
 return m
def main():
 streams=programs();values=(0,1,4,5,9,10,10921,10922,0x7FFFFFFF,0x80000000,0xFFFFFFFF)
 cases=[Case(values=(v,)*5,kind=k,angle=a,mode=mode,alias=alias,phase=phase)for v,k,a,mode,alias,phase in itertools.product(values,(0,255),(0,65535),(0,15),(0,1),(0,8))]
 cases += [Case(kind=k,values=(k*0x01010101,)*5,angle=k*257)for k in range(256)]
 cases += [Case(values=tuple(v if i==j else (4,9,0,10,5)[i]for i in range(5)),mode=mode,alias=alias)for j,v,mode,alias in itertools.product(range(5),values,(0,15),(0,1))]
 cases += [Case(fcsr=v)for v in(4,0x40,0x1004,0x10040)]
 # FCSR boundary cases are guest-only where C float-to-unsigned is undefined.
 cases += [Case(coefficient=v,angle=a,mode=0,values=(0xFFFFFFFF,)*5)for v,a in itertools.product((0,0x80000000,0x3F000000,0xCF000001,0x4F800000,0x7F800000,0xFF800000,0x7FC12345),(0,65535))]
 visits=set()
 for c in cases:
  machines=[check(ws,c)for ws in streams];visits.update(machines[1].visits)
  assert final_state(machines[0])==final_state(machines[1])==final_state(machines[2]),c
 faults=0
 for c in(Case(),Case(angle=0),Case(alias=1,mode=15,phase=8),Case(coefficient=0xCF000001)):
  full=check(streams[1],c)
  for cut in range(full.all_accesses):
   states=[]
   for ws in streams[1:]:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(m))
   assert states[0]==states[1];faults+=1
 missed=[i for i in range(210)if ENTRY+4*i not in visits]
 assert missed==[25,26,27,28,39,40,41,42,87,88,89,103,104,105,131,132,133,142,143,144,174]
 # A deliberately invalid partial record overlap witnesses why the allocator
 # and original caller's whole-record domain is part of the guard contract.
 partial=Case(alias=2)
 check(streams[1],partial);check(streams[2],partial)
 try:check(streams[0],partial)
 except AssertionError as e:assert 'memory' in str(e)or 'call boundary snapshots' in str(e)
 else:raise AssertionError('partial-overlap domain control was ineffective')
 r=dict(cases_per_stream=len(cases),streams=3,body_words=210,executed_words=210-len(missed),unexecuted_words=missed,whole_record_aliases_checked=True,partial_overlap_outside_contract_control=True,raw_complete_end_states_equal=True,normalized_access_fault_pairs=faults,explicit_FCSR=True,helper_internals_executed=False,source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
