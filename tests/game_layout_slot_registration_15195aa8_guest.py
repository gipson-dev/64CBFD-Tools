"""Independent layout-slot reference and bounded helper ABI providers."""
from dataclasses import dataclass
from pathlib import Path
import json,random,struct,sys
from tools.experiments import game_layout_slot_registration_15195aa8_match as p
r=p.ROOT;o=p.OUT
from tools.tests import game_texture_registration_15195dd4_guest as common
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};ENTRY=0x15195AA8;DISPLAY=0x30000;NODES=0x50000;NEW=0x60000;STACK=common.STACK;TILE_TOKEN=common.TILE_TOKEN;ROLES=common.ROLES[:3];put=common.put;read=common.read;u32=common.u32;s32=common.s32;s16=common.s16
assert all(S[n]==common.S[n]for n in('D_800E08E8','D_800E08F0','D_800BEAC0'))
@dataclass(frozen=True)
class Case:
 seed:int=0
 null:int=0
 gate:int=0
 asset:int=4
 mode:int=0
 state:int=0x12348001
 secondary:int=0
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
 fullness:int=0
 phase:int=0
def cases():
 rng=random.Random(0x15195AA8)
 for seed in range(768):
  yield Case(seed=seed,null=int(seed%53==0),gate=255*(seed&1),asset=rng.choice((0,4,-1,-2,32768,0x12348001)),mode=rng.choice((-1,-1,0,1,3,-2)),state=rng.choice((0,1,-1,5,0x12348001)),secondary=rng.choice((0,1,0x80000000)),double=rng.choice((0,1,-1)),hits=rng.randrange(4),failure=rng.choice((-1,-1,0,1)),head=rng.randrange(5),token=rng.choice((-2,4,9,0x12348001)),tiles=rng.choice((-1,0,1,2,255,256,511)),delta=rng.choice((-1,0,1,17)),index=rng.choice((0,2,5,32768)),mutation=rng.randrange(4),fullness=rng.randrange(6),phase=8*(seed&1))
 for secondary in(0,1):
  for full in range(6):
   for head in(0,1,2):yield Case(secondary=secondary,fullness=full,head=head,mode=-1,hits=3)
def args(c):return tuple(map(u32,(0 if c.null else DISPLAY,c.asset,c.double,c.mode,c.state,c.secondary,c.field12,c.field13)))
def fixture(c):
 m=common.fixture(c);home=STACK+c.phase
 # Constructor-produced records have the same empty five-slot backing.
 for base in[NODES+i*256 for i in range(3)]+[NEW+i*256 for i in range(4)]:
  for i in range(5):
   for offset in(0x1C,0x26):put(m,base+offset+2*i,7+i if i<c.fullness else -1,2)
 for i,key in enumerate((7,0,9)):put(m,NODES+i*256+8,key,2)
 if c.head==4:
  for i in range(3):put(m,NODES+i*256+8,7+i,2)
 for i,v in enumerate(args(c)[4:]):put(m,home+0x10+4*i,v)
 return m
def service(m,c,name,a,step):
 if name==ROLES[0]:
  put(m,a[3],c.tiles+step*c.delta)
  if c.mutation&1:put(m,S['D_800E08F0'],c.token+step+1)
  if c.mutation&2:
   for k in range(3):m[NODES+k*256+0x14]=(c.seed+step*61+k)&255
  return u32(c.index+step)if step<c.hits else 0xFFFFFFFF
 if name==ROLES[1]:
  if step==c.failure:return 0
  at=NEW+step*256;put(m,at+8,a[0],2);m[at+0x14]=1;return at
 assert name==ROLES[2]
 if c.mutation&1:put(m,S['D_800E08F0'],read(m,S['D_800E08F0'])+7)
 return u32(s16(a[0]))
def reference(initial,c):
 m=initial.copy();home=STACK+c.phase;tile=home-96+0x50;calls=[];asset=c.asset;search=0 if c.mode==-1 else c.mode;record=0;state=c.state;step=0;writeback=False
 put(m,home+8,c.double)
 if c.null:return m,calls,0,False
 def call(name,a):
  a=tuple(map(u32,a));calls.append((S[name],tuple(TILE_TOKEN if name==ROLES[0]and i==3 else v for i,v in enumerate(a))));return service(m,c,name,a,step)
 while True:
  index=s32(call(ROLES[0],(DISPLAY,asset,search,tile)))
  if index==-1:break
  if asset==0:asset=s32(read(m,S['D_800E08F0']))
  record=read(m,S['D_800E08E8']);command=DISPLAY+index*8;size=read(m,command+4);scale=read(m,command)
  while record and s16(read(m,record+8,2))!=0:record=read(m,record+4)
  if not record:
   record=call(ROLES[1],(asset,size,scale,c.double))
   if not record:return m,calls,0,False
   m[record+0x12]=c.field12&255;m[record+0x13]=c.field13&255;state=0
  else:index=s32(call(ROLES[2],(s16(index),record,size,c.double)));state=0
  count=s32(read(m,tile))
  if m[record+0x14]<count:m[record+0x14]=count&255
  search=s32(search+1);offset=0x26 if c.secondary else 0x1C;slots=0
  while slots<5 and s16(read(m,record+offset+2*slots,2))!=-1:slots+=1
  if slots<5:put(m,record+offset+slots*2,index,2);m[record+(0x35 if c.secondary else 0x30)+slots]=count&255
  step+=1
  if c.mode!=-1:break
 # The original preserves the incoming value on first miss, and writes zero
 # after any successful binding. Early null/constructor failures bypass it.
 put(m,home+0x10,state);writeback=True
 if asset==s32(read(m,S['D_800E08F0'])):put(m,S['D_800E08F0'],read(m,S['D_800E08F0'])-1)
 return m,calls,u32(record),writeback
