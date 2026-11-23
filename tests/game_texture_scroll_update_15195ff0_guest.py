"""Texture scroll leaf: independent word/phase reference and concrete MIPS."""
from dataclasses import dataclass,replace
from pathlib import Path
import json,random,struct,sys
from tools.experiments import game_texture_scroll_update_15195ff0_match as p
r=p.ROOT;o=p.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};ENTRY=0x15195FF0;NODES=0x50000;LINKS=0x60000;DL0=0x100000;DL1=0x200000;DL2=0x300000
u32=lambda n:n&0xffffffff
s32=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
s16=lambda n:((n&65535)^32768)-32768
s8=lambda n:((n&255)^128)-128
div=lambda n,d:(-1 if n<0 else 1)*(abs(n)//d)
@dataclass(frozen=True)
class Case:
 seed:int=0
 count:int=1
 gate:int=0
 delta:int=1
 width:int=32
 height:int=16
 u:int=10
 v:int=7
 speed_u:int=1
 speed_v:int=-8
 tiles:int=4
 primary:int=1
 secondary:int=1
 links:int=1
 phase:int=0
 mutation:int=0
def cases():
 rng=random.Random(0x15195FF0)
 for seed in range(640):
  yield Case(seed=seed,count=rng.choice((0,1,2,3)),gate=rng.choice((0,0,1,255)),delta=rng.choice((-3,0,1,2,7)),width=rng.choice((-16,0,1,2,16,32,32767)),height=rng.choice((-1,0,1,8,64,32767)),u=rng.choice((0,1,7,8,255,65535)),v=rng.choice((0,2,8,127,1024,65535)),speed_u=rng.choice((-128,-1,0,1,127)),speed_v=rng.choice((-128,-8,0,3,127)),tiles=rng.choice((0,1,2,4,8)),primary=rng.randrange(6),secondary=rng.randrange(6),links=rng.randrange(4),phase=8*(seed&1))
 for n in(0,1,8,9,255):
  for d in(0,1,0x7fffffff,-0x80000000):yield Case(tiles=n,delta=d,primary=2,secondary=2,links=2)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,4096)}
 for base,size in((NODES,3*0x100),(LINKS,9*0x20)):
  m.update({base+i:(i*29+c.seed*11+0x51)&255 for i in range(size)})
 put(m,S['D_800E08E8'],NODES if c.count else 0);put(m,S['D_800BE9E4'],c.delta);m[S['D_800BEAC0']]=c.gate
 count=min(c.tiles,8)
 for node in range(3):
  at=NODES+node*256;put(m,at+4,at+256 if node+1<c.count else 0);put(m,at+0xA,c.width,2);put(m,at+0xC,c.height,2);put(m,at+0xE,c.u,2);put(m,at+0x10,c.v,2);m[at+0x12]=c.speed_u&255;m[at+0x13]=c.speed_v&255;m[at+0x14]=c.tiles;put(m,at+0x18,LINKS+node*0x60 if c.links else 0)
  for slot in range(5):
   index=2+slot*24+node*160
   for offset,active in((0x1C,c.primary),(0x26,c.secondary)):put(m,at+offset+slot*2,index if slot<active else -1,2)
   m[at+0x30+slot]=count if(slot+c.seed)%3 else 0;m[at+0x35+slot]=count if(slot+c.seed)%4 else 0
   for base in(DL0,DL1):
    for byte in range(index*8-8,index*8+8*16+8):m[base+byte]=(byte*13+c.seed*19+0xA3)&255
  for k in range(3):
   link=LINKS+node*0x60+k*0x20;index=3+k*32+node*192;put(m,link+8,DL2);put(m,link+0xC,index,2);m[link+0xE]=count if k!=1 else 0;put(m,link+0x10,link+0x20 if k+1<c.links else 0)
   for byte in range(index*8-8,index*8+8*16+8):m[DL2+byte]=(byte*13+c.seed*19+0xA3)&255
 return m
