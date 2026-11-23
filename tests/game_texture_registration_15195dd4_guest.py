"""Texture registration reference, exact guest state and original owner relay."""
from dataclasses import dataclass,replace
import json,random,struct
from tools.experiments import game_texture_registration_15195dd4_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x15195DD4;RELAY=0x15195FB0;DISPLAY=0x30000;NODES=0x50000;NEW=0x60000;OWNER=0x70000;TILE_TOKEN=0xABC00010
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
ROLES=('func_15195868','func_15195984','func_15195A84','func_15195D00')
u32=lambda n:n&0xFFFFFFFF
s32=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
s16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 seed:int=0
 null:int=0
 gate:int=0
 asset:int=4
 mode:int=0
 separate:int=0
 double:int=1
 field12:int=0x123480FF
 field13:int=0xAABB8001
 hits:int=1
 failure:int=-1
 head:int=1
 token:int=-2
 tiles:int=2
 delta:int=1
 index:int=2
 mutation:int=0
 phase:int=0
def cases():
 rng=random.Random(0x15195DD4)
 for seed in range(768):
  yield Case(seed=seed,null=int(seed%53==0),gate=rng.choice((0,0,0,1,255)),asset=rng.choice((0,4,-1,-2,9,32768,0x12348001)),mode=rng.choice((-1,-1,0,1,3,-2)),separate=rng.choice((0,1,0x80000000)),double=rng.choice((0,1,-1)),hits=rng.randrange(4),failure=rng.choice((-1,-1,-1,0,1)),head=rng.randrange(5),token=rng.choice((-2,4,9,0x12348001)),tiles=rng.choice((-1,0,1,2,255,256,511)),delta=rng.choice((-1,0,1,17)),index=rng.choice((0,2,5,32768)),mutation=rng.randrange(4),phase=8*(seed&1))
 # Deterministic live repeated, existing-node, failed-allocation and early-miss controls.
 for seed in range(48):
  yield Case(seed=800+seed,mode=-1 if seed&1 else 0,asset=(0,4,-1,9)[seed%4],head=seed%5,hits=seed%4,failure=-1,separate=int(seed%3==0),mutation=seed%4,tiles=(0,255,256)[seed%3],phase=8*(seed&1))
def args(c,relay=False):return tuple(map(u32,((OWNER if relay else 0 if c.null else DISPLAY),c.asset,c.double,c.mode,c.separate,c.field12,c.field13)))
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2304)}
 for base,n in((NODES-32,0x340),(NEW-32,0x440),(OWNER,0x40)):
  m.update({base+i:(i*29+c.seed*11+0x51)&255 for i in range(n)})
 for k in range(4):
  at=DISPLAY+(c.index+k)*8;put(m,at,0xF2000000+k*0x101+c.seed);put(m,at+4,0x12345678+k*0x102+c.seed)
 for k,key in enumerate((-1,4,9)):
  at=NODES+k*0x100;put(m,at+4,NODES+(k+1)*0x100 if k<2 else 0);put(m,at+8,key,2);m[at+0x14]=(c.seed*7+k*31)&255
 head=(0,NODES,NODES+0x100,NODES+0x200,NODES)[c.head]
 if c.head==4:put(m,NODES+8,123,2);put(m,NODES+0x108,-7,2)
 put(m,s['D_800E08E8'],head);put(m,s['D_800E08F0'],c.token);m[s['D_800BEAC0']]=c.gate;put(m,OWNER+0x1C,0 if c.null else DISPLAY)
 return m
def service(m,c,name,a,step,s):
 if name==ROLES[0]:
  put(m,a[3],c.tiles+step*c.delta)
  if c.mutation&1:put(m,s['D_800E08F0'],c.token+step+1)
  if c.mutation&2:
   for k in range(3):m[NODES+k*0x100+0x14]=(c.seed+step*61+k)&255
  return u32(c.index+step)if step<c.hits else 0xFFFFFFFF
 if name==ROLES[1]:
  if step==c.failure:return 0
  at=NEW+step*0x100;put(m,at+8,a[0],2);m[at+0x14]=1;return at
 if name==ROLES[2]:return u32(s16(a[0]))
 assert name==ROLES[3]
 # A visible provider-side change distinguishes the final global reload.
 if c.mutation&1:put(m,s['D_800E08F0'],read(m,s['D_800E08F0'])+7)
 m[a[0]+0x15]=(step+0x5A)&255
 return 0x89ABCDEF
