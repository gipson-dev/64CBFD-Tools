"""Scene-view initialization, live count changes, request bytes and bounded caller."""
from dataclasses import dataclass
import json,struct
from tools.experiments import game_scene_view_setup_150fca30_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x150FCA30;OUTPUT=0x50000;MARK=0x70000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
u32=lambda v:v&0xffffffff
signed=lambda v:((v&0xffffffff)^0x80000000)-0x80000000
NAMES=('func_150FCBC0','func_1000FA64','func_15164F0C','func_151D8868')
ARITY=dict(zip(NAMES,(1,12,5,4)))
EXTRA={'func_151D87E0':1,'func_15181CC8':1,'func_1517EF00':1,'func_15167A68':6,'memcpy':3,'func_1501C010':2}
SOUND=((0x2b8,-2038,1560,-2631,45),(0x2b7,-319,-273,-3419,0),(0x2b6,1519,947,-2633,90))
@dataclass(frozen=True)
class Case:
 count:int=1
 mode:int=0
 seed:int=0
 phase:int=0
 gate:int=0

def cases():
 for count in(-2147483648,-2,-1,0,1,2,3,15,254,255,256,257,2147483647):
  for mode in range(7):
   for seed in(0,1):yield Case(count,mode,seed,8*seed)

def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,512)}
 for b,n in((OUTPUT,64),(MARK,32),(s['D_80082FA0'],4),(s['D_800E0B94'],1),(s['D_800BEAC0'],4),(s['D_80084060'],4),(s['D_800BE944'],4)):
  m.update({b+i:(i*29+c.seed*11+0x51)&255 for i in range(-16,n+16)})
 put(m,s['D_80082FA0'],c.count);m[s['D_800E0B94']]=int(c.gate==1)
 for i in range(4):m[s['D_800BEAC0']+i]=int(c.gate==3+i);m[s['D_80084060']+i]=i;m[s['D_800BE944']+i]=0 if c.gate==2 else 1
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}
def data(m,at,n):return bytes(m[at+i]for i in range(n))
def packet(m,home):
 at=home-12;m[at]=1;put(m,at+2,100,2);m[at+5]=15;m[at+4]=8;m[at+6]=255
 return at

class Providers:
 def __init__(self,m,c,s=None):self.m=m;self.c=c;self.s=S if s is None else s;self.calls=[];self.observed=[];self.resets=0;self.sounds=0;self.views=0;self.copies=[]
 def invoke(self,name,args):
  m,c,s=self.m,self.c,self.s;a=tuple(map(u32,args));self.calls.append((s[name],a));self.observed.append(read(m,s['D_80082FA0']));put(m,MARK,len(self.calls))
  value=0xdead8001
  if name==NAMES[0]:
   self.resets+=1
   if c.mode==1 and self.resets==1:put(m,s['D_80082FA0'],3)
  elif name==NAMES[1]:
   self.sounds+=1
   if c.mode==2 and self.sounds==3:put(m,s['D_80082FA0'],-1)
   if c.mode==6:put(m,s['D_80082FA0'],self.sounds-1)
  elif name==NAMES[2]:
   self.views+=1
   if c.mode==3 and self.views==1:put(m,s['D_80082FA0'],-1)
   if c.mode==4 and self.views==1:put(m,s['D_80082FA0'],3)
   if c.mode==5 and self.views==256:put(m,s['D_80082FA0'],255)
  elif name==NAMES[3]:
   self.copies.append(data(m,a[0],8))
   # Bounded opaque helper models the actual eight-byte copy, without claiming
   # that its validation/allocator providers were executed.
   for i,b in enumerate(self.copies[-1]):m[OUTPUT+14+i]=b
   value=OUTPUT
  elif name=='func_151D87E0':value=0 if c.gate==2 else 1
  elif name=='func_15181CC8':value=0 if c.gate==7 else 1
  elif name=='func_1517EF00':value=1 if c.gate==8 else 0
  elif name=='func_15167A68':value=0 if c.gate==9 else OUTPUT
  elif name=='func_1501C010':value=0xdeadbeef
  else:raise AssertionError(name)
  return u32(value)

def reference(initial,c,s=None,home=None):
 s=S if s is None else s;m=initial.copy();q=Providers(m,c,s);home=STACK+c.phase if home is None else home
 for i in range(3):q.invoke(NAMES[0],(i,))
 for kind,x,y,z,angle in SOUND:q.invoke(NAMES[1],(kind,x,y,z,28000,9000,7000,s['func_1000EC24'],angle,0,0,0))
 index=0
 if signed(u32(read(m,s['D_80082FA0'])+1))>0:
  while True:
   q.invoke(NAMES[2],(4,index&255,0,255,1));index=u32(index+1)
   if signed(index)>signed(read(m,s['D_80082FA0'])):break
   assert q.views<1024
 at=packet(m,home);q.invoke(NAMES[3],(at,0,255,0));return m,q

