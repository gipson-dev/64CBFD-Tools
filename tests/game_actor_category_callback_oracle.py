"""Actor category callback: literal guest state, real helper bodies and bounded callers."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_classifier_candidates import sections
r=o=None;F='func_1513DF9C';ENTRY=0x1513DF9C;ACTOR,CTX,MARK=0x30000,0x50000,0x70000
CALLBACKS=(0x1513E070,0x1513E084,0x15102D50,0x151C86AC,0x151416E8,0x150EF910,0x151BE604,0x151BE604,0x151C4AB0,0x150FDB0C,0x150F31D4)
MAPPING=(0,1,0,4,8,2,3,5,6,7,0,9,10)
OFFSETS=(96, 104, 96, 128, 160, 112, 120, 136, 144, 152, 168, 88, 80)
u32=lambda x:x&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 flags:int=0x400000
 category:int=12
 command:int=0xABCD001A
 event:int=1
 mutation:int=1
 tableset:int=0
 phase:int=0
 seed:int=0

def event(c):return (0,CTX,ACTOR+24,ACTOR+88,0x87654321)[c.event]
def targets(c):return CALLBACKS if c.tableset==0 else tuple(0x17400000+i*256 for i in range(11))
def index(c):return MAPPING[c.category]if c.flags&0x400000 and c.category<13 else 0
def identity(c,i):return 6 if not c.tableset and i==7 else i

def cases():
 rows=[]
 for category,fi,oi,phase in itertools.product(range(256),range(4),range(3),(0,8)):
  rows.append(Case((0,0x400000,0xFFFFFFFF,0x80000000)[fi],category,(0,0xABCD001A,0xFFFFFFFF)[oi],(category+fi+oi)%5,(category+oi)%2,(category+fi)%2,phase,oi%2))
 for command,category,flags in itertools.product(range(256),(0,1,3,4,7,8,11,12,13),(0,0x400000)):
  rows.append(Case(flags,category,0xA5A50000|command,(category+command)%5,command%2,category%2,8*(command%2),command%2))
 return rows

def fixture(c,s,entry):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+165)&255 for i in range(-512,512)}
 for base,n in((ACTOR,0x180),(CTX,64),(MARK,32)):
  m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 put(m,ACTOR+88,c.flags);m[ACTOR+25]=c.category
 for i,v in enumerate(targets(c)):put(m,s['D_80089F64']+4*i,v)
 for i,v in enumerate(OFFSETS):put(m,s['jtbl_800A5188_game']+4*i,entry+v)
 return m

def public(m,c):
 home=STACK+c.phase;return{a:b for a,b in m.items()if not home-512<=a<home+512}

def effect(m,c,i):
 ident=identity(c,i);e=event(c);cmd=c.command&255
 if c.mutation:m[ACTOR+25]^=128;put(m,ACTOR+88,read(m,ACTOR+88)^0x80000000)
 if c.mutation and e and all(e+j in m for j in range(4)):put(m,e,0xC0000000|(ident<<8)|cmd)
 for off,value in((0,ident),(4,e),(8,cmd),(12,0xB0000000|(ident<<16)|cmd)):put(m,MARK+off,value)

def reference(initial,c):
 i=index(c);m=dict(initial);effect(m,c,i);return public(m,c),[(targets(c)[i],(ACTOR,event(c),c.command&255))],i

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;self.indices=[]
  super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=(ACTOR,event(c),u32(c.command)))
 def record_call(self,t):
  assert t in targets(self.c),hex(t);self.calls.append((t,tuple(self.arguments(3))));self.indices.append(self.r[8]//4)
 def hook(self,t):
  i=self.indices[-1];assert targets(self.c)[i]==t;effect(self.memory,self.c,i)
  for j in range(4):self.put(self.r[29]+4*j,0xB5000000+j,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xB0000000|(identity(self.c,i)<<16)|(self.c.command&255)

def programs(layout):
 entry=ENTRY+layout*0x1000000;s=dict(jtbl_800A5188_game=(0x800A5188,0x80107FFC,0x80208004)[layout],D_80089F64=(0x80089F64,0x80208004,0x80307FFC)[layout]);roots=[]
 for name,obj in [('original',o/('original-'+F+'.o')),('selected',o/'selected-final.o')]:
  dest=o/('guest-%d-%s'%(layout,name));dest.with_suffix('.ld').write_text('SECTIONS{.text 0x%X:SUBALIGN(4){*(.text)} .rodata 0x%X:SUBALIGN(4){*(.rodata) *(.rdata)}}\n'%(entry,s['jtbl_800A5188_game']))
  q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(dest.with_suffix('.ld')),'-e',F,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(dest.with_suffix('.elf')),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr;secs=sections(dest.with_suffix('.elf'));roots.append(struct.unpack('>53I',secs['.text'][1][:212]))
  if name=='selected':assert secs['.rodata'][1][:52]==struct.pack('>13I',*[entry+x for x in OFFSETS])
 assert roots[0]==roots[1];return entry,s,roots


def qualify(root,output):
 global r,o
 r,o=Path(root),Path(output)
 body=(r/'conker/asm/nonmatchings/game_169510/func_1513DF9C.s').read_text().split('glabel '+F+'\n')[1].split('endlabel '+F)[0];p=o/('original-'+F)
 p.with_suffix('.s').write_text('.include "macro.inc"\n.text\n.set noat\n.set noreorder\n.globl '+F+'\n'+F+':\n.type '+F+', @function\n'+body+'\n.size '+F+', . - '+F+'\n');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 count=0;seen=set();indices=set()
 for layout in range(3):
  entry,s,roots=programs(layout)
  for c in cases():
   initial=fixture(c,s,entry);expected,calls,i=reference(initial,c);models=[]
   for root in roots:
    m=Oracle(root,initial,c,s,entry);m.run();assert public(m.memory,c)==expected,(layout,c,'memory');assert m.calls==calls and m.indices==[i],(layout,c,m.calls,calls,m.indices,i);assert m.r[16:24]==m.before[16:24]and m.r[29]==m.before[29];models.append(m);count+=1;seen.update(pc-layout*0x1000000 for pc in m.visits);indices.add(i)
   a,b=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls,a.indices)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls,b.indices)
 missing=sorted(set(range(ENTRY,ENTRY+212,4))-seen);assert missing==[ENTRY+44]and indices==set(range(11)),missing
 entry,s,roots=programs(0);pairs=0
 for c in[Case(),Case(flags=0),Case(category=255,event=3),Case(category=8,command=0xFFFFFFFF,event=2)]:
  m=Oracle(roots[0],fixture(c,s,entry),c,s,entry);m.run()
  for cut in range(m.all_accesses):
   models=[]
   for root in roots:
    q=Oracle(root,fixture(c,s,entry),c,s,entry);q.cut=cut
    try:q.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut not reached')
    models.append(q)
   a,b=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls);pairs+=1
 # Flag-clear must not read category even though callback0 is still invoked.
 c=Case(flags=0,mutation=0);initial=fixture(c,s,entry);del initial[ACTOR+25]
 for root in roots:m=Oracle(root,initial,c,s,entry);m.run();assert m.indices==[0]
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=len(cases())*3,executions=count,independent_link_layouts=3,covered_words=52,unreachable_offsets=[44],all_11_indices=True,all_256_categories_and_commands=True,opaque_event_word_forwarded=True,byte_command_poisons=True,callback_actor_context_mutations=True,actual_alias_and_unique_callback_tables=True,literal_full_model_state_equal=True,access_prefix_pairs=pairs,sparse_flag_clear_executions=2,void_return_value_not_claimed=True,real_callback_bodies_not_claimed=True)
 return q

def helper(root,output):
 global r,o
 r,o=Path(root),Path(output)
 import sys
 g=sys.modules[__name__]
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 rom=(r/'conker/conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes();COMMON=0x15169850;entry,s,roots=g.programs(0)
 callbacks={0x1513E070:20,0x15102D50:64,0x151BE604:64,0x150F31D4:64};original={};retained={};equal={}
 for va,size in callbacks.items():
  off=va-0x15000000+0x2D4B0;a=rom[off:off+size];at=elf_slot_offset(before,va,size);b=before[at:at+size];equal[hex(va)]=a==b;original.update(zip(range(va,va+size,4),struct.unpack('>%dI'%(size//4),a)));retained.update(zip(range(va,va+size,4),struct.unpack('>%dI'%(size//4),b)))
 class Oracle(g.Oracle):
  def record_call(self,t):
   if t==COMMON:self.calls.append((t,tuple(self.arguments(5))));return
   return super().record_call(t)
  def hook(self,t):
   assert t==COMMON;assert self.calls[-1][1]==(g.event(self.c),self.c.command&255,g.ACTOR+0x110,g.ACTOR+0x114,g.ACTOR)
   return super().hook(g.targets(self.c)[self.indices[-1]])
 helper_sets=[('original',original)]if all(equal.values())else [('original',original),('retained',retained)]
 count=0;seen=set()
 for label,connected in helper_sets:
  for category,flags,command,event,mutation,phase in itertools.product((0,5,8,9,12),(0,0x400000),(0,1,26,45,255,0xABCD001A,0xFFFFFFFF,256),range(5),(0,1),(0,8)):
   c=g.Case(flags,category,command,event,mutation,0,phase);i=g.index(c);initial=g.fixture(c,s,entry);expected=dict(initial);calls=[(g.targets(c)[i],(g.ACTOR,g.event(c),command&255))]
   if i!=0:calls.append((COMMON,(g.event(c),command&255,g.ACTOR+0x110,g.ACTOR+0x114,g.ACTOR)));g.effect(expected,c,i)
   expected=g.public(expected,c);models=[]
   for root in roots:
    m=Oracle(root,initial,c,s,entry,connected);m.run();assert m.calls==calls and g.public(m.memory,c)==expected,(label,c,m.calls,calls);models.append(m);seen.update(m.visits);count+=1
   a,b=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls)
 coverage={hex(va):dict(words=size//4,executed=sum(pc in seen for pc in range(va,va+size,4)),unexecuted=[hex(pc)for pc in range(va,va+size,4)if pc not in seen])for va,size in callbacks.items()}
 c=g.Case(flags=0,mutation=0);initial=g.fixture(c,s,entry);del initial[g.ACTOR+25]
 for root in roots:m=Oracle(root,initial,c,s,entry,original);m.run();assert m.indices==[0]
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=count//2,executions=count,helper_modes=[label for label,_ in helper_sets],retained_slots_equal_original=equal,original_helper_coverage=coverage,all_five_callback_indices=True,lower_common_five_slot_ABI=True,lower_common_function_stubbed=True,literal_full_model_state_equal=True,sparse_real_noop_executions=2,all_complex_callbacks_claim=False)
 return q

def callers(root,output):
 global r,o
 r,o=Path(root),Path(output)
 import sys
 g=sys.modules[__name__]
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 rom=(r/'conker/conker.us.bin').read_bytes();entry,s,roots=g.programs(0);REGISTRATIONS=(0x8008BA74,0x8008C398,0x8008C63C);IDS=(27,72,85);TABLEVIEW=0x8008B4DC;REF=0x60000
 routes=((0x15169160,5,0),(0x15169340,10,1),(0x15169514,5,2))

 def register_io(w):
  op,fn,rs,rt,rd=w>>26,w&63,w>>21&31,w>>16&31,w>>11&31
  if op==0:
   if fn in(0,2,3):return {rt},{rd}
   if fn in(8,9):return {rs},{rd}if fn==9 else set()
   if fn in(16,18):return set(),{rd}
   if fn in(17,19):return {rs},set()
   if fn in(12,13):return set(),set()
   return {rs,rt},set()if fn in(24,25,26,27)else{rd}
  if op==15:return set(),{rt}
  if op in(8,9,10,11,12,13,14,32,33,34,35,36,37,38,39):return {rs},{rt}
  if op in(40,41,42,43,46,63):return {rs,rt},set()
  if op in(49,53,57,61):return {rs},set()
  if op==17:
   if rs in(0,2):return set(),{rt}
   if rs in(4,6):return {rt},set()
   return set(),set()
  if op in(4,5,20,21):return {rs,rt},set()
  if op in(1,6,7,22,23):return {rs},set()
  if op in(2,3):return set(),set()
  raise AssertionError(('Unknown caller instruction',hex(w)))
 def no_return_consumption(start,n):
  rows=list(__import__('csv').DictReader((r/'conker/retail_layout.us.txt').open()));row=next(d for d in rows if int(d['address'],16)<=start<int(d['end'],16));lo,hi=int(row['address'],16),int(row['end'],16);ws=struct.unpack_from('>%dI'%((hi-lo)//4),rom,lo-0x15000000+0x2D4B0);code=dict(zip(range(lo,hi,4),ws));queue=[start+n*4];seen=set()
  def observe(pc):
   reads,writes=register_io(code[pc]);assert 2 not in reads,('Callback result consumed',hex(pc));return 2 not in writes
  while queue:
   pc=queue.pop()
   if pc in seen or pc not in code:continue
   seen.add(pc);w=code[pc];op,fn,rs=w>>26,w&63,w>>21&31
   if not observe(pc):continue
   if op==3 or(op==0 and fn in(8,9)):
    observe(pc+4);continue
   if op in(1,4,5,6,7,20,21,22,23):
    delay=observe(pc+4);target=pc+4+4*(((w&65535)^32768)-32768)
    if delay:queue.append(target)
    if op in(20,21,22,23)or delay:queue.append(pc+8)
   elif op==2:
    if observe(pc+4):queue.append((pc&0xF0000000)|((w&0x3FFFFFF)<<2))
   else:queue.append(pc+4)
  return len(seen)
 return_liveness={hex(start):no_return_consumption(start,n)for start,n,_ in routes}
 class Oracle(g.Oracle):
  def record_call(self,t):
   if t==g.ENTRY:self.calls.append((t,tuple(self.arguments(3))));return
   return super().record_call(t)
 count=0;coverage={}
 for start,n,kind in routes:
  words=struct.unpack_from('>%dI'%n,rom,start-0x15000000+0x2D4B0);end=start+n*4;seen=set()
  for registration,category,flags,command,event,phase in itertools.product(range(3),(0,1,5,8,9,12,255),(0,0x400000),(0,0xABCD001A,0xFFFFFFFF),(0,1,4),(0,8)):
   c=g.Case(flags,category,command,event,1,0,phase);initial=g.fixture(c,s,entry)
   for addr in REGISTRATIONS:g.put(initial,addr,g.ENTRY)
   g.put(initial,REF,IDS[registration]);expected,calls,i=g.reference(initial,c);calls=[(g.ENTRY,(g.ACTOR,g.event(c),command&255)),*calls];models=[]
   for root in roots:
    code=dict(zip(range(g.ENTRY,g.ENTRY+212,4),root));code[end]=0;m=Oracle(words,initial,c,s,start,code);m.r[16]=g.ACTOR;m.r[7]=0xDEADBEEF
    if kind==0:m.r[18]=g.event(c);m.r[19]=command;m.r[22]=REGISTRATIONS[registration]-28
    elif kind==1:m.r[18]=g.event(c);m.r[19]=command;m.r[22]=REF;m.r[23]=TABLEVIEW;m.r[30]=52
    else:m.r[19]=g.event(c);m.r[20]=command;m.r[22]=REGISTRATIONS[registration]-28
    m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller window end not observed')
    assert m.calls==calls and m.indices==[i]and g.public(m.memory,c)==expected,(kind,registration,c,m.calls,calls)
    assert m.r[29]==m.before[29];models.append(m);seen.update(m.visits);count+=1
   a,b=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls,a.indices)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls,b.indices)
  assert set(range(start,end,4))<=seen;coverage[hex(start)]=n
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=count//2,executions=count,descriptor_registrations=3,descriptor_indices=list(IDS),registry_view=TABLEVIEW,three_original_generic_windows=coverage,real_table_selection_and_three_slot_setup=True,byte_command_forwarded=True,opaque_event_word_forwarded=True,literal_full_bounded_model_state_equal=True,callback_result_not_consumed=True,return_liveness_instruction_counts=return_liveness,full_parent_functions_claim=False,preceding_filter_function_claim=False,void_interface=True)
 return q
