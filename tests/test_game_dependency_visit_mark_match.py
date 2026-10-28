"""Dependency visitor: live aliases, callback ABI, actual recursion and strict image."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_dependency_visit_mark_match as source
from tools.tests import game_dependency_visit_mark_oracle as oracle
from tools.tests.game_dependency_visit_mark_oracle import Case,fixture,reference,public,VisitOracle,LIST,BITS,OTHER,CALLBACK,WRAPPER,STACK,put,read,faults
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 return dict(wrong_end=b.replace('0xFFFF','0xFFFE'),skip_visit=b.replace('visit(index);',''),wrong_argument=b.replace('visit(index);','visit(index+1);'),cached_state_id=b.replace('D_800D2E70[*cursor]','D_800D2E70[index]'),wrong_state=b.replace('= 3;','= 2;'),cached_bitmap_id=b.replace('index = *cursor++;','cursor++;'),wrong_byte=b.replace('index >> 3','index >> 4'),wrong_bit=b.replace('index & 7','index & 3'),replace_bits=b.replace('|= 1','= 1'))

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+r'''
u8 D_800D2E70[65536];u8 *D_800D2E4C;
static u8 expectedState[65536],bits[8192],expectedBits[8192],other[8192],expectedOther[8192];
static struct {u8 padding[8192];u16 list[8];u8 fence[16];} actual,saved;
static u8 *expectedMap;static u32 mode,callCount,expectedCount,error;static u16 *active;static s32 called[8],wanted[8];
static void callback(s32 index){if(callCount>=8){error=1;return;}called[callCount++]=index;if(mode&1)*active=(u16)((index+1)%65535);if(mode&2)D_800D2E4C=other;if(mode&4)active[1]=65535;if(mode&8)*active=65535;active++;}
'''
 for name,body in dict(selected=source.SELECTED,**controls()).items():t+=body.replace('void '+source.FUNCTION,'void test_'+name)+'\n'
 t+=r'''
typedef void(*Fn)(u16*,void(*)(s32));
static int check(Fn fn){u32 n,i,j,iteration,index,mark,bitIndex;u16 *p;
 for(i=0;i<65536;i++)D_800D2E70[i]=expectedState[i]=(u8)i;
 for(i=0;i<8192;i++){bits[i]=expectedBits[i]=(u8)(i*13);other[i]=expectedOther[i]=(u8)(i*17);actual.padding[i]=saved.padding[i]=0;}
 for(iteration=0;iteration<65536;iteration++){
  n=(iteration+65534)&65535;
  mode=n&15;actual.list[0]=saved.list[0]=(u16)n;actual.list[1]=saved.list[1]=7;actual.list[2]=saved.list[2]=8;actual.list[3]=saved.list[3]=65535;for(i=4;i<8;i++)actual.list[i]=saved.list[i]=0xA5A5;
  for(i=0;i<16;i++)actual.fence[i]=saved.fence[i]=0x5A;
  D_800D2E4C=bits;expectedMap=expectedBits;active=actual.list;callCount=expectedCount=error=0;p=saved.list;index=*p;
  while(index!=65535){if(expectedCount>=8)return 2;wanted[expectedCount++]=index;if(mode&1)*p=(u16)((index+1)%65535);if(mode&2)expectedMap=expectedOther;if(mode&4)p[1]=65535;if(mode&8)*p=65535;mark=*p;expectedState[mark]=3;bitIndex=*p++;expectedMap[bitIndex>>3]|=(u8)(1u<<(bitIndex&7));index=*p;}
  fn(actual.list,callback);if(error||callCount!=expectedCount)return 1;
  for(i=0;i<callCount;i++)if(called[i]!=wanted[i])return 1;
  for(i=0;i<8;i++)if(actual.list[i]!=saved.list[i])return 1;
  for(i=0;i<16;i++)if(actual.fence[i]!=saved.fence[i])return 1;
  if((D_800D2E4C==other)!=(expectedMap==expectedOther))return 1;
  for(j=0;j<4;j++){i=j==0?n:j==1?(n+1)%65535:j==2?65535:7;if(D_800D2E70[i]!=expectedState[i]||bits[i>>3]!=expectedBits[i>>3]||other[i>>3]!=expectedOther[i>>3])return 1;}
 }
 for(i=0;i<65536;i++)if(D_800D2E70[i]!=expectedState[i])return 1;
 for(i=0;i<8192;i++)if(bits[i]!=expectedBits[i]||other[i]!=expectedOther[i]||actual.padding[i]!=saved.padding[i])return 1;
 return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,name in enumerate(controls()):t+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START

class DependencyVisitMarkTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>49I',cls.rom,source.ROM));cls.images=[]
  for filename in('qualified-padded.o','selected.o'):
   local=cls.fresh/filename;local.write_bytes((cls.out/filename).read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.images.append(list(struct.unpack_from('>49I',data,functions[source.FUNCTION]['value'])))
  cls.words,cls.raw=cls.images
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,state=source.STATE,bitmap=source.BITMAP):
  initial,pointer=fixture(c,state,bitmap);wanted,calls=reference(initial,pointer,c,state,bitmap);pair=[]
  for words in images or(self.truth,self.words,self.raw):
   m=VisitOracle(words,initial,c,entry,pointer=pointer,bitmap=bitmap).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls),c);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace)
  for m in pair[2:]:self.assertEqual((m.memory,m.calls,m.trace,m.r[16:24],m.r[29],m.r[31]),(pair[0].memory,pair[0].calls,pair[0].trace,pair[0].r[16:24],pair[0].r[29],pair[0].r[31]))
  return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);data=sections(p.with_suffix('.elf'))['.text'][1];length=functions[source.FUNCTION]['size'];return list(struct.unpack('>%dI'%(length//4),data[:length]))
 def test_01_owner_actual_Make_census_and_guards(self):
  self.assertEqual(self.words,self.truth);self.assertNotEqual(self.raw,self.truth);self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),19)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),18);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()));commands=json.loads((self.out/'Make-commands.json').read_text());self.assertEqual(len(commands),3);self.assertEqual(commands[0].count('-Wo,-loopunroll,0'),1)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0xCA18C])
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=49,frame=56,bindings=4,guards=16,neighbors=18,compact_functions=19,Make_commands=3,no_unroll=True,diagnostics=0,typed_callback_and_list=True,caller_bytes_unchanged=True)
 def test_02_raw_C_live_reload_mutation_and_alias_reference(self):
  count=0;seen=set()
  for values,mode,phase in itertools.product(((),(0,),(1,7,8),(2,2,2),(255,256,32767,32768,65534)),range(16),(0,8)):
   m=self.compare(Case(values=values,mode=mode,phase=phase));seen.update(m.visits);count+=1
  for seed in range(256):self.compare(Case(seed=seed));count+=1
  for alias,mode in itertools.product((1,2,3),range(16)):
   m=self.compare(Case(alias=alias,mode=mode));count+=1
  self.assertTrue(set(range(source.ENTRY,source.ENTRY+196,4))<=seen);self.receipt['guest']=dict(cases=count,visited_words=49,raw_memory_calls_trace_equal=True,retail_guarded_complete_state_equal=True,post_callback_and_post_state_store_reloads=True,table_list_and_bitmap_aliases=True,all_bitmap_byte_patterns=True)
 def test_03_original_wrapper_dispatcher_and_actual_recursion(self):
  parent=list(struct.unpack_from('>16I',self.rom,0xCA164));wrapper=list(struct.unpack_from('>8I',self.rom,0xCA144));graphs=({0:[]},{0:[1,2],1:[3],2:[3,1],3:[]},{0:[1,1,2],1:[],2:[]},{i:[i+1]for i in range(8)}|{8:[]});count=0;seen=set()
  for va,at,size in((source.PARENT,0xCA164,64),(WRAPPER,0xCA144,32)):
   pos=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],va,size);self.assertEqual(self.values['conker/build/conker.us.elf'][pos:pos+size],self.rom[at:at+size])
  for graph,seed,phase,entry in itertools.product(graphs,(0,1,128,255),(0,8),(source.PARENT,WRAPPER)):
   initial,c=oracle.graph_fixture(graph,seed,phase);wanted,calls=oracle.graph_reference(initial,0)
   if entry==WRAPPER:calls=[(source.PARENT,(0,))]+calls
   pair=[]
   for target in(self.truth,self.words,self.raw):
    connected={base+i*4:w for base,body in((source.ENTRY,target),(source.PARENT,parent))for i,w in enumerate(body)};m=VisitOracle(wrapper if entry==WRAPPER else parent,initial,c,entry,connected=connected,arguments=(0,)).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls));seen.update(m.visits);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual((pair[0].memory,pair[0].trace),(pair[2].memory,pair[2].trace));count+=1
  self.assertTrue(set(range(source.PARENT,source.PARENT+64,4))<=seen);self.assertTrue(set(range(WRAPPER,WRAPPER+32,4))<=seen);self.receipt['caller']=dict(cases=count,parent_words=16,wrapper_words=8,all_words_visited=True,actual_recursive_callback=True,shared_DAG_repeated_children_and_depth8=True,original_current_callers_byte_exact=True,return_ignored=True)
 def test_04_native32_all_halfwords_mutations_and_semantic_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());rows=[]
  for opt in('-O0','-O2','-O3'):
   target=self.fresh/('native'+opt);cmd=native_command(opt)+[str(p),'-o',str(target)];build=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stdout+build.stderr);run=subprocess.run([str(target)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stdout,run.stderr));rows.append(dict(profile=opt,cases=65536,negative_controls=9,UBSan_trap=True,full_state_and_both_bitmap_images_checked=True))
  self.receipt['native']=rows
 def test_05_access_faults_and_unbounded_recursive_cycle_prefixes(self):
  cuts=0
  for c in(Case(values=()),Case(values=(65534,),mode=8),Case(mode=15),Case(alias=1),Case(alias=2)):
   good=self.compare(c)
   for cut in range(good.access_count):
    pair=[]
    for words in(self.truth,self.words):
     initial,pointer=fixture(c);m=VisitOracle(words,initial,c,pointer=pointer);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
  cycle=0;parent=list(struct.unpack_from('>16I',self.rom,0xCA164))
  for graph in({0:[0]},{0:[1],1:[0]}):
   initial,c=oracle.graph_fixture(graph)
   for cut in(32,64,128):
    pair=[]
    for target in(self.truth,self.words):
     connected={base+i*4:w for base,body in((source.ENTRY,target),(source.PARENT,parent))for i,w in enumerate(body)};m=VisitOracle(parent,initial,c,source.PARENT,connected=connected,arguments=(0,));m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));cycle+=1
  self.receipt['faults']=dict(prefix_pairs=cuts,cycle_prefix_pairs=cycle,actual_recursion_without_inserted_depth_limit=True,complete_state_trace_PC_delay_equal=True)
 def test_06_all_entry_values_padder_GNU_rebases_and_guard_rejection(self):
  class Join(Exception):pass
  class Code(faults.TrackedCode):
   def __getitem__(self,pc):
    if pc in(source.ENTRY+64,source.ENTRY+156):raise Join(pc)
    return super().__getitem__(pc)
  # Exhaustively qualify the LHU / OR-zero to LHU / ANDI-ffff entry exchange.
  for value in range(65536):
   memory={STACK+i:0xA5 for i in range(-64,4)};put(memory,LIST,value,2);pair=[]
   for words in(self.truth,self.raw):
    m=VisitOracle(words,memory);m.code=Code(m.code,m)
    with self.assertRaises(Join)as hit:m.run()
    pair.append((hit.exception.args[0],m.r[16],m.memory))
   self.assertEqual(pair[0],pair[1])
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));self.assertEqual(len(source.NEW_GUARDS),16)
  for damaged,bindings in((raw[:-4],rs),(raw[:60]+bytes([raw[60]^1])+raw[61:],rs),(raw,{**rs,44:[('R_MIPS_HI16','wrong')]})):
   with self.assertRaises(ValueError):source.normalized_payload(damaged,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,(entry,state,bitmap)in enumerate(((source.ENTRY,source.STATE,source.BITMAP),(0x17007FFC,0x80017FFC,0x80028000),(0x2500FFFC,0x8001FFFC,0x80030000))):
   symbols=dict(D_800D2E70=state,D_800D2E4C=bitmap);images=[self.rebased(p,entry,symbols,'rebase-%d-%d'%(j,k))for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_C9EC0.c.o',self.out/'selected.o'))];self.assertEqual(images[0],images[1])
   for values,mode in itertools.product(((),(1,7,8),(32768,65534)),(0,1,2,4,8,15)):self.compare(Case(values=values,mode=mode),images,entry,state,bitmap);count+=1
  self.receipt['rebases']=dict(entry_values=65536,layouts=3,guest_cases=count,bindings=4,guards=16,actual_Make_raw_and_retail=True,HI16_LO16_carries=True,raw_binding_rejections=3)
 def test_07_actually_compiled_semantic_negatives(self):
  witnesses=[Case(values=(0,)),Case(values=(65534,)),Case(mode=1),Case(mode=8),Case(alias=1),Case(seed=255)]
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,dict(D_800D2E70=source.STATE,D_800D2E4C=source.BITMAP),'negative-link-'+name);effective=False
   for c in witnesses:
    initial,pointer=fixture(c);wanted,calls=reference(initial,pointer,c)
    try:m=VisitOracle(words,initial,c,pointer=pointer).run();different=(public(m.memory),m.calls)!=(public(wanted),calls)
    except (AssertionError,KeyError):different=True
    if different:effective=True;break
   self.assertTrue(effective,name)
  self.receipt['compiled_control']=dict(IDO_negatives=9,live_reload_call_and_bitmap_failures=True)
 def test_08_strict_entire_image_and_manifest_prefix(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+196];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,196);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+196,source.elf_slot_offset(before,source.PARENT,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  guards=source.guard_manifest(v['conker/retail_word_patches.us.csv']);self.assertTrue(guards.startswith(v['conker/retail_word_patches.us.csv']));self.assertEqual(guards,(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),152);self.receipt['image']=dict(changed_bytes=152,code_bytes=151,size_bytes=1,exclusions=0,effective_corruptions=6,inherited_guard_prefix_unchanged=True,new_guards=16,protected_bytes=189088)
