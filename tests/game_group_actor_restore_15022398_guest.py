"""Group actor restoration, public alias effects and original complete caller."""
from dataclasses import dataclass,replace
import json,struct
from tools.experiments import game_group_actor_restore_15022398_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x15022398;ACTIVE=0x30000;ROWA=0x40000;ROWB=0x50000;DESCA=0x100000;DESCB=0x110000;MARK=0x70000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};u32=lambda v:v&0xffffffff;signed=lambda v:((v&0xffffffff)^0x80000000)-0x80000000
PROVIDERS=('func_15083E0C','func_1505EEF4','func_15082A44','func_1505E650','func_1502225C','func_150222E0');ARITY=dict(zip(PROVIDERS,(1,1,5,7,2,2)))
@dataclass(frozen=True)
class Case:
 seed:int=0
 index:int=0
 group:int=0
 enabled:int=1
 kind:int=2
 identity:int=1
 key:int=1
 first:int=1
 second:int=1
 state:int=3
 flags:int=0xffffffff
 count:int=4
 slot:int=0
 mutation:int=0
 alias:int=0
 phase:int=0
 length:int=3
 runflag:int=1
 caller_mutation:int=0
def cases():
 for enabled in(0,1,2,65535):
  for kind in(0,1,2,3,65535):
   for group in(0,1):
    for key in(-1,0,1,255,0x80000000):yield Case(enabled=enabled,kind=kind,group=group,key=key)
 for first,second in((0,0),(0,1),(0,2),(1,0),(2,1)):
  for key,count in((-2,0),(-1,255),(0,0),(0,1),(1,1),(1,2),(254,255),(255,255),(0x7fffffff,255),(0x80000000,255)):
   for group in(0,1):yield Case(first=first,second=second,key=key,count=count,group=group)
 for identity in range(256):yield Case(identity=identity,group=identity&1,slot=(0,1,24,25)[identity%4],flags=(0,0x2a,0xffffffff,0x80000000)[identity%4])
 for mutation in(1,2,4,8,16,32,63):
  for alias in range(4):
   for group in(0,1):
    for first in(0,1):yield Case(mutation=mutation,alias=alias,group=group,first=first,seed=mutation%4,phase=8*(group&1))
 for state in(0,1,2,3,4,255):
  for flags in(0,1,0x2a,0xffffffff,0x80000000):
   for index in(0,1,3):yield Case(state=state,flags=flags,index=index)
 for slot in(1,24,25):
  for group in(0,1):yield Case(slot=slot,group=group,first=0,mutation=32)
def actor(c,value=1,s=None):return (S if s is None else s)['D_800CC2D0']+((c.slot if value==1 else(c.slot+1)%26)*0x32c)
def row(c,group=0,s=None):
 s=S if s is None else s
 if c.alias==1:return actor(c,1,s)
 return ROWA if group==0 or c.alias==2 else ROWB
def active(c,group=0,s=None):return row(c,group,s)if c.alias==3 else ACTIVE+8*group
def banks(c,s=None):
 s=S if s is None else s;return((s['D_800C35C8'],48),(s['D_800C3638'],4),(s['D_800D20FC'],8),(ACTIVE,16),(ROWA,32),(ROWB,32),(DESCA,256*48),(DESCB,256*48),(s['D_800CC2D0'],26*0x32c),(MARK,32))
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,256)}
 for b,n in banks(c,s):m.update({b+i:(i*29+c.seed*11+0x51)&255 for i in range(-16,n+16)})
 for value in(1,2):a=actor(c,value,s);m[a+5]=c.state;put(m,a+0xf4,c.flags)
 for group in(0,1):
  put(m,s['D_800C35C8']+4*group,active(c,group,s));put(m,s['D_800C35F0']+4*group,row(c,group,s));m[s['D_800C35EA']+group]=c.runflag;m[s['D_800C363A']+group]=c.length
  for i in range(4):put(m,active(c,group,s)+2*i,c.enabled,2);put(m,row(c,group,s)+8*i,c.kind,2);m[row(c,group,s)+8*i+2]=c.identity
 put(m,s['D_800D20FC'],DESCA);m[s['D_800D2100']]=c.count
 if signed(c.key)<-1:
  for base in(DESCA,DESCB):
   at=u32(base+u32(c.key)*48)
   for i in range(-16,64):m.setdefault(at+i,(i*29+c.seed*11+0x51)&255)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+256}
