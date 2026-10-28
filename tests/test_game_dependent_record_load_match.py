"""Prerequisite/destination record load: live gates, ABI, original helpers and image."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_dependent_record_load_match as source
from tools.tests import game_dependent_record_load_oracle as oracle
from tools.tests.game_dependent_record_load_oracle import Case,fixture,reference,public,RecordOracle,BLOCK,IBLOCK,MARK,LOOKUP,ALLOC,RELOC,RESOURCE,CONSUMER,STACK,put,read,faults,u32
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
def controls():
 b=source.SELECTED
 return dict(skip_initialize=b.replace('        func_15183ACC(requiredIndex);',''),initializer_index=b.replace('func_15183ACC(requiredIndex);','func_15183ACC(index);'),invert_first=b.replace('D_800DDE80[requiredIndex].words[0] == 0','D_800DDE80[requiredIndex].words[0] != 0'),missing_prerequisite=b.replace('if (D_800DDE80[requiredIndex].words[0] != 0)','if (1)'),stale_required=b.replace('    s32 *result;','    s32 *result;\n    s32 available = D_800DDE80[requiredIndex].words[0];').replace('if (D_800DDE80[requiredIndex].words[0] != 0)','if (available != 0)'),stale_target=b.replace('    s32 *result;','    s32 *result;\n    s32 occupied = D_800DDE80[index].words[0];').replace('if (D_800DDE80[index].words[0] == 0)','if (occupied == 0)'),invert_target=b.replace('D_800DDE80[index].words[0] == 0','D_800DDE80[index].words[0] != 0'),size_pointer=b.replace('func_1502B6BC(0, 0, 0, 2,','func_1502B6BC(D_800DDE80[0].words, 0, 0, 2,'),count=b.replace('func_1502B6BC(0, 0, 0, 2,','func_1502B6BC(0, 1, 0, 2,'),relocated=b.replace('func_1502B6BC(0, 0, 0, 2,','func_1502B6BC(0, 0, D_800DDE80[0].words, 2,'),depth=b.replace('0, 0, 0, 2, 9,','0, 0, 0, 3, 9,'),category=b.replace('2, 9, index','2, 8, index'),asset=b.replace('index + 0xAD','index + 0xAE'),pointer=b.replace('= (s32)result;','= (s32)(result + 1);'),first=b.replace('= result[0];','= result[1];'),second=b.replace('= result[2];','= result[1];'),last=b.replace('= result[6];','= result[5];'),clear=b.replace('words[4] = 0','words[4] = 1'),flag=b.replace('D_800DDF68[index] = 1','D_800DDF68[index] = 2'),early_copy=b.replace('            if (result != NULL) {','            if (result != NULL) {\n                s32 first = result[0];').replace('words[1] = result[0]','words[1] = first'))

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+r'''
Record15183974 D_800DDE80[11];u8 D_800DDF68[11];
static Record15183974 expected[11];static s32 buffer[16],expectedBuffer[16];static u8 expectedFlags[11];
static u32 error,initCalls,loadCalls,wantedInit,wantedLoad,initMode,loadMode,answerMode,indexValue,requiredValue;static s32 *resultPointer,*expectedPointer;
typedef char ABI[(sizeof(void*)==4&&sizeof(Record15183974)==20)?1:-1];
static void initEffect(Record15183974 *records){if(initMode&1)records[requiredValue].words[0]=(s32)0xF00D1234u;if(initMode&2)records[indexValue].words[0]=(s32)0xABCD4321u;if(initMode&4)records[indexValue].words[0]=0;}
static void loadEffect(Record15183974 *records,s32 *p){u32 j;if(loadMode&1)records[indexValue].words[0]=(s32)0xDEADBEEFu;if(loadMode&2)records[requiredValue].words[0]=0;if((loadMode&4)&&p)for(j=0;j<=6;j+=2)p[j]=(s32)(0x10203040u+j*0x1010101u);}
__attribute__((noinline,noclone)) void func_15183ACC(s32 index){initCalls++;if((u32)index!=requiredValue||loadCalls)error=1;initEffect(D_800DDE80);}
__attribute__((noinline,noclone)) void *func_1502B6BC(s32 *size,s32 count,s32 *relocated,s32 depth,...){__builtin_va_list args;s32 first,second;__builtin_va_start(args,depth);first=__builtin_va_arg(args,s32);second=__builtin_va_arg(args,s32);__builtin_va_end(args);loadCalls++;if(size||count||relocated||depth!=2||first!=9||second!=(s32)indexValue+0xAD||initCalls!=wantedInit)error=1;loadEffect(D_800DDE80,resultPointer);return resultPointer;}
'''
 for name,body in dict(selected=source.SELECTED,**controls()).items():t+=body.replace(source.FUNCTION,'test_'+name)+'\n'
 t+=r'''
typedef void(*Fn)(s32,s32);
static int check(Fn fn){u32 n,i,j;for(n=0;n<16384;n++){
 indexValue=n%11;requiredValue=(n/11)%11;initMode=(n>>2)&7;loadMode=(n>>5)&7;answerMode=(n>>8)&1;
 for(i=0;i<11;i++){for(j=0;j<5;j++)D_800DDE80[i].words[j]=expected[i].words[j]=(s32)(0x12340000u+n*101u+i*5u+j*17u);D_800DDF68[i]=expectedFlags[i]=(u8)(n+i*7);}
 for(i=0;i<16;i++)buffer[i]=expectedBuffer[i]=(s32)(0x87650000u+n*103u+i*19u);
 D_800DDE80[requiredValue].words[0]=expected[requiredValue].words[0]=(n&1)?(s32)0xFFFFFFFFu:0;D_800DDE80[indexValue].words[0]=expected[indexValue].words[0]=(n&2)?1:0;
 resultPointer=answerMode?buffer:0;expectedPointer=answerMode?expectedBuffer:0;
 wantedInit=wantedLoad=0;if(!expected[requiredValue].words[0]){wantedInit=1;initEffect(expected);}if(expected[requiredValue].words[0]&&!expected[indexValue].words[0]){wantedLoad=1;loadEffect(expected,expectedPointer);if(expectedPointer){s32 last;expected[indexValue].words[0]=(s32)resultPointer;expected[indexValue].words[1]=expectedPointer[0];expected[indexValue].words[2]=expectedPointer[2];last=expectedPointer[6];expected[indexValue].words[4]=0;expected[indexValue].words[3]=last;expectedFlags[indexValue]=1;}}
 initCalls=loadCalls=error=0;fn(requiredValue,indexValue);if(error||initCalls!=wantedInit||loadCalls!=wantedLoad)return 1;
 for(i=0;i<11;i++){for(j=0;j<5;j++)if(D_800DDE80[i].words[j]!=expected[i].words[j])return 2;if(D_800DDF68[i]!=expectedFlags[i])return 4;}
 for(i=0;i<16;i++)if(buffer[i]!=expectedBuffer[i])return 3;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,name in enumerate(n for n in controls()if n!='early_copy'):t+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class DependentRecordLoadTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>55I',cls.rom,source.ROM));cls.images=[]
  for filename in('qualified-padded.o','selected.o'):
   local=cls.fresh/filename;local.write_bytes((cls.out/filename).read_bytes());blob,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.images.append(list(struct.unpack_from('>55I',blob,functions[source.FUNCTION]['value'])))
  cls.words,cls.raw=cls.images
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=None,s=None,connected=None,original_init=False,original_loader=False):
  initial=fixture(c,s);wanted,calls=reference(initial,c,s,original_init,original_loader);pair=[]
  for words in images or(self.truth,self.words,self.raw):
   m=RecordOracle(words,initial,c,entry=entry,s=s,connected=connected).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);blob=sections(p.with_suffix('.elf'))['.text'][1];length=functions[source.FUNCTION]['size'];return list(struct.unpack('>%dI'%(length//4),blob[:length]))
 def test_01_owner_actual_Make_census_and_ABI(self):
  self.assertEqual(len(self.truth),55);self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.payload(self.out/'selected.o'),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),9)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),8);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual((self.out/'proposed-owner.c').read_text().count('#pragma GLOBAL_ASM'),0);commands=json.loads((self.out/'Make-commands.json').read_text());self.assertEqual(len(commands),3);self.assertFalse(any('-loopunroll'in x for row in commands for x in row))
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0x1B09AC])
  provider='conker/src/game_57FA0.c';self.assertIn('void *func_1502B6BC(s32 *size, s32 count, s32 *relocated, s32 depth, ...)',self.values[provider].decode());pos=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],source.LOAD,308);self.assertEqual(self.values['conker/build/conker.us.elf'][pos:pos+308],self.rom[0x58B6C:0x58CA0])
  self.assertIn('s32 func_1510CE60(void *data, s32 unresolvedOnly, s32 retain, s32 priority, s32 *output)',self.values['conker/src/game/generated_139FC0.c'].decode())
  self.assertIn('void func_151839F0(s32 requiredIndex, s32 index)' ,(self.out/'proposed-owner.c').read_text())
  pos=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],source.INITIALIZE,216);self.assertEqual(self.values['conker/build/conker.us.elf'][pos:pos+216],self.rom[0x1B0F7C:0x1B1054])
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=55,frame=40,bindings=8,guards=0,neighbors=8,compact_functions=9,Make_commands=3,GLOBAL_ASM=0,normal_profile=True,diagnostics=0,arguments=2,variadic_provider_ABI=True,void_return=True)
 def test_02_guest_live_gates_equal_indices_and_aliases(self):
  count=0;seen=set();pairs=((0,0),(0,1),(1,0),(7,10),(10,7),(10,10),(0,10),(10,0))
  for (required,index),a,b,im,lm,ans,phase in itertools.product(pairs,(0,0xFFFFFFFF),(0,1),(0,1,2,3,5,7),(0,7),range(8),(0,8)):
   m=self.compare(Case(required,index,a,b,im,lm,ans,phase,index*17+ans));seen.update(m.visits);count+=1
  for required,index,ans in itertools.product(range(11),range(11),(0,1)):
   self.compare(Case(required=required,index=index,answer=ans));count+=1
  for extreme,which,ans in itertools.product((-174,-173,-1,32767,-32768,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1),(0,1)):
   self.compare(Case(required=extreme if which==0 else 7,index=10 if which==0 else extreme,init_mode=5,load_mode=7,answer=ans));count+=1
  self.assertTrue(set(range(source.ENTRY,source.ENTRY+220,4))<=seen);self.receipt['guest']=dict(cases=count,visited_words=55,complete_state_trace_equal=True,valid_index_pairs=121,same_row_semantics=True,returned_record_aliases=6,aliases_and_extreme_indices_guest_only=True,prerequisite_and_destination_reloaded_after_initializer=True)
 def test_03_original_caller_initializer_and_variadic_loader(self):
  body=list(struct.unpack_from('>24I',self.rom,0x1B09A8));seen=set();count=0
  for a,b,im,lm,ans,phase in itertools.product((0,1),(0,1),(0,1,2,3,5,7),(0,7),(0,1,2),(0,8)):
   c=Case(required_live=a,target_live=b,init_mode=im,load_mode=lm,answer=ans,phase=phase);initial=fixture(c);sp=STACK+phase
   for off in range(0x58,0x94,4):put(initial,sp+off,0x12000000+off)
   put(initial,0x800A7328,0x3F400000);expected,calls=reference(initial,c);put(expected,MARK+12,0x98765432);args=(read(initial,sp+0x74),3,read(initial,sp+0x68),read(initial,sp+0x6C),read(initial,sp+0x70),u32(read(initial,sp+0x84)*4),read(initial,sp+0x80),0,0x3F400000,0x3F000000);calls=[(source.ENTRY,(7,10))]+calls+[(CONSUMER,args)];pair=[]
   for target in(self.truth,self.words,self.raw):
    m=RecordOracle(body,initial,c,entry=0x151834F8,connected={source.ENTRY+i*4:w for i,w in enumerate(target)});m.r[16]=3;m.r[4]=m.r[5]=0xFFFFFFFF;m.code[0x15183888]=0;m.code=WindowCode(m.code,m);m.code.ends=(0x15183888,)
    with self.assertRaises(WindowBoundary):m.run()
    self.assertEqual((public(m.memory),m.calls),(public(expected),calls));pair.append(m);seen.update(m.visits)
   for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
   count+=1
  self.assertTrue(set(range(0x151834F8,0x15183558,4))<=seen)
  init=list(struct.unpack_from('>54I',self.rom,0x1B0F7C));loader=list(struct.unpack_from('>77I',self.rom,0x58B6C));linked={source.INITIALIZE+i*4:w for i,w in enumerate(init)};helper_seen=set();loader_seen=set();integrated=0;deep=0
  for (required,index),a,b,ia,ans,im,lm,phase in itertools.product(((7,10),(0,0),(10,7)),(0,1),(0,1),(0,1,2),(0,1,5),(0,2,4),(0,7),(0,8)):
   m=self.compare(Case(required,index,a,b,im,lm,ans,phase,init_answer=ia),connected=linked,original_init=True);helper_seen.update(m.visits);integrated+=1
  connected=dict(linked);connected.update({source.LOAD+i*4:w for i,w in enumerate(loader)})
  for (required,index),a,b,ia,ans,missing,zero,im,phase in itertools.product(((7,10),(0,0)),(0,1),(0,1),(0,1),(0,1,5),(-1,0,1),(False,True),(0,4),(0,8)):
   m=self.compare(Case(required,index,a,b,im,0,ans,phase,init_answer=ia,missing=missing,block_zero=zero),connected=connected,original_init=True,original_loader=True);helper_seen.update(m.visits);loader_seen.update(m.visits);deep+=1
  self.assertTrue(set(range(source.INITIALIZE,source.INITIALIZE+216,4))<=helper_seen)
  unused=set(range(source.LOAD,source.LOAD+308,4))-loader_seen;self.assertEqual(unused,{0x1502B6F0,0x1502B7BC,0x1502B7C0,0x1502B7C4})
  self.receipt['integration']=dict(caller_window_words=24,caller_window_cases=count,parent_total_words=392,all_caller_window_words=True,full_parent_all_routes_claimed=False,caller_arguments=[7,10],following_consumer='func_15174FA4',consumer_arguments=10,initializer_words=54,initializer_cases=integrated,all_initializer_words=True,loader_words=77,loader_visited_words=73,loader_unused_addresses=list(map(hex,sorted(unused))),connected_loader_cases=deep,loader_scope='depth two; NULL size and relocated outputs',parent_and_consumer_C_placeholders_uncredited=True,existing_initializer_and_loader_C_bodies_unchanged=True,bounded_providers=['func_1502AC88','func_1502B350','func_1502B4A8','func_1510CE60','func_15174FA4'])
 def test_04_native32_two_index_and_variadic_ABI_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());rows=[]
  for opt in('-O0','-O2','-O3'):
   target=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+[str(p),'-o',str(target)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stdout+build.stderr);run=subprocess.run([str(target)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stdout,run.stderr));rows.append(dict(profile=opt,cases=16384,negative_controls=len(controls())-1,UBSan_trap=True,defined_index_pairs=121,same_row_alias_defined=True,disjoint_result_array=True,record_data_overlap_guest_only=True,real_variadic_arguments=True))
  self.receipt['native']=rows
 def test_05_fault_prefixes_before_and_after_provider_calls(self):
  cuts=0;linked={source.INITIALIZE+i*4:w for i,w in enumerate(struct.unpack_from('>54I',self.rom,0x1B0F7C))};linked.update({source.LOAD+i*4:w for i,w in enumerate(struct.unpack_from('>77I',self.rom,0x58B6C))});deep=0
  for c in(Case(),Case(required_live=1,target_live=1),Case(init_mode=0),Case(load_mode=7,answer=5,phase=8),Case(answer=0),Case(required=0,index=0)):
   good=self.compare(c)
   for cut in range(good.all_accesses):
    pair=[]
    for words in(self.truth,self.words,self.raw):
     m=RecordOracle(words,fixture(c),c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(m.current_pc,m.delay_of))
    cuts+=1
  for c in(Case(init_mode=0),Case(missing=0),Case(answer=0,init_answer=0),Case(answer=5,block_zero=True,init_mode=0)):
   good=self.compare(c,connected=linked,original_init=True,original_loader=True)
   for cut in range(good.all_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=RecordOracle(words,fixture(c),c,connected=linked);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));deep+=1
  self.receipt['faults']=dict(prefix_triples=cuts,integrated_provider_prefix_pairs=deep,complete_state_trace_PC_delay_equal=True,portable_C_fault_semantics_claimed=False)
 def test_06_padder_GNU_rebases_and_relocation_rejections(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'))
  for damaged,bindings in((raw[:-4],rs),(raw[:60]+bytes([raw[60]^1])+raw[61:],rs),(raw,{**rs,136:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.normalized_payload(damaged,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,(entry,table,flag)in enumerate(((source.ENTRY,source.TABLE,source.FLAG),(0x17007FFC,0x80017FFC,0x80028000),(0x2500FFFC,0x8001FFFC,0x80037FFF))):
   s=dict(D_800DDE80=table,D_800DDF68=flag,func_15183ACC=source.INITIALIZE if j==0 else entry+0x10004,func_1502B6BC=source.LOAD if j==0 else entry+0x20004);images=[self.rebased(p,entry,s,'rebase-%d-%d'%(j,k))for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_1B0740.c.o',self.out/'selected.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for (required,index),ans,mode,phase in itertools.product(((7,10),(0,0)),(0,1,5),(0,7),(0,8)):self.compare(Case(required=required,index=index,answer=ans,init_mode=1,load_mode=mode,phase=phase),images,entry,s);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,bindings=8,guards=0,actual_Make_raw_and_retail=True,HI16_LO16_carries=True,raw_binding_rejections=3)
 def test_07_actually_compiled_semantic_negatives(self):
  witnesses=tuple(Case(required=required,index=index,required_live=a,target_live=b,init_mode=im,load_mode=7,answer=ans)for(required,index),a,b,im,ans in itertools.product(((7,10),(0,0)),(0,1),(0,1),(0,1,2,3,5),(0,1,2,5)))
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,oracle.symbols(),'negative-link-'+name);effective=False
   for c in witnesses:
    initial=fixture(c);wanted,calls=reference(initial,c)
    try:m=RecordOracle(words,initial,c).run();different=(public(m.memory),m.calls)!=(public(wanted),calls)
    except (AssertionError,KeyError):different=True
    if different:effective=True;break
   self.assertTrue(effective,name)
  self.receipt['compiled_control']=dict(IDO_negatives=len(controls()),both_indices_and_loader_arguments=True,late_prerequisite_and_target_reads=True,early_copy_alias_control=True)
 def test_08_strict_entire_image_and_protected_providers(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+220];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,220);named={n:(p,f)for p,n,f,_ in source.symbol_rows(before)};positions=[20,at,at+180,at+220,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,source.LOAD,308),source.elf_slot_offset(before,source.INITIALIZE,216)]
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(v['conker/retail_word_patches.us.csv'],(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),165);self.receipt['image']=dict(changed_bytes=165,code_bytes=164,symbol_bytes=1,exclusions=0,effective_corruptions=len(positions)+1,all_named_definitions_preserved_except_target_extent=True,entire_guard_manifest_unchanged=True,new_guards=0,protected_bytes=189088,existing_provider_sources_objects_and_linked_bodies_unchanged=True)
