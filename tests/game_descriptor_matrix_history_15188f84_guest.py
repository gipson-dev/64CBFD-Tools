"""Descriptor history, pointer cells, overlapping copies and live node fields."""
from dataclasses import dataclass
import json,struct
from tools.experiments import game_descriptor_matrix_history_15188f84_match as p
from tools.tests.game_owner_cache_update_15188e48_oracle import Oracle as CopyBase
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x15188F84;NODE=0x30000;IDS=0x50000;DESCRIPTORS=0x90000;MATRICES=0x4000000;OTHER_MATRICES=0x5000000;BUFFERS=(0x1000000,0x2000000)
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};S.update(_id_cells=0x800dbed0,_matrix_cells=0x800dbee0,_registry=0x8008d580)
u32=lambda v:v&0xffffffff
@dataclass(frozen=True)
class Case:
 count:int=2
 match:int=0
 snapshots:int=3
 page:int=0
 filled:int=0
 identity:int=1
 mutation:int=0
 alias:int=0
 residue:int=0
 phase:int=0
 seed:int=0

def cases():
 for count in(0,1,2,4,8,65535):
  matches=(-1,)if count==0 else(0,)if count==65535 else(-1,0,count-1)
  for match in matches:
   for snapshots in(0,1,2,4):
    for page in(0,1):yield Case(count,match,snapshots,page)
 for snapshots in(3,4,255):
  for filled in(0,snapshots,254,255):
   for page in(0,1):
    for mutation in(0,1,2,4,8,16,32,63):yield Case(snapshots=snapshots,page=page,filled=filled,mutation=mutation,seed=mutation&3,phase=8*(page&1))
 for alias in(1,2,3,4):
  for page in(0,1):
   for residue in(0,1,2,3):
    for snapshots in(1,3):yield Case(snapshots=snapshots,page=page,identity=0,alias=alias,residue=residue,seed=alias)
 for identity in(0,1,255,65535):
  for snapshots in(0,1,4):yield Case(count=1,snapshots=snapshots,identity=identity,seed=identity&3)
 for residue in(1,2,3):
  for snapshots in(1,3):
   for page in(0,1):yield Case(residue=residue,snapshots=snapshots,page=page)

def current(c):
 if not c.alias:return MATRICES+c.identity*64
 at=BUFFERS[0]+c.residue+(0 if c.alias==2 else(c.snapshots-1+c.page*c.snapshots)*64)
 return at+(8 if c.alias==3 else-8 if c.alias==4 else 0)
def banks(c,s=None):
 s=S if s is None else s;regions=[(NODE-16,96),(IDS-16,4*min(c.count,16)+32),(s['_id_cells']-16,80),(s['D_80089240']-16,64),(s['D_80089250']-16,64),(s['D_800BE9C0']-16,33),(s['_registry']+4,4),(current(c)-16,96),(OTHER_MATRICES+c.identity*64-16,96)]
 for b in BUFFERS:
  for page in{c.page,c.page^1}:regions.append((b+c.residue+page*c.snapshots*64-16,(c.snapshots+1)*64+32))
 return regions
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,512)}
 for b,n in banks(c,s):
  for i in range(n):m[b+i]=((b+i)*13+c.seed*7+89)&255
 for i in range(4):put(m,s['D_80089240']+4*i,s['_id_cells']+4*i);put(m,s['_id_cells']+4*i,IDS)
 for i in range(2):put(m,s['D_80089250']+4*i,s['_matrix_cells']+4*i);put(m,s['_matrix_cells']+4*i,u32(current(c)-c.identity*64))
 put(m,s['D_800DBEE8'],c.count,2);put(m,s['D_800DBEF4'],DESCRIPTORS);m[s['D_800BE9C0']]=c.page
 for i in range(min(c.count,16)):put(m,IDS+4*i,c.identity if i==c.match else 16+i,2)
 m[NODE]=1;m[NODE+1]=c.snapshots;m[NODE+2]=c.filled;m[NODE+3]=61;put(m,NODE+6,10,2);put(m,NODE+8,BUFFERS[0]+c.residue);put(m,NODE+12,0);put(m,NODE+16,DESCRIPTORS+(c.identity if c.match>=0 else 999)*160)
 put(m,s['_registry']+4,ENTRY)
 return m
