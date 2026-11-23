"""Independent public-state model of the position callback and attachment gate."""
from dataclasses import dataclass
import json,struct
from tools.experiments import game_linked_effect_update_151d1138_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x151d1138;OWNER=0x30000;ACTOR=0x80000;OTHER=0x88000;CHILD=0x50000;MARK=0x90000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};S['_callbacks']=0x15300000
u32=lambda x:x&0xffffffff
LENGTHS=(0,0x80000000,1,0xbf800000,0x4395ffff,0x43960000,0x43960001,0x7f800000,0xff800000,0x7fc12345,0x7f800001)
@dataclass(frozen=True)
class Case:
 seed:int=0
 live:int=1
 identity:int=37
 actor_id:int=37
 callback_result:int=1
 selector:int=0
 length:int=0x3f800000
 vertical:int=0
 busy:int=0
 classword:int=0
 child:int=0
 mutation:int=0
 alias:int=0
 phase:int=0

def cases():
 for seed in range(512):yield Case(seed,0x80000000 if seed&1 else 1,37,37,(0,1,0x80000000)[seed%3],(0,1,127,255)[seed%4],LENGTHS[seed%len(LENGTHS)],(0,0x80000000,0x3f800000,0x7fc12345)[seed//11%4],seed//17%2,0xabc00000|(seed%32),seed&1,seed%32,int(seed%17==0),8*(seed&1))
 seed=1024
 for length in LENGTHS:
  for kind in(0,5,6,9,13,14,31):
   for success,child in((0,0),(1,0),(0,1),(1,1)):
    yield Case(seed,1,255,255,success,255,length,0,0,0x80000000|kind,child,0,0,8*(seed&1));seed+=1
 for seed in range(64):yield Case(2048+seed,0 if seed&1 else 1,255,254 if not seed&1 else 255,1,127,LENGTHS[seed%len(LENGTHS)],classword=seed,mutation=31,phase=8*(seed&1))

def actor(c):return OWNER if c.alias else ACTOR
def callback(c,s):return s['_callbacks']+64*c.selector
def vectors(c):return tuple(bits(float(((c.seed+3*i)%29)-14)*0.25)for i in range(3))
def words(m,at):return tuple(read(m,at+4*i)for i in range(3))
def putvec(m,at,values):
 for i,v in enumerate(values):put(m,at+4*i,v)

def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2304)}
 for base,n in((OWNER,512),(ACTOR,512),(OTHER,512),(CHILD,160),(MARK,32)):
  assert base+n+16<=STACK-2048 or base-16>=STACK+2304
  m.update({base+i:(i*29+c.seed*11+0x51)&255 for i in range(-16,n+16)})
 for i in range(256):put(m,s['D_8008FC30']+4*i,s['_callbacks']+64*i)
 put(m,OWNER+0x28,actor(c));m[OWNER+0x2c]=c.identity;put(m,OWNER+0x30,CHILD if c.child else 0);m[OWNER+0x5c]=c.selector;put(m,OWNER+0xe,123,2)
 for a in(ACTOR,OTHER,OWNER):
  put(m,a,0x13579bdf);m[a+0x3b]=17;m[a+0xad]=0;put(m,a+0x184,0xdeadbeef)
  if a!=OWNER:put(m,a+0x28,0)
 # Owner+0x28 is the captured pointer, so actor==owner intentionally aliases
 # its vertical field. These cases are guest-only and retain that actual word.
 put(m,OWNER+0x28,actor(c));put(m,actor(c),c.live);m[actor(c)+0x3b]=c.actor_id
 if not c.alias:put(m,actor(c)+0x28,c.vertical)
 m[actor(c)+0xad]=c.busy;put(m,actor(c)+0x184,c.classword);putvec(m,OWNER+0x40,vectors(c));put(m,OWNER+0x58,0x42480000)
 return m

def service(m,c,target,a,s):
 captured=actor(c);length=s['func_15143E64'];classify=s['func_1510F8CC']
 if target==callback(c,s):
  putvec(m,a[1],tuple(bits(float(((c.seed+i*7)%31)-15)*0.5)for i in range(3)))
  if c.mutation&1:put(m,OWNER+0x28,OTHER);m[OWNER+0x5c]^=7;put(m,captured+0x184,c.classword^0x1000000f)
  if c.mutation&2:putvec(m,OWNER+0x34,(0x3f800000,0xc0000000,0x40400000))
  return u32(c.callback_result)
 if target==length:
  if c.mutation&4:put(m,captured+0x28,0x3f800000);m[captured+0xad]=1;put(m,captured+0x184,c.classword^0x10000006)
  if c.mutation&8:put(m,OWNER+0x28,OTHER);put(m,OWNER+0x58,0xc1200000);put(m,OWNER+0x30,0 if c.child else CHILD)
  return c.length
 if target==classify:
  if c.mutation&16:put(m,OWNER+0x58,0x7fc12345 if c.seed&1 else 0);put(m,captured+0x28,0);m[captured+0xad]=0;put(m,OWNER+0x30,CHILD if c.seed&1 else 0)
  return a[0]&31
 if target==s['func_1516972C']:put(m,MARK,0x33333333);return 0xdeadbeef
 assert target in(s['func_151D13E0'],s['func_151D1448'])
 put(m,MARK,0x11111111 if target==s['func_151D13E0']else 0x22222222);put(m,OWNER+0x30,0 if target==s['func_151D13E0']else CHILD)
 return 0xdeadbeef

def observation(m,target,a,s,c):
 if target==callback(c,s):return('callback',a,words(m,OWNER+0x34),words(m,OWNER+0x40))
 if target==s['func_15143E64']:return('length',a,words(m,a[0]))
 if target==s['func_1510F8CC']:return('classify',a,read(m,OWNER+0x58))
 return('final',target,a,read(m,OWNER+0x30),read(m,OWNER+0x58))

