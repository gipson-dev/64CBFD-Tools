"""Execute retail cash callback, parent and text emitters; only allocator/sprintf are bounded services."""
from pathlib import Path
from dataclasses import dataclass
from collections import Counter
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import signed
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.patch_generated_slice_ld import load_game_data_layout
from tools.experiments import game_attached_cash_label_match as source
ENTRY=source.ENTRY
ROM=source.ROM
OWNER,LABEL,ACTOR,PACKET,TAIL,OUTPUT=0x30000,0x41000,0x45000,0x50000,0x60000,0x70000
PARENT,ATTACH,COLOR,COMMAND,WRAPPER,CORE,ALLOC,SPRINTF=0x150D0034,0x150432CC,0x1504332C,0x15042D78,0x15042E3C,0x15042ECC,0x10003C40,0x151EFF94
HELPERS=((ATTACH,12),(COLOR,22),(COMMAND,7),(WRAPPER,36),(CORE,252))
assert not STACK-2048<=LABEL<STACK+512, 'Fixture record must not overlap caller stack'
def configure(root,output,obj):
 global r,o,rom,start,base,end,truth,connected,raw_object
 r,o,raw_object=root,output,obj;rom=(r/'conker/conker.us.bin').read_bytes()
 start,base,end,_=load_game_data_layout(r/'conker')
 truth=words(ENTRY,51);connected={}
 for entry,n in HELPERS:connected.update(zip(range(entry,entry+n*4,4),words(entry,n)))
def words(entry,n):return list(struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2D4B0))
@dataclass(frozen=True)
class Case:
 remaining:int=1
 threshold:int=10
 rate:int=1
 amount:int=42
 allocate:int=1
 active:int=1
 same_id:int=1
 tail:int=0
 phase:int=0

def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
 for at,size in((OWNER,256),(LABEL,64),(ACTOR,128),(PACKET-16,128),(TAIL,128),(OUTPUT,16),(0x800CBD60,0x30),(0x80085CC0,128)):
  m.update({at+i:(i*29+0x59)&255 for i in range(size)})
 put(m,OWNER+0x48,LABEL);put(m,OWNER+0xE,c.remaining,2);m[OWNER+0x4C]=3;m[OWNER+0x30]=0xA5
 put(m,LABEL,ACTOR);m[LABEL+4]=7;put(m,LABEL+8,c.amount);put(m,LABEL+0xC,c.threshold,2);put(m,LABEL+0xE,c.rate,2)
 put(m,ACTOR,c.active);m[ACTOR+0x3B]=7 if c.same_id else 8
 for i,v in enumerate(b'$ %d\0'):m[0x800AB254+i]=v
 for address in(0x800CBD64,0x800CBD68,0x800CBD78):put(m,address,0)
 if c.tail:put(m,0x800CBD64,TAIL);put(m,0x800CBD68,TAIL);put(m,TAIL+0x18,0)
 m[0x8008FD90]=0;put(m,0x800CBD80,0x3F800000)
 at=0x80098B98
 for i in range(0x33*4):m[at+i]=rom[start+at-base+i]
 at=0x800888A0
 for i in range(16):m[at+i]=rom[start+at-base+i]
 return m

def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+512}
def cstring(m,p):
 b=bytearray()
 for i in range(128):
  v=m[p+i]
  if not v:return bytes(b)
  b.append(v)
 raise AssertionError('Unbounded test string')

class Oracle(FactoryOracle):
 def __init__(self,code,memory,c,entry=ENTRY,extra=None):
  args=(OWNER,)if entry==ENTRY else(OUTPUT,OWNER,0x12345678)
  super().__init__(code,memory,c,entry=entry,s={},connected=extra or connected,arguments=args)
  self.allocations=0;self.formats=[]
 def record_call(self,t):
  count={ENTRY:1,ATTACH:2,COLOR:4,COMMAND:1,WRAPPER:2,CORE:2,ALLOC:4,SPRINTF:3}[t]
  self.calls.append((t,tuple(self.arguments(count))))
 def hook(self,t):
  args=self.calls[-1][1]
  if t==ALLOC:
   assert args==(0x5C,1,0,1),args;self.allocations+=1;assert self.allocations==1;answer=PACKET if self.case.allocate else 0
  elif t==SPRINTF:
   destination,fmt,amount=args;assert cstring(self.memory,fmt)==b'%d';text=str(signed(amount)).encode();self.formats.append((destination,amount,text))
   for i,v in enumerate(text+b'\0'):self.memory[destination+i]=v
   answer=len(text)
  else:raise AssertionError(('Unexpected helper',hex(t)))
  # Bounded ABI services may overwrite their four argument homes, never the
  # caller's retained private halfword/pointer slots or saved registers.
  for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=answer