class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=S if s is None else s
  super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=())
  self.fp_before=self.f[:];self.entry_sp=self.r[29];self.providers=Providers(self.memory,c,self.s);self.request_copies=[]
 def record_call(self,t):
  if t==ENTRY:name=None;n=0
  else:name=next(n for n in(*NAMES,*EXTRA)if self.s[n]==t);n=(ARITY|EXTRA)[name]
  a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if name=='memcpy':self.request_copies.append(data(self.memory,a[1],a[2]))
 def hook(self,t):
  name=next(n for n in(*NAMES,*EXTRA)if self.s[n]==t);value=self.providers.invoke(name,self.calls[-1][1])
  for i in range(4):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value

def streams(s=None):return{label:bound_blob(*payload(o/path,p.FUNCTION),S if s is None else s)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.providers.observed,m.request_copies,m.dispatched_word)
def saved(m):return m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:]and m.r[29]==m.entry_sp
def check(m,initial,c,s=None,caller=False):
 expected,q=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert m.providers.calls==q.calls,(c,'calls',m.providers.calls,q.calls);assert m.providers.observed==q.observed,(c,'live reads');assert m.providers.copies==q.copies,(c,'packet')
 if caller:assert m.r[16:24]==m.before[16:24]and m.r[28:31]==m.before[28:31]and m.f[20:]==m.fp_before[20:]and m.r[31]==0x1509d454
 else:assert saved(m),(c,'saved')

def main():
 programs=streams();assert len({tuple(ws)for ws in programs.values()})==1;rom=(r/'conker/conker.us.bin').read_bytes();assert struct.pack('>100I',*programs['retail'])==rom[0x129ee0:0x12a070];visits=set();count=0
 for c in cases():
  initial=fixture(c);models=[]
  for ws in programs.values():m=Oracle(ws,initial,c);m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,direct_complete_identity=True,all_private_and_public_bytes_registers_accesses_calls_equal=True,independent_public_semantics_equal=True,unexecuted_original_words=[i for i in range(100)if ENTRY+4*i not in visits],unwritten_packet_bytes_preserved=True,full_index_vs_low_byte=True,live_count_mutations=True,void_result_compared=False,source_installed=p.installed(),matching_credit=0)
 (o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q

def faults():
 programs=streams();count=0
 for c in(Case(),Case(-1),Case(0,4),Case(3,4,1,8)):
  initial=fixture(c);full=Oracle(programs['retail'],initial,c);full.run()
  for cut in range(full.all_accesses):
   states=[]
   for ws in programs.values():
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access boundary did not fire')
    states.append(state(m))
   assert all(x==states[0]for x in states[1:]);count+=1
 q=dict(four_stream_full_state_and_dispatched_access_prefixes=count,portable_C_fault_claim=False);(o/'faults.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q

def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();begin=0x1509d44c;end=0x1509d76c;fragment=struct.unpack_from('>4I',rom,begin-0x15000000+0x2d4b0);count=0
 for c in(Case(),Case(-1),Case(0,4),Case(256,5,1,8)):
  initial=fixture(c);put(initial,STACK+c.phase+0xc4,0x87654321);models=[]
  for ws in streams().values():
   code=dict(zip(range(ENTRY,ENTRY+400,4),ws));code[end]=0;m=Oracle(fragment,initial,c,entry=begin,connected=code);m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller continuation not reached')
   check(m,initial,c,caller=True);assert m.r[2]==0x87654321 and m.r[29]==m.entry_sp;assert [a for t,a in m.calls if t==ENTRY]==[()];models.append(m)
  assert all(state(x)==state(models[0])for x in models[1:]);count+=1
 q=dict(original_bounded_caller_words=4,cases_per_stream=count,complete_dispatcher_claim=False,continuation_value_from_caller_stack=True,void_target_result_ignored=True);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q

def connected():
 rom=(r/'conker/conker.us.bin').read_bytes();code={}
 for entry,at,n in((0x151d8868,0x205d18,111),(0x151d87e0,0x205c90,34),(0x10022ec0,0x22ec0,11)):
  code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>'+str(n)+'I',rom,at)))
 count=copied=0
 for seed in range(4):
  for gate in range(10):
   c=Case(count=2,seed=seed,phase=8*(seed&1),gate=gate);initial=fixture(c);models=[]
   for ws in streams().values():
    m=Oracle(ws,initial,c,connected=code);m.run();assert saved(m);models.append(m)
    if gate==0:
     at=STACK+c.phase-12;packet_bytes=data(m.memory,at,8);assert m.request_copies==[packet_bytes];assert data(m.memory,OUTPUT+14,8)==packet_bytes;assert packet_bytes[1]==initial[at+1]and packet_bytes[7]==initial[at+7];assert m.memory[OUTPUT+22]==8
     assert [(a[0],a[1])for t,a in m.calls if t==S['func_1501C010']]==[(i,8)for i in range(4)]
    else:assert not m.request_copies and data(m.memory,OUTPUT,64)==data(initial,OUTPUT,64)
   assert all(state(x)==state(models[0])for x in models[1:]);count+=1;copied+=int(gate==0)
 q=dict(cases_per_stream=count,full_eight_byte_copy_cases=copied,original_request_helper_words=111,original_mask_validator_words=34,original_memcpy_words=11,seeded_unwritten_bytes_copied=True,allocator_player_validation_and_level_providers_bounded=True,full_transitive_provider_claim=False);(o/'connected.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main();print(faults());print(callers());connected()
