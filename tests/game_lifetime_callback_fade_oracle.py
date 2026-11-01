"""Private integer semantics and the actual complete void-result parent."""
from pathlib import Path
from dataclasses import dataclass
from collections import Counter
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.patch_generated_slice_ld import load_game_data_layout
from tools.experiments import game_lifetime_callback_fade_match as source
ENTRY=0x15154C90;PARENT=0x151670C0;OWNER=0x30000;TIMER=0x800BE9E4;METHODS=0x8008ACC8;RELEASE=0x1516972C;TABLE=0x8008B4A8;LISTS=0x800DCE50;DEPTH=0x800DD190;CURSORS=0x800DD198
signed16=lambda v:((v&65535)^32768)-32768
words=lambda entry,n:list(struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2D4B0))
def configure(root,output,obj):
 global r,o,rom,start,base,end,truth,parent,methods,raw_object
 r,o,raw_object=root,output,obj;rom=(r/'conker/conker.us.bin').read_bytes();start,base,end,_=load_game_data_layout(r/'conker')
 truth=words(ENTRY,60);parent=words(PARENT,74);methods=list(struct.unpack_from('>16I',rom,start+METHODS-base));assert methods[4]==0x151CB510
@dataclass(frozen=True)
class Case:
 duration:int=1
 delta:int=1
 flags:int=9
 method:int=4
 outcome:int=1
 mutation:int=0
 phase:int=0

def fixture(c,category=87,row=0):
 m={STACK+i:(i*13+0xA5)&255 for i in range(-1024,256)};m.update({OWNER+i:(i*29+0x59)&255 for i in range(0xA0)})
 put(m,OWNER,category);put(m,OWNER+8,0);put(m,OWNER+0x22,c.duration,2);put(m,OWNER+0x24,c.flags,2);put(m,OWNER+0x26,10,2);put(m,OWNER+0x28,255,2);m[OWNER+0x2E]=200;m[OWNER+0x68]=0xA0|c.method;put(m,TIMER,c.delta)
 for address,size in ((METHODS,64),(TABLE,0x1484)):
  for i in range(size):m[address+i]=rom[start+address-base+i]
 for i in range(0x340):m[LISTS+i]=0
 m[DEPTH]=0
 for i in range(32):m[CURSORS+i]=0
 put(m,LISTS+row*0x1A0+category*4,OWNER)
 return m

def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+256}

def effect(memory,c):
 if c.mutation&1:put(memory,OWNER+0x22,-3,2)
 if c.mutation&2:put(memory,OWNER+0x24,8,2);put(memory,OWNER+0x26,32767,2)

def reference(initial,c):
 m=dict(initial);calls=[];expired=False
 if read(m,OWNER+0x24,2)&1:
  value=(signed16(read(m,OWNER+0x22,2))-read(m,TIMER))&65535;put(m,OWNER+0x22,value,2);expired=bool(value&32768)
 method=m[OWNER+0x68]&15
 if method and not expired:
  calls.append((methods[method],(OWNER,)));effect(m,c);expired=not c.outcome
 if read(m,OWNER+0x24,2)&8:
  duration=signed16(read(m,OWNER+0x22,2))
  if duration<signed16(read(m,OWNER+0x26,2)):
   value=signed16(duration*signed16(read(m,OWNER+0x28,2)))
   if value<m[OWNER+0x2E]:m[OWNER+0x2E]=value&255
 if expired:calls.append((RELEASE,(OWNER,)))
 return m,calls

class Oracle(FactoryOracle):
 def __init__(self,program,m,c,entry=ENTRY,extra=None,poison=None):
  super().__init__(program,m,c,entry=entry,s={},connected=extra,arguments=(OWNER,));self.poison=poison;self.return_poison_fired=0
  if poison is not None:
   owner=self
   class Tracked(dict):
    def __getitem__(self,pc):
     if pc==0x15167178:owner.r[2]=poison;owner.return_poison_fired+=1
     return super().__getitem__(pc)
   self.code=Tracked(self.code)
 def record_call(self,target):self.calls.append((target,(self.r[4],)));assert target in (ENTRY,RELEASE,*methods),hex(target)
 def hook(self,target):
  assert self.r[4]==OWNER
  if target==RELEASE:answer=0xA500ABCD
  else:assert target==methods[self.case.method];effect(self.memory,self.case);answer=self.case.outcome
  for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=answer;self.hi=0xA5000010;self.lo=0xA5000011

