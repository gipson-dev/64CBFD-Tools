"""Actor action dispatch: signed bounds, live state, lazy context and original interpreter ABI."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_actor_action_dispatch_match as source
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
ROOT=Path(__file__).resolve().parents[2];RECORD,OTHER,ACTOR,CONTEXT,OTHER_CONTEXT=0x20000,0x60000,0x30000,0x32000,0x34000
VALUES=(-0x80000000,-1,0,1,7,127,254,255,256,0x7FFFFFFF)
@dataclass(frozen=True)
class Case:
 index:int=1
 count:int=8
 mode:int=2
 flag:int=0
 found:bool=True
 mutation:int=0
 layout:int=0
 home:int=0
 phase:int=0
 unmapped:bool=False
@dataclass(frozen=True)
class Globals:
 records:int=source.RECORDS
 count:int=source.COUNT
 mode:int=source.MODE
 lookup:int=source.LOOKUP
 action:int=source.ACTION
 alternate:int=source.ALTERNATE

def entered(c):return STACK+c.phase
def effective_index(c):return 0 if c.home&1 else c.index
def effective_context(c):return OTHER_CONTEXT if c.home&2 else CONTEXT
def record_address(c,g,sp):
 index=effective_index(c);target=None
 if 1<=c.layout<=4:target=g.mode+c.layout-1
 elif 5<=c.layout<=8:target=effective_context(c)+4+c.layout-5
 elif c.layout==9:target=sp
 elif c.layout==10:target=sp+4
 elif c.layout==11:target=g.count
 elif c.layout==12:target=g.records+3
 return ((target-2-index*48)&0xFFFFFFFF)if target is not None else RECORD

def fixture(c=Case(),g=Globals(),target_sp=None):
 sp=entered(c)if target_sp is None else target_sp;m={entered(c)+i:(i*17+0xA5)&255 for i in range(-1024,512)}
 if c.unmapped:return m
 for base,size in((g.records,4),(g.mode,4),(g.count,1),(CONTEXT,12),(OTHER_CONTEXT,12)):
  m.update({(base+i)&0xFFFFFFFF:(i*13+0x59)&255 for i in range(-8,size+8)})
 put(m,CONTEXT,0x2000|(c.index&0xFFFFFFFF));put(m,CONTEXT+4,c.flag&0xFFFFFFFF);put(m,OTHER_CONTEXT,0x2000);put(m,OTHER_CONTEXT+4,(c.flag^1)&0xFFFFFFFF);put(m,g.mode,c.mode&0xFFFFFFFF);put(m,g.count,c.count&255,1)
 base=record_address(c,g,sp);put(m,g.records,base)
 for ptr in(base,OTHER):
  at=(ptr+effective_index(c)*48+2)&0xFFFFFFFF
  if c.layout==0 or ptr==OTHER:
   for i in range(-2,6):m[(at+i)&0xFFFFFFFF]=(i*7+0xA5)&255
 # A state store through the saved context-pointer high byte redirects only the guest view.
 for ptr in(CONTEXT,OTHER_CONTEXT):
  redirected=ptr|0x01000000
  for i in range(8):m[redirected+i]=(i*11+0x37)&255
  put(m,redirected+4,(c.flag^1)&0xFFFFFFFF)
 return m

def context_pointer(c):return 0 if c.unmapped else CONTEXT
def provider_effect(m,c,g,sp):
 if c.home&1:put(m,sp,0)
 if c.home&2:put(m,sp+4,OTHER_CONTEXT)
 if c.mutation&1:put(m,g.count,read(m,g.count,1)^255,1)
 if c.mutation&2:put(m,g.mode,3 if read(m,g.mode)==2 else 2)
 if c.mutation&4:put(m,CONTEXT+4,read(m,CONTEXT+4)^1)
 if c.mutation&8:put(m,g.records,OTHER)

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
def reference(initial,c,g=Globals(),target_sp=None,actor=ACTOR):
 sp=entered(c)if target_sp is None else target_sp;m=dict(initial);put(m,sp+4,context_pointer(c));put(m,sp,c.index&0xFFFFFFFF);calls=[(g.lookup,(c.index&0xFFFFFFFF,))];provider_effect(m,c,g,sp)
 for i in range(4):put(m,sp-24+4*i,0xB5000000+i)
 if not c.found:return m,calls,0
 index=signed(read(m,sp))
 if index<read(m,g.count,1):put(m,(read(m,g.records)+index*48+2)&0xFFFFFFFF,1,1)
 mode=read(m,g.mode);context=read(m,sp+4)
 if mode==2 and read(m,(context+4)&0xFFFFFFFF)!=0:calls.append((g.alternate,(actor,)))
 else:calls.append((g.action,(actor,0)))
 return m,calls,999999
class Oracle(RayOracle):
 def __init__(self,words,memory,c=Case(),g=Globals(),entry=source.ENTRY,connected=None,arguments=None,actor=ACTOR):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=arguments or(c.index&0xFFFFFFFF,context_pointer(c)),connected=connected);self.case,self.globals,self.actor=c,g,actor;self.trace=[];self.target_entered=entered(c)
 def get(self,address,size):
  v=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,v))
  return v
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
 def record_call(self,target):
  sizes={source.ENTRY:2,self.globals.lookup:1,self.globals.action:2,self.globals.alternate:1};assert target in sizes,hex(target);args=self.arguments(sizes[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==source.ENTRY:self.target_entered=self.r[29]
 def hook(self,target):
  c,g=self.case,self.globals
  if target==g.lookup:provider_effect(self.memory,c,g,self.target_entered)
  else:assert target in(g.action,g.alternate)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=(self.actor if c.found else 0)if target==g.lookup else 0xDEAD1234
class WindowEnd(Exception):pass
class WindowCode(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc==0x150AE188:raise WindowEnd(pc)
  return super().__getitem__(pc)

def controls():
 b=source.SELECTED
 cached=b.replace('    struct127 *actor =','    s32 captured;\n    struct127 *actor =').replace('    if (index < D_800D2100)', '    captured = D_800D3840;\n    if (index < D_800D2100)').replace('if (D_800D3840 == 2)','if (captured == 2)')
 return dict(unsigned_bound=b.replace('index < D_800D2100','(u32)index < D_800D2100'),lower_bound=b.replace('index < D_800D2100','index >= 0 && index < D_800D2100'),inclusive_bound=b.replace('index < D_800D2100','index <= D_800D2100'),wrong_state=b.replace('.state = 1','.state = 2'),wrong_index=b.replace('[index].state','[index + 1].state'),wrong_offset=b.replace('[index].state','[index].reserved0[0]'),narrow_mode=b.replace('D_800D3840 == 2','(u8)D_800D3840 == 2'),broad_mode=b.replace('D_800D3840 == 2','D_800D3840 >= 2'),flag_one=b.replace('context[1] == 0','context[1] != 1'),wrong_context=b.replace('context[1]','context[0]'),wrong_action_arg=b.replace('func_15060F28(actor, 0)','func_15060F28(actor, 1)'),wrong_null=b.replace('return 0;','return 999999;'),wrong_result=b.replace('return 999999;','return 999998;'),cached_mode=cached)

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(SpawnLookupRecord)==48&&__builtin_offsetof(SpawnLookupRecord,state)==2)?1:-1];
static struct{u32 pre[4];SpawnLookupRecord pool[544];u32 post[4];}storage;
SpawnLookupRecord*D_800D20FC;u8 D_800D2100;s32 D_800D3840;static struct127 actor;static s32 context[2];
static s32 originalIndex,wantedIndex,wantedMode,wantedFlag,found,mutation,calls,bad,kind;static u32 wantedCount,wantedBase,written;static s32 returned;
static void reset_padding(void){u8*p=(u8*)&storage;u32 i;for(i=0;i<sizeof(storage);i++)p[i]=0xA5;}
__attribute__((noinline)) struct127*func_1505EEF4(s32 index){
 if(calls++!=0||index!=originalIndex)bad=1;
 if(mutation&1)D_800D2100^=255;
 if(mutation&2)D_800D3840=D_800D3840==2?3:2;
 if(mutation&4)context[1]^=1;
 if(mutation&8)D_800D20FC=&storage.pool[32];
 return found?&actor:0;
}
__attribute__((noinline)) void func_15060F28(struct127*p,s32 argument){if(calls++!=1||p!=&actor||argument!=0||kind!=1)bad=1;}
__attribute__((noinline)) s32 func_15053430(struct127*p){if(calls++!=1||p!=&actor||kind!=2)bad=1;return -1234567;}
'''
 for name,body in{'selected':source.SELECTED,**controls()}.items():t+=body.replace(source.FUNCTION,source.FUNCTION+'_'+name)+'\n'
 t+=r'''
static s32 execute_case(s32(*fn)(s32,s32*),s32 index,u32 count,s32 mode,s32 flag,s32 active,s32 effects){
 u32 i,j,expectedSlot;u8 value;originalIndex=index;found=active;mutation=effects;calls=bad=0;
 for(i=0;i<544;i++)storage.pool[i].state=0xA5;
 D_800D20FC=&storage.pool[16];D_800D2100=(u8)count;D_800D3840=mode;context[0]=0x2000|index;context[1]=flag;
 wantedIndex=index;wantedCount=(effects&1)?(count^255):count;wantedMode=(effects&2)?(mode==2?3:2):mode;wantedFlag=(effects&4)?(flag^1):flag;wantedBase=(effects&8)?32:16;
 written=active&&index<(s32)wantedCount;expectedSlot=wantedBase+index;kind=active?(wantedMode==2&&wantedFlag!=0?2:1):0;
 returned=fn(index,context);
 if(bad||calls!=(active?2:1)||returned!=(active?999999:0)||D_800D20FC!=&storage.pool[wantedBase]||D_800D2100!=wantedCount||D_800D3840!=wantedMode||context[1]!=wantedFlag)return 1;
 for(i=0;i<544;i++){value=written&&i==expectedSlot?1:0xA5;if(storage.pool[i].state!=value)return 2;}
 if(active){const u8*p=(const u8*)&storage.pool[expectedSlot];for(j=0;j<48;j++){value=written&&j==2?1:0xA5;if(p[j]!=value)return 3;}}
 for(i=0;i<4;i++)if(storage.pre[i]!=0xA5A5A5A5||storage.post[i]!=0xA5A5A5A5)return 4;
 return 0;
}
int main(void){
 s32 indexes[8]={-16,-1,0,1,127,254,255,256},modes[4]={0,2,3,258},flags[4]={0,1,-1,(-2147483647-1)},effects[6]={0,1,2,4,8,15};u32 i,c,m,f,e,n=0;
 reset_padding();
 for(i=0;i<65536;i++){if(execute_case(func_150979CC_selected,(s16)i,8,2,0,0,0))return 10;n++;}
 for(i=0;i<8;i++)for(c=0;c<256;c++)for(m=0;m<4;m++)for(f=0;f<4;f++)for(e=0;e<6;e++){if(execute_case(func_150979CC_selected,indexes[i],c,modes[m],flags[f],1,effects[e]))return 11;n++;}
 if(n!=262144)return 12;
'''
 # reset every negative-control family so previous wrong writes cannot qualify the next control.
 for number,name in enumerate(n for n in controls()if n!='cached_mode'):
  t+=' {s32 fired=0;reset_padding();for(i=0;i<8&&!fired;i++)for(c=0;c<256&&!fired;c++)for(m=0;m<4&&!fired;m++)for(f=0;f<4&&!fired;f++){fired=execute_case(func_150979CC_'+name+',indexes[i],c,modes[m],flags[f],'+('0'if name=='wrong_null'else'1')+',0);}if(!fired)return '+str(30+number)+';}\n'
 return t+'return 0;}\n'+START.replace('run()','main()')

class ActorActionDispatchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));cls.installed=(ROOT/source.SOURCE).read_bytes()==(cls.out/'proposed-owner.c').read_bytes();cls.fresh=cls.out/('fresh-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=True);obj=cls.fresh/'selected-local.o';obj.write_bytes((cls.out/'selected.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,obj,source.OWNER);f=functions[source.FUNCTION];cls.words=list(struct.unpack_from('>48I',data,f['value']));cls.receipt={}
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,g=Globals()):
  initial=fixture(c,g);want,calls,result=reference(initial,c,g);runs=[Oracle(ws,initial,c,g,entry).run()for ws in((self.truth,self.words)if images is None else images)]
  for m in runs:self.assertEqual((public(m.memory),m.calls,m.r[2]),(public(want),calls,result));self.assertEqual(m.r[29],entered(c))
  self.assertEqual(complete(runs[0]),complete(runs[1]));self.assertEqual(runs[0].trace,runs[1].trace);return runs[1]
 def test_01_owner_Make_signature_existing_record_view_and_literal_registration(self):
  source.check_inputs(ROOT,self.out,self.installed);self.assertEqual(source.payload(self.out/'selected.o'),source.payload(self.out/'original-func_150979CC.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),3);self.assertEqual(source.same_functions(self.out/'before-padded.o',self.out/'qualified-padded.o',(source.FUNCTION,)),3);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_C4DC0.c.o.compact'),4);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertNotIn('#pragma GLOBAL_ASM',(self.out/'proposed-owner.c').read_text());self.assertIn('s32 func_150979CC(s32 index, s32 *context)',source.SELECTED)
  for name in('before-owner','after-owner','selected','actual-Make'):self.assertFalse((self.out/(name+'-diagnostics.txt')).read_bytes())
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);jump=0x08000000|(source.ENTRY>>2&0x3FFFFFF);self.assertFalse(any(w in(jal,jump)for w in ws));self.assertEqual([i*4 for i,w in enumerate(ws)if w==source.ENTRY],[0x22CF20]);self.assertEqual(struct.unpack_from('>I',self.rom,0x22CF20)[0],source.ENTRY)
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=48,frame=24,bindings=10,guards=0,compact_functions=4,neighbors=3,GLOBAL_ASM=0,Make_commands=3,diagnostics=0,existing48byte_state2_view_and_canonical_actor_pointer=True,signed32_result_and_two_argument_callback=True)
 def test_02_guest_signed_bounds_live_homes_state_aliases_and_lazy_context(self):
  count=0;visits=set()
  for index,limit,mode,flag,found in itertools.product(VALUES,(0,1,127,255),(0,2,258),(0,0x80000000),(False,True)):
   c=Case(index,limit,mode,flag,found);m=self.compare(c);visits.update(m.visits);count+=1
  for layout,mutation,home,flag in itertools.product(range(13),(0,1,2,4,8,15),(0,1,2,3),(0,1)):
   self.compare(Case(mode=2,flag=flag,mutation=mutation,layout=layout,home=home,phase=(layout&1)*8));count+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4)));self.receipt['guest']=dict(cases=count,visited_body_words=len(visits),full_word_signed_index_and_mode_and_flag_boundaries=True,thirteen_state_mode_context_home_count_pointer_alias_layouts=True,opaque_provider_effects_and_incoming_home_probes=True,lazy_null_lookup_and_nonmode2_context=True,complete_private_trace_and_independent_public_call_reference=True,wrapped_invalid_native_indices_guest_only=True)
 def test_03_native32_all_count_bytes_and_null_signed16_indices_with_effective_controls(self):
  for opt in('-O0','-O2','-O3'):
   p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=90).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=262144,effective_controls=len(controls())-1,all256_counts_and_all65536_null_signed16_indices=True,negative_indices_valid_allocated_prefix=True,full_state_array_affected_padding_and_buffer_fences=True,trapping_UBSan=True,noinline_provider_mutations=True,guest_private_home_and_global_aliases_separate=True)
 def test_04_original_interpreter_window_and_retained_lookup_connected(self):
  caller=list(struct.unpack('>35I',(self.out/'original-caller-window.bin').read_bytes()));lookup=list(struct.unpack('>55I',(self.out/'original-lookup.bin').read_bytes()));self.assertEqual(caller[-3:],[0x02E0F825,0x03E00008,0x27BD0010]);self.assertEqual((self.out/'original-caller-window.bin').read_bytes(),self.rom[0xDB5B8:0xDB644]);self.assertEqual((self.out/'original-lookup.bin').read_bytes(),self.rom[0x8C3A4:0x8C480]);table=self.rom[0x22CF1C:0x22CF58];self.assertEqual(len(table),60);self.assertEqual(struct.unpack_from('>I',table,4)[0],source.ENTRY);count=0
  cases=itertools.chain(itertools.product((0,1,127,255),range(26),(0,2,258),(0,1)),itertools.product((0x12340001,-0x7FFFFFFF),(25,),(0,2,258),(0,1)))
  for index,slot,mode,flag in cases:
   found=slot<25 and 0<=index<=255;c=Case(index,8,mode,flag,found);target_sp=entered(c)-16;initial=fixture(c,target_sp=target_sp)
   for i in range(15):put(initial,source.TABLE+i*4,struct.unpack_from('>I',table,i*4)[0])
   for i in range(26):put(initial,0x800CC2D0+i*0x32C,0);initial[0x800CC2D0+i*0x32C+0x13F]=(index+1)&255
   actor=0x800CC2D0+slot*0x32C if found else 0
   if found:put(initial,actor,1);initial[actor+0x13F]=index
   want,calls,result=reference(initial,c,target_sp=target_sp,actor=actor);expected=[(source.ENTRY,(index&0xFFFFFFFF,CONTEXT)),*calls];runs=[]
   for words in(self.truth,self.words):
    code={**{source.ENTRY+i*4:w for i,w in enumerate(words)},**{source.LOOKUP+i*4:w for i,w in enumerate(lookup)}};m=Oracle(caller,initial,c,entry=0x150AE108,connected=code,arguments=(CONTEXT,),actor=actor);m.code=WindowCode(dict(m.code),m)
    with self.assertRaises(WindowEnd)as caught:m.run()
    self.assertEqual(caught.exception.args,(0x150AE188,));self.assertEqual((public(m.memory),m.calls,m.r[2]),(public(want),expected,result));self.assertEqual(m.r[29],target_sp);runs.append(m)
   self.assertEqual(complete(runs[0]),complete(runs[1]));self.assertEqual(runs[0].trace,runs[1].trace);count+=1
  self.receipt['caller']=dict(original_window_words=35,checked_return_tail_words=3,stop_after_target_return_before_outer_owned_s7_tail=True,connected_cases=count,retained_lookup_words=55,all25_actor_slots_and_not_found=True,tag2_table_slot1_and_maskFFFF0FFF=True,return0_or999999_propagated=True,current_parent_and_all_helpers_remain_placeholders=True,no_full_interpreter_helper_C_or_gameplay_claim=True)
 def test_05_fired_access_prefixes_and_unmapped_lazy_paths(self):
  cuts=0
  for layout,mode,found,home in itertools.product((0,1,4,5,8,9,10,11,12),(0,2),(False,True),(0,3)):
   c=Case(mode=mode,found=found,layout=layout,home=home);initial=fixture(c);good=self.compare(c)
   for cut in range(good.root_accesses):
    runs=[]
    for words in(self.truth,self.words):
     m=Oracle(words,initial,c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);runs.append(m)
    self.assertEqual(complete(runs[0]),complete(runs[1]));self.assertEqual(runs[0].trace,runs[1].trace);cuts+=1
  m=self.compare(Case(found=False,unmapped=True));self.assertFalse(any(a[0]=='R'and a[1]in(source.COUNT,source.MODE,source.RECORDS)for a in m.trace))
  for words in(self.truth,self.words):
   c=Case(mode=0);initial=fixture(c);m=Oracle(words,initial,c);m.r[5]=0;m.before[5]=0;m.run();self.assertEqual(m.r[2],999999)
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,complete_private_PC_delay_trace_equal=True,null_lookup_needs_no_globals_or_context_mapping=True,mode_not2_accepts_null_context=True,guest_home_and_byte_alias_order_preserved=True)
 def test_06_actual_padder_raw_controls_and_three_independent_GNU_layouts(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[80]^=1
  for data,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,{**rs,12:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.checked_payload(data,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,(entry,g)in enumerate(((source.ENTRY,Globals()),(0x17007FFC,Globals(0x800C7FFC,0x800D8004,0x800EFFFC,0x17012340,0x17022340,0x17032340)),(0x2500FFFC,Globals(0x800C8004,0x800DFFFC,0x800E8004,0x25123400,0x25234500,0x25345600)))):
   images=[]
   for k,obj in enumerate((self.out/'original-func_150979CC.o',self.out/'selected.o')):
    script=self.fresh/('layout-%d-%d.ld'%(j,k));elf=script.with_suffix('.elf');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);symbols=dict(D_800D20FC=g.records,D_800D2100=g.count,D_800D3840=g.mode,func_1505EEF4=g.lookup,func_15060F28=g.action,func_15053430=g.alternate);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,check=True);images.append(list(struct.unpack_from('>48I',sections(elf)['.text'][1])))
   self.assertEqual(*images)
   for index,mode,layout in itertools.product((-1,0,255),(0,2),(0,4,8,10)):
    self.compare(Case(index=index,mode=mode,layout=layout),images,entry,g);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,ten_HI_LO_J26_bindings=True,signed_low_half_carries=True,raw_binding_controls=3,actual_padder_equal=True,guards=0)
 def test_07_actual_IDO_cached_mode_lower_bound_and_result_controls(self):
  for name,c in(('cached_mode',Case(layout=4,flag=1)),('lower_bound',Case(index=-1)),('wrong_result',Case(index=255))):
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+controls()[name],'negative-'+name);self.assertFalse(diag);data,functions=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=functions[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));initial=fixture(c);want,calls,result=reference(initial,c);m=Oracle(words,initial,c).run();self.assertNotEqual((public(m.memory),m.calls,m.r[2]),(public(want),calls,result),name)
  self.receipt['compiled_controls']=dict(actual_IDO_controls=3,cached_mode_state_alias_lower_bound_and_result=True,all_fail_by_mapped_values_or_call_arguments=True)
 def test_08_strict_complete_image_and_effective_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+192];actual=(self.out/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,_,_ in source.symbol_rows(before)if n==source.FUNCTION)
  for pos in(20,at,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol+8,source.elf_slot_offset(before,source.TABLE,4)):
   bad=bytearray(actual);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),145);self.receipt['image']=dict(changed_bytes=145,code_bytes=144,size_bytes=1,exclusions=0,effective_corruptions=6,all_named_definitions_checked=True,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088,parent_lookup_and_action_placeholders_unchanged=True)