def reference(initial,c,s=None,home=None):
 s=S if s is None else s;home=STACK+c.phase if home is None else home;m=initial.copy();calls=[];tile=home-96+0x50;record=read(m,home-96+0x44)
 if c.null or c.gate:return m,calls,0,False
 asset=c.asset;search=0 if c.mode==-1 else c.mode;separate=c.separate;step=0;defined=False
 def call(name,a):
  a=tuple(map(u32,a));calls.append((s[name],tuple(TILE_TOKEN if name==ROLES[0]and i==3 else v for i,v in enumerate(a))));return service(m,c,name,a,step,s)
 while True:
  index=s32(call(ROLES[0],(DISPLAY,asset,search,tile)))
  if index==-1:break
  if asset==0:asset=s32(read(m,s['D_800E08F0']))
  key=-1 if separate else asset;record=read(m,s['D_800E08E8'])
  while record and s16(read(m,record+8,2))!=key:record=read(m,record+4)
  command=DISPLAY+index*8;size=read(m,command+4);scale=read(m,command)
  if not record:
   record=call(ROLES[1],(asset,size,scale,c.double));defined=True
   if not record:return m,calls,0,True
   m[record+0x12]=c.field12&255;m[record+0x13]=c.field13&255;separate=0
  else:index=s32(call(ROLES[2],(s16(index),record,size,c.double)));defined=True;separate=0
  count=s32(read(m,tile))
  if m[record+0x14]<count:m[record+0x14]=count&255
  call(ROLES[3],(record,DISPLAY,index,count));step+=1
  if c.mode!=-1:break
  search=s32(search+1)
 if asset==s32(read(m,s['D_800E08F0'])):put(m,s['D_800E08F0'],read(m,s['D_800E08F0'])-1)
 return m,calls,u32(record),defined
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None,relay=False):
  self.c=c;self.s=S if s is None else s;self.step=0
  super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=args(c,relay))
 def record_call(self,target):
  by={self.s[n]:n for n in ROLES}
  assert target in by or target==ENTRY,hex(target)
  n=7 if target==ENTRY else 4;a=tuple(map(u32,self.arguments(n)))
  self.calls.append((target,tuple(TILE_TOKEN if target==self.s[ROLES[0]]and i==3 else v for i,v in enumerate(a))));self.events.append(('CALL',target,a))
 def hook(self,target):
  name=next(n for n in ROLES if self.s[n]==target);a=tuple(map(u32,self.arguments(4)));step=self.step
  if name==ROLES[0]:self.step+=1;step=self.step-1
  else:step-=1
  value=service(self.memory,self.c,name,a,step,self.s)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def streams():return{label:bound_blob(*payload(o/path,'func_15195DD4'),S)for label,path in dict(raw='selected-final/candidate.o',padded='qualified-owner/generated_1C2C60.c.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls)
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def check(m,initial,c,s=None,home=None,relay=False):
 expected,calls,value,defined=reference(initial,c,s,home);prefix=[(ENTRY,args(c))]if relay else[]
 assert public(m.memory)==public(expected),(c,'public');assert m.calls==prefix+calls,(c,m.calls,calls);assert m.r[2]==value,(c,'return',hex(m.r[2]),hex(value));assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:],(c,'saved');return defined
def main():
 programs=streams();assert len({tuple(ws)for ws in programs.values()})==1;visits=set();count=uninit=0
 for c in cases():
  initial=fixture(c);models=[]
  for ws in programs.values():m=Oracle(ws,initial,c);m.run();models.append(m);check(m,initial,c)
  assert state(models[0])==state(models[1])==state(models[2]);visits.update(models[0].visits);count+=1;uninit+=not(c.null or c.gate)and c.hits==0
 q=dict(cases_per_stream=count,streams=list(programs),complete_state_and_access_trace_equal=True,independent_public_semantics_and_return_equal=True,guest_only_uninitialized_first_miss_returns=uninit,unexecuted_target_words=[i for i in range(119)if ENTRY+4*i not in visits],source_installed=p.installed(),matching_credit=0,limits='Helpers are bounded ABI providers. First-miss stack reads are guest behavior, not portable C semantics.');assert not q['unexecuted_target_words'];(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def faults():
 count=0
 for c in(Case(),Case(asset=0,mode=-1,hits=3,mutation=3),Case(head=0,hits=0),Case(head=0,failure=0),Case(asset=-1,separate=1)):
  initial=fixture(c);complete=Oracle(streams()['retail'],initial,c);complete.run()
  for cut in range(complete.all_accesses):
   states=[]
   for ws in streams().values():
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Own access boundary did not fire')
    states.append(state(m))
   assert states[0]==states[1]==states[2];count+=1
 q=dict(full_state_access_prefix_triples=count,includes_first_miss_seeded_stack_read=True,source_installed=p.installed(),matching_credit=0);(o/'faults.json').write_text(json.dumps(q,indent=2)+'\n');return q
def callers():
 relay=bound_blob(*payload(o/'original-relay.o','func_15195FB0'),S);assert len(relay)==16;count=0
 for c in list(cases())[::8]:
  initial=fixture(c);models=[]
  for ws in streams().values():
   m=Oracle(relay,initial,c,entry=RELAY,connected=dict(zip(range(ENTRY,ENTRY+476,4),ws)),relay=True);m.run();check(m,initial,c,home=STACK+c.phase-40,relay=True);models.append(m)
  assert state(models[0])==state(models[1])==state(models[2]);count+=1
 q=dict(original_owner_relay_words=16,seven_full_word_arguments_and_full_return=True,cases_per_stream=count,source_installed=p.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');return q
if __name__=='__main__':main();print(json.dumps(faults()));print(json.dumps(callers()))
