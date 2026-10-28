"""Display-list buffer allocation: live configuration, opaque allocator ABI and full-image gates."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_display_list_buffer_allocation_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];RECORD,OTHER=0x22000,0x23000
COUNTS=(0,1,399,400,7999,8000,0xFE70,0xFF00,0xFFFF)
RETURNS=((0x400000,0x500000),(0,0),(0,0x80000000),(0xFFFFFFFC,4),(0x7FFFFFFC,0x80000004),(0x90001000,0x80001000),(0x400008,0x400001))
@dataclass(frozen=True)
class Case:
 count:int=0
 first:int=0x400000
 second:int=0x500000
 mode:int=0
 changed:int=17
 first_override:int=0x480000
 layout:int=0
 phase:int=0
@dataclass(frozen=True)
class Globals:
 config:int=source.CONFIG
 slots:int=source.SLOTS
 limit:int=source.LIMIT
 allocator:int=source.ALLOCATOR

def get_count(m,g):return read(m,(read(m,g.config)+0x1C)&0xFFFFFFFF,2)
def set_count(m,g,v):put(m,(read(m,g.config)+0x1C)&0xFFFFFFFF,v&65535,2)
def observation(m,g,args):return(args,read(m,g.config),get_count(m,g),read(m,g.slots),read(m,g.slots+4),read(m,g.limit))
def provider_effect(m,c,g,ordinal):
 if ordinal==1:
  if c.mode&1:set_count(m,g,c.changed)
  if c.mode&2:put(m,g.config,OTHER)
 else:
  if c.mode&8:set_count(m,g,c.changed^0xFFFF)
  if c.mode&4:put(m,g.slots,c.first_override&0xFFFFFFFF)

def fixture(c=Case(),g=Globals()):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)}
 for base in(RECORD,OTHER):m.update({base+i:(i*13+0x59)&255 for i in range(-16,64)})
 for base,size in((g.config,4),(g.slots,8),(g.limit,4)):
  m.update({(base+i)&0xFFFFFFFF:(i*7+0xA5)&255 for i in range(-16,size+16)})
 put(m,g.slots,0xA5A5A5A5);put(m,g.slots+4,0x5A5A5A5A);put(m,g.limit,0x12345678);put(m,OTHER+0x1C,(c.count*13+7)&65535,2)
 record=RECORD
 if 1<=c.layout<=6:record=(g.slots+(c.layout-1)*2 if c.layout<=4 else g.limit+(c.layout-5)*2)-0x1C
 elif c.layout==7:record=g.config-0x1C
 elif c.layout==8:record=g.config-0x1A
 put(m,g.config,record&0xFFFFFFFF)
 if c.layout<7:put(m,(record+0x1C)&0xFFFFFFFF,c.count&65535,2)
 else:
  value=read(m,g.config);old=get_count(m,g)
  if c.layout==7:new_value=(((old+400)&65535)<<16)|(value&65535)
  else:new_value=(value&0xFFFF0000)|((old+400)&65535)
  put(m,(new_value+0x1C)&0xFFFFFFFF,c.count&65535,2)
 return m

def reference(initial,c,g=Globals()):
 m=dict(initial);calls=[];observations=[]
 if get_count(m,g)==0:set_count(m,g,8000)
 set_count(m,g,get_count(m,g)+400)
 for ordinal,returned in((1,c.first),(2,c.second)):
  args=(get_count(m,g)*8,255,2,0);calls.append((g.allocator,args));observations.append(observation(m,g,args));provider_effect(m,c,g,ordinal)
  if ordinal==1:put(m,g.slots,returned&0xFFFFFFFF)
  else:
   first=read(m,g.slots);put(m,g.slots+4,returned&0xFFFFFFFF);gap=signed((returned-first)&0xFFFFFFFF);put(m,g.limit,((gap>>3)-400)&0xFFFFFFFF)
 return m,calls,observations

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
class Oracle(RayOracle):
 def __init__(self,words,memory,c=Case(),g=Globals(),entry=source.ENTRY,connected=None):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(0x12345678,0x87654321,0xDEADBEEF,0xFEEDBEEF),connected=connected);self.case,self.globals=c,g;self.trace=[];self.allocations=0;self.snapshots=[]
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  if target==self.globals.allocator:
   args=self.arguments(4);self.allocations+=1;assert self.allocations<=2;self.snapshots.append(observation(self.memory,self.globals,args))
  elif target==source.HEAP:args=self.arguments(5)
  else:assert target==source.ENTRY;args=()
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target in(self.globals.allocator,source.HEAP)
  if target==source.HEAP:self.assert_heap_arguments()
  provider_effect(self.memory,self.case,self.globals,self.allocations)
  for i in range(5 if target==source.HEAP else 4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=(self.case.first if self.allocations==1 else self.case.second)&0xFFFFFFFF
 def assert_heap_arguments(self):
  args=self.calls[-1][1];assert args[1:]==(255,2,0,0),args

class WindowEnd(Exception):pass
class WindowCode(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc==self.owner.window_end:raise WindowEnd(pc)
  return super().__getitem__(pc)

def controls():
 b=source.SELECTED;field='*(u16 *)((u8 *)D_800B0DF0 + 0x1C)';call='allocate_memory('+field+' << 3, 255, 2, 0)'
 cached=b.replace('void func_15015E80(void) {','void func_15015E80(void) {\n    s32 bytes;').replace('    D_800BE9C8[0] =','    bytes = '+field+' << 3;\n    D_800BE9C8[0] =',1).replace(call,'allocate_memory(bytes, 255, 2, 0)')
 first=b.replace('void func_15015E80(void) {','void func_15015E80(void) {\n    s32 captured;').replace('    D_800BE9C8[1] =','    captured = D_800BE9C8[0];\n    D_800BE9C8[1] =',1).replace('(u32)D_800BE9C8[0])','(u32)captured)')
 return dict(no_default=b.replace('if ('+field+' == 0)','if (0)'),wrong_default=b.replace('= 8000;','= 8001;'),wrong_increment=b.replace('+= 400;','+= 399;'),wrong_size=b.replace(field+' << 3',field+' << 2'),wrong_arg1=b.replace(', 255, 2, 0)',', 254, 2, 0)'),wrong_arg2=b.replace(', 255, 2, 0)',', 255, 1, 0)'),wrong_arg3=b.replace(', 255, 2, 0)',', 255, 2, 1)'),cached_count=cached,cached_first=first,unsigned_gap=b.replace('((s32)((u32)D_800BE9C8[1]','((u32)((u32)D_800BE9C8[1]'),truncated_gap=b.replace(') >> 3) - 400',') / 8) - 400'),wrong_margin=b.replace(') - 400;',') - 399;'),check_null=b.replace('    D_800BE9C8[1] =','    if (D_800BE9C8[0] == 0) return;\n    D_800BE9C8[1] =',1),signed_count=b.replace(field+' << 3','(s32)*(s16 *)((u8 *)D_800B0DF0 + 0x1C) * 8'))

def native_harness():
 code=source.HEADERS+r'''
#include "structs.h"
typedef struct {u8 pad[0x1C];u16 count;u16 tail;}CountRecord;
typedef struct {u32 left[4];CountRecord records[2];s32 slots[2],limit;u32 config;u32 right[4];}World;
typedef struct {s32 a[4];u32 config,count,slot0,slot1,limit;}Observation;
typedef char ABI[(sizeof(void*)==4&&sizeof(CountRecord)==32&&__builtin_offsetof(CountRecord,count)==0x1C)?1:-1];
static World actual,expected,*current;static Observation observed[2],wanted[2];static u32 ordinal,mode,changed,firstValue,secondValue,overrideFirst;
#define D_800B0DF0 ((struct104*)&current->records[current->config])
#define D_800BE9C8 (current->slots)
#define D_800BEBA4 (current->limit)
s32 allocate_memory(s32,s32,s32,s32);
static void effects(World*w,u32 n){if(n==1){if(mode&1)w->records[w->config].count=(u16)changed;if(mode&2)w->config=1;}else{if(mode&8)w->records[w->config].count=(u16)(changed^65535u);if(mode&4)w->slots[0]=(s32)overrideFirst;}}
static void snapshot(Observation*x,World*w,s32 a,s32 b,s32 c,s32 d){x->a[0]=a;x->a[1]=b;x->a[2]=c;x->a[3]=d;x->config=w->config;x->count=w->records[w->config].count;x->slot0=(u32)w->slots[0];x->slot1=(u32)w->slots[1];x->limit=(u32)w->limit;}
__attribute__((noinline)) s32 allocate_memory(s32 a,s32 b,s32 c,s32 d){u32 n=ordinal++;if(n>=2)return 0;snapshot(observed+n,current,a,b,c,d);effects(current,n+1);return(s32)(n?secondValue:firstValue);}
'''
 for name,body in dict(selected=source.SELECTED,**controls()).items():code+=body.replace(source.FUNCTION,'test_'+name)+'\n'
 code+=r'''
static void reference(World*w){u32 n,bytes,gap,magnitude;u16 value;s32 commands;value=w->records[w->config].count;if(!value)w->records[w->config].count=8000;value=w->records[w->config].count;w->records[w->config].count=(u16)(value+400u);
 for(n=0;n<2;n++){bytes=(u32)w->records[w->config].count*8u;snapshot(wanted+n,w,(s32)bytes,255,2,0);effects(w,n+1);if(!n)w->slots[0]=(s32)firstValue;else{gap=secondValue-(u32)w->slots[0];w->slots[1]=(s32)secondValue;if(gap&0x80000000u){magnitude=~gap+1u;commands=-(s32)((magnitude+7u)/8u);}else commands=(s32)(gap/8u);w->limit=commands-400;}}
}
typedef void(*Init)(void);
static int check(Init fn){static const u32 a[]={0x400000u,0,0,0xFFFFFFFCu,0x7FFFFFFCu,0x90001000u,0x400008u},b[]={0x500000u,0,0x80000000u,4,0x80000004u,0x80001000u,0x400001u},modes[]={0,1,2,4,15};u32 n,p,i,j;u8*x=(u8*)&actual,*y=(u8*)&expected;
 for(n=0;n<65536;n++)for(p=0;p<5;p++){
  for(i=0;i<sizeof(World);i++)x[i]=(u8)(i*13+n*7+p);
  actual.config=0;actual.records[0].count=(u16)n;actual.records[1].count=(u16)(n*13u+7u);actual.slots[0]=(s32)0xA5A5A5A5u;actual.slots[1]=0x5A5A5A5A;actual.limit=0x12345678;
  mode=modes[p];changed=(u16)(n*17u);firstValue=a[(n>>4)%7];secondValue=b[(n>>4)%7];overrideFirst=0x480000u+n*4u;for(i=0;i<sizeof(World);i++)y[i]=x[i];reference(&expected);current=&actual;ordinal=0;fn();
  if(ordinal!=2)return 1;for(i=0;i<sizeof(World);i++)if(x[i]!=y[i])return 1;
  for(i=0;i<2;i++){for(j=0;j<4;j++)if(observed[i].a[j]!=wanted[i].a[j])return 1;if(observed[i].config!=wanted[i].config||observed[i].count!=wanted[i].count||observed[i].slot0!=wanted[i].slot0||observed[i].slot1!=wanted[i].slot1||observed[i].limit!=wanted[i].limit)return 1;}
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,name in enumerate(controls()):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 return code+'return 0;}\n'+START

class DisplayListBufferAllocationTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',cls.rom,source.ROM));p=cls.fresh/'qualified-padded.o';p.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,p,source.OWNER);f=functions[source.FUNCTION];cls.words=list(struct.unpack_from('>47I',data,f['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,g=Globals()):
  initial=fixture(c,g);want,calls,obs=reference(initial,c,g);pair=[]
  for words in images or(self.truth,self.words):
   m=Oracle(words,initial,c,g,entry).run();self.assertEqual((public(m.memory),m.calls,m.snapshots),(public(want),calls,obs),c);self.assertEqual(m.r[29],STACK+c.phase);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def test_01_actual_owner_Make_canonical_types_and_original_ABI(self):
  self.assertEqual(self.words,self.truth);self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),1)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),0);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_43330.c.o.compact'),1)
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertNotIn('#pragma GLOBAL_ASM',(self.out/'proposed-owner.c').read_text());self.assertIn('void func_15015E80(void)',source.SELECTED)
  self.assertIn('extern struct104 *D_800B0DF0;',source.DECLARATIONS);self.assertIn('extern s32 D_800BE9C8[];',source.DECLARATIONS);self.assertIn('s32 allocate_memory(s32, s32, s32, s32);',source.DECLARATIONS);self.assertIn('s32 allocate_memory(s32 arg0, s32 arg1, s32 arg2, s32 arg3)',self.values['conker/src/init_3C40.c'].decode());self.assertIn('extern s32 D_800BE9C8[];',self.values['conker/src/game_476D0.c'].decode())
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);jump=0x08000000|(source.ENTRY>>2&0x3FFFFFF);self.assertEqual([i*4 for i,w in enumerate(ws)if w in(jal,jump)],[0x3521C]);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual(self.rom[source.ROM+188:source.ROM+192],bytes(4))
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(body_words=47,slot_words=48,alignment_words=1,frame=24,bindings=12,guards=0,compact_functions=1,neighbors=0,GLOBAL_ASM_routines=0,Make_commands=3,diagnostics=0,canonical_struct104_pointer_s32_address_slots_and_s32_allocator_ABI=True,void_no_parameter_initializer=True)
 def test_02_guest_live_counts_provider_mutations_wrapped_gaps_and_aliases(self):
  count=0;visits=set()
  for value,pair,mode,layout in itertools.product(COUNTS,RETURNS,range(16),range(9)):
   m=self.compare(Case(value,*pair,mode,layout=layout,phase=(layout&1)*8));visits.update(m.visits);count+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+188,4)));self.receipt['guest']=dict(cases=count,visited_body_words=len(visits),all47_body_words_and_padding_retained=True,nine_count_pointer_slot_limit_alias_layouts=True,provider_redirect_count_and_first_slot_mutations=True,zero_and_wrapped16_count_and_wrapped32_gap_boundaries=True,nullable_allocator_results_unchecked=True,complete_private_state_trace_and_independent_public_call_reference=True)
 def test_03_native32_all_count_encodings_and_effective_controls(self):
  self.assertTrue(all(b!=source.SELECTED for b in controls().values()))
  for opt in('-O0','-O2','-O3'):
   p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=60).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=65536*5,effective_controls=len(controls()),all65536_count_encodings=True,typed_count_record_and_s32_slot_storage=True,valid_provider_mutations_and_defined_wrapped_address_math=True,whole_storage_fences_and_call_observations=True,trapping_UBSan=True,guest_only_pointer_halfword_aliases=True,no_full_heap_service_claim=True)
 def test_04_original_caller_and_retained_allocator_wrapper_chain(self):
  entry=0x15007D6C;parent=list(struct.unpack_from('>4I',self.rom,0x3521C));self.assertEqual(parent,[0x0D4057A0,0,0x0D4058AC,0]);asm=self.values['conker/asm/nonmatchings/game_34F20/func_15007B3C.s'].decode();literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',asm)};self.assertEqual(parent,[literal[entry+i*4]for i in range(4)]);helper=self.rom[0x3C40:0x3C6C];before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,source.ALLOCATOR,44);self.assertEqual(before[at:at+44],helper);hw=list(struct.unpack('>11I',helper));self.assertEqual(hw[0],0x27BDFFE0);self.assertEqual(hw[6],0xAFAE0010);count=0
  for value,mode,pair in itertools.product(COUNTS,(0,3,4,15),RETURNS):
   c=Case(value,*pair,mode);initial=fixture(c);want,calls,obs=reference(initial,c);expected=[(source.ENTRY,())]
   for target,args in calls:expected.extend(((target,args),(source.HEAP,(*args[:3],0,args[3]))))
   pair_runs=[]
   for words in(self.truth,self.words):
    connected={**{source.ENTRY+i*4:w for i,w in enumerate(words)},**{source.ALLOCATOR+i*4:w for i,w in enumerate(hw)}};m=Oracle(parent,initial,c,entry=entry,connected=connected);m.window_end=entry+8;m.code=WindowCode(dict(m.code),m)
    with self.assertRaises(WindowEnd)as caught:m.run()
    self.assertEqual(caught.exception.args,(entry+8,));self.assertEqual((public(m.memory),m.calls,m.snapshots),(public(want),expected,obs));self.assertEqual(m.r[29],STACK);pair_runs.append(m)
   self.assertEqual(complete(pair_runs[0]),complete(pair_runs[1]));self.assertEqual(pair_runs[0].trace,pair_runs[1].trace);count+=1
  self.assertIn('s32 func_15007B3C() {\n    return 0;\n}',self.values['conker/src/game_34F20.c'].decode());self.receipt['caller']=dict(original_window_words=4,connected_call_return_words=2,connected_cases=count,following_JAL_discards_initializer_result=True,retained_allocator_words=11,allocator_wrapper_frame=32,nested_initializer_wrapper_frame=56,inner_heap_args_are_original_first3_then_zero_then_original_fourth=True,current_parent_stub_unchanged=True,final_heap_provider_bounded_no_full_heap_claim=True)
 def test_05_fired_access_prefixes_and_zero_default_store_order(self):
  cuts=0
  for value,mode,layout in itertools.product((0,1,0xFE70,0xFFFF),(0,3,4,15),range(9)):
   c=Case(count=value,mode=mode,layout=layout);initial=fixture(c);good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=Oracle(words,initial,c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);cuts+=1
  for value,writes in((0,[8000,8400]),(1,[401]),(0xFE70,[0])):
   m=self.compare(Case(count=value));observed=[e[3]for e in m.trace if e[0]=='W'and e[1]==RECORD+0x1C];self.assertEqual(observed,writes)
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,complete_state_PC_delay_trace_equal=True,zero_default_then_advance_order=True,wrapped_zero_not_redefaulted=True,opaque_provider_GPR_FPR_HI_LO_and_outgoing_home_clobbers=True)
 def test_06_actual_padder_raw_controls_and_three_independent_GNU_layouts(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));self.assertEqual(len(raw),188);self.assertEqual(len(rs),12);bad=bytearray(raw);bad[100]^=1
  for data,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,{**rs,80:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.checked_payload(data,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
  for j,(entry,g)in enumerate(((source.ENTRY,Globals()),(0x17007FFC,Globals(0x800A7FFC,0x800B8004,0x800CFFFC,0x17012340)),(0x2500FFFC,Globals(0x800A8004,0x800BFFFC,0x800C8004,0x25123400)))):
   images=[]
   for k,obj in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o')):
    p=self.fresh/('layout-%d-%d.ld'%(j,k));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);symbols=dict(D_800B0DF0=g.config,D_800BE9C8=g.slots,D_800BEBA4=g.limit,allocate_memory=g.allocator);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,check=True);images.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])))
   self.assertEqual(*images)
   for value,mode,layout in itertools.product((0,1,0xFE70,0xFFFF),(0,3,4,15),(0,1,7,8)):
    self.compare(Case(count=value,mode=mode,layout=layout),images,entry,g);cases+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=cases,twelve_HI_LO_J26_bindings=True,signed_low_half_carry_and_negative_gap_cases=True,raw_binding_controls=3,actual_padder_equal=True,guards=0)
 def test_07_actual_IDO_cached_count_first_slot_and_gap_rounding_controls(self):
  probes=(('cached_count',Case(mode=1),('second_size',136,67200)),('cached_first',Case(mode=4),('limit',65136,130672)),('truncated_gap',Case(first=0x400008,second=0x400001),('limit',-401,-400)))
  for name,c,expected in probes:
   body=controls()[name];self.assertNotEqual(body,source.SELECTED);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);data,functions=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=functions[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));initial=fixture(c);want,calls,obs=reference(initial,c);m=Oracle(words,initial,c).run()
   if expected[0]=='second_size':self.assertEqual((calls[1][1][0],m.calls[1][1][0]),expected[1:])
   else:self.assertEqual((signed(read(want,source.LIMIT)),signed(read(m.memory,source.LIMIT))),expected[1:])
   self.assertNotEqual((public(m.memory),m.calls,m.snapshots),(public(want),calls,obs))
  self.receipt['compiled_controls']=dict(actual_IDO_controls=3,cached_count_second_size136_vs67200=True,cached_first_limit65136_vs130672=True,negative_gap_floor_minus401_vs_trunc_minus400=True,all_fail_by_values_or_call_arguments_in_mapped_memory=True)
 def test_08_strict_entire_image_body_extent_and_effective_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+188,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(x!=y for x,y in zip(before,expected)),149);self.receipt['image']=dict(changed_bytes=149,code_bytes=148,size_bytes=1,body188_slot192=True,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,guard_manifest_headers_allocator_wrapper_and_parent_unchanged=True)