def observation(m,c,s):
 return tuple(read(m,s['D_800C35C8']+4*g)for g in(0,1))+tuple(read(m,s['D_800C35F0']+4*g)for g in(0,1))+(read(m,s['D_800D20FC']),m[s['D_800D2100']],m[s['D_800C3638']],m[s['D_800C363A']+c.group],read(m,MARK))+tuple(v for val in(1,2)for v in(m[actor(c,val,s)+5],read(m,actor(c,val,s)+0xf4)))
class Providers:
 def __init__(self,m,c,s=None):self.m=m;self.c=c;self.s=S if s is None else s;self.calls=[];self.observed=[];self.index=c.index;self.group=c.group;self.lookups=0;self.last_actor=None;self.posts=0
 def invoke(self,name,args):
  m,c,s=self.m,self.c,self.s;a=tuple(map(u32,args));self.calls.append((s[name],a));self.observed.append(observation(m,c,s));put(m,MARK,len(self.calls))
  if name==PROVIDERS[0]:
   assert len(a)==1 and a[0]<=255;self.lookups=0
   if c.mutation&1:
    for g in(0,1):put(m,s['D_800C35F0']+4*g,ROWB);m[row(c,g,s)+8*self.index+2]=255
   value=c.key
  elif name==PROVIDERS[1]:
   assert a==(u32(c.key),);self.lookups+=1;result=c.first if self.lookups==1 else c.second;value=actor(c,result,s)if result else 0;self.last_actor=value
   if c.mutation&2:
    m[s['D_800D2100']]=255 if c.seed&1 else 0;put(m,s['D_800D20FC'],DESCB)
    if value:m[value+5]=3;put(m,value+0xf4,0xaaaaaaaa)
  elif name==PROVIDERS[2]:
   expected=u32(read(m,s['D_800D20FC'])+u32(c.key)*48);assert a==(expected,u32(c.key),0,u32(self.group),0),('construct',a,expected)
   # Guest modular addresses can wrap; materialize the observed descriptor byte.
   assert expected+2 in m,'Descriptor fixture is not mapped';m[expected+2]^=1
   if c.mutation&4:
    m[s['D_800D2100']]=0;put(m,s['D_800D20FC'],DESCA);put(m,s['D_800C35F0']+4*self.group,ROWA);m[ROWA+8*self.index+2]=0
   value=0x12345678
  elif name==PROVIDERS[3]:
   assert a==(self.last_actor,0,0,0,0,0,1),('physics',a,self.last_actor)
   if c.mutation&8:m[self.last_actor+5]=255;put(m,self.last_actor+0xf4,0x12345678);put(m,s['D_800C35F0']+4*self.group,ROWB)
   if c.mutation&32:self.last_actor=actor(c,2,s)
   value=0x87654321
  elif name==PROVIDERS[4]:
   assert len(a)==2;put(m,MARK+4,a[0]);put(m,MARK+8,a[1])
   if c.mutation&16:m[s['D_800C363A']+self.group]=min(c.length,2);put(m,s['D_800C35F0']+4*self.group,ROWB)
   value=0xfedcba98
  else:
   assert name==PROVIDERS[5]and a==(u32(self.index),u32(self.group));self.posts+=1
   if c.caller_mutation==1:m[s['D_800C363A']+self.group]=0
   elif c.caller_mutation==2 and self.posts==1:m[s['D_800C363A']+self.group]=3
   value=0xdeadbeef
  return u32(value)
def execute(m,service,index,group,s=None):
 s=S if s is None else s;service.index=index;service.group=group
 if read(m,read(m,s['D_800C35C8']+4*group)+2*index,2)==0:return
 entry=s['D_800C35F0']+4*group;record=read(m,entry)+8*index
 if read(m,record,2)!=2:return
 identity=m[record+2];key=service.invoke(PROVIDERS[0],(identity,))
 if key==0xffffffff:return
 a=service.invoke(PROVIDERS[1],(key,))
 if a:
  if m[a+5]==3:m[a+5]=0 if entry==s['D_800C35F0']else 4
  if identity==1:put(m,a+0xf4,read(m,a+0xf4)&0xffffffd5)
 elif signed(key)<m[s['D_800D2100']]:
  service.invoke(PROVIDERS[2],(u32(read(m,s['D_800D20FC'])+key*48),key,0,group,0));a=service.invoke(PROVIDERS[1],(key,))
  if a:
   service.invoke(PROVIDERS[3],(a,0,0,0,0,0,1));difference=signed(u32(a-s['D_800CC2D0']));quotient=(abs(difference)//0x32c)*(-1 if difference<0 else 1);service.invoke(PROVIDERS[4],(u32(quotient),group))
def reference(initial,c,s=None):
 s=S if s is None else s;m=initial.copy();service=Providers(m,c,s);execute(m,service,c.index,c.group,s);return m,service
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None,arguments=None):
  self.c=c;self.s=S if s is None else s;super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=(c.index,c.group)if arguments is None else arguments);self.fp_before=self.f[:];self.entry_sp=self.r[29];self.providers=Providers(self.memory,c,self.s)
 def record_call(self,t):
  n=2 if t==ENTRY else ARITY[next(n for n in PROVIDERS if self.s[n]==t)];a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==ENTRY:self.providers.index=signed(a[0]);self.providers.group=signed(a[1])
 def hook(self,t):
  name=next(n for n in PROVIDERS if self.s[n]==t);value=self.providers.invoke(name,self.calls[-1][1])
  for i in range(4):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
