"""Owner row cleanup: dynamic loop-rotation proof, cycles and original helpers/caller."""
import subprocess
from tools.pad_generated_object import emit_padded_assembly
"""Private dynamic proof for raw C and the closed loop rotation; no adoption."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=o=None
RAW_OBJECT=NORM_OBJECT=None
ENTRY,FREE,OWNER=0x1518BBF4,0x1516972C,0x50000
NODES=tuple(0x30000+i*0x100 for i in range(7))
signed=lambda n:((n&255)^128)-128
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 owner:int=OWNER
 depth:int=0
 pattern:int=3
 mutation:int=0
 phase:int=0
 seed:int=0

def cases():
 rows=[Case(owner,depth,pattern,mutation,phase,seed)for owner,depth,pattern,mutation,phase,seed in itertools.product((0,OWNER,0x87654321,4),(-128,-127,-76,-3,-2,-1,0,1,126,127),range(6),range(5),(0,8),(0,1))]
 rows.extend(Case(owner,depth,0,0,phase)for owner,depth,phase in itertools.product((0,OWNER),range(256),(0,8)))
 return rows

def group(layout):
 base=(0x800DCE50,0x80107FFC,0x8020FF10)[layout]
 return dict(table=base,depth=base+0x340,slots=base+0x348)
def index(m,s):return signed(m[s['depth']])
def slot(m,s):return s['slots']+index(m,s)*4
def fixture(c,s):
 m={STACK+c.phase+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 m.update({s['table']+i:0 for i in range(-64,0x600)})
 for base in NODES:m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(64)});put(m,base+8,0)
 chains=(((),()),((0,),()),((0,1),(2,)),((0,1,2),(3,4)),((0,1),(1,)),((),(3,4)))[c.pattern]
 for row,chain in enumerate(chains):
  put(m,s['table']+row*0x1A0+0x7C,NODES[chain[0]]if chain else 0)
  for left,right in zip(chain,chain[1:]):put(m,NODES[left]+8,NODES[right])
 m[s['depth']]=c.depth&255
 return m
def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-1024<=a<STACK+c.phase+1024}

def repair_effect(m,s,node):
 count=index(m,s)
 for i in range(max(0,count)):
  addr=s['slots']+4*i
  if read(m,addr)==node:put(m,addr,read(m,node+8))
def effect(m,c,s,node):
 pending=read(m,slot(m,s));old_next=read(m,node+8)
 if c.mutation==1:put(m,slot(m,s),0)
 if c.mutation==2:
  m[s['depth']]=(m[s['depth']]+1)&255
  put(m,slot(m,s),pending)
 if c.mutation==3:put(m,s['table']+0x1A0+0x7C,NODES[6]);put(m,NODES[6]+8,0)
 if c.mutation==4 and old_next:
  saved=m[s['depth']];m[s['depth']]=(saved+1)&255;repair_effect(m,s,old_next);m[s['depth']]=saved
  put(m,old_next+8,0)
 put(m,node+8,0)

class ReferenceCycle(Exception): pass
class CallBoundary(Exception): pass

def reference(initial,c,s,extra_depth_exit=False,prime_once=False,max_calls=None):
 m=dict(initial);calls=[];steps=0;seen=set()
 if not c.owner:return public(m,c),calls
 if prime_once:m[s['depth']]=(m[s['depth']]+1)&255
 for row in range(2):
  record=read(m,s['table']+row*0x1A0+0x7C)
  if not prime_once:m[s['depth']]=(m[s['depth']]+1)&255
  while record:
   if c.mutation==3 and max_calls is None:
    key=(row,record,bytes(m[s['table']+i]for i in range(-64,0x600)),tuple((read(m,n+8),read(m,n+0x24))for n in NODES))
    if key in seen:raise ReferenceCycle(c)
    seen.add(key)
   steps+=1;assert steps<64,('Reference did not terminate',c)
   put(m,slot(m,s),read(m,record+8));put(m,record+0x24,c.owner)
   calls.append((FREE,(record,)))
   if max_calls is not None and len(calls)==max_calls:return public(m,c),calls
   effect(m,c,s,record);record=read(m,slot(m,s))
  m[s['depth']]=(m[s['depth']]-1)&255
  if extra_depth_exit and index(m,s)<0:break
 return public(m,c),calls

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s
  super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=(u32(c.owner),))
 def record_call(self,t):
  assert t==FREE,hex(t);self.calls.append((t,tuple(self.arguments(1))))
  if getattr(self,'call_limit',None)==len(self.calls):raise CallBoundary
 def hook(self,t):
  assert t==FREE;node=self.calls[-1][1][0];assert read(self.memory,node+0x24)==u32(self.c.owner)
  effect(self.memory,self.c,self.s,node)
  for j in range(4):self.put(self.r[29]+4*j,0xB5000000+j,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF


def programs(layout):
 entry=ENTRY+layout*0x1000000;s=group(layout)
 if s['depth']!=s['table']+0x340 or s['slots']!=s['depth']+8:raise ValueError('Row traversal group geometry changed')
 symbols=dict(D_800DCE50=s['table'],D_800DD190=s['depth'],D_800DD198=s['slots'],func_1516972C=FREE);result=[]
 for name,obj,size in [('original',o/'original-func_1518BBF4.o',220),('raw',RAW_OBJECT or o/'selected-final.o',216),('normalized',NORM_OBJECT or o/'normalized-isolated.o',220)]:
  dest=o/('public-layout-%d-%s'%(layout,name));dest.with_suffix('.ld').write_text('SECTIONS{.text 0x%X:SUBALIGN(4){*(.text)}}\n'%entry)
  subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(dest.with_suffix('.ld')),'-e','func_1518BBF4',*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(dest.with_suffix('.elf')),str(obj)],capture_output=True,check=True)
  image=dest.with_suffix('.elf').read_bytes();at=elf_slot_offset(image,entry,size);words=struct.unpack_from('>%dI'%(size//4),image,at);result.append(words);regs=[0]*32
  for word in words[9:17]:
   op,rs,rt=word>>26,word>>21&31,word>>16&31;imm=word&65535
   if op==15:regs[rt]=imm<<16
   elif op==9:regs[rt]=(regs[rs]+((imm^32768)-32768))&0xFFFFFFFF
   else:raise AssertionError(('Unexpected initializer',hex(word)))
  assert(regs[17],regs[18],regs[19],regs[20])==(s['depth'],s['slots'],s['table'],s['depth'])
 assert result[0]==result[2];return entry,s,result

def qualify(root,output,raw_object=None):
 global r,o,RAW_OBJECT,NORM_OBJECT
 r,o=Path(root),Path(output);RAW_OBJECT=Path(raw_object)if raw_object is not None else o/'selected-final.o'
 NORM_OBJECT=o/'public-normalized-isolated.o';assembly=NORM_OBJECT.with_suffix('.s')
 assembly.write_text(emit_padded_assembly(RAW_OBJECT,o/'isolated-retail.s',filename='generated_1B8F40',word_patches_path=o/'proposed-guards.csv'))
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(NORM_OBJECT),str(assembly)],capture_output=True,check=True)
 assert NORM_OBJECT.read_bytes()==(o/'normalized-isolated.o').read_bytes()
 all_cases=cases();root_cases=[];cyclic=[]
 for c in all_cases:
  try:reference(fixture(c,group(0)),c,group(0))
  except ReferenceCycle:cyclic.append(c)
  else:root_cases.append(c)
 count=0;seen=set();raw_seen=set()
 for layout in range(3):
  entry,s,roots=programs(layout)
  for c in root_cases:
   initial=fixture(c,s);expected,calls=reference(initial,c,s);models=[]
   for number,words in enumerate(roots):
    m=Oracle(words,initial,c,s,entry);m.run();assert public(m.memory,c)==expected and m.calls==calls,(layout,c,number,m.calls,calls)
    assert m.r[16:24]==m.before[16:24]and m.r[29]==m.before[29];models.append(m);count+=1
    (raw_seen if number==1 else seen).update(pc-layout*0x1000000 for pc in m.visits)
   a,b,d=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(d.r,d.f,d.memory,d.trace,d.hi,d.lo,d.calls)
   assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls),('Raw dynamic state/access mismatch',layout,c)
 cyclic_count=0
 for layout in range(3):
  entry,s,roots=programs(layout)
  for c in cyclic:
   initial=fixture(c,s);expected,calls=reference(initial,c,s,max_calls=16);models=[]
   for words in roots:
    m=Oracle(words,initial,c,s,entry);m.call_limit=16
    try:m.run()
    except CallBoundary:pass
    else:raise AssertionError('Cyclic callback boundary not reached')
    assert public(m.memory,c)==expected and m.calls==calls,(layout,c,'cyclic prefix');models.append(m);cyclic_count+=1
   a,b,d=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls)==(d.r,d.f,d.memory,d.trace,d.hi,d.lo,d.calls)
 missing=sorted(set(range(ENTRY,ENTRY+220,4))-seen);raw_missing=sorted(set(range(ENTRY,ENTRY+216,4))-raw_seen)
 assert missing==raw_missing==[ENTRY+x for x in(0x74,0x78,0x7C,0x80)],(missing,raw_missing)
 entry,s,roots=programs(0);pairs=0
 for c in (Case(),Case(owner=0),Case(owner=4,depth=-3),Case(depth=-76),Case(mutation=2),Case(mutation=4)):
  m=Oracle(roots[0],fixture(c,s),c,s,entry);m.run()
  for cut in range(m.all_accesses):
   models=[]
   for words in roots:
    q=Oracle(words,fixture(c,s),c,s,entry);q.cut=cut
    try:q.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access prefix cut did not fire')
    models.append(q)
   a,b,d=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(d.r,d.f,d.memory,d.trace,d.hi,d.lo,d.calls)
   assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls),('Raw prefix state mismatch',c,cut)
   pairs+=1
 # Null owner has no public mapping, and opaque nonzero owners are never dereferenced.
 c=Case(owner=0);initial={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
 for words in roots:m=Oracle(words,initial,c,s,entry);m.run();assert not m.calls
 # Independently reject the two semantic changes suggested by the advisory.
 c=Case(depth=-1,pattern=5);initial=fixture(c,s);assert reference(initial,c,s)!=reference(initial,c,s,extra_depth_exit=True)
 c=Case(depth=0,pattern=0);initial=fixture(c,s);assert reference(initial,c,s)!=reference(initial,c,s,prime_once=True)
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=len(root_cases)*3,executions=count,total_input_cases=len(all_cases),cyclic_cases=len(cyclic),cyclic_prefix_executions=cyclic_count,cyclic_callback_limit=16,cyclic_reference_state_repeat_verified=True,independent_group_link_layouts=3,raw_words=54,normalized_words=55,original_words_covered=51,raw_words_covered=50,unreachable_offsets=[0x74,0x78,0x7C,0x80],raw_and_normalized_full_bounded_state_and_access_trace_equal=True,access_prefix_triplets=pairs,null_owner_unmapped_public_executions=3,opaque_owner_not_dereferenced=True,all_256_depth_bytes_empty_rows=True,signed_depth_alias_boundaries=True,live_stack_and_depth_mutations=True,modeled_nested_repair=True,actual_cleanup_helper_stubbed=True,raw_fault_PC_or_BD_equivalence_claim=False,extra_static_load_adds_no_dynamic_read=True,advisory_extra_depth_exit_rejected=True,advisory_prime_once_rejected=True)
 return q

def helper(root,output):
 global r,o
 r,o=Path(root),Path(output)
 import sys
 g=sys.modules[__name__]
 REPAIR,DEFAULT,LOWER,DESCRIPTORS=0x151696DC,0x15169804,0x15168B10,0x8008B4D0
 CALLBACKS={2:0x17400200,31:0x17401F00}
 rom=(r/'conker/conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes();connected={};equal={}
 helper_sizes={g.FREE:112,REPAIR:80,DEFAULT:32}
 for va,size in helper_sizes.items():
  data=rom[va-0x15000000+0x2D4B0:va-0x15000000+0x2D4B0+size];at=elf_slot_offset(before,va,size);equal[hex(va)]=before[at:at+size]==data;connected.update(zip(range(va,va+size,4),struct.unpack('>%dI'%(size//4),data)))
 assert all(equal.values()),equal
 entry,s,roots=g.programs(0)

 def fixture(c,kindshift,callback):
  m=g.fixture(c,s)
  for i,node in enumerate(g.NODES):m[node]=(0,1,2,31)[(i+kindshift)%4]
  for kind in (2,31):g.put(m,DESCRIPTORS+kind*52,CALLBACKS[kind]if callback else 0)
  g.put(m,s['slots'],g.NODES[0])
  return m

 def reference(initial,c,max_free=None):
  m=dict(initial);calls=[];free_count=0;seen=set()
  if not c.owner:return g.public(m,c),calls
  for row in range(2):
   node=g.read(m,s['table']+row*0x1A0+0x7C);m[s['depth']]=(m[s['depth']]+1)&255
   while node:
    if c.mutation==3 and max_free is None:
     key=(row,node,bytes(m[s['table']+i]for i in range(-64,0x600)),tuple((g.read(m,n+8),g.read(m,n+0x24))for n in g.NODES))
     if key in seen:raise g.ReferenceCycle(c)
     seen.add(key)
    g.put(m,g.slot(m,s),g.read(m,node+8));g.put(m,node+0x24,c.owner);calls.append((g.FREE,(node,)));free_count+=1
    if max_free is not None and free_count==max_free:return g.public(m,c),calls
    calls.append((REPAIR,(node,)));g.repair_effect(m,s,node);kind=m[node]
    if kind>=2:
     target=g.read(m,DESCRIPTORS+kind*52)
     if target:calls.append((target,(node,)))
     else:calls.extend(((DEFAULT,(node,)),(LOWER,(node,1))))
     g.effect(m,c,s,node)
    node=g.read(m,g.slot(m,s))
   m[s['depth']]=(m[s['depth']]-1)&255
  return g.public(m,c),calls

 class Oracle(g.Oracle):
  def record_call(self,t):
   assert t in(g.FREE,REPAIR,DEFAULT,LOWER,*CALLBACKS.values()),hex(t)
   self.calls.append((t,tuple(self.arguments(2 if t==LOWER else 1))))
   if t==g.FREE:
    assert g.read(self.memory,self.calls[-1][1][0]+0x24)==g.u32(self.c.owner)
    self.free_count=getattr(self,'free_count',0)+1
    if getattr(self,'free_limit',None)==self.free_count:raise g.CallBoundary
  def hook(self,t):
   assert t in(LOWER,*CALLBACKS.values()),hex(t);node=self.calls[-1][1][0]
   if t==LOWER:assert self.calls[-1][1][1]==1
   g.effect(self.memory,self.c,self.s,node)
   for j in range(4):self.put(self.r[29]+4*j,0xB5000000+j,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
   self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF

 count=prefix_count=case_count=cyclic=0;seen=set()
 samples=g.cases()[::101]+[g.Case(depth=-76,pattern=1,mutation=3),g.Case(pattern=3),g.Case(pattern=2,depth=1)]
 for c,kindshift,callback in itertools.product(samples,range(4),(0,1)):
  initial=fixture(c,kindshift,callback);limit=None
  try:expected,calls=reference(initial,c)
  except g.ReferenceCycle:limit=16;cyclic+=1;expected,calls=reference(initial,c,limit)
  models=[]
  for words in roots:
   m=Oracle(words,initial,c,s,entry,connected);m.free_limit=limit
   try:m.run()
   except g.CallBoundary:assert limit is not None
   else:assert limit is None
   assert g.public(m.memory,c)==expected and m.calls==calls,(c,kindshift,callback,limit,m.calls,calls)
   models.append(m);seen.update(m.visits)
   if limit is None:count+=1
   else:prefix_count+=1
  a,b,d=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls)==(d.r,d.f,d.memory,d.trace,d.hi,d.lo,d.calls)
  if limit is None:case_count+=1
 coverage={hex(va):dict(words=size//4,executed=sum(pc in seen for pc in range(va,va+size,4)),unexecuted=[hex(pc)for pc in range(va,va+size,4)if pc not in seen])for va,size in helper_sizes.items()}
 assert all(not row['unexecuted']for row in coverage.values()),coverage
 helper_report=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=case_count,executions=count,cyclic_cases=cyclic,cyclic_prefix_executions=prefix_count,cyclic_free_limit=16,retained_helpers_equal_original=equal,original_helper_coverage=coverage,live_outer_pending_pointer_repair=True,default_and_typed_callback_routes=True,lower_release_two_slot_ABI=True,lower_release_and_callbacks_stubbed=True,complete_bounded_machine_and_access_state_equal=True,full_engine_claim=False)
 return helper_report

def callers(root,output):
 global r,o
 r,o=Path(root),Path(output)
 import sys
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 g=sys.modules[__name__]
 rom=(r/'conker/conker.us.bin').read_bytes();entry,s,roots=programs(0)
 WINDOW,END=0x1509856C,0x15099C00
 window=struct.unpack_from('>4I',rom,0xC5A1C);assert window==(0x0D462EFD,0x02202025,0x100005A2,0x24020001)
 class CallerOracle(g.Oracle):
  def record_call(self,t):
   if t==g.ENTRY:self.calls.append((t,tuple(self.arguments(1))));return
   return super().record_call(t)
 count=case_count=skipped=0;seen=set()
 for c in g.cases()[::37]:
  initial=g.fixture(c,s)
  try:expected,calls=g.reference(initial,c,s)
  except g.ReferenceCycle:skipped+=1;continue
  calls=[(g.ENTRY,(g.u32(c.owner),)),*calls];models=[]
  for root in roots:
   code=dict(zip(range(g.ENTRY,g.ENTRY+len(root)*4,4),root));code[END]=0;m=CallerOracle(window,initial,c,s,WINDOW,code);m.r[17]=g.u32(c.owner);m.r[4]=0xDEADBEEF;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller branch endpoint not reached')
   assert m.r[2]==1 and m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]
   assert m.calls==calls and g.public(m.memory,c)==expected,(c,m.calls,calls);models.append(m);seen.update(m.visits);count+=1
  a,b,d=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls)==(d.r,d.f,d.memory,d.trace,d.hi,d.lo,d.calls);case_count+=1
 assert set(range(WINDOW,WINDOW+16,4))<=seen
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=case_count,executions=count,window_words=4,all_window_words_executed=True,aligned_direct_JAL_ROM=0xC5A1C,actual_S1_to_A0_delay_slot=True,full_width_owner_forwarded=True,caller_forces_return_one=True,root_void_return_interface=True,full_parent_function_claim=False,cyclic_root_cases_kept_in_separate_prefix_suite=skipped,complete_bounded_machine_and_access_state_equal=True)
 return q
