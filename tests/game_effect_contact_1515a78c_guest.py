"""Effect callback with live public aliases and retained initialized point."""
from dataclasses import dataclass,replace
import json,math,struct
from tools.experiments import game_effect_contact_1515a78c_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_animation_timeline_oracle import bits,floating
r,o=p.ROOT,p.OUT;ENTRY=0x1515a78c;RECORD=0x30000;POSITION=0x50000;MARK=0x70000;POINT=0x88000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};u32=lambda v:v&0xffffffff
GLOBALS=('D_800A6408','D_800A640C','D_800A6410');PROVIDERS=('func_1515A60C','func_1514672C','func_15046C00','func_150ADA68','func_151D8E20','func_151DBCBC');ARITY=dict(zip(PROVIDERS,(2,1,4,0,0,7)))
@dataclass(frozen=True)
class Case:
 seed:int=0
 vertical:int=0x3f800000
 rate:int=0xc7c34ff3
 threshold:int=0x40000000
 inside:int=1
 hit:int=1
 floor:int=0x3fa00000
 random:int=0
 state:int=3
 selector:int=255
 mutation:int=0
 alias:int=0
 phase:int=0
 position_address:int=0
def position(c):return c.position_address or(RECORD+0x40 if c.alias==1 else RECORD+0x44 if c.alias==2 else RECORD+0xb8 if c.alias==3 else POSITION)
def cases():
 for vertical in(0,0x80000000,0x3f800000,0xbf800000,1,0x80000001,0x7f800000,0x7fc00001):
  for rate in(0xc7c34ff3,0xc7c34ff2,0xc7c34ff4,0,0x40000000,0x40000001,0xbf800000,0x7f800000,0xff800000,0x7fc00001):
   for inside,hit in((0,0),(0xffffffff,0),(1,1),(1,0x80000000)):yield Case(vertical=vertical,rate=rate,inside=inside,hit=hit)
 for state in(0,2,3,4,255):
  for random in(0,0x80000000,0x3e4ccccc,0x3e4ccccd,0x3e4cccce,0xbf800000,1,0x7f800000,0xff800000,0x7fc00001,0x7f7fffff):
   for rate in(0,0xc7c34ff3):yield Case(state=state,random=random,rate=rate,seed=state%4)
 for selector in range(256):yield Case(selector=selector,seed=selector%4)
 for mutation in(1,2,4,8,16,32,63):
  for alias in range(4):
   for inside,hit in((0,1),(1,0),(1,1),(-1,-1)):yield Case(mutation=mutation,alias=alias,inside=inside,hit=hit,phase=8*(alias&1),seed=mutation%4)
 for floor in(0,0x80000000,0x7f800000,0xff800000,0x7fc00001,1):yield Case(floor=floor)
def banks(c,s=None):
 s=S if s is None else s;return((RECORD,0xcc),(POSITION,12),(MARK,32),(s[GLOBALS[0]],12))
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,256)}
 for b,n in banks(c,s):m.update({b+i:(i*29+c.seed*11+0x51)&255 for i in range(-16,n+16)})
 for offset,value in((0x40,bits(1)),(0x44,c.threshold),(0x48,bits(3)),(0x4c,bits(0.25)),(0x54,bits(-0.5)),(0x5c,c.vertical),(0x80,c.floor),(0xa8,bits(8)),(0xc8,c.rate)):put(m,RECORD+offset,value)
 m[RECORD+0x9d]=c.state
 for i,v in enumerate((bits(9),bits(10),bits(11))):put(m,position(c)+4*i,v)
 for name,value in zip(GLOBALS,(0xc7c34ff3,0x3e4ccccd,0x3e4ccccd)):put(m,s[name],value)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+256 and not POINT<=a<POINT+12}
def observation(m,s,point):
 return tuple(read(m,RECORD+i)for i in(0x40,0x44,0x48,0x4c,0x54,0x5c,0x80,0xa8,0xc8))+tuple(m[RECORD+i]for i in(1,0xc,0x2b,0x9d))+tuple(read(m,s[n])for n in GLOBALS)+(read(m,MARK),)+(tuple(read(m,point+4*i)for i in range(3))if point is not None else(0,0,0))
