"""Concrete guest semantics, private-role relation, faults and full death dispatcher."""
from dataclasses import dataclass,replace
import json,struct
from tools.experiments import game_ground_burst_callback_150df334_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x150df334;OWNER=0x30000;MARK=0x90000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
u32=lambda x:x&0xffffffff
RANDOM=(0,1,2,3,61,62,63,0x7fffffff,0x80000000,0xfffffffe,0xffffffff)
@dataclass(frozen=True)
class Case:
 seed:int=0
 hit:int=1
 mutation:int=0
 ground_mode:int=2
 first:int=0xffffffff
 second:int=0x80000000
 phase:int=0
 channel:int=255
 context:int=128
def cases():
 for seed in range(11):
  for hit in(0,1,-1):
   for mutation in(0,1,2,4,8,16,32,63):
    yield Case(seed,hit,mutation,seed%3,RANDOM[seed],RANDOM[-1-seed],8*(seed&1),(0,127,128,255)[seed%4],(0,1,128,255)[seed%4])
 for seed in range(8):yield Case(seed=seed,hit=seed&1,mutation=63,ground_mode=2,first=seed+119,second=seed+2,channel=seed,context=255-seed)
def vec(m,a):return tuple(read(m,a+4*i)for i in range(3))
def putvec(m,a,v):
 for i,x in enumerate(v):put(m,a+4*i,x)
def data(m,a,n):return tuple(m[a+i]for i in range(n))
def fixture(c,raw=False):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2304)}
 for base,n in((OWNER,128),(MARK,32)):m.update({base+i:(i*29+c.seed*11+0x51)&255 for i in range(-16,n+16)})
 m[OWNER+12]=c.channel;m[OWNER+1]=c.context;putvec(m,OWNER+40,tuple(bits(float(((c.seed+i*7)%31)-15)*0.25)for i in range(3)))
 # Identical arbitrary initial bytes under the escaped-block address relation.
 if raw:
  home=STACK+c.phase;old=data(m,home-80,76)
  for i,v in enumerate(old):m[home-76+i]=v
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
class Providers:
 def __init__(self,m,c,raw=False,home=None,s=None):self.m=m;self.c=c;self.s=S if s is None else s;self.home=STACK+c.phase if home is None else home;self.block=self.home-(76 if raw else 80);self.escaped={};self.observed=[];self.calls=[];self.random_count=0
 def canonical(self,a):return a-4 if self.block==self.home-76 and self.block<=a<self.block+76 else a
 def invoke(self,name,a):
  m,c=self.m,self.c;number=len(self.calls)+1;buffers=((a[0],12),(a[3],36))if name=='func_1504697C'else((a[0],12),)if name=='func_150E83AC'else((a[0],12),(a[3],36))if name=='func_151A9834'else()
  for address,n in buffers:
   if STACK-2048<=address<STACK+2304:self.escaped[self.canonical(address)]=(address,n)
  args=tuple(self.canonical(v)for v in a);self.calls.append((self.s[name],args));snap=tuple((key,n,data(m,address,n))for key,(address,n)in sorted(self.escaped.items()));supplied=tuple((self.canonical(address),n,data(m,address,n))for address,n in buffers);self.observed.append((name,args,snap,supplied))
  # Each independent mutation bit makes a later required reload observable.
  if name=='func_1504697C':
   if c.ground_mode:
    put(m,a[3],bits(float(c.seed)-20.5));m[a[3]+28]=(c.seed*3)&255
    if c.ground_mode==2:
     for i in range(4,36):m[a[3]+i]=(i*7+c.seed*3)&255
   if c.mutation&1:putvec(m,OWNER+40,(bits(71.0),bits(-19.0),bits(23.0)))
   result=c.hit
  elif name=='func_150ADA20':
   self.random_count+=1;result=c.first if self.random_count==1 else c.second
   if c.mutation&2:putvec(m,OWNER+40,(bits(31.0+self.random_count),bits(-7.0),bits(13.0)));m[OWNER+12]^=0x55;m[OWNER+1]^=0xaa
   if c.mutation&4:
    for key,(address,n)in self.escaped.items():
     if n==12:putvec(m,address,(bits(100.0+number),bits(-30.0-number),bits(50.0+number)))
   if c.mutation&32:
    for key,(address,n)in self.escaped.items():
     if n==36:
      for i in range(n):m[address+i]=(i*5+number+c.seed)&255
  elif name=='func_150E83AC':
   if c.mutation&8:putvec(m,a[0],(bits(202.0),bits(-88.0),bits(3.0)))
   if c.mutation&16:putvec(m,OWNER+40,(bits(65.0),bits(34.0),bits(-17.0)));m[OWNER+12]^=0x33;m[OWNER+1]^=0xcc
   result=0xdeadbeef
  else:
   assert name in('func_151A9834','func_1516972C');put(m,MARK,number);result=0xdeadbeef
  return u32(result)
