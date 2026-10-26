"""Complete reset state, access sequence, pointer aliases and fault prefixes."""
from pathlib import Path
import csv,io,itertools,json,struct,subprocess,unittest
from tools.experiments import game_menu_state_reset_match as source
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.check_game_data_layout import audit_layout

ROOT=Path(__file__).resolve().parents[2]
BUFFER=0x30000
DEFAULT={n:int(n[2:],16)for n in (
 'D_800BE3F8','D_800BE3D8','D_800BE3DC','D_800BE3DE','D_80082BC0','D_800D2E4C','D_800D2E60')}

class AccessBoundary(Exception):
 pass

def get(memory,address,size=4):
 return sum(memory[address+i]<<(8*(size-i-1))for i in range(size))

def fixture(pointer=BUFFER,seed=0,phase=0,symbols=None):
 s=symbols or DEFAULT;m={}
 for base,size in [(STACK-512,1280),(BUFFER-64,256),
                   *[(a-64,176)for a in s.values()]]:
  for i in range(size):
   a=base+i;m.setdefault(a,(a*13+seed*17+(a>>8))&255)
 put(m,s['D_800D2E4C'],pointer)
 return m

def reference(initial,symbols=None):
 s=symbols or DEFAULT;m=dict(initial);events=[]
 def write(a,value,n=1):
  if not all(a+i in m for i in range(n)):raise AccessBoundary(('write',a,n))
  put(m,a,value,n);events.append(('W',a,n))
 def read(a,n=4):
  if not all(a+i in m for i in range(n)):raise AccessBoundary(('read',a,n))
  events.append(('R',a,n));return get(m,a,n)
 try:
  for offset in(8,24,40):write(s['D_800BE3F8']+offset,0xFFFFFFFF,4)
  for offset in(14,30,46):write(s['D_800BE3F8']+offset,255)
  write(s['D_800BE3DC'],65535,2);write(s['D_800BE3DE'],0);write(s['D_80082BC0'],1)
  for i in range(27):write((read(s['D_800D2E4C'])+i)&0xFFFFFFFF,0)
  for i in range(9):write(s['D_800D2E60']+i,0)
  for i in(3,2,1,0):write(s['D_800BE3D8']+i,255)
 except AccessBoundary as error:
  return m,error.args,events
 return m,None,events

class ResetOracle(TimingOracle):
 def __init__(self,words,memory,phase=0,entry=source.ENTRY,connected=None,
              target_entry=None,fault=None):
  self.target_entry=entry if target_entry is None else target_entry
  self.target_accesses=0;self.reset_fault=fault
  super().__init__(words,memory,phase=phase,entry=entry,
                   arguments=(0x12345678,0x89ABCDEF,0x87654321,0xFEDCBA98),connected=connected)
  self.hi,self.lo=0x12345678,0x89ABCDEF
 def execute(self,word):
  if word>>26!=32:return super().execute(word)
  self.dispatched_word=word;self.own_instruction=True
  try:
   base,reg=(word>>21)&31,(word>>16)&31
   offset=((word&65535)^32768)-32768
   value=self.get((self.r[base]+offset)&0xFFFFFFFF,1)
   self.r[reg]=((value^128)-128)&0xFFFFFFFF;self.r[0]=0
  finally:self.own_instruction=False
 def access(self):
  if self.own_instruction and self.target_entry<=self.current_pc<self.target_entry+source.BODY:
   if self.target_accesses==self.reset_fault:raise AccessBoundary(('cut',self.reset_fault))
   self.target_accesses+=1
 def get(self,address,size):
  if not all(address+i in self.memory for i in range(size)):
   self.access();raise AccessBoundary(('read',address,size))
  return super().get(address,size)
 def put(self,address,value,size):
  if self.recording and self.own_instruction and not all(address+i in self.memory for i in range(size)):
   self.access();raise AccessBoundary(('write',address,size))
  return super().put(address,value,size)
 def record_call(self,target):
  raise AssertionError(('Unexpected reset call',target))
 def hook(self,target):
  raise AssertionError(('Unexpected reset provider',target))