def data(m,at,n):return bytes(m[u32(at+i)]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
def observe(m,s):return(m[s['D_800BE9C0']],m[NODE+1],m[NODE+2],read(m,NODE+8),read(m,NODE+16),read(m,s['D_800DBEE8'],2),read(m,s['_matrix_cells']),read(m,IDS,2))
def effect(m,c,s,ordinal):
 if ordinal!=1:return
 if c.mutation&1:m[s['D_800BE9C0']]^=1;m[NODE+1]=(c.snapshots+1)&255;m[NODE+2]=c.snapshots
 if c.mutation&2:put(m,NODE+8,BUFFERS[1]+c.residue)
 if c.mutation&4:put(m,s['_matrix_cells']+4*c.page,OTHER_MATRICES);put(m,NODE+16,DESCRIPTORS+777*160)
 if c.mutation&8:m[NODE+2]=255
 if c.mutation&16:put(m,s['D_800DBEE8'],0,2);put(m,s['D_800DBEF4'],DESCRIPTORS+160);put(m,IDS,65535,2)
 if c.mutation&32:
  at=read(m,NODE+8)+((c.page^1)*c.snapshots+2)*64
  for i in range(8):m[u32(at+i)]^=0x5a
class Providers:
 def __init__(self,m,c,s=None):self.m=m;self.c=c;self.s=S if s is None else s;self.calls=[];self.observed=[];self.copies=[]
 def copy(self,a):
  a=tuple(map(u32,a));self.calls.append((self.s['bcopy'],a));self.observed.append(observe(self.m,self.s));packet=data(self.m,a[0],a[2]);self.copies.append(packet)
  for i,b in enumerate(packet):self.m[u32(a[1]+i)]=b
  effect(self.m,self.c,self.s,len(self.calls))
def reference(initial,c,s=None):
 s=S if s is None else s;m=initial.copy();q=Providers(m,c,s);depth=m[NODE+1];page=m[s['D_800BE9C0']];first=page*depth;other=(page^1)*depth;index=0
 if read(m,s['D_800DBEE8'],2)>0:
  entries=read(m,read(m,s['D_80089240']));base=read(m,s['D_800DBEF4']);key=read(m,NODE+16)
  while True:
   identity=read(m,entries,2)
   if key==u32(base+identity*160):break
   index+=1;entries+=4
   if index>=read(m,s['D_800DBEE8'],2):break
 if index==read(m,s['D_800DBEE8'],2):m[NODE+2]=0;return m,q
 identity=read(m,read(m,read(m,s['D_80089240']))+index*4,2);last=u32(read(m,read(m,s['D_80089250']+4*page))+identity*64)
 for i in range(depth):
  buffer=read(m,NODE+8);source=last if i+1==depth else u32(buffer+(i+other+1)*64);destination=u32(buffer+(first+i)*64);q.copy((source,destination,64))
 if m[NODE+2]!=m[NODE+1]:m[NODE+2]=(m[NODE+2]+1)&255
 return m,q
class Oracle(CopyBase):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=S if s is None else s
  FactoryOracle.__init__(self,words,initial.copy(),c,entry=entry,arguments=(NODE,),s={},connected=connected)
  self.providers=Providers(self.memory,c,self.s);self.fp_before=self.f[:];self.entry_sp=self.r[29];self.copy_snapshots=[]
 def record_call(self,t):
  assert t in(ENTRY,self.s['bcopy']),hex(t);a=tuple(self.arguments(1 if t==ENTRY else 3));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.s['bcopy']:self.copy_snapshots.append(data(self.memory,a[0],a[2]))
 def hook(self,t):
  assert t==self.s['bcopy'];a=self.calls[-1][1];self.providers.copy(a)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(a[1])
def streams(s=None):return{label:bound_blob(*payload(o/path,p.FUNCTION),S if s is None else s)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def saved(m):return m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.r[29]==m.entry_sp and m.f[20:]==m.fp_before[20:]
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.copy_snapshots,m.dispatched_word)
def check(m,initial,c,s=None,caller=False):
 expected,q=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert [a for t,a in m.calls if t==(S if s is None else s)['bcopy']]==[a for t,a in q.calls],(c,'calls');assert m.copy_snapshots==q.copies,(c,'copy snapshots')
 if not caller:assert saved(m),(c,'saved roles')
 if m.providers.calls:assert m.providers.observed==q.observed,(c,'live observations')
def main():
 programs=streams();rom=(r/'conker/conker.us.bin').read_bytes();assert struct.pack('>101I',*programs['retail'])==rom[0x1b6434:0x1b65c8];visits=set();count=0
 for c in cases():
  initial=fixture(c);models=[]
  for ws in programs.values():m=Oracle(ws,initial,c);m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,independent_public_effects_calls_and_live_observations_equal=True,padded_retail_all_private_bytes_and_registers_equal=True,raw_private_or_fault_identity_claim=False,unexecuted_original_words=[i for i in range(101)if ENTRY+4*i not in visits],void_result_compared=False,source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 programs=[v for k,v in streams().items()if k!='raw'];count=0
 for c in(Case(),Case(count=0,match=-1),Case(match=-1),Case(snapshots=0),Case(mutation=63,phase=8)):
  initial=fixture(c);full=Oracle(programs[-1],initial,c);full.run()
  for cut in range(full.all_accesses):
   states=[]
   for ws in programs:
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    states.append(state(m))
   assert all(v==states[0]for v in states[1:]);count+=1
 q=dict(padded_retail_full_state_and_dispatched_access_prefix_triples=count,raw_or_portable_C_fault_claim=False);(o/'faults.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
def connected():
 rom=(r/'conker/conker.us.bin').read_bytes();body=struct.unpack_from('>196I',rom,0x23a10);count=0
 for c in(Case(),Case(page=1),Case(snapshots=0),Case(match=-1),*[Case(residue=residue)for residue in range(4)],*[Case(snapshots=3,identity=0,alias=a,residue=residue)for a in range(1,5)for residue in range(4)]):
  initial=fixture(c);models=[];code=dict(zip(range(S['bcopy'],S['bcopy']+784,4),body))
  for ws in streams().values():m=Oracle(ws,initial,c,connected=code);m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);count+=1
 q=dict(cases_per_stream=count,actual_original_bcopy_words=196,overlap_both_directions_and_all_byte_alignments=True,SDK_copy_internal_execution=True,source_installed=p.installed(),matching_credit=0);(o/'connected.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def callers():
 begin=0x15188c00;end=0x15188c24;rom=(r/'conker/conker.us.bin').read_bytes();fragment=struct.unpack_from('>9I',rom,0x1b60b0);count=0
 for c in(Case(),Case(match=-1),Case(snapshots=0),Case(page=1,mutation=63,phase=8)):
  initial=fixture(c);models=[]
  for ws in streams().values():
   code=dict(zip(range(ENTRY,ENTRY+404,4),ws));code[end]=0;m=Oracle(fragment,initial,c,entry=begin,connected=code);m.r[16]=NODE;m.r[21]=S['_registry'];m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Original callback continuation not reached')
   check(m,initial,c,caller=True);assert m.r[2]==initial[NODE+3]and m.r[11]==10 and m.r[29]==m.entry_sp;assert m.r[16:24]==m.before[16:24]and m.r[28:31]==m.before[28:31]and m.r[31]==0x15188c1c;assert [a for t,a in m.calls if t==ENTRY]==[(NODE,)];models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);count+=1
 q=dict(original_JALR_window_words=9,cases_per_stream=count,actual_table_slot=1,void_result_overwritten_by_opacity=True,continuation_timer_and_opacity_verified=True,complete_dispatcher_claim=False);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();print(faults(),flush=True);connected();print(callers(),flush=True)
