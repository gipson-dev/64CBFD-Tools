"""Scene-list traversal, live opaque providers and bounded original call windows."""
from dataclasses import dataclass,replace
import json,struct
from tools.experiments import game_scene_node_render_15030e08_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x15030e08;NODES=0x30000;ACTORS=0x90000;CURSOR=0x60020;MARK=0x70000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};u32=lambda v:v&0xffffffff
signed=lambda v:((v&0xffffffff)^0x80000000)-0x80000000
node=lambda i:NODES+i*0x240
def actor(c,i):return ACTORS+(0 if c.alias==1 else i)*0x240 if c.alias!=2 else node(i)
@dataclass(frozen=True)
class Case:
 seed:int=0
 length:int=3
 view:int=0
 mode:int=0
 status:int=255
 mutation:int=0
 gate:int=0
 alias:int=0
 phase:int=0
def cases():
 views=(0,1,7,8,15,16,31,32,33,-1,-32,0x7fffffff,0x80000000)
 for mode in(0,1,2,3,-1,0x80000000):
  for view in views:
   for gate in range(11):yield Case(view=view,mode=mode,gate=gate,seed=gate&3)
 for status in(-0x80000000,-1,0,1,254,255,256,0x7fffffff):
  for mode in(0,1,2,3):
   for mutation in(1,2,4,8,16,32,63):
    for alias in(0,1,2):yield Case(view=33,mode=mode,status=status,mutation=mutation,alias=alias,seed=mutation%4,phase=8*(status&1))
 for length in range(5):
  for view in views:
   for mode in(0,1,2):yield Case(length=length,view=view,mode=mode)
def banks(s=None):
 s=S if s is None else s;return((NODES,4*0x240),(ACTORS,4*0x240),(CURSOR-32,512),(MARK,32),(s['D_800C3EE0'],4))
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,256)}
 for base,n in banks(s):m.update({base+i:(i*29+c.seed*11+0x51)&255 for i in range(-16,n+16)})
 put(m,s['D_800C3EE0'],node(0)if c.length else 0)
 for i in range(4):
  a=actor(c,i);put(m,a+0x1d4,1);m[a+0x74]=0;m[a+5]=7
 for i in range(4):
  n=node(i);m[n]=i+1;m[n+3]=1;m[n+4]=0;put(m,n+0x54,node(i+1)if i+1<c.length else 0)
 if c.gate==1:m[node(0)+3]=0
 if c.gate==3:put(m,actor(c,0)+0x1d4,0)
 if c.gate==4:m[actor(c,0)+0x74]=(1<<(c.view&31))&255
 if c.gate==5:m[node(0)+4]=2
 if c.gate==7:m[actor(c,0)+5]=1
 if c.gate==8:m[actor(c,0)+5]=6
 if c.gate==9:m[node(0)+4]=4
 if c.gate==10:m[actor(c,0)+0x74]=1
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+256}
def observation(m,s):return(read(m,s['D_800C3EE0']),tuple((m[node(i)+3],m[node(i)+4],read(m,node(i)+0x54))for i in range(4)),tuple((read(m,ACTORS+i*0x240+0x1d4),m[ACTORS+i*0x240+0x74],m[ACTORS+i*0x240+5])for i in range(4)),read(m,MARK))
class Providers:
 def __init__(self,m,c,s=None):self.m=m;self.c=c;self.s=S if s is None else s;self.calls=[];self.observed=[];self.current=None
 def invoke(self,name,a):
  m,c,s=self.m,self.c,self.s;a=tuple(map(u32,a));self.calls.append((s[name],a));self.observed.append(observation(m,s));put(m,MARK,len(self.calls))
  if name=='func_15083E90':
   i=a[0]-1;assert 0<=i<4;self.current=i;n=node(i);value=0 if c.gate==2 and i==0 else actor(c,i)
   if c.mutation&1:put(m,s['D_800C3EE0'],0);put(m,n+0x54,0)
   if c.mutation&2:put(m,actor(c,i)+0x1d4,(i+1)&1);m[actor(c,i)+0x74]=1<<(c.view&7);m[actor(c,i)+5]=(1,7,6,255)[i]
  elif name=='func_1506196C':
   i=self.current;n=node(i);assert a==(actor(c,i),u32(c.view));value=254 if c.gate==6 else c.status
   if c.mutation&4:m[n+4]^=2;m[actor(c,i)+5]=1
   if c.mutation&16:
    put(m,n+0x54,0)
    if i+1<4:m[node(i+1)+3]=1;put(m,actor(c,i+1)+0x1d4,1);m[actor(c,i+1)+5]=7
  else:
   assert name=='func_150311C4';i=self.current;n=node(i);assert a[1:]==(n,actor(c,i),u32(c.view),0);value=0 if c.mutation&32 else u32(a[0]+8*(1+(len(self.calls)+c.seed)%3))
   if c.mutation&8:
    put(m,s['D_800C3EE0'],node(3));put(m,n+0x54,0)
    if i+1<4:m[node(i+1)+3]=0
  return u32(value)