class Providers:
 def __init__(self,m,c,s=None):self.m=m;self.c=c;self.s=S if s is None else s;self.calls=[];self.observed=[];self.point=None
 def invoke(self,name,args):
  m,c,s=self.m,self.c,self.s;a=tuple(map(u32,args))
  if name in('func_1514672C','func_15046C00'):self.point=a[0]
  elif name=='func_151DBCBC':
   if self.point is None:self.point=a[4]
   else:assert self.point==a[4]
  canonical=tuple(POINT if self.point is not None and v==self.point else v for v in a);self.calls.append((s[name],canonical));self.observed.append(observation(m,s,self.point));put(m,MARK,len(self.calls))
  if name=='func_1515A60C':
   assert a==(RECORD,position(c))
   if c.mutation&1:
    put(m,RECORD+0x5c,0xbf800000 if c.seed&1 else 0x7fc00001);put(m,RECORD+0xc8,bits(-2));put(m,position(c)+4,bits(-3));put(m,RECORD+0x40,bits(-4));m[RECORD+1]^=0x80
   answer=0
  elif name=='func_1514672C':
   assert len(a)==1
   if c.mutation&2:
    put(m,RECORD+0x44,bits(4));put(m,RECORD+0xc8,bits(9));put(m,s[GLOBALS[0]],0)
    for i,v in enumerate((17,18,19)):put(m,self.point+4*i,bits(v))
   answer=c.inside
  elif name=='func_15046C00':
   assert a[1]==0 and a[2]==read(m,RECORD+0x44)and a[3]==RECORD+0x80
   put(m,RECORD+0x80,c.floor);m[RECORD+0x9d]=c.state
   if c.mutation&4:
    put(m,RECORD+0x44,bits(-1));put(m,RECORD+0x5c,bits(-1));put(m,RECORD+0xc8,bits(-1));put(m,s[GLOBALS[2]],bits(2));put(m,self.point,bits(23))
   answer=c.hit
  elif name=='func_150ADA68':
   assert not a
   if c.mutation&8:
    m[RECORD+0x9d]=0 if c.state==3 else 3;put(m,RECORD+0xa8,bits(6));put(m,s[GLOBALS[1]],bits(0.75));put(m,s[GLOBALS[2]],bits(0.25))
    if self.point is not None:put(m,self.point+4,bits(99))
   answer=c.random
  elif name=='func_151D8E20':
   assert not a
   if c.mutation&16:
    put(m,RECORD+0xa8,bits(-7));put(m,s[GLOBALS[2]],bits(0.5));m[RECORD+0x2b]=255;m[RECORD+0xc]=128;m[RECORD+1]=254
    if self.point is not None:put(m,self.point+8,bits(11))
   answer=c.selector&255
  else:assert name=='func_151DBCBC'and len(a)==7;answer=0
  if c.mutation&32 and self.point is not None:
   for i in range(3):put(m,self.point+4*i,bits((len(self.calls)+i)*0.5))
  return u32(answer)
def reference(initial,c,s=None):
 s=S if s is None else s;m=initial.copy();service=Providers(m,c,s);service.invoke(PROVIDERS[0],(RECORD,position(c)))
 if floating(read(m,RECORD+0x5c))<0:return m,service,1
 put(m,POINT,bits(floating(read(m,RECORD+0x40))+floating(read(m,RECORD+0x4c))));put(m,POINT+4,read(m,position(c)+4));put(m,POINT+8,bits(floating(read(m,RECORD+0x48))+floating(read(m,RECORD+0x54))));rate=read(m,RECORD+0xc8);result=1
 if floating(rate)==floating(read(m,s[GLOBALS[0]])):
  if service.invoke(PROVIDERS[1],(POINT,))==0:return m,service,0
  if service.invoke(PROVIDERS[2],(POINT,0,read(m,RECORD+0x44),RECORD+0x80))!=0:put(m,POINT+4,read(m,RECORD+0x80));result=0
 elif floating(rate)<=floating(read(m,RECORD+0x44)):put(m,POINT+4,rate);result=0
 if result==0 and floating(service.invoke(PROVIDERS[3],()))<floating(read(m,s[GLOBALS[1]]))and m[RECORD+0x9d]==3:
  selector=service.invoke(PROVIDERS[4],());service.invoke(PROVIDERS[5],(selector&255,bits(floating(read(m,RECORD+0xa8))*floating(read(m,s[GLOBALS[2]]))),m[RECORD+0x2b],RECORD+0x84,POINT,m[RECORD+0xc],m[RECORD+1]))
 return m,service,result
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None,arguments=None):
  self.c=c;self.s=S if s is None else s;super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=(RECORD,position(c))if arguments is None else arguments);self.fp_before=self.f[:];self.entry_sp=self.r[29];self.providers=Providers(self.memory,c,self.s)
 def record_call(self,t):
  n=2 if t==ENTRY else ARITY[next(n for n in PROVIDERS if self.s[n]==t)];a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  name=next(n for n in PROVIDERS if self.s[n]==t);value=self.providers.invoke(name,self.calls[-1][1])
  for i in range(4):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
  if name==PROVIDERS[3]:self.f[0]=value