def reference(initial,c,s=None,home=None):
 m=initial.copy();home=STACK+c.phase if home is None else home;service=Providers(m,c,home=home,s=s);burst=home-80;probe=home-68;contact=home-56;ground=home-40
 putvec(m,probe,(read(m,OWNER+40),bits(floating(read(m,OWNER+44))+500.0),read(m,OWNER+48)))
 hit=service.invoke('func_1504697C',(probe,0,bits(floating(read(m,probe+4))-1000.0),ground))
 if hit:putvec(m,contact,(read(m,OWNER+40),read(m,ground),read(m,OWNER+48)))
 selected=contact if hit else OWNER+40
 lifetime=service.invoke('func_150ADA20',())%62+120
 service.invoke('func_150E83AC',(selected,lifetime,m[OWNER+12],m[OWNER+1]))
 selected=contact if hit else OWNER+40;putvec(m,burst,vec(m,selected));put(m,burst+4,bits(floating(read(m,burst+4))+500.0))
 count=service.invoke('func_150ADA20',())%3+3
 service.invoke('func_151A9834',(burst,bits(floating(read(m,burst+4))-1000.0),bits(250.0),ground,count,1,0,m[OWNER+12],m[OWNER+1]))
 return m,service
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,raw=False,connected=None):
  self.c=c;self.s=S if s is None else s;super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=(OWNER,));self.fp_before=self.f[:];self.entry_sp=self.r[29];self.providers=Providers(self.memory,c,raw=raw,home=self.entry_sp,s=self.s)
 def record_call(self,t):
  counts={self.s['func_1504697C']:4,self.s['func_150ADA20']:0,self.s['func_150E83AC']:4,self.s['func_151A9834']:9,self.s['func_1516972C']:1,ENTRY:1};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  name=next(n for n in('func_1504697C','func_150ADA20','func_150E83AC','func_151A9834','func_1516972C')if self.s[n]==t);a=self.calls[-1][1];result=self.providers.invoke(name,a)
  for i in range(max(4,len(a))):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=result
def streams(s=None):return{label:bound_blob(*payload(o/path,p.FUNCTION),S if s is None else s)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.providers.observed,m.dispatched_word)
def check(m,initial,c,s=None):
 expected,service=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert m.providers.calls==service.calls,(c,'calls',m.providers.calls,service.calls);assert m.providers.observed==service.observed,(c,'observed');assert m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:]and m.r[29]==m.entry_sp,(c,'saved')
def main():
 programs=streams();assert len({tuple(v)for k,v in programs.items()if k!='raw'})==1;assert struct.pack('>97I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x10c7e4:0x10c968];count=0;visits=set()
 for c in cases():
  initial=fixture(c);models=[]
  for label,ws in programs.items():m=Oracle(ws,fixture(c,label=='raw'),c,raw=label=='raw');m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,padded_retail_complete_identity=True,independent_public_effects_and_escaped_buffer_observations_equal=True,padded_retail_all_private_bytes_and_saved_registers_equal=True,raw_private_address_relation_only=True,unexecuted_original_words=[i for i in range(97)if ENTRY+4*i not in visits],source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 programs=[v for k,v in streams().items()if k!='raw'];count=0
 for c in(Case(hit=0),Case(),Case(hit=-1,mutation=63,ground_mode=0),Case(mutation=63,phase=8)):
  initial=fixture(c);full=Oracle(programs[-1],initial,c);full.run()
  for cut in range(full.all_accesses):
   values=[]
   for ws in programs:
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    values.append(state(m))
   assert all(v==values[0]for v in values[1:]);count+=1
 q=dict(padded_retail_full_state_and_dispatched_word_access_prefix_triples=count,raw_private_or_fault_identity_claim=False,portable_C_fault_claim=False);(o/'faults.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
def callers():
 raw=(o/'original-dispatcher.bin').read_bytes();assert len(raw)==180;caller=list(struct.unpack('>45I',raw));count=0;retired=0;programs=streams();models_seen=0
 for c in list(cases())[::19]:
  initial=fixture(c);initial[OWNER+13]=0;initial[OWNER+16]=8;initial[OWNER+17]=255;put(initial,OWNER+14,0xffff,2);put(initial,S['D_8008A4C0']+32,ENTRY)
  # Dispatcher frame24 nests the callback; role-related input block follows it.
  expected,service=reference(initial,c,home=STACK+c.phase-24);service.invoke('func_1516972C',(OWNER,));models=[]
  for label,ws in programs.items():
   image=initial.copy()
   if label=='raw':
    home=STACK+c.phase-24;seed=data(initial,home-80,76)
    for i,v in enumerate(seed):image[home-76+i]=v
   m=Oracle(caller,image,c,entry=0x15149264,connected=dict(zip(range(ENTRY,ENTRY+4*len(ws),4),ws)),raw=label=='raw');m.providers.home-=24;m.providers.block-=24;m.run();assert public(m.memory)==public(expected)and m.providers.calls==service.calls and m.providers.observed==service.observed,(c,'caller');assert m.r[29]==m.entry_sp and m.r[16:24]==m.before[16:24]and m.r[30:]==m.before[30:];models.append(m);models_seen+=1
  assert all(state(m)==state(models[1])for m in models[2:]);count+=1;retired+=1
 q=dict(complete_original_dispatcher_words=45,death_callback_table_index=8,update_callback_index=-1,cases_per_stream=count,final_retirement_cases=retired,guest_runs=models_seen,full_caller_returns_and_effects_equal=True,retirement_provider='opaque compatible provider',additional_caller_matching_credit=0);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();print(json.dumps(faults()));print(json.dumps(callers()))
