"""Independent command snapshots, live banks, provider effects and public aliases."""
from dataclasses import dataclass,replace
import json,struct
from tools.experiments import game_actor_command_1506e46c_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x1506e46c;ACTOR=0x30000;COMMAND=0x50000;MARK=0x70000;ROWA=0x100000;ROWB=0x140000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};u32=lambda v:v&0xffffffff
@dataclass(frozen=True)
class Case:
 seed:int=0
 code:int=0xff2007d0
 mode:int=0
 gate:int=0
 replacement:int=0x00030017
 random:int=0
 choice:int=0xdeadbeef
 mutation:int=0
 alias:int=0
 selector:int=0
 phase:int=0
 command_address:int=0
def row_index(c):return max((c.code&0x7fff)-2000,0)
def command(c,s=None):
 s=S if s is None else s
 return c.command_address or(ACTOR+0x284 if c.alias==1 else s['D_800BE5A8']+4*c.selector if c.alias==2 else ROWA+4*row_index(c)if c.alias==3 else MARK if c.alias==4 else COMMAND)
def cases():
 for index in(0,1,1999,2000,2001,32767):
  for flags in(0,0x200000,0x01000000,0xff200000,0xffff0000,0x80000000):
   for mode in(0,1,2,3,-1,0x80000000):
    for gate in(0,1,2,-1):yield Case(code=flags|index,mode=mode,gate=gate,seed=index%4,selector=(0,1,127,255)[index%4])
 for threshold in(0,1,127,255):
  for random in range(256):yield Case(code=(threshold<<24)|0x30011,random=random,choice=(0,1,0xffffffff,0x80000000,0xffff8000)[random%5],seed=random%4,selector=(0,1,127,255)[random%4])
 for value in(0,1,0x10001,0xffffff,0x80000000,0xff000000,0xffffffff,0x10000001):
  for flags in(0,0x200000,0xff200000,0x80000000):
   for random in(0,1,255):yield Case(code=flags|2000,replacement=value,random=random)
 for mode in(0,1,2,3):
  for mutation in(1,2,4,8,16,32,63):
   for alias in range(5):yield Case(mode=mode,mutation=mutation,alias=alias,code=0xff230011 if alias==2 else 0xff2007d0,selector=(0,1,127,255)[mode],phase=8*(mutation&1),seed=mutation%4)
def banks(c,s=None):
 s=S if s is None else s;return((ACTOR,704),(c.command_address or COMMAND,16),(MARK,32),(s['D_800BE5A8'],1024),(ROWA+4*row_index(c),4),(ROWB+4*row_index(c),4))
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,256)}
 for base,n in banks(c,s):m.update({base+i:(i*29+c.seed*11+0x51)&255 for i in range(-16,n+16)})
 for i in range(256):put(m,s['D_800BE5A8']+4*i,ROWA)
 put(m,s['D_800BE5A8']+4*((c.selector+1)&255),ROWB);m[ACTOR+0x288]=c.selector;put(m,ROWA+4*row_index(c),c.replacement);put(m,ROWB+4*row_index(c),c.replacement^0x10000001);put(m,command(c,s),c.code);return m
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+256}
def observation(m,c,s):return(read(m,command(c,s)),m[ACTOR+0x288],read(m,s['D_800BE5A8']+4*m[ACTOR+0x288]),read(m,ROWA+4*row_index(c)),read(m,ROWB+4*row_index(c)),read(m,MARK),read(m,ACTOR+0x284))
class Providers:
 def __init__(self,m,c,s=None):self.m=m;self.c=c;self.s=S if s is None else s;self.calls=[];self.observed=[]
 def invoke(self,name,a):
  m,c,s=self.m,self.c,self.s;a=tuple(map(u32,a));self.calls.append((s[name],a));self.observed.append(observation(m,c,s));put(m,MARK,len(self.calls));at=4*row_index(c)
  if name in('func_100107F8','func_10010894','func_151F2CDC'):
   assert a==(()if name=='func_151F2CDC'else(ACTOR,))
   if c.mutation&1:put(m,command(c,s),0x12345678);m[ACTOR+0x288]=(c.selector+1)&255
   if c.mutation&2:put(m,ROWA+at,0);put(m,ROWB+at,0)
   if c.mutation&16:put(m,s['D_800BE5A8']+4*m[ACTOR+0x288],ROWB)
   answer=c.gate
  elif name=='func_150ADA20':
   assert not a
   if c.mutation&4:put(m,command(c,s),0x01234567);m[ACTOR+0x288]^=0x80
   if c.mutation&32:put(m,ROWA+at+4,0x13579bdf);put(m,ROWB+at-4,0xfedcba98)
   answer=c.random
  else:
   assert name=='func_1000F568'and len(a)==2
   if c.mutation&8:put(m,command(c,s),0x89abcdef);m[ACTOR+0x288]^=0x80;put(m,s['D_800BE5A8']+4*m[ACTOR+0x288],ROWA)
   answer=c.choice
  return u32(answer)
