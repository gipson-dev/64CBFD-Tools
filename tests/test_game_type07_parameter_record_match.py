"""Type-7 constructor: sixteen-input ABI, original callers and complete image audit."""
from dataclasses import replace
from pathlib import Path
import itertools,json,math,os,re,struct,subprocess,unittest
from tools.experiments import game_type07_parameter_record_match as source
from tools.tests import game_type07_parameter_record_oracle as oracle
from tools.tests.game_type07_parameter_record_oracle import Case,DEFAULT,fixture,reference,public,packet,head,destination,ConstructorOracle,WindowCode,WindowBoundary,OUTPUT,PREVIOUS,ACTOR,STACK,put,read,faults
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.game_animation_timeline_oracle import bits,signed
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ROOT=Path(__file__).resolve().parents[2]
SITES=(0x15026AE0,0x15026BA0,0x150C3A5C,0x150C3BB4,0x150C3DF8)
VALUES=(0,1,0x7FFF,0x8000,0xFFFF,0x10000,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0xAABBCCDD)

def controls():
 b=source.SELECTED;out=dict(wrong_kind=b.replace('(7, context','(6, context'),wrong_context=b.replace('(7, context','(7, 0'),wrong_size=b.replace('context, 0x2C','context, 0x2A'),wrong_view=b.replace('0, view, 1','0, 0, 1'),wrong_heap_flag=b.replace('0, view, 1','0, view, 0'),swapped_first=b.replace('record->first = first','record->first = second'),truncated_value=b.replace('record->value = value','record->value = (u8)value'),missing_success=b.replace('if (record != NULL)','if (0)'))
 for i in range(11):out['parameter_'+str(i)]=b.replace('parameters[%d] = p%d'%(i,i),'parameters[%d] = p%d'%(i,(i+1)%11))
 return out

def native_harness(values):
 t=source.HEADERS+source.DECLARATIONS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(Type07ParameterRecord)==44&&__builtin_offsetof(Type07ParameterRecord,value)==16&&__builtin_offsetof(Type07ParameterRecord,first)==20&&__builtin_offsetof(Type07ParameterRecord,second)==21&&__builtin_offsetof(Type07ParameterRecord,parameters)==22)?1:-1];
static struct{u32 left[4];Type07ParameterRecord record;u32 right[4];}actual,expected;
static u32 fail,mode,calls,initializers,error;
static s32 func_10003C6C(s32 size,s32 a,s32 b,s32 inserted,s32 flag){calls++;if(size!=44||a!=1||b||inserted||flag!=1)error=1;return fail?0:(s32)(u32)&actual.record;}
static void func_15168A4C(void*p,s32 kind){initializers++;if(p!=&actual.record||kind!=7)error=1;((u8*)p)[0]=(u8)kind;if(mode&2)((u8*)p)[2]^=0xA5;}
'''
 wrapper=values['conker/src/game_1944C0.c'].decode();lo,hi=source.function_span(wrapper,'func_15167A68');wrapper=wrapper[lo:hi]
 # Preserve the legacy s32 heap return using an explicit same-width Native bridge.
 t+=wrapper.replace('ret = func_10003C6C','ret = (u8 *)(u32)func_10003C6C')+'\n'
 for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('void '+source.FUNCTION,'static void '+name)+'\n'
 t+=r'''
typedef void(*Constructor)(s32,s32,s16,s16,s16,s16,s16,s16,s16,s16,s16,s16,s16,u32,u8,s32);
static int check(Constructor fn){u32 n,pattern,i,a[16];u8*p=(u8*)&actual,*q=(u8*)&expected;
 for(n=0;n<65536;n++)for(pattern=0;pattern<4;pattern++){
  for(i=0;i<16;i++)a[i]=n*(2*i+1)+0xA5000000u+i*0x13579u;
  for(i=0;i<sizeof(actual);i++)p[i]=q[i]=(u8)(i*13+n*3+pattern);
  fail=pattern&1;mode=pattern;calls=initializers=error=0;
  if(!fail){expected.record.header[0]=7;expected.record.header[1]=(u8)a[15];expected.record.header[12]=(u8)a[14];if(mode&2)expected.record.header[2]^=0xA5;
   expected.record.first=(u8)a[0];expected.record.second=(u8)a[1];for(i=0;i<11;i++)expected.record.parameters[i]=(s16)a[i+2];expected.record.value=a[13];}
  fn((s32)a[0],(s32)a[1],(s16)a[2],(s16)a[3],(s16)a[4],(s16)a[5],(s16)a[6],(s16)a[7],(s16)a[8],(s16)a[9],(s16)a[10],(s16)a[11],(s16)a[12],a[13],(u8)a[14],(s32)a[15]);
  if(error||calls!=1||initializers!=!fail)return 1;for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 1;
 }return 0;}