def reference(initial,c,s=None,cursor=CURSOR):
 s=S if s is None else s;m=initial.copy();service=Providers(m,c,s);n=read(m,s['D_800C3EE0']);visited=0
 while n:
  visited+=1;assert visited<=4;following=read(m,n+0x54)
  if m[n+3]:
   a=service.invoke('func_15083E90',(m[n],))
   mask=1<<(c.view&31)
   if a and read(m,a+0x1d4)and(m[a+0x74]&mask)!=mask:
    if c.mode==2:draw=m[a+5]==7
    else:
     status=signed(service.invoke('func_1506196C',(a,c.view)))
     draw=(bool(m[n+4]&2)or status!=255 or m[a+5]==1)if c.mode==1 else not(m[n+4]&2)and status>=255 and m[a+5]!=1
    if draw:cursor=service.invoke('func_150311C4',(cursor,n,a,c.view,0))
  n=following
 return m,service,u32(cursor)
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None,arguments=None):
  self.c=c;self.s=S if s is None else s;super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=(CURSOR,c.view,c.mode)if arguments is None else arguments);self.fp_before=self.f[:];self.entry_sp=self.r[29];self.providers=Providers(self.memory,c,self.s)
 def record_call(self,t):
  counts={self.s['func_15083E90']:1,self.s['func_1506196C']:2,self.s['func_150311C4']:5,ENTRY:3};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  name=next(n for n in('func_15083E90','func_1506196C','func_150311C4')if self.s[n]==t);a=self.calls[-1][1];result=self.providers.invoke(name,a)
  for i in range(max(4,len(a))):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=result
def streams(s=None):return{label:bound_blob(*payload(o/path,p.FUNCTION),S if s is None else s)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.providers.observed,m.dispatched_word)
def saved(m):return m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:]and m.r[29]==m.entry_sp
def check(m,initial,c,s=None):
 expected,service,cursor=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert m.providers.calls==service.calls,(c,'calls',m.providers.calls,service.calls);assert m.providers.observed==service.observed,(c,'observed');assert m.r[2]==cursor,(c,'cursor');assert saved(m),(c,'saved')
def main():
 programs=streams();assert len({tuple(v)for k,v in programs.items()if k!='raw'})==1;assert struct.pack('>99I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x5e2b8:0x5e444];count=0;visits=set()
 for c in cases():
  initial=fixture(c);models=[]
  for ws in programs.values():m=Oracle(ws,initial,c);m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,padded_retail_complete_identity=True,independent_public_effects_arguments_observations_cursor_equal=True,padded_retail_all_private_bytes_and_registers_equal=True,raw_private_or_fault_identity_claim=False,unexecuted_original_words=[i for i in range(99)if ENTRY+4*i not in visits],source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 programs=[v for k,v in streams().items()if k!='raw'];count=0
 for c in(Case(length=0),Case(),Case(mode=1,mutation=63,view=31),Case(mode=2,alias=2),Case(mode=3,status=-1,mutation=17,phase=8)):
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
 begin,end=0x1502bcd4,0x1502bd48;rom=(r/'conker/conker.us.bin').read_bytes();caller=list(struct.unpack('>29I',rom[0x59184:0x591f8]));programs=streams();count=called=bypassed=0;global_address=S['D_8003C8E0']
 (o/'original-caller-window.bin').write_bytes(rom[0x59184:0x591f8])
 for c0 in(Case(),Case(mode=1,mutation=1),Case(mode=2,mutation=8),Case(view=31,mutation=17),Case(length=0),Case(status=-1,mutation=4,alias=1),Case(view=-1,mutation=16,phase=8)):
  for outer in(0,1,2,3,6,-1):
   mode={1:0,2:1,6:2}.get(outer);c=replace(c0,mode=mode if mode is not None else 0);initial=fixture(c)
   for i in range(-16,20):initial[global_address+i]=0xa5
   if mode is None:expected=initial.copy();service=Providers(expected,c);cursor=CURSOR;bypassed+=1
   else:expected,service,cursor=reference(initial,c);called+=1
   put(expected,global_address,0x1ffffff);put(expected,cursor,0xde000000);put(expected,cursor+4,0x80084190);models=[]
   for ws in programs.values():
    code=dict(zip(range(ENTRY,ENTRY+4*len(ws),4),ws));code[end]=0;m=Oracle(caller,initial,c,entry=begin,connected=code);m.r[1]=0x80040000;m.r[14]=0x1ffffff;m.r[18]=CURSOR;m.r[19]=u32(outer);m.r[20]=2;m.r[21]=u32(c.view);m.r[23]=1;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Actual caller boundary did not fire')
    assert public(m.memory)==public(expected)and m.providers.calls==service.calls and m.providers.observed==service.observed,(c,outer,'caller effects');assert m.r[18]==u32(cursor+8),(c,outer,'returned cursor consumed');assert all(m.r[i]==m.before[i]for i in(16,17,19,20,21,22,23,28,29,30))and m.f[20:]==m.fp_before[20:];assert [a for t,a in m.calls if t==ENTRY]==([]if mode is None else[(CURSOR,u32(c.view),mode)]);models.append(m)
   assert all(state(m)==state(models[1])for m in models[2:]);count+=1
 q=dict(actual_complete_caller_window_words=29,cases_per_stream=count,called_cases=called,bypassed_cases=bypassed,all_three_mode_call_sites_executed=True,all_four_streams_arguments_public_state_and_boundary_equal=True,post_call_cursor_used_for_two_display_list_stores=True,whole_1502BAD0_execution_claim=False,additional_caller_matching_credit=0);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();print(json.dumps(faults()),flush=True)