def reference(initial,c,s=None):
 s=S if s is None else s;m=initial.copy();service=Providers(m,c,s);word=read(m,command(c,s));index=word&0x7fff
 if word&0x200000:
  name={0:'func_100107F8',1:'func_10010894',2:'func_151F2CDC'}.get(c.mode)
  if name:
   result=service.invoke(name,()if c.mode==2 else(ACTOR,))
   if(result==1 if c.mode==2 else result!=0):return m,service,0
 if index>=2000:
  base=read(m,s['D_800BE5A8']+4*m[ACTOR+0x288]);value=read(m,base+4*(index-2000))
  if value==0:return m,service,0
  flags=word&0xff200000;word=flags|(value&0xffffff)if flags else value
 options=word>>16
 if options:
  random=service.invoke('func_150ADA20',())
  if random&255>word>>24:return m,service,0
  word&=0x7fff
  if options&31:word=service.invoke('func_1000F568',(word,options&31))
 put(m,command(c,s),word);return m,service,1
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None,arguments=None):
  self.c=c;self.s=S if s is None else s;super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=(ACTOR,command(c,self.s),c.mode)if arguments is None else arguments);self.fp_before=self.f[:];self.entry_sp=self.r[29];self.providers=Providers(self.memory,c,self.s)
 def record_call(self,t):
  counts={self.s['func_100107F8']:1,self.s['func_10010894']:1,self.s['func_151F2CDC']:0,self.s['func_150ADA20']:0,self.s['func_1000F568']:2,ENTRY:3};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  name=next(n for n in('func_100107F8','func_10010894','func_151F2CDC','func_150ADA20','func_1000F568')if self.s[n]==t);result=self.providers.invoke(name,self.calls[-1][1])
  for i in range(4):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=result
def streams(s=None):return{label:bound_blob(*payload(o/path,p.FUNCTION),S if s is None else s)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.providers.observed,m.dispatched_word)
def saved(m):return m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:]and m.r[29]==m.entry_sp
def check(m,initial,c,s=None):
 expected,service,result=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert m.providers.calls==service.calls,(c,'calls',m.providers.calls,service.calls);assert m.providers.observed==service.observed,(c,'observed');assert m.r[2]==result,(c,'result');assert saved(m),(c,'saved')