def state(model):
 return complete(model),model.current_pc,model.delay_of,model.target_accesses

def executed(words,memory,**kwargs):
 model=ResetOracle(words,memory,**kwargs);error=None
 try:model.run()
 except AccessBoundary as failure:error=failure.args
 return model,error

def semantic_controls():
 body=source.SELECTED
 chain='D_800BE3D8.byte0 = D_800BE3D8.byte1 = D_800BE3D8.byte2 = D_800BE3D8.byte3 = -1;'
 controls={
  'wrong_word':body.replace('D_800BE3F8.unk18 = -1;','D_800BE3F8.unk18 = 0;'),
  'wrong_half':body.replace('D_800BE3DC = -1;','D_800BE3DC = 0;'),
  'wrong_flag':body.replace('D_800BE3DE = 0;','D_800BE3DE = 1;'),
  'wrong_ready':body.replace('D_80082BC0 = 1;','D_80082BC0 = 0;'),
  'short_indirect':body.replace('i >= 27','i >= 26'),
  'short_direct':body.replace('D_800D2E60 + 9','D_800D2E60 + 8'),
  'lost_sentinel':body.replace(chain,'D_800BE3D8.byte0 = 0; D_800BE3D8.byte1 = D_800BE3D8.byte2 = D_800BE3D8.byte3 = -1;'),
  'clobbered_padding':body.replace('D_800BE3F8.unk8 = -1;','D_800BE3F8.unk8 = -1; ((u8 *)&D_800BE3F8)[0] = 0;'),
 }
 assert all(x!=body for x in controls.values())
 return controls

def native_harness():
 controls=semantic_controls()
 text='#include <ultra64.h>\n#include "variables.h"\n'+source.SELECTED+'\n'
 for name,body in controls.items():text+=body.replace(source.FUNCTION,'negative_'+name)+'\n'
 text+=r'''
struct162 D_800BE3F8;
MenuResetSentinels D_800BE3D8;
s16 D_800BE3DC;
u8 D_800BE3DE, D_80082BC0;
struct102 *D_800D2E4C;
u8 D_800D2E60[32];
typedef char pointer_width[sizeof(void*)==4?1:-1];
typedef char sentinel_layout[(sizeof(MenuResetSentinels)==4 &&
 __builtin_offsetof(MenuResetSentinels,byte0)==0 &&
 __builtin_offsetof(MenuResetSentinels,byte1)==1 &&
 __builtin_offsetof(MenuResetSentinels,byte2)==2 &&
 __builtin_offsetof(MenuResetSentinels,byte3)==3)?1:-1];
typedef char record_layout[(sizeof(struct162)==48 &&
 __builtin_offsetof(struct162,unk8)==8 && __builtin_offsetof(struct162,unk18)==24 &&
 __builtin_offsetof(struct162,unk28)==40 && __builtin_offsetof(struct162,unkE)==14 &&
 __builtin_offsetof(struct162,unk1E)==30 && __builtin_offsetof(struct162,unk2E)==46)?1:-1];
typedef struct {u32 before[4];u8 bytes[64];u32 after[4];} NativeBuffer;
static NativeBuffer arena;
static u8 pattern(unsigned seed,unsigned index){return(u8)(seed*17+index*3+0x5A);}
static int trial(void(*fn)(void),unsigned seed){
 unsigned i;u8*p=(u8*)&D_800BE3F8,*a=(u8*)&arena,*b=(u8*)&D_800BE3D8;
 for(i=0;i<sizeof(D_800BE3F8);i++)p[i]=pattern(seed,i);
 for(i=0;i<sizeof(arena);i++)a[i]=pattern(seed,i);
 for(i=0;i<4;i++)b[i]=pattern(seed,i);
 for(i=0;i<32;i++)D_800D2E60[i]=pattern(seed,i);
 ((u8*)&D_800BE3DC)[0]=pattern(seed,0);((u8*)&D_800BE3DC)[1]=pattern(seed,1);
 D_800BE3DE=pattern(seed,2);D_80082BC0=pattern(seed,3);
 D_800D2E4C=(struct102*)arena.bytes;
 fn();
 if(D_800D2E4C!=(struct102*)arena.bytes || D_800BE3DC!=-1 ||
    D_800BE3DE!=0 || D_80082BC0!=1)return 1;
 for(i=0;i<sizeof(D_800BE3F8);i++){
  unsigned ff=(i>=8&&i<12)||(i>=24&&i<28)||(i>=40&&i<44)||i==14||i==30||i==46;
  if(p[i]!=(ff?255:pattern(seed,i)))return 1;
 }
 for(i=0;i<sizeof(arena);i++)if(a[i]!=((i>=16&&i<43)?0:pattern(seed,i)))return 1;
 for(i=0;i<4;i++)if(b[i]!=255)return 1;
 for(i=0;i<32;i++)if(D_800D2E60[i]!=(i<9?0:pattern(seed,i)))return 1;
 return 0;
}
static int run(void){
 unsigned seed,n,hit;
 static void(*negative[])(void)={''' + ','.join('negative_'+n for n in controls) + r'''};
 for(seed=0;seed<256;seed++)if(trial(func_15007778,seed))return 1;
 for(n=0;n<sizeof(negative)/sizeof(*negative);n++){
  hit=0;for(seed=0;seed<256;seed++)hit+=trial(negative[n],seed);
  if(!hit)return 2+n;
 }
 return 0;
}
'''
 return text+START