def streams(s=None):return{label:bound_blob(*payload(o/path,p.FUNCTION),S if s is None else s)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.providers.observed,m.dispatched_word)
def saved(m):return m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:]and m.r[29]==m.entry_sp
def check(m,initial,c,s=None):
 expected,service,result=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert m.providers.calls==service.calls,(c,'calls',m.providers.calls,service.calls);assert m.providers.observed==service.observed,(c,'observed',m.providers.observed,service.observed);assert m.r[2]==result and saved(m),(c,'return or saved')
def main():
 programs=streams();assert len({tuple(v)for k,v in programs.items()if k!='raw'})==1;assert struct.pack('>101I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x187c3c:0x187dd0];count=0;visits=set()
 for c in cases():
  initial=fixture(c);models=[]
  for ws in programs.values():m=Oracle(ws,initial,c);m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,padded_retail_complete_identity=True,independent_public_effects_calls_observations_results_equal=True,padded_retail_all_private_bytes_and_registers_equal=True,raw_private_or_fault_identity_claim=False,unexecuted_original_words=[i for i in range(101)if ENTRY+4*i not in visits],source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 programs=[v for k,v in streams().items()if k!='raw'];count=0
 for c in(Case(),Case(vertical=0xbf800000),Case(inside=0),Case(hit=0),Case(rate=0,random=0x7fc00001),Case(mutation=63,alias=1,phase=8)):
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
 programs=streams();rom=(r/'conker/conker.us.bin').read_bytes();begin=0x15130a0c;end=0x15130a50;offset=begin-0x15000000+0x2d4b0;caller=list(struct.unpack('>17I',rom[offset:offset+68]));(o/'15130a0c-original-caller.bin').write_bytes(rom[offset:offset+68]);count=called=bypassed=zeros=0;table=S['D_80089760']
 for original in(Case(),Case(vertical=0xbf800000),Case(inside=0),Case(hit=0),Case(rate=0),Case(mutation=16),Case(mutation=32),Case(random=0x7fc00001)):
  for index,flag in((21,0),(-1,0),(21,1),(21,255)):
   c=replace(original,position_address=STACK+original.phase+0x48);initial=fixture(c)
   for i in range(-16,128):initial.setdefault(table+i,0xa5)
   put(initial,table+4*21,ENTRY);initial[RECORD+0x72]=index&255;expected,service,result=reference(initial,c)if index==21 and flag==0 else(initial.copy(),Providers(initial.copy(),c),None);want=1 if result==0 else flag;zeros+=int(result==0);called+=int(result is not None);bypassed+=int(result is None);models=[]
   for ws in programs.values():
    code=dict(zip(range(ENTRY,ENTRY+4*len(ws),4),ws));m=Oracle(caller,initial,c,entry=begin,connected=code,arguments=(RECORD,0x12345678,0xfedcba98,flag));m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller boundary missed')
    assert m.r[4]==RECORD and m.r[7]==want,(c,index,flag,'caller result');assert public(m.memory)==public(expected)and m.providers.calls==service.calls and m.providers.observed==service.observed,(c,index,flag,'caller effects');assert read(m.memory,position(c)+4)==read(expected,position(c)+4);models.append(m)
   assert all(state(m)==state(models[1])for m in models[2:]);count+=1
 q=dict(actual_original_dispatch_window=True,words=17,cases_per_stream=count,callback_called=called,callback_bypassed=bypassed,zero_result_sets_flag=zeros,record_and_flag_restored_after_callback=True,bounded_window_only=True,whole_caller_or_transitive_provider_claim=False,additional_caller_matching_credit=0);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();print(json.dumps(faults()),flush=True);print(json.dumps(callers()),flush=True)