class Oracle(common.Base):
 def __init__(self,words,initial,c):
  self.c=c;self.step=0;super().__init__(words,initial.copy(),common.BaseCase(phase=c.phase),entry=ENTRY,s={},arguments=args(c))
 def record_call(self,target):
  assert target==ENTRY or target in[S[n]for n in ROLES];a=tuple(map(u32,self.arguments(8 if target==ENTRY else 4)));self.calls.append((target,tuple(TILE_TOKEN if target==S[ROLES[0]]and i==3 else v for i,v in enumerate(a))));self.events.append(('CALL',target,a))
 def hook(self,target):
  name=next(n for n in ROLES if S[n]==target);a=tuple(map(u32,self.arguments(4)));step=self.step
  if name==ROLES[0]:self.step+=1
  else:step-=1
  value=service(self.memory,self.c,name,a,step)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def public(m,c):
 home=STACK+c.phase
 return{a:b for a,b in m.items()if not home-96<=a<home and not home+0x10<=a<home+0x14}
def streams():return{label:bound_blob(*payload(o/path,'func_15195AA8'),S)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.dispatched_word,m.visits)
def main():
 programs=streams();rom=(r/'conker/conker.us.bin').read_bytes();assert struct.pack('>150I',*programs['retail'])==rom[0x1C2F58:0x1C31B0];count=0;home_writes=0;visits=set()
 for c in cases():
  initial=fixture(c);expected,calls,value,writeback=reference(initial,c);models=[]
  for label,ws in programs.items():
   m=Oracle(ws,initial,c);m.run();assert public(m.memory,c)==public(expected,c),(label,c,'public');assert m.calls==calls,(label,c,m.calls,calls);assert m.r[2]==value,(label,c,'return');assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:];models.append(m)
   if label!='raw':assert read(m.memory,STACK+c.phase+0x10)==read(expected,STACK+c.phase+0x10)
  assert state(models[1])==state(models[2])==state(models[3]);home=STACK+c.phase;traces=[[v for v in m.trace if not home-96<=v[1]<home and not home+0x10<=v[1]<home+0x14]for m in models];assert all(t==traces[0]for t in traces[1:]),c;visits.update(models[-1].visits);count+=1;home_writes+=writeback
 assert[i for i in range(150)if ENTRY+4*i not in visits]==[108]
 q=dict(cases_per_stream=count,streams=4,public_memory_result_calls_and_access_order_equal=True,normalized_entire_register_private_memory_and_trace_equal=True,ABI_argument4_writeback_cases=home_writes,retail_unexecuted_words=[108],scope='Raw/public comparison excludes only frame96 and argument4 ABI home. Normalized private/home/GPR/FPR/full trace is compared literally with retail.',source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
def faults():
 from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
 programs=[ws for k,ws in streams().items()if k!='raw'];count=0
 for c in(Case(),Case(null=1),Case(hits=0),Case(head=0,failure=0),Case(head=0,mode=-1,hits=3),Case(mode=-1,hits=3,fullness=5),Case(secondary=1,mode=-1,hits=3,fullness=3),Case(mutation=3,state=-1)):
  initial=fixture(c);complete=Oracle(programs[-1],initial,c);complete.run()
  for cut in range(complete.all_accesses):
   states=[]
   for ws in programs:
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Actual access boundary did not fire')
    states.append(state(m))
   assert states[0]==states[1]==states[2];count+=1
 q=dict(full_state_and_dispatched_word_access_prefix_triples=count,source_installed=p.installed(),matching_credit=0);(o/'faults.json').write_text(json.dumps(q,indent=2)+'\n');return q
def callers():
 from dataclasses import replace
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 meta=p.MANIFEST['caller_window'];start,end=meta['entry'],meta['end'];rom=(r/'conker/conker.us.bin').read_bytes();data=rom[start-0x15000000+0x2D4B0:end-0x15000000+0x2D4B0];elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,start,meta['caller_size']);assert elf[at:at+meta['caller_size']]==rom[start-0x15000000+0x2D4B0:start-0x15000000+0x2D4B0+meta['caller_size']];assert len(data)==56;words=struct.unpack('>14I',data);count=0
 for c in list(cases())[::8]:
  c=replace(c,double=1,mode=-1,state=0,secondary=0,field12=0,field13=-8);initial=fixture(c);put(initial,S['D_800B0E00'],0 if c.null else DISPLAY);put(initial,S['D_800902B8'],c.asset);expected,calls,value,_=reference(initial,c);models=[]
  for label,ws in streams().items():
   m=Oracle(ws,initial,c);m.code=dict(zip(range(start,end,4),words))|dict(zip(range(ENTRY,ENTRY+len(ws)*4,4),ws));m.code[end]=0;m.entry=start;m.r[29]=STACK+c.phase+64;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller did not reach declared boundary')
   wanted=expected.copy();put(wanted,STACK+c.phase+0x24,m.before[31]);assert public(m.memory,c)==public(wanted,c),(label,c,'caller public');assert m.calls==[(ENTRY,args(c))]+calls,(label,c,'caller ABI');assert m.r[2]==value and m.r[29]==STACK+c.phase;models.append(m)
  assert state(models[1])==state(models[2])==state(models[3]);count+=1
 q=dict(actual_caller_prefix_words=14,entry=f'{start:08X}',end=f'{end:08X}',cases_per_stream=count,eight_full_word_arguments=True,linked_entire_748_byte_caller_equals_ROM=True,source_installed=p.installed(),matching_credit=0,limits='Executes the authentic prefix and first connected call, not the complete 748-byte parent.');(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');return q