class CallerBoundary(Exception):
 pass
class CallerEndCode(faults.TrackedCode):
 def __contains__(self,pc):return pc in self.owner.ends or super().__contains__(pc)
 def __getitem__(self,pc):
  if pc in self.owner.ends:raise CallerBoundary
  return super().__getitem__(pc)
class CallerOracle(ResetOracle):
 def __init__(self,words,memory,target,phase,pattern):
  self.ends={0x151DE944,0x151DE97C};self.provider_pattern=pattern;self.target_calls=[]
  connected={source.ENTRY+4*i:w for i,w in enumerate(target)}
  super().__init__(words,memory,phase,0x151DE8F0,connected,source.ENTRY)
  self.code=CallerEndCode(self.code,self)
 def record_call(self,target):
  if target==source.ENTRY:
   args=();self.target_calls.append(args)
  else:
   assert target in(0x151EDF4C,0x151E7DC0,0x151E81EC)
   args=('opaque-registers',*self.r[4:8])
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target in(0x151EDF4C,0x151E7DC0,0x151E81EC)
  if target==0x151EDF4C:self.memory[0x8008FDA4]=(0,7,255)[self.provider_pattern]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)]
  self.r[2]=self.provider_pattern

class ResetTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;source.verify_prepared(cls.out);cls.values=source.snapshot(cls.out)
  rom=cls.values['conker/conker.us.bin']
  cls.truth=list(struct.unpack_from('>44I',rom,source.ROM))
  data,functions=link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
  at=functions[source.FUNCTION]['value'];cls.words=list(struct.unpack_from('>44I',data,at))
  data,functions=link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
  at=functions[source.FUNCTION]['value'];cls.raw=list(struct.unpack_from('>44I',data,at))
 def compare(self,pointer=BUFFER,seed=0,phase=0,check_raw=True):
  initial=fixture(pointer,seed,phase);expected,error,events=reference(initial)
  pair=[executed(w,initial,phase=phase)for w in(self.truth,self.words)]
  for model,failure in pair:
   self.assertEqual(failure,error,(pointer,seed,phase))
   self.assertEqual(model.memory,expected,(pointer,seed,phase))
   self.assertEqual([(e[0],e[1],e[2])for e in model.events if e[0]in('R','W')],events)
   self.assertEqual(model.r[29],STACK+phase)
   self.assertFalse(model.calls)
  self.assertEqual(state(pair[0][0]),state(pair[1][0]))
  if check_raw:
   model,failure=executed(self.raw,initial,phase=phase)
   self.assertEqual(failure,error);self.assertEqual(model.memory,expected)
  return pair[0][0],error
 def test_01_complete_slot_and_derived_binding_fit(self):
  self.assertEqual(self.words,self.truth)
  self.assertEqual(self.values['conker/conker.us.bin'][source.ROM+source.BODY:source.ROM+source.SIZE],bytes(8))
  q=json.loads((self.out/'derived-fit.json').read_text())
  self.assertEqual((q['words'],q['frame'],q['guards'],q['relocations']),(44,0,23,19))
  self.assertTrue(q['complete_raw_bytes_and_bindings_equal_to_original'])
  installed=(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE]
  source.check_inputs(ROOT,self.out,installed)
  make=json.loads((self.out/'make-shadow.json').read_text())
  self.assertEqual(make['commands'],3);self.assertEqual(make['compact_functions_equal'],18)
  self.assertTrue(make['complete_padded_object_equal'])
 def test_02_guest_states_and_canaries(self):
  visited=set()
  for seed,phase in itertools.product(range(256),(0,8)):
   model,error=self.compare(seed=seed,phase=phase);self.assertIsNone(error);visited.update(model.visits)
   self.assertEqual(model.target_accesses,76)
  self.assertEqual(visited,set(range(source.ENTRY,source.ENTRY+source.BODY,4)))
  self.receipt['guest']=dict(cases=512,all_byte_patterns=True,accesses=76,stores=49,pointer_reloads=27,all_body_words_visited=True,raw_memory_equal=True,fitted_complete_states_equal=True)
 def test_03_pointer_aliases_and_reload_faults(self):
  pointers=set(STACK+i for i in range(-128,129,4))
  for name,low,high,step in(('D_800BE3F8',-8,52,4),('D_800BE3D8',-16,12,4),
                           ('D_80082BC0',-16,12,4),('D_800D2E60',-28,16,4),
                           ('D_800D2E4C',-8,9,1)):
   pointers.update(DEFAULT[name]+i for i in range(low,high,step))
  faults=0;cases=0
  for pointer,seed,phase in itertools.product(sorted(pointers),(0,1,127,255),(0,8)):
   _,error=self.compare(pointer,seed,phase);faults+=error is not None;cases+=1
  self.assertGreater(faults,0)
  self.receipt['aliases']=dict(cases=cases,pointers=len(pointers),phases=2,unmapped_pointer_faults=faults,raw_memory_prefixes_equal=True,fitted_complete_states_equal=True,portable_C_fault_behavior_claimed=False)
 def test_04_fired_original_fault_prefixes(self):
  pairs=0
  for seed,phase in itertools.product((0,127),(0,8)):
   initial=fixture(seed=seed,phase=phase)
   full,error=executed(self.truth,initial,phase=phase);self.assertIsNone(error)
   for cut in range(full.target_accesses):
    a,ea=executed(self.truth,initial,phase=phase,fault=cut)
    b,eb=executed(self.words,initial,phase=phase,fault=cut)
    self.assertEqual(ea,(('cut',cut),));self.assertEqual(eb,ea);self.assertEqual(state(a),state(b));pairs+=1
  self.receipt['faults']=dict(fired_prefix_pairs=pairs,complete_states_equal=True,portable_C_fault_behavior_claimed=False)
 def test_05_signed_byte_opcode_controls(self):
  for value in range(256):
   memory=fixture();memory[BUFFER]=value
   model=ResetOracle([],memory);model.r[3]=BUFFER
   model.execute((32<<26)|(3<<21)|(8<<16))
   self.assertEqual(model.r[8],((value^128)-128)&0xFFFFFFFF)
   self.assertEqual(model.target_accesses,1)
   self.assertEqual(model.events,[('R',BUFFER,1,value)])
  self.receipt['signed_byte_control']=dict(all_256_values=True,sign_extension_and_access_checked=True)
 def test_06_sdk_native32_and_effective_semantic_controls(self):
  c=self.out/'native-reset.c';c.write_text(native_harness())
  results=[]
  for opt in('-O0','-O2','-O3'):
   executable=self.out/('native-reset-'+opt[1:])
   command=native_command(opt);command[1:1]=['-I',str(self.out/'raw-after-v2')]
   command += [str(c),'-o',str(executable)]
   compiled=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
   self.assertEqual(compiled.returncode,0,compiled.stdout+compiled.stderr)
   run=subprocess.run([str(executable)],capture_output=True,text=True)
   self.assertEqual(run.returncode,0,(opt,run.stdout,run.stderr))
   results.append(dict(optimization=opt,positive_cases=256,effective_compiled_negatives=len(semantic_controls()),trap_UBSan=True))
  self.receipt['native32']=dict(results=results,SDK_types=True,layout_assertions=True,all_byte_patterns=True,record_buffer_sentinel_canaries=True,void_no_argument_ABI=True)
 def test_07_real_caller_and_void_no_argument_ABI(self):
  rom=self.values['conker/conker.us.bin'];parent=0x151DE8F0
  words=list(struct.unpack_from('>21I',rom,parent-0x14FD2B50));cases=0;entered=0
  for flag,pattern,alias,phase in itertools.product(range(256),range(3),(0,1),(0,8)):
   pointer=0x8008FDA4-8 if alias else BUFFER
   initial=fixture(pointer,flag,phase)
   for i in range(-32,64):initial[0x8008FDA4+i]=(i*13+0x5A)&255
   initial[0x8008FDA4]=flag;pair=[]
   for target in(self.truth,self.words):
    model=CallerOracle(words,initial,target,phase,pattern)
    self.assertEqual(model.provider_pattern,pattern)
    with self.assertRaises(CallerBoundary):model.run()
    self.assertEqual(model.target_calls,[()]if flag==0 else[])
    self.assertEqual(model.r[29],STACK+phase-64)
    if flag==0:
     late=0 if alias else(0,7,255)[pattern]
     self.assertEqual(model.r[4],late)
     self.assertEqual(get(model.memory,model.r[29]+0x20),late)
     self.assertEqual(model.r[1],int(late<4))
    entered+=len(model.target_calls);pair.append(model)
   self.assertEqual(complete(pair[0]),complete(pair[1]));cases+=1
  self.receipt['caller']=dict(cases=cases,actual_target_calls=entered,site=0x151DE91C,
       void_no_argument_ABI=True,late_flag_reload=True,all_initial_mode_bytes=True,
       opaque_provider_patterns=[0,1,2],whole_parent_or_provider_acceptance=False)
 def test_08_guards_real_padder_and_GNU_relocations(self):
  raw,bindings=payload(self.out/'selected.o',source.FUNCTION)
  for i in range(44):
   bad=bytearray(raw);bad[4*i+3]^=1
   with self.assertRaises(ValueError):source.normalized(bytes(bad),bindings)
  for offset in bindings:
   changed=dict(bindings);changed[offset]=[('R_MIPS_LO16','D_800BE3D9')]
   with self.assertRaises(ValueError):source.normalized(raw,changed)
  with self.assertRaises(ValueError):source.normalized(raw[:-4],bindings)
  with self.assertRaises(ValueError):source.guard_bytes(self.values['conker/retail_word_patches.us.csv']+b'\n',raw,bindings)
  rows=list(csv.DictReader(io.StringIO((self.out/'qualified-guards.csv').read_text())))
  rows[-1]['expected']='0x%08X'%(int(rows[-1]['expected'],16)^1)
  bad=self.out/'negative-real-legacy-padder.csv'
  with bad.open('w',newline='')as stream:
   writer=csv.DictWriter(stream,fieldnames=list(rows[-1]));writer.writeheader();writer.writerows(rows)
  result=subprocess.run(['python3',str(ROOT/'tools/pad_c_object.py'),str(self.out/'after-owner.o'),
       str(ROOT/'conker/retail_layout.us.txt'),source.OWNER,str(self.out/'negative-real-padder.s'),
       '--word-patches',str(bad)],capture_output=True,text=True)
  self.assertNotEqual(result.returncode,0);self.assertIn('stale word patch',result.stderr)
  fit,rs=source.normalized(raw,bindings)
  anchors=dict(DEFAULT)
  anchors.update({n:anchors[b]+add for n,(b,add)in source.ALIASES.items()})
  asm,missing=emit_function(fit,dict(value=0,size=source.BODY),rs,source.FUNCTION,anchors)
  self.assertFalse(missing);path=self.out/'independent-fitted.s';path.write_text(asm);obj=path.with_suffix('.o')
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(path)],capture_output=True,check=True)
  carry=dict(zip(DEFAULT,(0x12347FF8,0x22347FFC,0x33348000,0x33348002,0x44347FFF,0x55347FFC,0x66347FFC)))
  layouts=[(source.ENTRY,DEFAULT),(source.ENTRY+0x200000,{n:a+0x17000 for n,a in DEFAULT.items()}),(source.ENTRY+0x500000,carry)]
  links=0;raw_carry_difference=False
  for index,(entry,symbols)in enumerate(layouts):
   definitions=dict(symbols);definitions.update({n:definitions[b]+add for n,(b,add)in source.ALIASES.items()})
   images=[]
   for kind,target in enumerate((self.out/('original-'+source.FUNCTION+'.o'),obj,self.out/'selected.o')):
    script=self.out/('rebase-%d-%d.ld'%(index,kind));elf=script.with_suffix('.elf')
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
    command=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
       *['--defsym=%s=0x%X'%item for item in definitions.items()],'-o',str(elf),str(target)]
    run=subprocess.run(command,capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stdout+run.stderr)
    images.append(list(struct.unpack_from('>44I',sections(elf)['.text'][1])));links+=1
   self.assertEqual(images[0],images[1])
   for seed in(0,127,255):
    initial=fixture(seed=seed,symbols=symbols);expected,error,_=reference(initial,symbols);self.assertIsNone(error)
    a,ea=executed(images[0],initial,entry=entry);b,eb=executed(images[1],initial,entry=entry)
    self.assertIsNone(ea);self.assertIsNone(eb);self.assertEqual(a.memory,expected);self.assertEqual(state(a),state(b))
   if index==2:
    initial=fixture(seed=47,symbols=symbols);expected,_,_=reference(initial,symbols)
    model,error=executed(images[2],initial,entry=entry)
    raw_carry_difference=error is not None or model.memory!=expected
  self.receipt['guards']=dict(raw_word_controls=44,binding_controls=len(bindings),extent_history=True,
       real_padder_negative=True,GNU_links=links,layouts=3,HI_LO_carry=True,
       end_alias_offset=9,byte_alias_offsets=[0,1,2,3],
       raw_GNU_end_expression_carry_difference_observed=raw_carry_difference)
 def test_09_strict_image_and_protected_data(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE]
  actual=(self.out/'first-linked.elf').read_bytes();source.check_image(before,actual,truth)
  audit=source.linked_function_audit(self.out/'before-conker_build_conker.us.elf',self.out/'first-linked.elf')
  by_name={n:(off,fields)for off,n,fields,_ in symbol_rows(before)}
  positions=(0,len(actual)-1,elf_slot_offset(before,source.ENTRY,source.SIZE),
       elf_slot_offset(before,0x8008B040,16),by_name[source.FUNCTION][0]+8,
       by_name[source.SERIALIZATION[0]][0]+4,
       source.elf_sections(before)['.strtab'][4]+by_name[source.SERIALIZATION[0]][1][0]+3)
  for at in positions:
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  data=audit_layout(self.out/'first-linked.elf',ROOT/'conker')
  self.assertEqual((data['exact'],data['owner_count'],data['bytes'],data['different_bytes']),(True,720,189088,0))
  q=json.loads((self.out/'qualification.json').read_text())
  self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(238,153,85,0))
  self.receipt['strict']=dict(changed_bytes=238,code_bytes=153,metadata_bytes=85,exclusions=0,
       image_corruptions=7,functions=audit['functions'],other_bodies_fixed=audit['other_bodies_fixed'],
       protected_data=data,closed_symbol_cycle=list(source.SERIALIZATION))