def reference(initial,c):
 m=initial.copy();record=read(m,S['D_800E08E8']);commands=[]
 while record:
  u=read(m,record+0xE,2);v=read(m,record+0x10,2);width=s16(read(m,record+0xA,2));height=s16(read(m,record+0xC,2));tu=div(u,8)+2;tv=div(v,8)+2
  if tu>=width:tu-=width
  if tv>=height:tv-=height
  commands=[]
  for level in range(min(m[record+0x14],8)):
   commands.append(0xF2000000|((tu&4095)<<12)|(tv&4095));tu=div(tu,2);tv=div(tv,2)
  width*=8;height*=8
  if not m[S['D_800BEAC0']]:
   delta=s32(read(m,S['D_800BE9E4']));u=s32(u+s8(m[record+0x12])*delta);v=s32(v+s8(m[record+0x13])*delta)
  if u<0:u=s32(u+width)
  elif u>=width:u=s32(u-width)
  if v<0:v=s32(v+height)
  elif v>=height:v=s32(v-height)
  put(m,record+0xE,u,2);put(m,record+0x10,v,2)
  for index_offset,count_offset,base in((0x1C,0x30,DL0),(0x26,0x35,DL1)):
   for slot in range(5):
    index=s16(read(m,record+index_offset+slot*2,2))
    if index==-1:break
    for level in range(m[record+count_offset+slot]):put(m,base+index*8+level*16,commands[level])
  link=read(m,record+0x18)
  while link:
   index=read(m,link+0xC,2)
   for level in range(m[link+0xE]):put(m,read(m,link+8)+index*8+level*16,commands[level])
   link=read(m,link+0x10)
  record=read(m,record+4)
 return m
class Oracle(Base):
 def __init__(self,words,initial,c,arguments=None):super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=ENTRY,s={},arguments=(DL0,DL1)if arguments is None else arguments)
 def record_call(self,target):raise AssertionError('Unexpected call in texture scroll leaf: '+hex(target))
def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-128<=a<STACK+c.phase}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls)
def streams():
 from tools.tests.game_texture_scroll_update_15195ff0_normalizer import normalize
 raw=payload(o/'selected-final/candidate.o','func_15195FF0');programs={'raw':bound_blob(*raw,S),'normalized':bound_blob(*normalize(*raw),S),'retail':bound_blob(*payload(o/'original-target.o','func_15195FF0'),S)}
 padded=o/'qualified-owner/generated_1C2C60.c.o'
 if padded.exists():programs['padded']=bound_blob(*payload(padded,'func_15195FF0'),S)
 assert len({tuple(v)for k,v in programs.items()if k!='raw'})==1
 return programs