def run_suite():
 text,fs,rs=parse_object(raw_object);syms=dict(D_800BE9E4=TIMER,D_8008ACC8=METHODS,func_1516972C=RELEASE);asm,unknown=emit_function(text,fs['func_15154C90'],rs,'func_15154C90',syms);assert not unknown
 p=o/'raw-linked';p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x15154C90 : SUBALIGN(4) { *(.text) } }\n'+'\n'.join('%s = 0x%X;'%(k,v) for k,v in syms.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_15154C90','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 raw=list(struct.unpack('>60I',sections(p.with_suffix('.elf'))['.text'][1][:240]));count=0;visits=set()
 selected_methods=[0,4,next(i for i in range(1,16) if i!=4 and methods[i])]
 for duration,delta,flags,method,outcome,mutation in itertools.product((-32768,-1,0,1,32767),(-2147483648,-1,0,1,2147483647),(0,1,8,9),selected_methods,(0,1),(0,3)):
  c=Case(duration,delta,flags,method,outcome,mutation);initial=fixture(c);expected,calls=reference(initial,c)
  for program in (truth,raw):
   m=Oracle(program,initial,c);m.run();assert public(m.memory)==public(expected) and m.calls==calls,(c,m.calls,calls);visits.update(m.visits)
  count+=1
 parent_cases=0;parent_visits=set()
 for category,row,outcome,mutation in itertools.product((87,93),(0,1),(0,1),(0,3)):
  c=Case(outcome=outcome,mutation=mutation);initial=fixture(c,category,row);baseline=None
  for program,poison in itertools.product((truth,raw),(0,1,0x80000000,0xFFFFFFFF)):
   extra=dict(zip(range(ENTRY,ENTRY+240,4),program));m=Oracle(parent,initial,c,entry=PARENT,extra=extra,poison=poison);m.run();assert m.return_poison_fired==1
   observed=(public(m.memory),m.calls,tuple(m.r[16:24]),m.r[29]);parent_visits.update(m.visits)
   if baseline is None:baseline=observed
   else:assert observed==baseline,(category,row,outcome,mutation,poison)
   assert m.calls[0]==(ENTRY,(OWNER,)) and m.memory[DEPTH]==0
  parent_cases+=1
 assert TABLE+87*0x34==0x8008C654 and TABLE+93*0x34==0x8008C78C
 report=dict(private_only=True,installed=False,matching_credit=0,root_cases=count,root_executions=count*2,root_reachable_words=len(visits&set(range(ENTRY,ENTRY+240,4))),original_parent='func_151670C0',parent_words=74,parent_cases=parent_cases,parent_executions=parent_cases*8,parent_reachable_words=len(parent_visits&set(range(PARENT,PARENT+296,4))),return_poison_controls_per_raw_or_retail=4,parent_ignores_callback_word=True,callback_slots=['D_8008B4A8[87].unk0','D_8008B4A8[93].unk0'],timer_subtraction_covers_all_signed32_boundary_classes=True,callback_mutations_live=True,callback_and_release_are_explicit_ABI_services=True,source_raw_byte_exact=False,guards_not_installed=True,remaining=['closed spill/register-cycle proof','native32','Make/padder/strict image','canonical tools','production recount/docs/graph/commits'])
 return report

def run_sparse_and_aliases():
 global OWNER
 raw=list(struct.unpack('>60I',sections(o/'raw-linked.elf')['.text'][1][:240]))
 executions=0
 cases=[(Case(flags=0,method=0),{0x24,0x25,0x68}),
        (Case(duration=-1,delta=0,flags=1),{0x22,0x23,0x24,0x25,0x68}),
        (Case(duration=10,flags=8,method=0),{0x22,0x23,0x24,0x25,0x26,0x27,0x68})]
 for c,offsets in cases:
  initial=fixture(c);allowed={OWNER+i for i in offsets}
  if c.flags&1:allowed.update(range(TIMER,TIMER+4))
  initial={a:v for a,v in initial.items() if a in allowed or STACK-1024<=a<STACK+256}
  for program in (truth,raw):
   m=Oracle(program,initial,c);m.run()
   assert all(a in allowed for kind,a,n,v in m.trace if kind=='R' and not STACK-1024<=a<STACK+256)
   assert all(target==RELEASE for target,args in m.calls)
   executions+=1
 aliases=0;original=OWNER
 try:
  for offset in (0x22,0x26):
   OWNER=TIMER-offset;c=Case(delta=1);initial=fixture(c);expected,calls=reference(initial,c)
   for program in (truth,raw):
    m=Oracle(program,initial,c);m.run();assert public(m.memory)==public(expected) and m.calls==calls
   aliases+=1
 finally:OWNER=original
 return dict(sparse_executions=executions,guest_global_overlap_cases=aliases,
             guest_overlap_does_not_claim_portable_C_alias_semantics=True)

