"""Direct C distance handle: original routes, floating ABI and literal image."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_distance_effect_handle_match as source
from tools.tests import game_distance_effect_handle_oracle as oracle
from tools.tests.game_distance_effect_handle_oracle import Case,HandleOracle,fixture,reference,public
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 return dict(unsigned_distance=b.replace('(f32)func_150AD9A0','(f32)(u32)func_150AD9A0'),
  unsigned_duration=b.replace('/ (f32)duration','/ (f32)(u32)duration'),
  reverse_step=b.replace('kind, step,','kind, -step,'),
  coordinate=b.replace('(x, y, z, targetX, targetY, targetZ,','(x, y, z, targetY, targetX, targetZ,'),
  kind=b.replace('kind, step,','(u8)kind, step,'),
  extra=b.replace('step, 0, 0.0f','step, 1, 0.0f'),
  float_extra=b.replace('0.0f, 0.0f, 0.0f, 0,','0.0f, 1.0f, 0.0f, 0,'),
  sentinel=b.replace('0, -99)','0, -98)'),
  signed_slot=b.replace('effect[0x48] + 1','(s8)effect[0x48] + 1'),
  wrong_slot=b.replace('effect[0x48]','effect[0x49]'),
  zero_based=b.replace('effect[0x48] + 1','effect[0x48]'))

def cases():
 result=[Case(slot=i,outcome=o,phase=(i%2)*8)for i,o in itertools.product(range(256),range(2))]
 nums=(0,1,-1,16777217,-16777217,2147483647,-2147483648)
 for d,t in itertools.product(nums,nums):result.append(Case(distance=d,values=(2147483647,-2147483648,-3,-1,1,2147483647,0x12340081,t)))
 for i in range(8):
  for v in nums:
   a=list(Case().values);a[i]=v;result.append(Case(values=tuple(a),slot=255))
 return result

def native_harness():
 t=source.HEADERS+'\n'.join(b.replace(source.FUNCTION,'test_'+n)for n,b in dict(selected=source.SELECTED,**controls()).items())
 rows=[]
 for c in cases():
  a=oracle.args(c);diff=[oracle.u32(a[i]-a[i+3])for i in range(3)]
  rows.append('{{%s},{%s},0x%Xu,0x%Xu,%d,%d}'%(','.join('0x%Xu'%v for v in a),','.join('0x%Xu'%v for v in diff),oracle.u32(c.distance),oracle.ratio(c.distance,a[7]),c.slot,c.outcome))
 t+='''
typedef s32(*Fn)(s32,s32,s32,s32,s32,s32,s32,s32);
typedef struct {u32 a[8],diff[3],distance,step;int slot,outcome;} Case;
static const Case cases[]={'''+','.join(rows)+'''};
static const Case *c;static int calls,bad;static u8 object[160];
static int same_float(u32 a,u32 b){return a==b||((a&0x7FFFFFFF)>0x7F800000&&(b&0x7FFFFFFF)>0x7F800000);}
s32 func_150AD9A0(s32 x,s32 y,s32 z){
 if(calls++!=0||(u32)x!=c->diff[0]||(u32)y!=c->diff[1]||(u32)z!=c->diff[2])bad=1;
 return (s32)c->distance;
}
s32 func_150E3020(s32 x,s32 y,s32 z,s32 tx,s32 ty,s32 tz,s32 kind,f32 step,s32 e,f32 f,f32 g,f32 h,s32 i,s16 j){
 union {f32 f;u32 u;} v;v.f=step;
 if(calls++!=1||(u32)x!=c->a[0]||(u32)y!=c->a[1]||(u32)z!=c->a[2]||(u32)tx!=c->a[3]||
  (u32)ty!=c->a[4]||(u32)tz!=c->a[5]||(u32)kind!=c->a[6]||!same_float(v.u,c->step)||e||i||j!=-99)bad=2;
 v.f=f;if(v.u)bad=3;v.f=g;if(v.u)bad=4;v.f=h;if(v.u)bad=5;
 return c->outcome?(s32)(object+16):0;
}
static int check(Fn fn){u32 k,j;s32 result;
 for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){
  c=cases+k;for(j=0;j<sizeof(object);j++)object[j]=(u8)(j*13+0xA5);
  object[16+0x48]=(u8)c->slot;calls=bad=0;
  result=fn((s32)c->a[0],(s32)c->a[1],(s32)c->a[2],(s32)c->a[3],(s32)c->a[4],(s32)c->a[5],(s32)c->a[6],(s32)c->a[7]);
  if(bad||calls!=2||result!=(c->outcome?c->slot+1:0))return 1;
  for(j=0;j<sizeof(object);j++)if(object[j]!=(j==16+0x48?(u8)c->slot:(u8)(j*13+0xA5)))return 2;
 }return 0;
}
static int run(void){if(check(test_selected))return 10;
'''
 for i,n in enumerate(controls()):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class DistanceEffectHandleTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>50I',cls.rom,source.ROM));cls.words=cls.linked(cls.out/'qualified-padded.o',source.ENTRY,'qualified');cls.raw=cls.linked(cls.out/'selected.o',source.ENTRY,'selected')
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 @classmethod
 def linked(cls,obj,entry,label,s=None):
  defs=oracle.symbols()if s is None else s;text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION];assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,defs);assert not unknown;p=cls.fresh/label
  p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
  return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
 def compare(self,c=Case(),images=None,entry=None,s=None,connected=False):
  initial=fixture(c,s,self.rom if connected else None);wanted=reference(initial,c,s,connected);pair=[];code=oracle.helper_code(self.rom)if connected else None
  for words in images or(self.truth,self.words,self.raw):
   m=HandleOracle(words,initial,c,entry=entry,s=s,connected=code).run();self.assertEqual((public(m.memory),m.calls,m.r[2]),(public(wanted[0]),wanted[1],wanted[2]),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0]
 def test_01_owner_Make_and_binding_contract(self):
  self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/'original-func_150E3208.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),13)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),12);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertFalse(source.NEW_GUARDS)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertEqual([i*4 for i,w in enumerate(ws)if w==jal],[0xCAA40]);self.assertNotIn(source.ENTRY,ws)
  before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,oracle.DISTANCE,128);self.assertEqual(before[at:at+128],self.rom[0xDAE50:0xDAED0])
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(body_words=50,frame=64,bindings=2,guards=0,neighbors=12,compact_functions=13,Make_commands=3,eight_s32_arguments=True,provider_C_still_placeholder=True,original_distance_GLOBAL_ASM_retained=True)
 def test_02_guest_width_float_and_late_homes(self):
  vectors=cases()+[replace(Case(),mutation=1,phase=p)for p in(0,8)];visited=set()
  for c in vectors:visited.update(self.compare(c).visits)
  self.assertEqual(len(visited),50);self.receipt['guest']=dict(cases=len(vectors),covered_words=50,all_output_byte_lanes=True,wrapping_input_differences=True,late_home_mutations=2,masked_IEEE_default_rounding=True,FCSR_or_hardware_claimed=False)
 def test_03_original_helpers_caller_and_traps(self):
  vectors=[]
  for xyz in itertools.permutations((17,31,65)):
   for signs in itertools.product((-1,1),repeat=3):vectors.append(Case(values=tuple(v*s for v,s in zip(xyz,signs))+(0,0,0,129,3)))
  vectors.extend(Case(occupied=n,outcome=o)for n,o in itertools.product(range(256),range(2)))
  vectors.extend(Case(values=xyz+(0,0,0,0,7))for xyz in((0,0,0),(700000000,500000000,1),(3,3,3)))
  visited=set()
  for c in vectors:visited.update(self.compare(c,connected=True).visits)
  count=0
  for connected,occupied,outcome in itertools.product(range(2),(0,1,7,31,127,255),range(2)):
   c=Case(occupied=occupied,outcome=outcome);pair=[]
   for words in(self.truth,self.words):
    m,initial=oracle.caller_machine(self.rom,words,c,bool(connected))
    with self.assertRaises(oracle.WindowBoundary):m.run()
    expected,calls,value=reference(initial,c,connected=bool(connected))
    self.assertEqual((public(m.memory),m.calls),(public(expected),[(source.ENTRY,oracle.args(c))]+calls));self.assertEqual(oracle.read(m.memory,oracle.STACK+c.phase+0xC4),((value<<6)|0xE004)if value else 0);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
  traps=[]
  for xyz in((-2147483648,0,0),(0,-2147483648,0),(0,0,-2147483648),(2147483647,4,4),(2147483640,32,0)):
   c=Case(values=xyz+(0,0,0,0,1));pair=[]
   with self.assertRaises(oracle.ArithmeticOverflow):oracle.distance_reference(xyz)
   for words in(self.truth,self.words):
    m=HandleOracle(words,fixture(c),c,connected=oracle.helper_code(self.rom))
    with self.assertRaises(oracle.ArithmeticOverflow):m.run()
    self.assertEqual(len(m.calls),1);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));traps.append(dict(pc=pair[0].current_pc,delay=pair[0].delay_of))
  coverage=[sum(pc in visited for pc in range(entry,entry+n*4,4))for entry,_,n in oracle.HELPERS]
  self.assertEqual(coverage,[32,118]);self.receipt['integration']=dict(connected_cases=len(vectors),caller_cases=count,caller_words=19,helper_coverage=coverage,unreachable_factory_words=['0x150E3184','0x150E31A4','0x150E31C4','0x150E31E4'],overflow_cuts=traps,trapping_state_scope='registers RAM PC delay prefix; no CP0 exception entry',allocator_bounded=True,complete_parent_or_gameplay_claimed=False)
 def test_04_native32_SDK_and_semantic_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());logs={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);built=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=built.stderr)
  self.receipt['native']=dict(optimizations=logs,cases_per_profile=len(cases()),controls=len(controls()),SDK=True,pointers32=True,trapping_UBSan=True,NaN_classification_not_payload=True,provider_bounded=True,valid_backing_and_canaries=True)
 def test_05_direct_and_caller_fault_prefixes(self):
  count=delay=0
  for outcome,connected,parent in itertools.product(range(2),range(2),range(2)):
   c=Case(outcome=outcome,occupied=127)
   def machine(words):return oracle.caller_machine(self.rom,words,c,bool(connected))[0]if parent else HandleOracle(words,fixture(c),c,connected=oracle.helper_code(self.rom)if connected else None)
   full=machine(self.truth)
   if parent:
    with self.assertRaises(oracle.WindowBoundary):full.run()
   else:full.run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=machine(words);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(pair[1].current_pc,pair[1].delay_of,cut));count+=1;delay+=pair[0].delay_of is not None
  self.receipt['faults']=dict(prefix_pairs=count,delay_slot_cuts=delay,complete_state_PC_trace=True,portable_C_fault_claimed=False)
 def test_06_rejections_padder_and_three_GNU_layouts(self):
  raw,rs=source.payload(self.out/'selected.o');rejects=0
  for at in range(0,len(raw),4):
   bad=bytearray(raw);bad[at+3]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   rejects+=1
  for at in rs:
   bad=dict(rs);bad[at]=[(rs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):source.checked_payload(raw,bad)
   rejects+=1
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   s=oracle.symbols()
   if j:s.update(func_150AD9A0=entry+0x10000,func_150E3020=entry+0x20000)
   paths=(self.out/'original-func_150E3208.o',self.out/'make-shadow/src/game/generated_1104D0.c.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for slot,outcome,phase in itertools.product((0,127,128,255),range(2),(0,8)):self.compare(Case(slot=slot,outcome=outcome,phase=phase),images,entry,s);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,all_three_objects_linked=True,no_guards=True)
 def test_07_compiled_semantic_negatives(self):
  evidence={}
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name)
   for c in(Case(),Case(distance=-17),Case(values=(3,-8,5,-7,2,-4,0x12340081,-3))):
    initial=fixture(c);m=HandleOracle(words,initial,c).run();wanted=reference(initial,c)
    if(public(m.memory),m.calls,m.r[2])!=(public(wanted[0]),wanted[1],wanted[2]):evidence[name]=dict(distance=c.distance,duration=c.values[7]);break
   self.assertIn(name,evidence)
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,private_stack_excluded=True)
 def test_08_strict_whole_image_and_inputs(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+200];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,200);named={n:(p,f,loc)for p,n,f,loc in source.symbol_rows(before)}
  positions=[20,at,at+200,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.DISTANCE,128),source.elf_slot_offset(before,oracle.FACTORY,488),named['D_800D99D0'][0]+4]
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),158)
  self.receipt['image']=dict(changed_bytes=158,code_bytes=157,extent_bytes=1,metadata_bytes=0,exclusions=0,corruptions=len(positions)+1,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v))