def main():
 programs=streams();assert len({tuple(v)for k,v in programs.items()if k!='raw'})==1;assert struct.pack('>100I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x9b91c:0x9baac];count=0;visits=set()
 for c in cases():
  initial=fixture(c);models=[]
  for ws in programs.values():m=Oracle(ws,initial,c);m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,padded_retail_complete_identity=True,independent_public_effects_calls_observations_results_equal=True,padded_retail_all_private_bytes_and_registers_equal=True,raw_private_or_fault_identity_claim=False,unexecuted_original_words=[i for i in range(100)if ENTRY+4*i not in visits],source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 programs=[v for k,v in streams().items()if k!='raw'];count=0
 for c in(Case(),Case(gate=1),Case(code=17),Case(mode=2,gate=2,mutation=63,alias=1),Case(code=0x00030011,random=255,alias=3),Case(alias=4,mutation=8,phase=8)):
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
 q=dict(padded_retail_full_state_and_dispatched_access_prefix_triples=count,raw_private_or_portable_C_fault_claim=False);(o/'faults.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
POST=('func_1506BA4C','func_1506BB64','func_1506BAD8')
class CallerProviders(Providers):
 def invoke(self,name,a):
  if name not in POST:return super().invoke(name,a)
  a=tuple(map(u32,a));assert a==(300,1800);self.calls.append((self.s[name],a));self.observed.append(observation(self.m,self.c,self.s));put(self.m,MARK,0xcafe0000^self.s[name]);self.m[ACTOR+0x288]^=1;return 0xdead1234
class CallerOracle(Oracle):
 def __init__(self,*args,**kw):super().__init__(*args,**kw);self.providers=CallerProviders(self.memory,self.c,self.s)
 def record_call(self,t):
  if t in{self.s[n]for n in POST}:a=tuple(map(u32,self.arguments(2)));self.calls.append((t,a));self.events.append(('CALL',t,a))
  else:super().record_call(t)
 def hook(self,t):
  name=next((n for n in POST if self.s[n]==t),None)
  if name is None:return super().hook(t)
  value=self.providers.invoke(name,self.calls[-1][1])
  for i in range(4):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def callers():
 programs=streams();rom=(r/'conker/conker.us.bin').read_bytes();count=called=bypassed=0;global_actor=S['D_800D154C'];global_command=S['D_800D1580'];fixtures=(Case(),Case(gate=1),Case(gate=2),Case(code=17),Case(replacement=0),Case(code=0x00030011,random=255),Case(choice=0x80000000,mutation=8),Case(mode=2,gate=0,mutation=63,phase=8))
 for begin,mode,post in((0x1506e5fc,0,POST[0]),(0x1506e898,2,POST[1]),(0x1506e8d8,1,POST[2])):
  offset=begin-0x15000000+0x2d4b0;caller=list(struct.unpack('>16I',rom[offset:offset+64]));(o/(f'{begin:x}-original-caller.bin')).write_bytes(rom[offset:offset+64])
  for original in fixtures:
   c=replace(original,mode=mode,command_address=global_command);initial=fixture(c)
   for i in range(-16,20):initial[global_actor+i]=0xa5
   put(initial,global_actor,ACTOR);expected,service,result=reference(initial,c);after=CallerProviders(expected,c);after.calls=service.calls[:];after.observed=service.observed[:]
   if result:after.invoke(post,(300,1800));called+=1
   else:bypassed+=1
   models=[]
   for ws in programs.values():
    code=dict(zip(range(ENTRY,ENTRY+4*len(ws),4),ws));m=CallerOracle(caller,initial,c,entry=begin,connected=code,arguments=(0x12345678,0x87654321,0xfedcba98));m.run();assert public(m.memory)==public(expected)and m.providers.calls==after.calls and m.providers.observed==after.observed,(begin,c,'connected caller');assert saved(m),(begin,c,'caller ABI');assert [a for t,a in m.calls if t==ENTRY]==[(ACTOR,global_command,mode)];models.append(m)
   assert all(state(m)==state(models[1])for m in models[2:]);count+=1
 q=dict(actual_original_callers=3,words_per_caller=16,modes=[0,2,1],cases_per_stream=count,post_action_called_cases=called,post_action_bypassed_cases=bypassed,all_four_streams_complete_caller_state_and_arguments_equal=True,caller_boolean_result_consumption_verified=True,transitive_provider_execution_claim=False,additional_caller_matching_credit=0);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();print(json.dumps(faults()),flush=True)