def run_parent_two():
 raw=list(struct.unpack('>60I',sections(o/'raw-linked.elf')['.text'][1][:240]));seen=set();executions=0;baseline=None
 for program in (truth,raw):
  for poison in (0,1,0x80000000,0xFFFFFFFF):
   c=Case();initial=fixture(c);other=0x32000
   for i in range(0xA0):initial[other+i]=0
   put(initial,OWNER+8,other);put(initial,other,87)
   extra=dict(zip(range(ENTRY,ENTRY+240,4),program));m=Oracle(parent,initial,c,entry=PARENT,extra=extra,poison=poison);m.run()
   assert m.return_poison_fired==2 and [args[0] for target,args in m.calls if target==ENTRY]==[OWNER,other]
   observed=(public(m.memory),m.calls,tuple(m.r[16:24]),m.r[29])
   if baseline is None:baseline=observed
   else:assert observed==baseline
   seen.update(m.visits);executions+=1
 assert len(seen&set(range(PARENT,PARENT+296,4)))==74
 report=dict(private_only=True,installed=False,matching_credit=0,original_parent_words=74,parent_reachable_words=74,two_node_executions=executions,raw_and_retail_tested=True,return_poison_controls=4,callback_return_word_unobserved=True,live_next_cursor_traversal=True)
 return report

def run_closed_proof():
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
 from tools.experiments.game_four_head_lookup_match import payload
 raw_bytes,bindings=payload(raw_object,'func_15154C90');retail_bytes,rb=payload(r/source.BUILD/'original-func_15154C90.o','func_15154C90');assert bindings==rb
 raw=list(struct.unpack('>60I',raw_bytes));retail=list(struct.unpack('>60I',retail_bytes));different=[i for i in range(60) if raw[i]!=retail[i]];assert different==[26,31,37,39,44,45,46]
 # The closed fade window is a V0/V1 role exchange and commutative MULTU.
 # Neither caller-saved temporary is live at the release call/void return.
 for low in range(65536):
  c=Case(duration=1,flags=8);initial={OWNER+i:0x59 for i in range(0x40)};put(initial,OWNER+0x22,1,2);put(initial,OWNER+0x26,10,2);put(initial,OWNER+0x28,low,2);initial[OWNER+0x2E]=low&255;models=[]
  for program in (retail,raw):
   m=Oracle(program[37:52],initial,c,entry=ENTRY+0x94);m.r[4]=OWNER;m.r[5]=0;m.code=WindowCode(m.code,m);m.code.ends=(ENTRY+0xD0,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Fade window did not reach its fixed boundary')
   models.append(m)
  a,b=models;assert a.memory==b.memory and a.trace==b.trace and(a.hi,a.lo)==(b.hi,b.lo)
  assert [v for i,v in enumerate(a.r) if i not in (2,3)]==[v for i,v in enumerate(b.r) if i not in (2,3)]
  expected=signed16(low);expected=(expected&255) if expected<(low&255) else low&255;assert a.memory[OWNER+0x2E]==expected
 # Full callback instruction prefixes, including live service effects and byte spill.
 raw_linked=list(struct.unpack('>60I',sections(o/'raw-linked.elf')['.text'][1][:240]));prefixes=0
 for c in (Case(),Case(-1,1,9),Case(32767,-2147483648,9),Case(1,0,8,4,0),Case(1,1,1,4,1,3),Case(0,0,9,4,1,3)):
  initial=fixture(c);models=[]
  for program in (truth,raw_linked):
   m=Oracle(program,initial,c);m.run();models.append(m)
  def normalized(m,raw):
   address=STACK+c.phase-32+31
   return [(kind,p-4 if raw and p==address else p,n,v) for kind,p,n,v in m.trace]
  assert normalized(models[0],False)==normalized(models[1],True)
  for cut in range(len(models[0].trace)):
   pair=[]
   for program in (truth,raw_linked):
    m=Oracle(program,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Prefix control did not fire')
    pair.append(m)
   assert normalized(pair[0],False)==normalized(pair[1],True) and public(pair[0].memory)==public(pair[1].memory) and pair[0].calls==pair[1].calls
   prefixes+=1
 guards=[]
 for i in different:
  assert i*4 not in bindings
  guards.append(dict(offset=hex(i*4),expected='0x%08X'%raw[i],replacement='0x%08X'%retail[i],expected_relocations='-',replacement_relocations='-'))
 normalized=list(raw)
 for row in guards:normalized[int(row['offset'],0)//4]=int(row['replacement'],0)
 assert normalized==retail
 report=dict(private_only=True,installed=False,matching_credit=0,full_payload_words=60,guards=guards,exhaustive_low16_values=65536,window_executions=131072,fired_prefix_cases=prefixes,prefix_executions=prefixes*2,private_byte_mapping='raw SP+0x1F -> retail SP+0x1B',closed_V0_V1_cycle=True,commutative_unsigned_multiply=True,caller_saved_results_proven_unobserved_by_actual_parent=True,all_bindings_unchanged=True,full_normalized_payload_equals_retail=True,insertions=0,omissions=0,portable_C_fault_semantics_claimed=False,native_and_Make_image_production_gates_pending=True)
 return report