def raw_words():
 p=raw_object;text,fs,rs=parse_object(p);syms=dict(func_150432CC=ATTACH,func_1504332C=COLOR,func_15042D78=COMMAND,func_15042E3C=WRAPPER,D_800AB254=0x800AB254)
 asm,unknown=emit_function(text,fs['func_151D7000'],rs,'func_151D7000',syms);assert not unknown;p=o/'linked-cash-raw';p.with_suffix('.s').write_text(asm)
 p.with_suffix('.ld').write_text('SECTIONS { .text 0x151D7000 : SUBALIGN(4) { *(.text) } }\n'+'\n'.join('%s = 0x%X;'%(n,v)for n,v in syms.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_151D7000','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>51I',sections(p.with_suffix('.elf'))['.text'][1][:204]))

def run_connected():
 raw=raw_words();normalized=list(raw)
 for guard in source.NEW_GUARDS:normalized[int(guard["offset"],0)//4]=int(guard["replacement"],0)
 assert normalized==truth
 rows=[];seen=set();parent_seen=set();cases=0;outcomes=Counter()
 for remaining,threshold,rate,amount,allocation,gate in itertools.product((-32768,-1,0,1,32767),(0,10,32767),(-32768,-1,1,255),(-2147483648,0,2147483647),(0,1),(0,1,2)):
  c=Case(remaining,threshold,rate,amount,allocation,0 if gate==0 else 1,0 if gate==1 else 1,(remaining+amount)&1,8*(allocation&1));initial=fixture(c);models=[]
  valid=c.active and c.same_id;expected_return=PACKET if valid and allocation else 0
  for program in(truth,raw):
   m=Oracle(program,initial,c);m.run();assert m.r[2]==expected_return,(c,hex(m.r[2]),hex(expected_return))
   if valid:
    assert m.allocations==1
    if allocation:
     expected=b'$ '+str(amount).encode();assert cstring(m.memory,PACKET+0x1C)==expected
     assert read(m.memory,PACKET)==ACTOR and m.memory[PACKET+0xC]==0x81
     fade=255
     if remaining<threshold:fade=((remaining*rate)&65535);fade=0 if fade&32768 else fade
     assert tuple(m.memory[PACKET+i]for i in range(0xE,0x12))==(50,125,28,fade&255)
     assert read(m.memory,0x800CBD68)==PACKET and read(m.memory,0x800CBD78)==0
     assert read(m.memory,TAIL+0x18)==PACKET if c.tail else read(m.memory,0x800CBD64)==PACKET
    else:assert not m.formats and read(m.memory,0x800CBD78)==ACTOR
   else:assert not m.allocations and not m.calls and public(m.memory)==public(initial)
   models.append(m)
  assert public(models[0].memory)==public(models[1].memory)and models[0].calls==models[1].calls
  seen.update(models[0].visits);cases+=1;outcomes['packet'if expected_return else'zero']+=1
  # Exercise the complete original parent independently with both connected roots.
  if cases%29:continue
  pm=[]
  for program in(truth,raw):
   code=dict(connected);code.update(zip(range(ENTRY,ENTRY+204,4),program));m=Oracle(words(PARENT,35),initial,c,entry=PARENT,extra=code);m.run()
   assert m.r[2]==OUTPUT
   if expected_return:
    assert read(m.memory,OWNER+0xE,2)==(remaining&65535)and m.memory[OWNER+0x30]==0xA4
   else:assert read(m.memory,OWNER+0xE,2)==65535 and m.memory[OWNER+0x30]==0xA5
   pm.append(m);parent_seen.update(m.visits)
  assert public(pm[0].memory)==public(pm[1].memory)and pm[0].calls==pm[1].calls
  rows.append(c.__dict__)
 assert cases==1080
 # The no-callback selector covers the parent's final previously unseen word.
 c=Case();initial=fixture(c);initial[OWNER+0x4C]=255;expected=dict(initial);expected[OWNER+0x30]&=0xFE
 m=Oracle(words(PARENT,35),initial,c,entry=PARENT);m.run();assert m.r[2]==OUTPUT and not m.calls and public(m.memory)==public(expected);parent_seen.update(m.visits)
 report=dict(private_only=True,installed=False,matching_credit=0,raw_byte_exact=False,root_cases=cases,root_executions=cases*2,parent_cases=len(rows)+1,parent_executions=len(rows)*2+1,parent_words=35,connected_original_helper_words=sum(n for _,n in HELPERS),helper_words={hex(k):n for k,n in HELPERS},core_reachable_words=len(seen&set(range(CORE,CORE+252*4,4))),callback_reachable_words=len(seen&set(range(ENTRY,ENTRY+204,4))),parent_reachable_words=len(parent_seen&set(range(PARENT,PARENT+35*4,4))),format='$ %d',callback_table='D_800888A0',callback_index=3,callback_pointer_ROM='0x22D36C',callback_pointer_VA='0x800888AC',return_word_consumed=True,return_zero_expires_owner=True,return_value_on_success='actual final emitted packet address',return_value_on_allocation_failure=0,outcomes=dict(outcomes),only_allocator_and_decimal_sprintf_are_ABI_hooks=True,full_sprintf_hardware_or_all_format_paths_claimed=False,existing_void_C_wrapper_not_retyped=True)
 return report

from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_four_head_lookup_match import payload
class ClampCase:phase=0
def execute(program,entry,initial,registers):
 m=FactoryOracle(program,initial,ClampCase(),entry=entry,s={},arguments=(0,))
 m.r[3]=LABEL;m.r[4]=1;m.r[5]=0x109;m.r[6]=ACTOR
 for k,v in registers.items():m.r[k]=v&0xFFFFFFFF
 m.code=WindowCode(m.code,m);m.code.ends=(ENTRY+0x80,)
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Clamp window did not stop before the helper JAL')
 return m

def run_clamp():
 global rw,tw,rs,trs
 F=source.FUNCTION;raw,rs=payload(raw_object,F);retail,trs=payload(r/source.BUILD/('original-'+F+'.o'),F);assert rs==trs
 rw=list(struct.unpack('>51I',raw));tw=list(struct.unpack('>51I',retail));changed=[i for i in range(51)if rw[i]!=tw[i]]
 assert changed==[19,20,22,24,25,26,27,28,31,34]
 assert rw[22]==0x01040019 and tw[22]==0x00880019 # Same unsigned multiply, commuted inputs.
 assert rw[31]==0xA7A2001C and tw[31]==0xA7A2001A
 assert rw[34]==0x97A2001C and tw[34]==0x87A2001A
 memory={STACK+i:0xA5 for i in range(0x30)};memory.update({LABEL+0xE:0,LABEL+0xF:0})
 count=0
 for low in range(65536):
  expected=low if low<32768 else 0;incoming=0xA5A50000|low;machines=[]
  for program,offset in((tw,0x1A),(rw,0x1C)):
   m=execute(program[24:32],ENTRY+0x60,memory,{2:incoming});assert(m.r[2],m.r[3],m.r[4],m.r[5],m.r[6])==(expected,LABEL,ACTOR,0x109,ACTOR)
   assert read(m.memory,STACK+offset,2)==expected
   assert m.trace==[('W',STACK+offset,2,expected)]
   assert all(m.memory[p]==v for p,v in memory.items()if p not in(STACK+offset,STACK+offset+1))
   machines.append(m)
  count+=1
 # The first changed branch has the same arguments and memory prefix whether
 # the fade is skipped or the signed multiplication is performed.
 branch_cases=0
 for test in(0,1):
  for duration in(-32768,-1,0,1,32767):
   for rate in(-32768,-1,0,1,255,32767):
    initial=dict(memory);put(initial,LABEL+0xE,rate,2);models=[]
    for program,offset in((tw,0x1A),(rw,0x1C)):
     m=execute(program[19:32],ENTRY+0x4C,initial,{1:test,2:255,4:duration})
     low=(duration*rate)&65535;expected=(0 if low&32768 else low)if test else 255
     assert(m.r[2],m.r[3],m.r[4],m.r[5],m.r[6])==(expected,LABEL,ACTOR,0x109,ACTOR)
     expected_trace=([('R',LABEL+0xE,2,rate&65535)]if test else[])+[('W',STACK+offset,2,expected)]
     assert m.trace==expected_trace,(test,duration,rate,m.trace,expected_trace)
     models.append(m)
    assert(models[0].hi,models[0].lo)==(models[1].hi,models[1].lo)
    branch_cases+=1
 # The retained output is always 0..32767, including default255. Both loads
 # produce exactly the same word, and the helper additionally masks its low byte.
 for value in range(32768):
  assert value==((value^32768)-32768) and(value&255)==((value&65535)&255)
 guards=[]
 for i in changed:
  assert i*4 not in rs and i*4 not in trs
  guards.append(dict(offset=hex(i*4),expected='0x%08X'%rw[i],replacement='0x%08X'%tw[i],expected_relocations='-',replacement_relocations='-'))
 normalized=list(rw)
 for row in guards:
  i=int(row['offset'],0)//4;assert normalized[i]==int(row['expected'],0);normalized[i]=int(row['replacement'],0)
 assert normalized==tw
 report=dict(private_only=True,installed=False,matching_credit=0,source='cash-assignment-8.c',raw_words=51,retail_words=51,guards=guards,closed_region=['0x4C','0x80'],all_low_halfword_patterns=count,exhaustive_clamp_executions=count*2,branch_cases=branch_cases,branch_executions=branch_cases*2,spill_reload_values_checked=32768,private_spill_mapping={'raw':'SP+0x1C','retail':'SP+0x1A','width':2},unchanged_pointer_spill='SP+0x20',saved_RA='SP+0x14',argument_homes='SP+0x00..0x0F',all_binding_offsets_and_symbols_unchanged=True,normalized_payload_equals_entire_retail_payload=True,insertions=0,omissions=0,FP_operations_changed=0,helper_calls_changed=0,guards_are_not_merely_register_scheduling=True,normalization_kind='closed low16 signed-clamp control flow, commutative MULTU and private halfword spill layout',upper_product_bits_discarded_by_both_first_narrowing_operations=True,caller_saved_temporaries_not_live_at_next_helper=True,complete_C_or_production_qualification_pending=True)
 return report

def run_prefixes_and_sparse():
 """Guest instruction-prefix proof, not a portable C fault guarantee."""
 from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
 class FirstHelper(Exception):pass
 class Prefix(Oracle):
  def record_call(self,t):
   super().record_call(t)
   assert t==ATTACH
   raise FirstHelper
 def first(program,initial,c,cut=None):
  m=Prefix(program,initial,c);m.cut=cut
  try:m.run()
  except (FirstHelper,AccessBoundary) as error:return m,type(error)
  raise AssertionError('Active callback must reach its first helper')
 def trace(m,raw):
  slot=STACK+m.case.phase-0x28+0x1C
  return [(kind,address-2 if raw and address==slot else address,n,value)
          for kind,address,n,value in m.trace]
 programs=(truth,raw_words());prefixes=0
 for c in (Case(),Case(-1,10,255),Case(32767,0,-32768),Case(1,10,-1,phase=8)):
  initial=fixture(c);complete=[first(p,initial,c)[0] for p in programs]
  assert trace(complete[0],False)==trace(complete[1],True)
  assert complete[0].calls==complete[1].calls
  for cut in range(len(complete[0].trace)):
   pair=[first(p,initial,c,cut) for p in programs]
   assert all(error is AccessBoundary for _,error in pair)
   assert trace(pair[0][0],False)==trace(pair[1][0],True)
   assert public(pair[0][0].memory)==public(pair[1][0].memory)
   assert pair[0][0].calls==pair[1][0].calls
   prefixes+=1
 # Invalid actors must not touch lifetime, threshold, rate or later helpers.
 sparse=0
 for active,same in ((0,1),(1,0)):
  c=Case(active=active,same_id=same);initial=fixture(c)
  allowed={*(range(OWNER+0x48,OWNER+0x4C)),*(range(LABEL,LABEL+4)),
           *(range(ACTOR,ACTOR+4)),LABEL+4,ACTOR+0x3B}
  initial={a:v for a,v in initial.items() if a in allowed or STACK-2048<=a<STACK+512}
  for program in programs:
   m=Oracle(program,initial,c);m.run()
   assert m.r[2]==0 and not m.calls and public(m.memory)==public(initial)
   assert all(a in allowed for kind,a,n,v in m.trace if kind=='R' and not STACK-2048<=a<STACK+512)
   sparse+=1
 # These valid overlapping objects preserve the same live loads and stores.
 aliases=0
 for label,actor in ((LABEL,OWNER),(OWNER+0x20,ACTOR),(OWNER+0x20,OWNER)):
  c=Case();initial=fixture(c)
  old_label=bytes(initial[LABEL+i] for i in range(16));old_actor=bytes(initial[ACTOR+i] for i in range(128))
  for i,v in enumerate(old_actor):initial[actor+i]=v
  for i,v in enumerate(old_label):initial[label+i]=v
  put(initial,OWNER+0x48,label);put(initial,label,actor);initial[label+4]=initial[actor+0x3B]=7
  put(initial,actor,1);put(initial,OWNER+0xE,1,2)
  models=[]
  for program in programs:
   m=Oracle(program,initial,c);m.run();models.append(m)
  assert public(models[0].memory)==public(models[1].memory) and models[0].calls==models[1].calls and models[0].r[2]==models[1].r[2]
  aliases+=1
 return dict(fired_prefix_cases=prefixes,prefix_executions=prefixes*2,
             private_spill_mapping='raw SP+0x1C -> retail SP+0x1A',
             sparse_invalid_executions=sparse,connected_alias_cases=aliases,
             portable_C_fault_semantics_claimed=False)
