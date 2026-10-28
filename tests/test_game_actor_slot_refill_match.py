"""Actor-slot refill: raw-C semantics, symbolic schedules, real Make, ABI and image gates."""
from pathlib import Path
from unittest.mock import patch
import csv,hashlib,io,itertools,json,os,re,struct,subprocess,time,unittest
from tools.experiments import game_actor_slot_refill_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
F=source.FUNCTION;ENTRY=source.ENTRY;GLOBAL=source.GLOBAL;ACTOR=0x22000;TABLE=0x30000;SLOTS=0x50000
class Oracle(RayOracle):
 def __init__(self,words,memory,entry=ENTRY,connected=None):
  TimingOracle.__init__(self,words,memory,entry=entry,arguments=(ACTOR,),connected=connected);self.trace=[]
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  assert target==ENTRY;args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):raise AssertionError(('unexpected helper',target))
def fixture(counter,count,selector,alias=0):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-768,512)};m.update({ACTOR+i:(i*13+0x59)&255 for i in range(-16,0x8D0)});m.update({SLOTS+i:0xA5 for i in range(-16,160)})
 put(m,GLOBAL,TABLE);put(m,ACTOR+0x5FC,counter&65535,2);put(m,ACTOR+0x5F8,0xA55A,2);put(m,ACTOR+0x60C,0x80000000);put(m,ACTOR+0x8BC,SLOTS);m[ACTOR+0x23D]=selector
 for i in range(256):put(m,TABLE+i*0x180+4,count)
 if alias==1:put(m,ACTOR+0x8BC,TABLE+selector*0x180+4)
 if alias==2:put(m,ACTOR+0x8BC,ACTOR+0x5FC)
 if alias==3:
  put(m,ACTOR+0x8BC,ACTOR+0x23C)
  put(m,TABLE+252*0x180+4,0)
 if alias==4:
  put(m,ACTOR+0x8BC,GLOBAL+2);put(m,(TABLE&0xFFFF0000)+0xFFFC+selector*0x180+4,0)
 if alias==5:
  put(m,ACTOR+0x8BC,ACTOR+0x8BC)
  m.update({0xFFFC28BC+i:0x59 for i in range(32)})
 return m

def reference(initial):
 m=dict(initial);counter=read(m,ACTOR+0x5FC,2);result=0
 if counter:
  put(m,ACTOR+0x5F8,1,2);index=0;offset=0
  while floating(bits(float(signed(index))))<floating(read(m,(read(m,GLOBAL)+m[ACTOR+0x23D]*0x180+4)&0xFFFFFFFF)):
   dest=(read(m,ACTOR+0x8BC)+offset)&0xFFFFFFFF
   assert dest in m and dest+1 in m,hex(dest)
   put(m,dest,0xFFFC,2);index=(index+1)&0xFFFFFFFF;offset=(offset+2)&0xFFFFFFFF;assert index<40,'Unbounded fixture'
  counter=read(m,ACTOR+0x5FC,2);put(m,ACTOR+0x60C,0);put(m,ACTOR+0x5FC,(counter-1)&65535,2);result=1
 return m,result

def public(m):return{a:b for a,b in m.items()if not STACK-768<=a<STACK+512}
def compare(initial,images):
 want,result=reference(initial);pair=[]
 for image in images:
  m=Oracle(image,initial).run();assert(public(m.memory),m.r[2],m.r[29],m.calls)==(public(want),result,STACK,[]);pair.append(m)
 assert pair[0].trace==pair[1].trace
 for reg in(16,17,18,19,20,21,22,23,28,29,30,31):assert pair[0].r[reg]==pair[1].r[reg]
 return pair
def plus(*args):
 terms=[];constant=0
 for x in args:
  if isinstance(x,int):constant+=x
  elif isinstance(x,tuple)and x[0]=='add':
   for a in x[1:]:
    if isinstance(a,int):constant+=a
    else:terms.append(a)
  else:terms.append(x)
 if constant&0xFFFFFFFF:terms.append(constant&0xFFFFFFFF)
 terms.sort(key=repr)
 return 0 if not terms else terms[0]if len(terms)==1 else('add',*terms)