def reference(initial,c,s=None):
 s=S if s is None else s;m=initial.copy();calls=[];observed=[];captured=read(m,OWNER+0x28)
 def call(t,*a):
  a=tuple(map(u32,a));calls.append((t,a));observed.append(observation(m,t,a,s,c));return service(m,c,t,a,s)
 if read(m,captured)==0 or m[OWNER+0x2c]!=m[captured+0x3b]:put(m,OWNER+0xe,0xffff,2)
 else:
  putvec(m,OWNER+0x34,words(m,OWNER+0x40));detach=not call(callback(c,s),captured,OWNER+0x40)
  if detach:putvec(m,OWNER+0x40,words(m,OWNER+0x34))
  for i in range(3):put(m,OWNER+0x4c+4*i,bits(floating(read(m,OWNER+0x40+4*i))-floating(read(m,OWNER+0x34+4*i))))
  put(m,OWNER+0x58,call(s['func_15143E64'],OWNER+0x4c));kind=call(s['func_1510F8CC'],read(m,captured+0x184));distance=floating(read(m,OWNER+0x58))
  detach=detach or distance>300.0 or distance<=0.0 or floating(read(m,captured+0x28))!=0.0 or m[captured+0xad]!=0 or kind in(5,6,9,13,14)
  if detach:call(s['func_151D13E0'],OWNER)
  elif read(m,OWNER+0x30)==0:call(s['func_151D1448'],OWNER)
 return m,calls,observed

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=S if s is None else s;self.observed=[]
  super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=(OWNER,));self.fp_before=list(self.f);self.entry_sp=self.r[29]
 def record_call(self,t):
  counts={callback(self.c,self.s):2,self.s['func_15143E64']:1,self.s['func_1510F8CC']:1,self.s['func_151D13E0']:1,self.s['func_151D1448']:1,ENTRY:1,self.s['func_1516972C']:1};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t!=ENTRY:self.observed.append(observation(self.memory,t,a,self.s,self.c))
 def hook(self,t):
  result=service(self.memory,self.c,t,self.calls[-1][1],self.s)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
  if t==self.s['func_15143E64']:self.f[0]=result
  else:self.r[2]=u32(result)

def streams():return{label:bound_blob(*payload(o/path,p.FUNCTION),S)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.observed,m.dispatched_word)
def check(m,initial,c,s=None):
 expected,calls,observed=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert m.calls==calls,(c,'calls');assert m.observed==observed,(c,'observed');assert m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:]and m.r[29]==m.entry_sp,(c,'saved')
def main():
 programs=streams();assert len({tuple(v)for v in programs.values()})==1;assert struct.pack('>124I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x1fe5e8:0x1fe7d8];count=0;visits=set()
 for c in cases():
  initial=fixture(c);models=[]
  for ws in programs.values():m=Oracle(ws,initial,c);m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,complete_direct_instruction_and_binding_identity=True,independent_public_memory_calls_and_float_gates_equal=True,all_guest_private_bytes_and_saved_registers_equal=True,unexecuted_original_words=[i for i in range(124)if ENTRY+4*i not in visits],source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 programs=list(streams().values());count=0
 for c in(Case(),Case(live=0),Case(identity=1),Case(callback_result=0),Case(length=0x7fc12345,classword=31,mutation=3),Case(mutation=31,alias=1)):
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
 q=dict(full_state_and_dispatched_word_access_prefix_quadruples=count,portable_C_fault_claim=False);(o/'faults.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
def callers():
 raw=(o/'original-dispatcher.bin').read_bytes();assert len(raw)==180;caller=list(struct.unpack('>45I',raw));count=0;underflows=0;retired=0;tick_values=set()
 table=S['D_8008A4E8'];ticks=S['D_800BE9E4'];programs=streams()
 for c in list(cases())[::11]:
  initial=fixture(c);initial[OWNER+0xd]=c.seed&1;initial[OWNER+0x10]=255;initial[OWNER+0x11]=95;put(initial,table+95*4,ENTRY);step=(0,1,124,0x80000000)[c.seed//2%4];put(initial,ticks,step)
  before=initial.copy()
  if before[OWNER+0xd]&1:
   put(before,OWNER+0xe,read(before,OWNER+0xe,2)-step,2);tick_values.add(step);underflows+=int(bool(read(before,OWNER+0xe,2)&0x8000))
  expected,calls,obs=reference(before,c);calls=[(ENTRY,(OWNER,))]+calls
  if read(expected,OWNER+0xe,2)&0x8000:
   t=S['func_1516972C'];a=(OWNER,);calls.append((t,a));obs.append(observation(expected,t,a,S,c));service(expected,c,t,a,S);retired+=1
  models=[]
  for ws in programs.values():
   m=Oracle(caller,initial,c,entry=0x15149264,connected=dict(zip(range(ENTRY,ENTRY+496,4),ws)));m.run();assert public(m.memory)==public(expected)and m.calls==calls and m.observed==obs,(c,'complete caller');assert m.r[29]==m.entry_sp and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:];models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]);count+=1
 assert underflows>0 and retired>0 and len(tick_values)==4
 q=dict(complete_original_dispatcher_words=45,callback_table_index=95,cases_per_stream=count,all_four_streams_and_full_caller_return_equal=True,ticking_counter_values=sorted(tick_values),pre_callback_lifetime_underflow_cases=underflows,final_retirement_cases=retired,secondary_cleanup_callback_index=-1,final_retirement_provider='opaque compatible provider',additional_caller_matching_credit=0);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();print(json.dumps(faults()))