def streams(s=None):return{label:bound_blob(*payload(o/path,p.FUNCTION),S if s is None else s)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.providers.observed,m.dispatched_word)
def saved(m):return m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:]and m.r[29]==m.entry_sp
def check(m,initial,c,s=None):
 expected,service=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert m.providers.calls==service.calls,(c,'calls',m.providers.calls,service.calls);assert m.providers.observed==service.observed,(c,'observed');assert saved(m),(c,'saved')
def main():
 programs=streams();assert len({tuple(v)for k,v in programs.items()if k!='raw'})==1;assert struct.pack('>100I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x4f848:0x4f9d8];count=0;visits=set()
 for c in cases():
  initial=fixture(c);models=[]
  for ws in programs.values():m=Oracle(ws,initial,c);m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,padded_retail_complete_identity=True,independent_public_effects_calls_observations_equal=True,padded_retail_all_private_bytes_and_registers_equal=True,raw_private_or_fault_identity_claim=False,void_return_value_compared=False,unexecuted_original_words=[i for i in range(100)if ENTRY+4*i not in visits],source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 programs=[v for k,v in streams().items()if k!='raw'];count=0
 for c in(Case(),Case(enabled=0),Case(kind=1),Case(key=-1),Case(first=0,second=0),Case(first=0,mutation=63,alias=1,phase=8)):
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
def callers():
 programs=streams();rom=(r/'conker/conker.us.bin').read_bytes();begin=0x15022848;offset=0x4fcf8;caller=list(struct.unpack('>39I',rom[offset:offset+156]));(o/'15022848-original-caller.bin').write_bytes(rom[offset:offset+156]);count=callbacks=posts=0
 for c in(Case(),Case(length=0),Case(runflag=0),Case(runflag=2),Case(first=0),Case(key=-1),Case(caller_mutation=1),Case(length=1,caller_mutation=2),Case(mutation=63,first=0),Case(alias=1),Case(alias=2,group=1),Case(alias=3,group=1)):
  initial=fixture(c);expected=initial.copy();service=Providers(expected,c);calls=0
  if expected[S['D_800C35EA']+c.group]==1:
   expected[S['D_800C3638']]=0;i=0
   while i<expected[S['D_800C363A']+c.group]:
    assert i<4;execute(expected,service,i,c.group);service.invoke(PROVIDERS[5],(i,c.group));i+=1;calls+=1
   expected[S['D_800C3638']]=1
  models=[]
  for ws in programs.values():
   connected=dict(zip(range(ENTRY,ENTRY+4*len(ws),4),ws));m=Oracle(caller,initial,c,entry=begin,connected=connected,arguments=(c.group,));m.run();assert public(m.memory)==public(expected)and m.providers.calls==service.calls and m.providers.observed==service.observed,(c,'caller public/calls');assert saved(m),(c,'caller saved');assert [a for t,a in m.calls if t==ENTRY]==[(i,c.group)for i in range(calls)];models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);callbacks+=calls;posts+=sum(t==S[PROVIDERS[5]]for t,a in service.calls);count+=1
 q=dict(actual_original_complete_caller=True,words=39,frame=40,cases_per_stream=count,target_calls=callbacks,post_calls=posts,live_count_shrink_and_growth=True,void_callback_result_ignored=True,all_four_streams_complete_caller_state_equal=True,transitive_provider_execution_claim=False,additional_caller_matching_credit=0);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main();print(json.dumps(faults()),flush=True);callers()