def mul(a,b):
 if isinstance(a,int)and isinstance(b,int):return(a*b)&0xFFFFFFFF,(a*b)>>32
 return('mul_lo',*sorted((a,b),key=repr)),('mul_hi',*sorted((a,b),key=repr))
class State:
 def __init__(self,words,mode):
  self.words=words;self.r=[('incoming',i)for i in range(32)];self.r[0]=0;self.r[4]='actor';self.f=[('incoming_fp',i)for i in range(32)];self.lo,self.hi='incoming_lo','incoming_hi';self.events=[];self.writes=[];self.condition='incoming_condition';self.visits=set();self.mode=mode
 def read(self,a,size):
  v=('read',a,size,tuple(self.writes));self.events.append(('R',a,size,v));return v
 def step(self,at):
  self.visits.add(at);w=self.words[at//4];op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63;imm=w&65535;imm=imm if imm<32768 else imm-65536
  if w==0:return
  if op==0:
   if fn==37:self.r[rd]=self.r[rs]if self.r[rt]==0 else self.r[rt]if self.r[rs]==0 else('or',self.r[rs],self.r[rt])
   elif fn==33:self.r[rd]=plus(self.r[rs],self.r[rt])
   elif fn==25:self.lo,self.hi=mul(self.r[rs],self.r[rt])
   elif fn==18:self.r[rd]=self.lo
   elif fn==8:self.events.append(('RETURN',self.r[rs]))
   else:raise AssertionError(hex(w))
  elif op==9:self.r[rt]=plus(self.r[rs],imm)
  elif op==13:
   assert self.r[rs]==0;self.r[rt]=w&65535
  elif op==15:self.r[rt]=(w&65535)<<16
  elif op in(33,35,36,49):
   size={33:2,35:4,36:1,49:4}[op];v=self.read(plus(self.r[rs],imm),size)
   if op==49:self.f[rt]=v
   else:self.r[rt]=('sign16',v)if op==33 else v
  elif op in(41,57):
   size=2 if op==41 else 4;v=self.r[rt]if op==41 else self.f[rt];v=('low16',v)if op==41 else v;row=('W',plus(self.r[rs],imm),size,v);self.events.append(row);self.writes.append(row)
  elif op==20:
   assert rt==0;target=at+4+imm*4;self.events.append(('EQ_LIKELY',self.r[rs],0,target))
  elif op==17:
   fmt=rs;ft=rt;fs=w>>11&31;fd=w>>6&31
   if fmt==4:self.f[fs]=self.r[rt]
   elif fmt==8:self.events.append(('FP_BRANCH',ft,self.condition,at+4+imm*4))
   elif fmt==20 and fn==32:self.f[fd]=('cvt_f32_signed32',self.f[fs])
   elif fmt==16 and fn==60:self.condition=('c_lt_s',self.f[fs],self.f[ft])
   else:raise AssertionError(hex(w))
  else:raise AssertionError(hex(w))
  self.r[0]=0
 def run(self,addresses):
  for at in addresses:self.step(at)
  return self

def interfaces(a,b):
 assert a.events==b.events,(a.events,b.events)
 assert a.r[4]==b.r[4]=='actor'
 for i in(16,17,18,19,20,21,22,23,28,29,30,31):assert a.r[i]==b.r[i]
 for i in range(20,32):assert a.f[i]==b.f[i]
def symbolic_proof(truth,raw):
 # Zero-counter path: original schedules only the address of the global before its branch.
 a=State(truth,'retail').run((0,4,8,12,16,184,188));b=State(raw,'compiler').run((0,4,8,184,188));interfaces(a,b);assert a.r[2]==b.r[2]==0
 # Active prefix: likely entry delay is annulled. Both reach the same floating loop test.
 a=State(truth,'retail').run((0,4,8,12,*range(20,84,4)));b=State(raw,'compiler').run((0,4,*range(12,84,4)));interfaces(a,b);assert a.condition==b.condition
 assert(a.r[2],a.r[3],a.r[5],a.r[6],a.r[7],a.f[0])==(0,0,GLOBAL,384,0xFFFC,0)
 assert(b.r[2],b.r[3],b.r[6],b.r[5],b.r[7],b.f[0])==(0,0,GLOBAL,384,0xFFFC,0)
 # Empty loop: likely floating delay supplies the fresh counter, then the common exit.
 a.run((84,*range(160,180,4)));b.run((84,*range(160,180,4)));interfaces(a,b);assert a.r[2]==b.r[2]==1
 # Loop induction: arbitrary index, byte offset and live destination, with no fixed count assumption.
 def check_loop(candidate):
  a=State(truth,'retail');b=State(candidate,'compiler')
  for state in(a,b):state.r[2]='index';state.r[3]='offset';state.r[7]=0xFFFC;state.r[10]='live_destination';state.f[0]=0
  for state,g,s in((a,5,6),(b,6,5)):state.r[g]=GLOBAL;state.r[s]=384
  for state in(a,b):state.run(range(92,152,4))
  interfaces(a,b);assert a.condition==b.condition;assert(a.r[2],a.r[3],a.f[0])==(b.r[2],b.r[3],b.f[0])==(plus('index',1),plus('offset',2),0)
  # Taken backedge delay reloads the live destination; the invariant is closed.
  for state in(a,b):state.step(152)
  interfaces(a,b);assert a.r[10]==b.r[10]
 check_loop(raw)
 # Untaken backedge annuls that reload and reads the current signed counter at +156.
 a=State(truth,'retail');b=State(raw,'compiler')
 for state in(a,b):state.f[0]=0;state.run(range(156,180,4))
 interfaces(a,b);assert a.r[2]==b.r[2]==1
 assert hashlib.sha256(struct.pack('>48I',*raw)).hexdigest()=='1b2941ea990ee0755dc4c9d273d66a68c295e2cb516de5038576621c7f976183'
 assert hashlib.sha256(struct.pack('>48I',*truth)).hexdigest()=='d13b2f6391829834b46bf37cccae2e791cf709d1c59ca19a03339aefb957d19a'
 negative_controls=0
 for at,value in((92,0x24420002),(104,0xA5600000),(136,0xC5EA0008),(152,0x8C8A08C0)):
  candidate=list(raw);candidate[at//4]=value
  try:check_loop(candidate)
  except AssertionError:negative_controls+=1
  else:raise AssertionError(('Ineffective symbolic negative control',at))
 # Exact raw function fingerprints make this proof fail closed if either body changes.
 q=dict(private_only=True,production_installed=False,matching_credit=0,compiler_raw_linked_SHA256=hashlib.sha256(struct.pack('>48I',*raw)).hexdigest(),retail_linked_SHA256=hashlib.sha256(struct.pack('>48I',*truth)).hexdigest(),effective_symbolic_controls=negative_controls,different_words=sum(x!=y for x,y in zip(raw,truth)),entry_likely_delay_and_target_exact=True,empty_loop_exit=True,symbolic_loop_induction_for_arbitrary_index_offset_destination=True,live_memory_events_include_full_prior_write_history=True,global_address_and_stride_register_swap_closed=True,temporary_value_lifetimes_and_commutative_adds_equal=True,taken_backedge_live_destination_reload=True,untaken_backedge_counter_reload_and_return_delay_store=True,inactive_scratch_global_address_clobber_is_caller_saved=True,callee_saved_registers_and_stack_preserved=True,no_new_guards=True,canonical_Make_rebase_production_recount_and_documentation_still_pending=True)

 return q
def controls():
 selected=source.HEADERS+source.DECLARATIONS+source.SELECTED
 return dict(wrong_marker=selected.replace('= 0xFFFC;','= 0xFFFB;'),positive_counter=selected.replace('== 0) goto inactive','<= 0) goto inactive'),inclusive_bound=selected.replace('while ((f32)index <','while ((f32)index <='),skip_decrement=selected.replace('*(s16 *)(actor + 0x5FC) -= 1;',';'),skip_clear=selected.replace('*(f32 *)(actor + 0x60C) = 0.0f;',';'),wrong_stride=selected.replace('* 0x180 + 4','* 0x184 + 4'),wrong_return=selected.replace('return 1;','return 0;'))
def native_harness():
 selected=source.HEADERS+source.DECLARATIONS+source.SELECTED
 variants=controls()
 preamble=r'''#include <ultra64.h>
 typedef struct {u8 pad0[0x23D];u8 selector;u8 pad23E[0x3BA];s16 state;u16 reserved;s16 counter;u8 pad5FE[0xE];f32 timer;u8 pad610[0x2AC];u16 *slots;} Actor;
 typedef struct {u32 first;f32 count;u8 tail[0x178];} Setting;
 typedef char ABI[(sizeof(void*)==4&&sizeof(Actor)==0x8C0&&sizeof(Setting)==0x180&&__builtin_offsetof(Actor,counter)==0x5FC&&__builtin_offsetof(Actor,slots)==0x8BC)?1:-1];
 static struct {u32 before[4];Actor actor;u32 after[4];}actual,expected;
 static struct {u32 before[4];u16 slots[40];u32 after[4];}output,outputWant;
 static Setting settings[256];s32 D_800BE628;
 static f32 real(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
 '''
 code=preamble
 for name,body in dict(selected=selected,**variants).items():code+=body[body.index('/* Reset'):].replace(F,name)+'\n'
 code+=r'''
 typedef s32(*Update)(u8*);
 static int check(Update fn){u32 n,i,j,selector,pattern;u8 *p=(u8*)&actual,*q=(u8*)&expected,*a=(u8*)&output,*b=(u8*)&outputWant;s32 result,want;s16 counter;u32 markers;const u32 counts[]={0xBF800000u,0,0x3F000000u,0x3F800000u,0x40200000u,0x41800000u,0x7FC12345u,0x80000000u};
  for(n=0;n<67584;n++){
   counter=n<65536?(s16)n:(s16)(n&1?-1:1);selector=n<65536?(u8)(n>>8):(u8)(n>>3);pattern=n&7;
   for(i=0;i<sizeof(actual);i++)p[i]=(u8)(i*13+n);for(i=0;i<sizeof(output);i++)a[i]=(u8)(i*7+n);
   for(i=0;i<256;i++){settings[i].first=0x59A5A559u;settings[i].count=0;for(j=0;j<sizeof(settings[i].tail);j++)settings[i].tail[j]=(u8)j;}
   settings[selector].count=real(counts[pattern]);actual.actor.selector=selector;actual.actor.state=(s16)0xA55A;actual.actor.counter=counter;actual.actor.timer=-0.0f;actual.actor.slots=output.slots;D_800BE628=(s32)settings;
   for(i=0;i<sizeof(actual);i++)q[i]=p[i];for(i=0;i<sizeof(output);i++)b[i]=a[i];want=0;
   if(counter){expected.actor.state=1;markers=pattern==2?1:pattern==3?1:pattern==4?3:pattern==5?16:0;for(i=0;i<markers;i++)outputWant.slots[i]=0xFFFC;expected.actor.timer=0.0f;expected.actor.counter=(s16)(counter-1);want=1;}
   result=fn((u8*)&actual.actor);if(result!=want)return 1;
   for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 1;for(i=0;i<sizeof(output);i++)if(a[i]!=b[i])return 1;
  }return 0;}
 static int run(void){if(check(selected))return 10;
 '''
 for k,name in enumerate(variants):code+='if(!check('+name+'))return '+str(20+k)+';\n'
 code+='return 0;}\n'+START

 return code

class WindowEnd(Exception):pass
class Code(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc in(self.owner.end_fallthrough,self.owner.end_skip):raise WindowEnd(pc)
  return super().__getitem__(pc)

class ActorSlotRefillTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM))
  for name,attribute in(('selected.o','raw'),('qualified-padded.o','words')):
   p=cls.fresh/name;p.write_bytes((cls.out/name).read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,p,source.OWNER);info=functions[F];setattr(cls,attribute,list(struct.unpack_from('>48I',data,info['value'])))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,initial):return compare(initial,(self.truth,self.raw))
 def test_01_actual_owner_Make_and_canonical_ABI(self):
  self.assertEqual(self.words,self.truth);raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));self.assertEqual(source.normalized_payload(raw,rs),source.payload(self.out/('original-'+F+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),15)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(F,)),14);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_157840.c.o.compact'),15)
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertNotIn('#pragma GLOBAL_ASM',(self.out/'proposed-owner.c').read_text())
  self.assertIn('s32 func_1512B53C(u8 *actor)',source.SELECTED);self.assertIn('extern s32 D_800BE628;',source.DECLARATIONS);self.assertRegex(self.values['conker/include/variables.h'].decode(),r'extern\s+s32\s+D_800BE628;')
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=48,frame=0,raw_bindings=2,normalized_bindings=2,guards=21,neighbors=14,compact_functions=15,GLOBAL_ASM_routines=0,Make_commands=3,diagnostics=0,canonical_integer_held_guest_address_and_s32_u8_pointer_ABI=True)
 def test_02_raw_C_guest_cases_aliases_and_fired_access_prefixes(self):
  truth,raw=self.truth,self.raw
  patterns=(0,0x80000000,1,0x80000001,0xBF800000,0x3F000000,0x3F800000,0x40200000,0x41800000,0xFF800000,0x7FC12345,0xFFC12345)
  start=time.monotonic();cases=0;visits=set()
  for counter,count,selector in itertools.product((0,1,-1,-32768,32767),patterns,(0,1,127,128,255)):
   pair=self.compare(fixture(counter,count,selector));visits.update(pair[0].visits);cases+=1
  for selector in range(256):self.compare(fixture(1,0x40200000,selector));cases+=1
  for alias,counter in itertools.product(range(1,6),(1,-1,-32768,32767)):
   initial=fixture(counter,0x3FC00000 if alias==5 else 0x40200000,3,alias)
   if alias==2:
    # The last marker remains inside the actor but touches no pointer/count fields.
    pass
   self.compare(initial);cases+=1
  assert visits==set(range(ENTRY,ENTRY+192,4))-{ENTRY+180}
  # Inject every fired access boundary in representative paths; raw schedules may differ in PC/GPR scratch.
  cuts=0
  for counter,count,alias in itertools.product((0,1,-32768),(0,0x40200000),(0,1,2,3,4)):
   initial=fixture(counter,count,3,alias);pair=self.compare(initial)
   for cut in range(pair[0].root_accesses):
    pair=[]
    for image in(truth,raw):
     m=Oracle(image,initial);m.root_fault=cut
     try:m.run()
     except faults.AccessBoundary:pass
     else:raise AssertionError(('unfired access',cut))
     assert m.root_accesses==cut;pair.append(m)
    assert public(pair[0].memory)==public(pair[1].memory)and pair[0].trace==pair[1].trace;cuts+=1
  # Inactive gate has no table/destination dependency.
  initial=fixture(0,0,0)
  for address in(GLOBAL,ACTOR+0x8BC):
   for i in range(4):initial.pop(address+i)
  self.compare(initial)
  self.receipt['guest']=dict(cases=cases,visited_words=len(visits),unreachable_word=180,all256_selector_bytes=True,signed_counter_and_fractional_nonfinite_boundaries=True,raw_C_public_memory_return_callee_saved_and_trace_equal=True,live_float_bound_selector_global_and_destination_aliases=True,fault_prefix_pairs=cuts,inactive_table_and_destination_unmapped=True)
 def test_03_symbolic_blocks_close_register_and_schedule_invariants(self):
  self.receipt['symbolic']=symbolic_proof(self.truth,self.raw)
  self.assertEqual(self.receipt['symbolic']['effective_symbolic_controls'],4)
 def test_04_native32_valid_storage_and_effective_controls(self):
  for opt in('-O0','-O2','-O3'):
   p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=60).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=67584,effective_controls=len(controls()),trapping_UBSan=True,all65536_counter_encodings=True,all256_selector_values=True,typed_valid_actor_and_slot_and_setting_storage=True,guest_overlap_probes_separate_from_native=True)
 def test_05_padder_expected_word_bindings_and_three_GNU_rebases(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
  for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,{**rs,20:[('R_MIPS_HI16','wrong')]})):
   with self.assertRaises(ValueError):source.normalized_payload(b,bindings)
  for i in range(21):
   rows=[dict(x)for x in source.NEW_GUARDS];rows[i]['expected']='0xDEADBEEF'
   with patch.object(source,'NEW_GUARDS',rows):
    with self.assertRaises(ValueError):source.normalized_payload(raw,rs)
  rows=[dict(x)for x in source.NEW_GUARDS];rows[0]['replacement_relocations']='-'
  with patch.object(source,'NEW_GUARDS',rows):
   with self.assertRaises(ValueError):source.normalized_payload(raw,rs)
  before=self.values['conker/retail_word_patches.us.csv'];proposal=(self.out/'proposed-word-patches.csv').read_bytes();self.assertTrue(proposal.startswith(before));self.assertEqual(proposal,source.guard_manifest(before))
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=self.out/'proposed-word-patches.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
  reader=csv.DictReader(io.StringIO(proposal.decode()));fields=reader.fieldnames;rows=list(reader);next(x for x in rows if x['function']==F)['expected']='0x00000000';bad_csv=self.fresh/'bad.csv'
  with bad_csv.open('w',newline='')as stream:writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(rows)
  with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=bad_csv,filename=source.OWNER)
  normalized,bindings=source.normalized_payload(raw,rs);asm,unresolved=emit_function(normalized,dict(value=0,size=192),bindings,F,{'D_800BE628':GLOBAL});self.assertFalse(unresolved);p=self.fresh/'normalized.s';p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(p)],capture_output=True,check=True);cases=0
  for j,(entry,global_address)in enumerate(((ENTRY,GLOBAL),(0x17007FFC,0x800B7FFC),(0x2500FFFC,0x800C8004))):
   pair=[]
   for k,artifact in enumerate((self.out/('original-'+F+'.o'),obj)):
    p=self.fresh/('layout-%d-%d.ld'%(j,k));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',F,'--defsym=D_800BE628=0x%X'%global_address,'-o',str(elf),str(artifact)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>48I',sections(elf)['.text'][1])))
   self.assertEqual(*pair)
   for counter,count in itertools.product((0,1,-32768),(0,0x40200000,0x7FC12345)):
    initial=fixture(counter,count,3);want,result=reference(initial);value=read(initial,GLOBAL)
    for i in range(4):initial.pop(GLOBAL+i);want.pop(GLOBAL+i)
    put(initial,global_address,value);put(want,global_address,value)
    for words in pair:
     m=Oracle(words,initial,entry).run();self.assertEqual(public(m.memory),public(want));self.assertEqual(m.r[2],result)
    cases+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=cases,relocation_motion_from20_32_to4_8=True,signed_low_half_carry=True,effective_raw_and_binding_and_guard_controls=26,actual_padder_bad_expected_rejected=True,guards=21)
 def test_06_original_call_window_and_skip_gate_contract(self):
  rom=self.rom;truth,raw=self.truth,self.raw
  caller=list(struct.unpack_from('>11I',rom,0x158204));caller_cases=0
  for counter,count in itertools.product((0,1,-1,-32768,32767),(0,0x40200000,0x7FC12345)):
   initial=fixture(counter,count,3);want,result=reference(initial);pair=[]
   for image in(truth,raw):
    m=Oracle(caller,initial,0x1512AD54,{ENTRY+4*i:w for i,w in enumerate(image)});m.end_fallthrough=0x1512AD7C;m.end_skip=0x1512B0EC;m.code=Code(dict(m.code),m)
    try:m.run()
    except WindowEnd as end:assert end.args[0]==(m.end_skip if result else m.end_fallthrough)
    else:raise AssertionError('Caller did not leave window')
    assert public(m.memory)==public(want);assert m.r[2]==result and m.r[16]==ACTOR and m.r[29]==STACK-0x70;assert m.calls==[(ENTRY,(ACTOR,))];pair.append(m)
   assert pair[0].trace==pair[1].trace;caller_cases+=1
  asm=self.values[source.ASM].decode();literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',asm)};self.assertEqual(caller,[literal[0x1512AD54+i*4]for i in range(11)])
  ws=struct.unpack('>%dI'%(len(rom)//4),rom);jal=0x0C000000|(ENTRY>>2&0x3FFFFFF);jump=0x08000000|(ENTRY>>2&0x3FFFFFF);self.assertEqual([i*4 for i,w in enumerate(ws)if w in(jal,jump)],[0x15821C]);self.assertFalse(any(w==ENTRY for w in ws));self.assertIn('s32 func_1512AD54() {\n    return 0;\n}',self.values[source.SOURCE].decode())
  self.receipt['caller']=dict(original_words=11,connected_cases=caller_cases,s32_result_controls_skip_branch=True,current_parent_placeholder_unchanged=True,no_full_parent_or_gameplay_acceptance=True)
 def test_07_actually_compiled_cached_bound_fails_by_written_value(self):
  selected=source.HEADERS+source.DECLARATIONS+source.SELECTED;o=self.fresh;r=ROOT
  bad=selected.replace('    u32 offset;','    u32 offset;\n    f32 captured;').replace('        while ((f32)index < *(f32 *)((u32)D_800BE628 + actor[0x23D] * 0x180 + 4)) {','        captured = *(f32 *)((u32)D_800BE628 + actor[0x23D] * 0x180 + 4);\n        while ((f32)index < captured) {');assert bad!=selected
  obj,diag=source.compile_owner(r,o,bad,'negative-cached-bound');assert not diag;linked,funcs=source.link_owner(r,o,obj,'generated_157840');info=funcs[F];badwords=list(struct.unpack_from('>%dI'%(info['size']//4),linked,info['value']));initial=fixture(1,0x3FC00000,3,1);want,result=reference(initial);negative=Oracle(badwords,initial).run();assert public(negative.memory)!=public(want)and negative.r[2]==result
  address=TABLE+3*0x180+4;self.assertEqual((read(want,address),read(negative.memory,address)),(0xFFFC0000,0xFFFCFFFC));self.receipt['compiled_control']=dict(cached_bound_rejected_by_value=True,mapped_overlapping_count_has_one_vs_two_marker_writes=True,no_unmapped_failure_substitute=True)
 def test_08_strict_entire_image_and_effective_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==F)+8
  for offset in(20,at,at+180,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  q=json.loads((self.out/'preparation.json').read_text());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),q['changed_bytes']);self.assertEqual(q['metadata_bytes'],1)
  self.receipt['image']=dict(changed_bytes=q['changed_bytes'],code_bytes=q['code_bytes'],size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,inherited_guards_shared_headers_and_current_caller_unchanged=True)