static int run(void){if(check(selected))return 10;
'''
 for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START

class Type07ParameterRecordTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>48I',data,functions[source.FUNCTION]['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,factory=source.FACTORY):
  initial=fixture(c);want,args,out=reference(initial,c);pair=[]
  for words in images or(self.truth,self.words):
   m=ConstructorOracle(words,initial,c,entry,factory=factory).run();self.assertEqual((public(m.memory),m.calls),(public(want),[(factory,args)]),c)
   if out:self.assertEqual(bytes(m.memory[out+i]for i in range(16,44)),bytes(want[out+i]for i in range(16,44)),c)
   pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def link_object(self,obj,entry,factory,label):
  p=self.fresh/(label+'.ld');elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=func_15167A68=0x%X'%factory,'-o',str(elf),str(obj)],capture_output=True,check=True);raw=sections(elf)['.text'][1];return list(struct.unpack('>%dI'%(len(raw)//4),raw))
 def test_01_owner_Make_census_and_source_ABI(self):
  self.assertEqual(self.words,self.truth);source.checked_payload(*source.payload(self.out/'selected.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),4)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),3);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),proposed);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertNotIn('#pragma GLOBAL_ASM',proposed)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([i*4+0x14FD2B50 for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],list(SITES))
  for name,path in(('func_150265CC','conker/src/game/generated_50D80.c'),('func_150C3994','conker/src/game_EF410.c'),('func_150C3D5C','conker/src/game_EF410.c')):self.assertIn('s32 '+name+'() {\n    return 0;\n}',self.values[path].decode())
  self.assertIn('void *func_15167A68(s32 arg0, s32 arg1, s32 arg2, s32 arg3, u8 arg4, u8 arg5)',self.values['conker/src/game_1944C0.c'].decode())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=48,frame=32,bindings=1,guards=0,neighbors=3,compact_functions=4,GLOBAL_ASM_routines=0,Make_commands=3,diagnostics=0,arguments=16,void_result_supported_by_callers=True,direct_sites=list(map(hex,SITES)),all_current_parents_unchanged_placeholders=True)
 def test_02_guest_all_arguments_narrowing_live_homes_and_aliases(self):
  count=0;visits=set()
  for index,value,fail,mutation,phase in itertools.product(range(16),VALUES,(False,True),(0,1,2,3),(0,8)):
   args=list(DEFAULT);args[index]=value;m=self.compare(Case(tuple(args),fail,mutation,phase=phase));visits.update(m.visits);count+=1
  for n,fail in itertools.product(range(256),(False,True)):
   args=tuple((v&0xFFFFFF00)|((n+i*7)&255)for i,v in enumerate(DEFAULT));self.compare(Case(args,fail));count+=1
  for home,mutation,phase in itertools.product((-16,0,4,8,16,32,48,64),(0,1,2,3),(0,8)):
   self.compare(Case(home=home,mutation=mutation,phase=phase));count+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4)));self.receipt['guest']=dict(cases=count,visited_words=48,all16_arguments_and_raw_high_bits=True,all_byte_encodings=True,eight_incoming_home_aliases=True,late_parameter_reads_after_provider_mutations=True,full_state_and_trace=True,void_result_preserves_literal_guest_register_state=True)
 def test_03_five_original_call_windows_and_retained_allocator_chain(self):
  before=self.values['conker/build/conker.us.elf'];helpers={}
  for entry,rom_at,size in((source.FACTORY,0x194F18,112),(source.INITIALIZER,0x195EFC,80)):
   raw=self.rom[rom_at:rom_at+size];at=source.elf_slot_offset(before,entry,size);self.assertEqual(before[at:at+size],raw);helpers.update({entry+4*i:w for i,w in enumerate(struct.unpack('>%dI'%(size//4),raw))})
  count=0;visits=set()
  for row,old,fail,phase in itertools.product((0,1,128,255),(0,PREVIOUS),(False,True),(0,8)):
   args=list(DEFAULT);args[15]=0xA5000000|row;c=Case(tuple(args),fail,phase=phase);initial=fixture(c);put(initial,head(c.args),old);want,packet_args,out=reference(initial,c,initialize=True);expected=[(source.FACTORY,packet_args),(source.HEAP,(44,1,0,0,1))]+([]if fail else[(source.INITIALIZER,(OUTPUT,7))]);pair=[]
   for code in(self.truth,self.words):
    m=ConstructorOracle(code,initial,c,connected=helpers).run();self.assertEqual((public(m.memory),m.calls),(public(want),expected));pair.append(m);visits.update(m.visits)
   self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
  self.assertTrue(set(helpers)<=visits)
  windows=((0x15026A70,0x15026AF0,(0x15029BA0,0x15029BA4)),(0x15026B30,0x15026BB0,(0x15029BA0,0x15029BA4)),(0x150C39C8,0x150C3A6C,(0x150C3A78,)),(0x150C3B1C,0x150C3BBC,(0x150C3BBC,)),(0x150C3D6C,0x150C3E00,(0x150C3E00,)))
  cases=0;target_calls=0
  for which,(entry,end,joins)in enumerate(windows):
   parent=list(struct.unpack_from('>%dI'%((end-entry)//4),self.rom,entry-0x14FD2B50))
   for n,fail,gate,phase in itertools.product((0,1,127,255),(False,True),(0,1),(0,8)):
    c=Case(fail=fail,phase=phase);initial=fixture(c);sp=STACK+phase;initial[ACTOR+4]=gate;coords=(n+0.75,-n-0.5,n*2+0.25)
    for i,x in enumerate(coords):put(initial,ACTOR+0x14+4*i,bits(x))
    put(initial,ACTOR+0x20,bits(3.5));base=0x12345000;put(initial,sp+0x75C,base);put(initial,sp+0x76C,0x87650000|n);put(initial,sp+0x770,0xA5000000|n)
    if which<2:args=(3 if which==0 else 47,3 if which==0 else 1,0,0,0,800 if which==0 else 2000,1200 if which==0 else 1000,400,200,102 if which==0 else 1024,455 if which==0 else 1024,2 if which==0 else 6,n,0x87650000|n,0xA5000000|n,0)
    else:
     x,y,z=(math.trunc(v)for v in coords);y=math.trunc(coords[1]+30.0)if which<4 else y
     constants=((2000,1000,400,200,3072,3072,1,1),(2200,1280,800,700,3072,3072,20,1),(1400,1280,800,1200,512,512,30,1))[which-2]
     args=(47,1,((x&65535)^32768)-32768,((y&65535)^32768)-32768,z,*constants,0,255,0)
    args=tuple(v&0xFFFFFFFF for v in args);reached=which>=2 or not gate;pair=[]
    for code in(self.truth,self.words):
     connected={source.ENTRY+4*i:w for i,w in enumerate(code)};m=ConstructorOracle(parent,initial,c,entry,connected,arguments=(0,));m.r[16]=ACTOR;m.r[2]=base+n;m.r[1]=0x41F00000;m.window_ends=joins;m.code=WindowCode(dict(m.code),m)
     with self.assertRaises(WindowBoundary):m.run()
     self.assertEqual(m.target_entries,[args]if reached else[],(which,n,fail,gate));self.assertEqual(m.calls,[(source.ENTRY,args),(source.FACTORY,packet(args))]if reached else[])
     if reached:
      want,_,out=reference(initial,replace(c,args=args))
      if out:self.assertEqual(bytes(m.memory[out+i]for i in range(16,44)),bytes(want[out+i]for i in range(16,44)))
      if which<2:self.assertEqual(m.r[2],1)
     self.assertEqual(m.r[29],sp);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));cases+=1;target_calls+=int(reached)
  self.receipt['caller']=dict(original_windows=5,caller_window_words=[(b-a)//4 for a,b,_ in windows],cases=cases,target_calls=target_calls,all_direct_sites_executed=True,gate_paths_checked=True,argument_setup_float_truncation_and_void_join=True,retained_helper_words=[28,20],helper_cases=count,all_helper_words_visited=True,three_current_parent_placeholders_preserved=True,lower_heap_provider_bounded_no_gameplay_claim=True)
 def test_04_native32_sixteen_argument_interface_and_effective_controls(self):
  for opt in('-O0','-O2','-O3'):
   p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness(self.values));binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=65536*4,effective_controls=len(controls()),trapping_UBSan=True,all11_halfword_encodings=True,actual_sixteen_argument_function_pointer=True,whole_storage_fences=True,actual_factory_C_with_explicit_32bit_legacy_heap_return_bridge=True,list_initializer_bounded_in_native_full_original_in_guest=True)
 def test_05_fired_access_prefixes_and_NULL_late_read_boundary(self):
  cuts=0
  for fail,mutation,home,phase in itertools.product((False,True),(0,3),(None,0),(0,8)):
   c=Case(fail=fail,mutation=mutation,home=home,phase=phase);initial=fixture(c);good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=ConstructorOracle(words,initial,c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
  for code in(self.truth,self.words):
   c=Case(fail=True);m=ConstructorOracle(code,fixture(c),c);m.drop_late=True;m.run();self.assertEqual(m.r[2],0)
   reads=[x for x in m.trace if x[0]=='R'and STACK<=x[1]<STACK+64];self.assertEqual(reads[-1][1:3],(STACK,4));self.assertFalse(any(e[0]=='W'and OUTPUT<=e[1]<OUTPUT+44 for e in m.trace))
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,full_private_state_trace_PC_delay=True,NULL_requires_first_argument_delay_load_only=True,remaining_argument_homes_can_be_unmapped_after_failure=True,no_record_store_on_failure=True)
 def test_06_real_padder_raw_controls_and_three_GNU_rebases(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
  for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,{52:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.checked_payload(b,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
  for j,(entry,factory)in enumerate(((source.ENTRY,source.FACTORY),(0x17007FFC,0x17012340),(0x2500FFFC,0x25123400))):
   images=[self.link_object(p,entry,factory,'layout-%d-%d'%(j,k))[:48]for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o'))];self.assertEqual(*images)
   for fail,mutation,home in itertools.product((False,True),(0,3),(None,0)):
    self.compare(Case(fail=fail,mutation=mutation,home=home),images,entry,factory);cases+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=cases,one_J26_binding=True,original_and_compiler_objects=True,raw_binding_controls=3,guards=0)
 def test_07_actually_compiled_order_and_argument_controls(self):
  b=source.SELECTED;cached=b.replace('    Type07ParameterRecord *record =','    volatile s32 cachedFirst = first;\n    Type07ParameterRecord *record =').replace('record->first = first','record->first = cachedFirst');early=b.replace('        record->value = value;\n','').replace('        record->first = first;','        record->value = value;\n        record->first = first;')
  for name,body,c in(('cached_first',cached,Case(mutation=1)),('early_value',early,Case(home=0)),('wrong_kind',controls()['wrong_kind'],Case()),('wrong_parameter',controls()['parameter_10'],Case())):
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.link_object(obj,source.ENTRY,source.FACTORY,'negative-'+name);initial=fixture(c);want,args,out=reference(initial,c);m=ConstructorOracle(words,initial,c).run();self.assertNotEqual((bytes(m.memory[out+i]for i in range(16,44)),m.calls),(bytes(want[out+i]for i in range(16,44)),[(source.FACTORY,args)]),name)
  self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=4,late_argument_home_and_ordered_alias_store_controls=True,value_failure_not_unmapped_read=True)
 def test_08_strict_entire_image_extent_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  count=sum(x!=y for x,y in zip(before,expected));self.assertEqual(count,143);self.receipt['image']=dict(changed_bytes=count,code_bytes=142,size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,guard_manifest_shared_headers_helpers_and_current_parents_unchanged=True)
