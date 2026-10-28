"""Record initializer: caller ABI, native32 semantics, original loader and strict image."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_initializer_match as source
from tools.tests import game_record_initializer_oracle as oracle
from tools.tests.game_record_initializer_oracle import Case,fixture,reference,public,RecordOracle,BLOCK,MARK,LOOKUP,ALLOC,RELOC,STACK,put,read,faults,u32
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
CALLS=(0x1B0A08,0x1B0A68,0x1B0A70,0x1B0A78,0x1B0A80,0x1B0B18,0x1B0B20,0x1B0B28,0x1B0B30,0x1B0C68,0x1B0D98,0x1B0E5C,0x1B0E7C,0x1B0ED0,0x1C6000)
def controls():
 b=source.SELECTED
 return dict(invert_gate=b.replace('words[0] == 0','words[0] != 0'),size_pointer=b.replace('func_1502B6BC(0, 0, 0, 2,','func_1502B6BC(D_800DDE80[0].words, 0, 0, 2,'),count=b.replace('func_1502B6BC(0, 0, 0, 2,','func_1502B6BC(0, 1, 0, 2,'),relocated=b.replace('func_1502B6BC(0, 0, 0, 2,','func_1502B6BC(0, 0, D_800DDE80[0].words, 2,'),depth=b.replace('0, 0, 0, 2, 9,','0, 0, 0, 3, 9,'),category=b.replace('2, 9, index','2, 8, index'),asset=b.replace('index + 0xAD','index + 0xAE'),first_word=b.replace('= result[0];','= result[1];'),second_word=b.replace('= result[2];','= result[1];'),last_word=b.replace('= result[6];','= result[5];'),publish=b.replace('= result[4];','= result[5];'),resource_pointer=b.replace('(void *)D_800DDF78[index]','(void *)(D_800DDF78[index] + 4)'),unresolved=b.replace('D_800DDF78[index], 0, 1,','D_800DDF78[index], 1, 1,'),retain=b.replace('], 0, 1, 0x3E','], 0, 0, 0x3E'),priority=b.replace('0x3E','0x3F'),output=b.replace('&D_800DDE80[index].words[4]','&D_800DDE80[index].words[3]'),flag=b.replace('D_800DDF68[index] = 1','D_800DDF68[index] = 2'),early_flag=b.replace('            func_1510CE60','            D_800DDF68[index] = 1;\n            func_1510CE60').replace('            D_800DDF68[index] = 1;\n        }','        }'),honor_failure=b.replace('            func_1510CE60','            if (!func_1510CE60').replace('&D_800DDE80[index].words[4]);','&D_800DDE80[index].words[4])) return;'),early_copy=b.replace('        if (result != NULL) {','        if (result != NULL) {\n            s32 first = result[0];').replace('words[1] = result[0]','words[1] = first'))

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+r'''
Record15183974 D_800DDE80[11];u8 D_800DDF68[11];u32 D_800DDF78[11];
static Record15183974 expected[11];static s32 buffer[16],expectedBuffer[16],atCall[5];static u8 expectedFlags[11],atFlag;static u32 expectedViews[11],atView;
static u32 error,loadCalls,resourceCalls,wantedLoad,wantedResource,loadMode,resourceMode,answerMode,indexValue;static s32 *resultPointer,*expectedPointer;
typedef char ABI[(sizeof(void*)==4&&sizeof(Record15183974)==20)?1:-1];
static void loadEffect(Record15183974 *records,s32 *p){u32 j;if(loadMode&1)records[indexValue].words[3]=(s32)0xFEDCBA98u;if(loadMode&2)records[indexValue].words[0]=(s32)0xDEADBEEFu;if((loadMode&4)&&p)for(j=0;j<=6;j+=2)p[j]=(s32)(0x10203040u+j*0x1010101u);}
static void resourceEffect(Record15183974 *records,u32 *views,u8 *flags,s32 *output){*output=0x2468ACE0;if(resourceMode&1)records[indexValue].words[0]=0x31415926;if(resourceMode&2)views[indexValue]=0x27182818;if(resourceMode&4)flags[indexValue]=0x80;}
__attribute__((noinline,noclone)) void *func_1502B6BC(s32 *size,s32 count,s32 *relocated,s32 depth,...){__builtin_va_list args;s32 first,second;__builtin_va_start(args,depth);first=__builtin_va_arg(args,s32);second=__builtin_va_arg(args,s32);__builtin_va_end(args);loadCalls++;if(size||count||relocated||depth!=2||first!=9||second!=(s32)indexValue+0xAD||resourceCalls)error=1;loadEffect(D_800DDE80,resultPointer);return resultPointer;}
__attribute__((noinline,noclone)) s32 func_1510CE60(void *data,s32 unresolvedOnly,s32 retain,s32 priority,s32 *output){u32 j;resourceCalls++;if(loadCalls!=1||(u32)data!=atView||unresolvedOnly||retain!=1||priority!=62||output!=&D_800DDE80[indexValue].words[4]||D_800DDF78[indexValue]!=atView||D_800DDF68[indexValue]!=atFlag)error=1;for(j=0;j<5;j++)if(D_800DDE80[indexValue].words[j]!=atCall[j])error=1;resourceEffect(D_800DDE80,D_800DDF78,D_800DDF68,output);return resourceMode&1;}
'''
 for name,body in dict(selected=source.SELECTED,**controls()).items():t+=body.replace(source.FUNCTION,'test_'+name)+'\n'
 t+=r'''
typedef void(*Fn)(s32);
static int check(Fn fn){u32 n,i,j;for(n=0;n<8192;n++){
 indexValue=n%11;loadMode=(n>>2)&7;resourceMode=(n>>5)&7;answerMode=(n>>1)&1;
 for(i=0;i<11;i++){for(j=0;j<5;j++)D_800DDE80[i].words[j]=expected[i].words[j]=(s32)(0x12340000u+n*101u+i*5u+j*17u);D_800DDF68[i]=expectedFlags[i]=(u8)(n+i*7);D_800DDF78[i]=expectedViews[i]=0xABCD1234u+n+i;}
 for(i=0;i<16;i++)buffer[i]=expectedBuffer[i]=(s32)(0x87650000u+n*103u+i*19u);
 D_800DDE80[indexValue].words[0]=expected[indexValue].words[0]=(n&1)?(s32)0xFFFFFFFFu:0;
 resultPointer=answerMode?buffer:0;expectedPointer=answerMode?expectedBuffer:0;
 wantedLoad=wantedResource=0;if(!expected[indexValue].words[0]){wantedLoad=1;loadEffect(expected,expectedPointer);if(expectedPointer){wantedResource=1;expected[indexValue].words[0]=(s32)resultPointer;expected[indexValue].words[1]=expectedPointer[0];expected[indexValue].words[2]=expectedPointer[2];expected[indexValue].words[3]=expectedPointer[6];expectedViews[indexValue]=expectedPointer[4];for(j=0;j<5;j++)atCall[j]=expected[indexValue].words[j];atView=expectedViews[indexValue];atFlag=expectedFlags[indexValue];resourceEffect(expected,expectedViews,expectedFlags,&expected[indexValue].words[4]);expectedFlags[indexValue]=1;}}
 loadCalls=resourceCalls=error=0;fn(indexValue);if(error||loadCalls!=wantedLoad||resourceCalls!=wantedResource)return 1;
 for(i=0;i<11;i++){for(j=0;j<5;j++)if(D_800DDE80[i].words[j]!=expected[i].words[j])return 2;if(D_800DDF68[i]!=expectedFlags[i]||D_800DDF78[i]!=expectedViews[i])return 4;}
 for(i=0;i<16;i++)if(buffer[i]!=expectedBuffer[i])return 3;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,name in enumerate(n for n in controls()if n!='early_copy'):t+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class RecordInitializerTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>54I',cls.rom,source.ROM));cls.images=[]
  for filename in('qualified-padded.o','selected.o'):
   local=cls.fresh/filename;local.write_bytes((cls.out/filename).read_bytes());blob,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.images.append(list(struct.unpack_from('>54I',blob,functions[source.FUNCTION]['value'])))
  cls.words,cls.raw=cls.images
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=None,s=None,connected=None,original_loader=False):
  initial=fixture(c,s);wanted,calls,observations=reference(initial,c,s,original_loader);pair=[]
  for words in images or(self.truth,self.words,self.raw):
   m=RecordOracle(words,initial,c,entry=entry,s=s,connected=connected).run();self.assertEqual((public(m.memory),m.calls,m.observations),(public(wanted),calls,observations),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);blob=sections(p.with_suffix('.elf'))['.text'][1];length=functions[source.FUNCTION]['size'];return list(struct.unpack('>%dI'%(length//4),blob[:length]))
 def test_01_owner_actual_Make_census_and_ABI(self):
  self.assertEqual(len(self.truth),54);self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.payload(self.out/'selected.o'),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),9)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),8);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual((self.out/'proposed-owner.c').read_text().count('#pragma GLOBAL_ASM'),0);commands=json.loads((self.out/'Make-commands.json').read_text());self.assertEqual(len(commands),3);self.assertFalse(any('-loopunroll'in x for row in commands for x in row))
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],list(CALLS))
  provider='conker/src/game_57FA0.c';self.assertIn('void *func_1502B6BC(s32 *size, s32 count, s32 *relocated, s32 depth, ...)',self.values[provider].decode());pos=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],source.LOAD,308);self.assertEqual(self.values['conker/build/conker.us.elf'][pos:pos+308],self.rom[0x58B6C:0x58CA0])
  self.assertIn('s32 func_1510CE60(void *data, s32 unresolvedOnly, s32 retain, s32 priority, s32 *output)',self.values['conker/src/game/generated_139FC0.c'].decode())
  self.assertIn('void func_15183ACC(s32 index);',(self.out/'proposed-owner.c').read_text())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=54,frame=40,bindings=8,guards=0,neighbors=8,compact_functions=9,Make_commands=3,GLOBAL_ASM=0,normal_profile=True,diagnostics=0,arguments=1,variadic_provider_ABI=True,void_return=True)
 def test_02_guest_gate_fields_aliases_and_helper_mutations(self):
  count=0;seen=set()
  for index,current,lm,rm,ans,phase in itertools.product(range(11),(0,0xFFFFFFFF),(0,1,2,7),(0,1,2,7),range(8),(0,8)):
   m=self.compare(Case(index,current,lm,rm,ans,phase,index*17+ans));seen.update(m.visits);count+=1
  for index,ans in itertools.product((-174,-173,-1,32767,-32768,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,2,7)):
   self.compare(Case(index=index,load_mode=7,resource_mode=7,answer=ans));count+=1
  self.assertTrue(set(range(source.ENTRY,source.ENTRY+216,4))<=seen);self.receipt['guest']=dict(cases=count,visited_words=54,complete_state_trace_and_provider_observations_equal=True,valid_rows=11,returned_record_aliases=6,aliases_and_extreme_indices_guest_only=True,resource_return_ignored=True,flag_after_resource=True)
 def test_03_original_calls_wrappers_and_variadic_loader(self):
  count=0;sites=set()
  for pos in CALLS:
   body=list(struct.unpack_from('>2I',self.rom,pos));entry=pos+0x14FD2B50;delay=body[1];index=(delay&0xFFFF)if delay>>26==9 and(delay>>21&31)==0 and(delay>>16&31)==4 else 5
   for current,ans,mode,phase in itertools.product((0,1),(0,1,2),(0,7),(0,8)):
    c=Case(index=index,current=current,answer=ans,load_mode=mode,resource_mode=mode,phase=phase);initial=fixture(c);wanted,calls,observations=reference(initial,c);calls=[(source.ENTRY,(index,))]+calls;pair=[]
    for target in(self.truth,self.words,self.raw):
     m=RecordOracle(body,initial,c,entry=entry,connected={source.ENTRY+i*4:w for i,w in enumerate(target)});m.r[2]=m.r[3]=oracle.row(c,oracle.symbols());m.r[4]=index;m.r[5]=index;m.code[entry+8]=0;m.code=WindowCode(m.code,m);m.code.ends=(entry+8,)
     with self.assertRaises(WindowBoundary):m.run()
     self.assertEqual((public(m.memory),m.calls,m.observations),(public(wanted),calls,observations));pair.append(m);sites.update(set(m.visits)&{entry,entry+4})
    for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
    count+=1
  self.assertEqual(len(sites),30)
  wrappers=0;wrapper_seen=set()
  for entry,pos,length in((0x151838B0,0x1B0D60,49),(0x15183974,0x1B0E24,31)):
   body=list(struct.unpack_from('>%dI'%length,self.rom,pos))
   for index,current,adjacent,ans,mode,phase in itertools.product((0,5,9),(0,1),(0,1),(0,1,2),(0,7),(0,8)):
    c=Case(index=index,current=current,answer=ans,load_mode=mode,resource_mode=mode,phase=phase);initial=fixture(c);put(initial,oracle.row(c,oracle.symbols())+20,adjacent);pair=[]
    for target in(self.truth,self.words,self.raw):
     m=RecordOracle(body,initial,c,entry=entry,connected={source.ENTRY+i*4:w for i,w in enumerate(target)}).run();pair.append(m);wrapper_seen.update(m.visits)
    for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
    wrappers+=1
  self.assertTrue(set(range(0x151838B0,0x15183974,4))<=wrapper_seen);self.assertTrue(set(range(0x15183974,0x151839F0,4))<=wrapper_seen)
  loader=list(struct.unpack_from('>77I',self.rom,0x58B6C));connected={source.LOAD+i*4:w for i,w in enumerate(loader)};seen=set();deep=0
  for index,current,ans,missing,zero,phase in itertools.product((0,10),(0,1),(0,1,2,7),(-1,0,1),(False,True),(0,8)):
   m=self.compare(Case(index=index,current=current,answer=ans,missing=missing,block_zero=zero,phase=phase),connected=connected,original_loader=True);seen.update(m.visits);deep+=1
  unused=set(range(source.LOAD,source.LOAD+308,4))-seen;self.assertEqual(unused,{0x1502B6F0,0x1502B7BC,0x1502B7C0,0x1502B7C4})
  self.receipt['integration']=dict(direct_call_sites=15,call_window_words=30,call_window_cases=count,full_dispatchers_claimed=False,whole_original_wrappers=2,wrapper_words=80,wrapper_cases=wrappers,loader_words=77,loader_visited_words=73,loader_unused_addresses=list(map(hex,sorted(unused))),connected_loader_cases=deep,loader_scope='depth two; NULL size and relocated outputs',existing_provider_C_unchanged=True,bounded_providers=['func_1502AC88','func_1502B350','func_1502B4A8','func_1510CE60'])
 def test_04_native32_variadic_and_resource_ABI_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());rows=[]
  for opt in('-O0','-O2','-O3'):
   target=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+[str(p),'-o',str(target)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stdout+build.stderr);run=subprocess.run([str(target)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stdout,run.stderr));rows.append(dict(profile=opt,cases=8192,negative_controls=len(controls())-1,UBSan_trap=True,defined_rows=11,disjoint_result_array=True,record_overlap_guest_only=True,real_variadic_arguments=True,resource_entry_observations=True))
  self.receipt['native']=rows
 def test_05_fault_prefixes_before_and_after_provider_calls(self):
  cuts=0;linked={source.LOAD+i*4:w for i,w in enumerate(struct.unpack_from('>77I',self.rom,0x58B6C))};deep=0
  for c in(Case(),Case(current=1),Case(load_mode=7,resource_mode=7,answer=2,phase=8),Case(answer=0)):
   good=self.compare(c)
   for cut in range(good.all_accesses):
    pair=[]
    for words in(self.truth,self.words,self.raw):
     m=RecordOracle(words,fixture(c),c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(m.current_pc,m.delay_of))
    cuts+=1
  for c in(Case(),Case(missing=0),Case(answer=0),Case(answer=2,block_zero=True)):
   good=self.compare(c,connected=linked,original_loader=True)
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
  for damaged,bindings in((raw[:-4],rs),(raw[:60]+bytes([raw[60]^1])+raw[61:],rs),(raw,{**rs,172:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.normalized_payload(damaged,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,(entry,table,flag,views)in enumerate(((source.ENTRY,source.TABLE,source.FLAG,source.VIEWS),(0x17007FFC,0x80017FFC,0x80028000,0x8003FFFC),(0x2500FFFC,0x8001FFFC,0x80037FFF,0x80047FFC))):
   s=dict(D_800DDE80=table,D_800DDF68=flag,D_800DDF78=views,func_1502B6BC=source.LOAD if j==0 else entry+0x20004,func_1510CE60=source.RESOURCE if j==0 else entry+0x30004);images=[self.rebased(p,entry,s,'rebase-%d-%d'%(j,k))for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_1B0740.c.o',self.out/'selected.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for index,ans,mode,phase in itertools.product((0,10),(0,1,2),(0,7),(0,8)):self.compare(Case(index=index,answer=ans,load_mode=mode,resource_mode=mode,phase=phase),images,entry,s);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,bindings=8,guards=0,actual_Make_raw_and_retail=True,HI16_LO16_carries=True,raw_binding_rejections=3)
 def test_07_actually_compiled_semantic_negatives(self):
  witnesses=tuple(Case(current=current,answer=p,load_mode=lm,resource_mode=rm)for current,p,lm,rm in itertools.product((0,1),(0,1,2,7),(0,7),(0,7)))
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,oracle.symbols(),'negative-link-'+name);effective=False
   for c in witnesses:
    initial=fixture(c);wanted,calls,observations=reference(initial,c)
    try:m=RecordOracle(words,initial,c).run();different=(public(m.memory),m.calls,m.observations)!=(public(wanted),calls,observations)
    except (AssertionError,KeyError):different=True
    if different:effective=True;break
   self.assertTrue(effective,name)
  self.receipt['compiled_control']=dict(IDO_negatives=len(controls()),loader_and_resource_all_arguments=True,publication_and_flag_order=True,early_copy_alias_control=True)
 def test_08_strict_entire_image_and_protected_providers(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+216];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,216);named={n:(p,f)for p,n,f,_ in source.symbol_rows(before)};positions=[20,at,at+180,at+216,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,source.LOAD,308),source.elf_slot_offset(before,source.RESOURCE,652)]
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(v['conker/retail_word_patches.us.csv'],(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),164);self.receipt['image']=dict(changed_bytes=164,code_bytes=163,symbol_bytes=1,exclusions=0,effective_corruptions=len(positions)+1,all_named_definitions_preserved_except_target_extent=True,entire_guard_manifest_unchanged=True,new_guards=0,protected_bytes=189088,existing_provider_sources_objects_and_linked_bodies_unchanged=True)
