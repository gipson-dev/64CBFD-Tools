"""Direct C scene reset, callback ABI, original bounded helpers and strict image."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_scene_state_reset_match as source
from tools.tests import game_scene_state_reset_oracle as oracle
from tools.tests.game_scene_state_reset_oracle import Case,ResetOracle,fixture,reference,public
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
 return dict(default=b.replace('D_80087260 = 3','D_80087260 = 4'),mask=b.replace('& 0x200','& 0x400'),
  first_array=b.replace('D_80087270[0] = 0','D_80087270[1] = 0'),wide_word=b.replace('*(s8 *)&D_8008FD94 = 1','D_8008FD94 = 1'),
  unsigned_scene=b.replace('(6, D_800BE3DF,','(6, (u8)D_800BE3DF,'),signed_channel=b.replace(', D_800BE3E0, 0, 1)',', (s8)D_800BE3E0, 0, 1)'),
  command=b.replace('(6, D_800BE3DF,','(4, D_800BE3DF,'),fifth=b.replace('D_800BE3E0, 0, 1)','D_800BE3E0, 0, 0)'),
  half=b.replace('D_8008FDBC = 0','D_8008FDBC = 1'),post=b.replace('D_800E0B99 = 1','D_800E0B99 = 0'),
  early=b.replace('    D_800E0B99 = 1;\n','').replace('    func_1501C730(','    D_800E0B99 = 1;\n    func_1501C730('),
  omit_final=b.replace('    func_151E7EF8();',''))

def native_harness():
 t=source.HEADERS+'\n'.join(b.replace(source.FUNCTION,'test_'+n)for n,b in dict(selected=source.SELECTED,**controls()).items())
 t+='''
s8 D_80087260,D_8008FD8C,D_8008FD90,D_800BE3DF;
u8 D_80087270[8],D_800BE618,D_800D23A8,D_800E0B94,D_800D2E40,D_800BE3E0,D_800E0B99,D_800E0BB1;
s16 D_8008FDBC;s32 D_8008FD94;u32 D_800E9D00;
typedef void(*Fn)(void);
'''
 t+='static u8 *objects[]={'+','.join('(u8*)&'+n for n,w in oracle.FIELDS)+'};\n'
 t+='static const u32 widths[]={'+','.join(str(w)for n,w in oracle.FIELDS)+'};\n'
 t+=r'''
static u8 expected[15][8];static int calls,bad,mode,scene,channel;
static int compare(void){u32 i,j;for(i=0;i<15;i++)for(j=0;j<widths[i];j++)if(objects[i][j]!=expected[i][j])return 1;return 0;}
static void change(int final){
 if(final){if(mode&4){D_800E0B99^=2;D_800E0BB1^=4;expected[12][0]^=2;expected[13][0]^=4;}}
 else{
  if(mode&1){D_80087260^=1;((u8*)&D_8008FD94)[1]=0x55;D_800E0B99=0xAB;D_800E0BB1=0xCD;
   expected[0][0]^=1;expected[4][1]=0x55;expected[12][0]=0xAB;expected[13][0]=0xCD;}
  if(mode&2){D_800BE3DF^=0xFF;D_800BE3E0^=0xFF;expected[10][0]^=0xFF;expected[11][0]^=0xFF;}
 }
}
void func_1501C730(s32 a,s32 b,s32 c,s32 d,s32 e){
 if(calls++!=0||compare()||a!=6||b!=scene||c!=channel||d||e!=1)bad=1;
 change(0);expected[12][0]=expected[13][0]=1;
}
void func_151E7EF8(void){if(calls++!=1||compare())bad=2;change(1);}
static u32 masks[]={0,0x200,0xFFFFFDFF,0xFFFFFFFF};
static int check(Fn fn){u32 byte,field,flag,i,j;
 for(byte=0;byte<256;byte++)for(field=0;field<2;field++)for(flag=0;flag<4;flag++)for(mode=0;mode<8;mode++){
  for(i=0;i<15;i++)for(j=0;j<widths[i];j++)objects[i][j]=(u8)(i*17+j*13+byte);
  D_800BE3DF=(s8)(field?0x80:byte);D_800BE3E0=(u8)(field?byte:0xFE);D_800E9D00=masks[flag];
  for(i=0;i<15;i++)for(j=0;j<widths[i];j++)expected[i][j]=objects[i][j];
  scene=(((u8)D_800BE3DF)^128)-128;channel=D_800BE3E0;
  expected[0][0]=(masks[flag]&512)?51:3;expected[1][0]=expected[7][0]=expected[8][0]=expected[9][0]=0;
  expected[2][0]=expected[3][0]=expected[4][0]=expected[6][0]=1;expected[5][0]=expected[5][1]=0;
  calls=bad=0;fn();if(bad||calls!=2||compare())return 1;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,n in enumerate(controls()):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class SceneStateResetTests(unittest.TestCase):
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
   m=ResetOracle(words,initial,c,entry=entry,s=s,connected=code).run();self.assertEqual((public(m.memory),m.calls,m.snapshots),(public(wanted[0]),wanted[1],wanted[2]),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0]
 def test_01_owner_Make_callback_and_binding_contract(self):
  self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/'original-func_151E327C.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),60)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),59);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertFalse(source.NEW_GUARDS)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertFalse(any(w in(jal,source.ENTRY)for w in ws))
  image=self.values['conker/build/conker.us.elf']
  # Only the already-recovered integrity helpers are retail in the current image.
  for entry,off,n in oracle.HELPERS[1:]:
   at=source.elf_slot_offset(image,entry,n*4);self.assertEqual(image[at:at+n*4],self.rom[off:off+n*4])
  self.assertEqual(struct.unpack_from('>I',self.rom,0x23B478)[0],0x1501C784)
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(body_words=50,frame=32,bindings=32,guards=0,neighbors=59,compact_functions=60,Make_commands=3,callback_void_no_arguments=True,provider_C_still_placeholder=True)
 def test_02_guest_sign_width_and_effect_order(self):
  cases=[replace(Case(),**{field:i},effect=3)for field,i in itertools.product(('scene','channel'),range(256))]
  cases.extend(Case(flags=f,effect=e,phase=p,seed=f&255)for f,e,p in itertools.product((0,512,1024,0xFFFFFFFF,0xFFFFFDFF),range(8),(0,8)))
  cases.extend(Case(flags=1<<i)for i in range(32));visited=set()
  for c in cases:visited.update(self.compare(c).visits)
  self.assertEqual(len(visited),50);self.receipt['guest']=dict(cases=len(cases),covered_words=50,all_signed_and_unsigned_byte_lanes=True,partial_word_and_array_canaries=True,call_boundary_snapshots=True,void_return_not_interpreted=True)
 def test_03_original_helpers_registration_and_dispatch(self):
  count=0;visited=set()
  for selector,good,effect in itertools.product((0,2,128,255),range(2),(0,7)):
   m=self.compare(Case(selector=selector,checksum_good=bool(good),effect=effect),connected=True);visited.update(m.visits);count+=1
  registers=dispatches=0
  for flags in(0,16,32,0xFFFF):
   m,initial=oracle.register_machine(self.rom,flags=flags)
   with self.assertRaises(oracle.WindowBoundary):m.run()
   expected=dict(initial)
   if flags&16:
    for address,value,n in((oracle.SLOT,source.ENTRY,4),(0x800E0B94,7,1),(0x8008FD74,3,1),(0x8008FDA8,0xE1,1),(0x800BE3DC,0xFFFF,2),(0x80082BC0,0,1)):oracle.put(expected,address,value,n)
   self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,[(oracle.SETUP,(0xFFFFFF80,))]if flags&16 else []);registers+=1
  for effect,phase,connected in itertools.product(range(8),(0,8),range(2)):
   c=Case(effect=effect,phase=phase);pair=[]
   for words in(self.truth,self.words):
    m,initial=oracle.dispatcher_machine(self.rom,words,c,bool(connected));m.run();want=reference(initial,c,connected=bool(connected))
    self.assertEqual((public(m.memory),m.calls,m.snapshots),(public(want[0]),[(source.ENTRY,())]+want[1],want[2]));pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));dispatches+=1
  wrong,_=oracle.register_machine(self.rom,flags=16,wrong=True)
  with self.assertRaises(oracle.WindowBoundary):wrong.run()
  self.assertNotEqual(oracle.read(wrong.memory,oracle.SLOT),source.ENTRY)
  wrong,initial=oracle.dispatcher_machine(self.rom,self.words,wrong=True);wrong.run();self.assertEqual(wrong.calls,[(source.ENTRY+0x100,())]);self.assertEqual(public(wrong.memory),public(initial))
  coverage=[sum(pc in visited for pc in range(entry,entry+n*4,4))for entry,_,n in oracle.HELPERS]
  self.receipt['integration']=dict(connected_cases=count,registration_cases=registers,dispatcher_cases=dispatches,helper_coverage=coverage,original_transition_command6=True,original_integrity_helpers=True,checksum_code_words=(oracle.CODE_END-oracle.CODE_START)//4,checksum_pass_and_fail=True,callback_negative_controls=2,registration_window_words=30,dispatcher_window_words=8,bounded_services=['func_1501C53C','func_10017870','func_150076BC'],complete_parent_or_gameplay_claimed=False)
 def test_04_native32_SDK_and_semantic_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());logs={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);built=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=built.stderr)
  self.receipt['native']=dict(optimizations=logs,cases_per_profile=256*2*4*8,controls=len(controls()),SDK=True,pointers32=True,trapping_UBSan=True,first_representation_byte_not_logical_word=True,valid_backing_and_canaries=True)
 def test_05_direct_and_dispatch_fault_prefixes(self):
  count=delay=0
  for flags,effect,parent in itertools.product((0,512),(0,7),range(2)):
   c=Case(flags=flags,effect=effect)
   def machine(words):return oracle.dispatcher_machine(self.rom,words,c)[0]if parent else ResetOracle(words,fixture(c),c)
   full=machine(self.truth).run()
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
   if j:
    for i,(name,w)in enumerate(oracle.FIELDS):s[name]=(0x80417FFC,0x80528004)[j-1]+32*i
    s.update(func_1501C730=entry+0x10000,func_151E7EF8=entry+0x20000)
   paths=(self.out/'original-func_151E327C.o',self.out/'make-shadow/src/game/generated_20AE20.c.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for flags,effect,phase in itertools.product((0,512),range(8),(0,8)):self.compare(Case(flags=flags,effect=effect,phase=phase),images,entry,s);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,all_three_objects_linked=True,no_guards=True,signed_low_addresses=True)
 def test_07_compiled_semantic_negatives(self):
  evidence={}
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name)
   for c in(Case(flags=f,effect=7,scene=128,channel=254)for f in(0,512,1024)):
    initial=fixture(c);m=ResetOracle(words,initial,c).run();wanted=reference(initial,c)
    if (public(m.memory),m.calls,m.snapshots)!=(public(wanted[0]),wanted[1],wanted[2]):evidence[name]=dict(flags=c.flags);break
   self.assertIn(name,evidence)
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,private_stack_and_ignored_return_excluded=True)
 def test_08_strict_whole_image_and_inputs(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+200];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,200);named={n:(p,f,loc)for p,n,f,loc in source.symbol_rows(before)}
  positions=[20,at,at+200,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.CHECK,104),source.elf_slot_offset(before,0x800969B8,4),named['D_800E0A88'][0]+4]
  for n in('D_800E0B99','D_80099324','D_800A3624','D_8009ED24'):positions.extend((named[n][0]+4,named[n][2]))
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),205)
  self.receipt['image']=dict(changed_bytes=205,code_bytes=174,extent_bytes=1,metadata_bytes=30,closed_named_symbol_cycle=4,exclusions=0,corruptions=len(positions)+1,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v))