def main():
 programs=streams();assert struct.pack('>202I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x1C34A0:0x1C37C8];count=0;trace_diffs=0;visits=set()
 for c in cases():
  initial=fixture(c);expected=reference(initial,c);models=[]
  for label,ws in programs.items():
   m=Oracle(ws,initial,c);m.run();assert public(m.memory,c)==public(expected,c),(label,c,'public');assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:];assert not m.calls;models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);assert all(m.memory==models[0].memory for m in models[1:]);trace_diffs+=[v for v in models[0].trace if not STACK+c.phase-128<=v[1]<STACK+c.phase]!=[v for v in models[1].trace if not STACK+c.phase-128<=v[1]<STACK+c.phase];visits.update(models[-1].visits);count+=1
 assert trace_diffs==0
 q=dict(cases_per_stream=count,streams=list(programs),public_memory_equal=True,raw_entire_final_memory_equal=True,normalized_full_state_equal=True,ordered_public_trace_differences=trace_diffs,retail_unexecuted_words=[i for i in range(202)if ENTRY+4*i not in visits],unexecuted_range_proof='Unsigned phase loads are 0..65535, so division-by-eight negative correction is unreachable. Adding two gives 2..8193; subtracting a signed16 dimension once only when value >= dimension leaves 0..40961, so divide-by-two negative correction remains unreachable through eight iterations.',source_installed=p.installed(),matching_credit=0);assert q['retail_unexecuted_words']==[23,24,29,30,56,57,61,62];(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def probes():
 for phase in(0,8):
  for mode in('primary-count','secondary-count','association-count','association-base','scratch-output','saved-output','uninitialized'):
   c=Case(seed=1,phase=phase,u=0,v=0,width=2,height=2,delta=0,primary=0,secondary=0,links=0);initial=fixture(c);a=[DL0,DL1];home=STACK+phase
   if mode=='primary-count':
    put(initial,NODES+0x1C,2,2);put(initial,NODES+0x1E,26,2);initial[NODES+0x30]=0;initial[NODES+0x31]=4;a[0]=NODES+0x30-26*8
   elif mode=='secondary-count':put(initial,NODES+0x26,2,2);initial[NODES+0x35]=4;a[1]=NODES+0x34-2*8
   elif mode.startswith('association'):
    put(initial,NODES+0x18,LINKS);initial[LINKS+0xE]=4;put(initial,LINKS+0x10,0);put(initial,LINKS+8,LINKS+(0xC if mode=='association-count'else 8)-3*8)
    if mode=='association-base':initial.update({0xF2000000+i:0xA7 for i in range(0,256)})
   else:
    put(initial,NODES+0x1C,2,2);initial[NODES+0x30]=4
    if mode=='uninitialized':initial[NODES+0x14]=0
    else:a[0]=home-(36 if mode=='scratch-output'else 124)-2*8
   # Broad real guest backing for intentional private/uninitialized reads.
   yield c,initial,tuple(map(u32,a)),mode
def aliases():
 programs=streams();count=0
 for c,initial,a,mode in probes():
  models=[]
  for k,ws in programs.items():m=Oracle(ws,initial,c,a);run_probe(m,mode);models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]),mode
  assert all(m.memory==models[0].memory for m in models[1:]),mode
  assert [v for v in models[0].trace if not STACK+c.phase-128<=v[1]<STACK+c.phase]==[v for v in models[1].trace if not STACK+c.phase-128<=v[1]<STACK+c.phase],mode
  if mode=='primary-count':assert models[1].memory[NODES+0x31]==0
  if mode=='secondary-count':assert models[1].memory[NODES+0x35]==0
  if mode=='association-count':assert models[1].memory[LINKS+0xE]==0
  if mode=='association-base':assert read(models[1].memory,LINKS+8)==0xF2000000 and read(models[1].memory,0xF2000028)==0xF2000000
  if mode=='saved-output':assert models[1].r[16]==0xF2000000 and models[1].r[29]==STACK+c.phase
  count+=1
 q=dict(guest_only_alias_and_uninitialized_cases=count,raw_final_memory_and_public_access_order_equal=True,normalized_complete_state_equal=True,scope='Guest aliases can overwrite live counts, a reloaded association base, scratch or saved slots. Seeded uninitialized scratch reads are guest evidence only; native valid counts are bounded by generated words.',source_installed=p.installed(),matching_credit=0);(o/'aliases.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def run_probe(m,mode):
 if mode!='saved-output':return m.run()
 # This deliberate guest write corrupts a saved register. Complete the real
 # JR and delay slot to a private sentinel, instead of asking the generic
 # ABI oracle to claim preservation of the register the fixture overwrote.
 end=0xDEAD1000;m.r[31]=m.before[31]=end;m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
 try:m.run()
 except WindowBoundary:return m
 raise AssertionError('Guest saved-slot witness did not return')
def faults():
 programs={k:v for k,v in streams().items()if k!='raw'};count=0
 examples=[(c,fixture(c),(DL0,DL1),'ordinary')for c in(Case(count=0),Case(primary=5,secondary=5,links=3),Case(gate=255,tiles=8),Case(u=65535,v=65535,width=-1,height=0))]+list(probes())
 for c,initial,a,mode in examples:
  m=Oracle(programs['retail'],initial,c,a);run_probe(m,mode)
  for cut in range(m.all_accesses):
   states=[]
   for ws in programs.values():
    n=Oracle(ws,initial,c,a);n.cut=cut
    try:run_probe(n,mode)
    except AccessBoundary:pass
    else:raise AssertionError('Own-access boundary did not fire')
    states.append(state(n))
   assert all(v==states[0]for v in states[1:]),(mode,cut);count+=1
 q=dict(full_state_own_access_prefix_sets=count,streams=list(programs),includes_aliases_private_slots_and_uninitialized_scratch=True,source_installed=p.installed(),matching_credit=0);(o/'faults.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>5I',rom,0x1A1EC0);start=0x15174A10;end=start+20;count=0
 class Caller(Base):
  def record_call(self,target):
   assert target==ENTRY;args=tuple(map(u32,self.arguments(2)));assert args==(DL0,DL1);self.calls.append((target,args));self.events.append(('CALL',target,args))
 for c in list(cases())[::10]:
  initial=fixture(c);put(initial,S['D_800B0E00'],DL0);put(initial,S['D_800B0E00']+4,DL1);models=[]
  for label,ws in streams().items():
   m=Caller(window,initial.copy(),BaseCase(phase=c.phase),entry=start,s={},connected=dict(zip(range(ENTRY,ENTRY+4*len(ws),4),ws)),arguments=(0xABC00001,0xABC00002));m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Original five-word call window did not complete')
   assert public(m.memory,c)==public(reference(initial,c),c);assert m.calls==[(ENTRY,(DL0,DL1))];models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);assert all(m.memory==models[0].memory for m in models[1:]);count+=1
 q=dict(original_caller_window_words=5,caller_window_ROM='0x1A1EC0..0x1A1ED4',original_JAL='0x15174A1C',two_full_word_arguments=True,void_result=True,cases_per_stream=count,source_installed=p.installed(),matching_credit=0,limits='Actual caller load/JAL/delay-slot window and complete child; surrounding opaque providers and full parent are outside scope.');(o/'caller-window.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
