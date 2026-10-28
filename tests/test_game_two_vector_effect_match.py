"""Two-vector callback: direct words, 16-argument ABI, caller routes and original provider."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_two_vector_effect_match as source
from tools.tests import game_two_vector_effect_oracle as oracle
from tools.tests.game_two_vector_effect_oracle import Case,fixture,call_reference,provider_reference,public,data,EffectOracle,OWNER,OUTPUT,MARK,FACTORY,COPY,STACK,put,read,faults
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED;args=['owner','5','&first','&second','D_800A5E58','2','300','255','255','255','255','1','0','0','255','1'];wrong=['NULL','4','&second','&first','0.0f','3','299','254','254','254','254','0','1','1','254','0'];start=b.index('func_15160CDC(');end=b.index(';',start)+1;rows={}
 for i,v in enumerate(wrong):
  a=list(args);a[i]=v;rows['wrong_argument_'+str(i)]=b[:start]+'func_15160CDC('+', '.join(a)+');'+b[end:]
 rows['global_vector_alias']=b.replace('&first, &second','&D_800A5970, &second');rows['skip_null_owner']=b[:start]+'if (owner) '+b[start:]
 return rows

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+r'''
GameEffectVector D_800A5970,D_800A597C;f32 D_800A5E58;
typedef char ABI[(sizeof(void*)==4&&sizeof(GameEffectVector)==12&&__builtin_offsetof(GameEffectVector,z)==8)?1:-1];
static u8 actor[128],expectedActor[128],wantedA[12],wantedB[12],expectedA[12],expectedB[12];
static u32 error,calls,mode,wantedParam,expectedParam;static u8*wantedOwner;
static u32 word(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
static f32 real(u32 x){union{f32 f;u32 u;}v;v.u=x;return v.f;}
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
__attribute__((noinline,noclone)) void *func_15160CDC(u8*owner,u8 type,GameEffectVector*a,GameEffectVector*b,f32 param,u8 kind,s16 duration,s32 r,s32 g,s32 blue,s32 alpha,u8 firstFlag,u8 field,u8 secondFlag,u8 slot,s32 context){u32 i;
 calls++;if(calls!=1||owner!=wantedOwner||type!=5||a==b||a==&D_800A5970||b==&D_800A597C||word(param)!=wantedParam||kind!=2||duration!=300||r!=255||g!=255||blue!=255||alpha!=255||firstFlag!=1||field||secondFlag||slot!=255||context!=1)error=1;
 for(i=0;i<12;i++)if(((u8*)a)[i]!=wantedA[i]||((u8*)b)[i]!=wantedB[i])error=1;
 if(mode&1){for(i=0;i<12;i++){((u8*)&D_800A5970)[i]^=90;((u8*)&D_800A597C)[i]^=90;}D_800A5E58=real(word(D_800A5E58)^0x5A5A5A5Au);}
 if(mode&2)for(i=0;i<12;i++){((u8*)a)[i]^=165;((u8*)b)[i]^=165;}
 if((mode&4)&&owner)owner[3]^=85;
 return(void*)((mode&4)?0x87654321u:0u);
}
'''
 for name,body in dict(selected=source.SELECTED,**controls()).items():t+=body.replace('GameEffectVector second = D_800A597C;','GameEffectVector second = D_800A597C; (void)first; (void)second;').replace(source.FUNCTION,'test_'+name)+'\n'
 t+=r'''
typedef void(*Fn)(u8*);
static int check(Fn fn){u32 n,i,j,values[7];
 for(n=0;n<65536;n++){
  mode=n&7;wantedOwner=(n&8)?actor:0;
  for(j=0;j<7;j++){u32 base=(j&1)?0xBF000000u:0x3F000000u;values[j]=base|(n^(j*719u));if((n&31)==0)values[j]=0x7FC00000u|(n+j);}
  D_800A5970.x=real(values[0]);D_800A5970.y=real(values[1]);D_800A5970.z=real(values[2]);D_800A597C.x=real(values[3]);D_800A597C.y=real(values[4]);D_800A597C.z=real(values[5]);D_800A5E58=real(values[6]);wantedParam=values[6];expectedParam=wantedParam^((mode&1)?0x5A5A5A5Au:0);
  copy(wantedA,(u8*)&D_800A5970,12);copy(wantedB,(u8*)&D_800A597C,12);
  for(i=0;i<12;i++){expectedA[i]=wantedA[i]^((mode&1)?90:0);expectedB[i]=wantedB[i]^((mode&1)?90:0);}
  for(i=0;i<128;i++)actor[i]=expectedActor[i]=(u8)(n+i*17);if((mode&4)&&wantedOwner)expectedActor[3]^=85;
  calls=error=0;fn(wantedOwner);if(calls!=1||error||word(D_800A5E58)!=expectedParam)return 1;
  for(i=0;i<12;i++)if(((u8*)&D_800A5970)[i]!=expectedA[i]||((u8*)&D_800A597C)[i]!=expectedB[i])return 2;
  for(i=0;i<128;i++)if(actor[i]!=expectedActor[i])return 3;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,name in enumerate(controls()):t+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class TwoVectorEffectTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>49I',cls.rom,source.ROM));cls.images=[]
  for filename in('qualified-padded.o','selected.o'):
   local=cls.fresh/filename;local.write_bytes((cls.out/filename).read_bytes());blob,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.images.append(list(struct.unpack_from('>49I',blob,functions[source.FUNCTION]['value'])))
  cls.words,cls.raw=cls.images
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=None,s=None):
  initial=fixture(c,s);wanted,calls,obs=call_reference(initial,c,s);pair=[]
  for words in images or(self.truth,self.words,self.raw):
   m=EffectOracle(words,initial,c,entry=entry,s=s).run();self.assertEqual((public(m.memory),m.calls,m.effect_observations),(public(wanted),calls,obs),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);blob=sections(p.with_suffix('.elf'))['.text'][1];length=functions[source.FUNCTION]['size'];return list(struct.unpack('>%dI'%(length//4),blob[:length]))
 def test_01_owner_actual_Make_census_and_ABI(self):
  self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.payload(self.out/'selected.o'),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),4);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),78)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),77);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual((self.out/'proposed-owner.c').read_text().count('#pragma GLOBAL_ASM'),0);commands=json.loads((self.out/'Make-commands.json').read_text());self.assertEqual(len(commands),3);self.assertFalse(any('-loopunroll'in x for row in commands for x in row))
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22F5C0]);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws))
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=49,frame=96,bindings=7,guards=0,neighbors=77,compact_functions=78,Make_commands=3,GLOBAL_ASM=0,normal_profile=True,selected_diagnostics=0,inherited_owner_warnings=4,additional_warnings=0,arguments=1,provider_arguments=16,void_return=True)
 def test_02_guest_vectors_all_arguments_aliases_and_mutations(self):
  count=0;seen=set()
  for seed,mode,phase,owner in itertools.product(range(256),(0,1,2,7),(0,8),(0,OWNER)):
   m=self.compare(Case(owner=owner,seed=seed,mode=mode,phase=phase));seen.update(m.visits);count+=1
  for owner,answer,mode,phase in itertools.product((1,3,0x7FFFFFFF,0x80000000,0xFFFFFFFC,0xFFFFFFFF),(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,7),(0,8)):
   self.compare(Case(owner=owner,answer=answer,mode=mode,phase=phase));count+=1
  for phase,mode,layout in itertools.product((0,8),(0,7),range(3)):
   sp=STACK+phase-96;s=oracle.symbols();s.update(D_800A5970=sp+72,D_800A597C=sp+84)
   if layout==1:s['D_800A597C']=sp+80
   if layout==2:s['D_800A5E58']=sp+84
   self.compare(Case(seed=17,mode=mode,phase=phase),s=s,images=[self.rebased(self.out/'selected.o',source.ENTRY,s,'alias-%d-%d-%d'%(phase,mode,layout))]);count+=1
  self.assertTrue(set(range(source.ENTRY,source.ENTRY+196,4))<=seen);self.receipt['guest']=dict(cases=count,visited_words=49,complete_state_trace_equal=True,all_16_arguments=True,distinct_vector_snapshots=True,arbitrary_float_bits_guest=True,source_and_local_mutations=True,guest_stack_alias_layouts=3,portable_stack_alias_claimed=False)
 def test_03_original_callback_routes_and_effect_provider(self):
  table=self.rom[0x22F530:0x22F618];self.assertEqual(len(table),232);self.assertEqual(struct.unpack('>58I',table)[36],source.ENTRY);pos=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],source.TABLE,232);self.assertEqual(self.values['conker/build/conker.us.elf'][pos:pos+232],table)
  windows=((0x1514D230,0x1514D270),(0x1514D270,0x1514D2AC),(0x1514D2AC,0x1514D2F8));count=0;seen=set()
  for start,end in windows:
   body=list(struct.unpack_from('>%dI'%((end-start)//4),self.rom,start-0x15000000+0x2D4B0))
   for enabled,selector,phase,mode in itertools.product((0,1),(0,36),(0,8),(0,7)):
    c=Case(phase=phase,mode=mode);initial=fixture(c);sp=STACK+phase
    for off in(0x3C,0x40,0x44):put(initial,sp+off,0)
    put(initial,sp+0x48,OWNER)
    for i,b in enumerate(table):initial[source.TABLE+i]=b
    initial[0x800A5ED8]=selector;initial[0x800A5EC0]=selector;put(initial,0x8008AB90,0x90000);initial[0x90000]=selector;pair=[]
    for target in(self.truth,self.words,self.raw):
     m=EffectOracle(body,initial,c,entry=start,connected={source.ENTRY+i*4:w for i,w in enumerate(target)});m.r[2]=m.r[3]=7 if enabled else 0;m.r[16]=2 if enabled else 0;m.r[17]=1;ends=(end,0x1514D2FC)if start==0x1514D2AC else(end,)
     for stop in ends:m.code[stop]=0
     m.code=WindowCode(m.code,m);m.code.ends=ends
     with self.assertRaises(WindowBoundary):m.run()
     pair.append(m);seen.update(m.visits)
    for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
    entered=bool(enabled and selector);expected,calls,obs=call_reference(initial,c)if entered else(initial,[],[]);self.assertEqual((public(pair[0].memory),pair[0].calls,pair[0].effect_observations),(public(expected),([(source.ENTRY,(OWNER,))]if entered else[])+calls,obs));count+=1
  self.assertTrue(set(p for start,end in windows for p in range(start,end,4))<=seen)
  provider=list(struct.unpack_from('>85I',self.rom,0x18E18C));integration=0;provider_seen=set()
  for owner,allocated,alias,phase,mode,seed in itertools.product((0,OWNER),(False,True),(False,True),(0,8),(0,1),(0,19)):
   c=Case(owner=owner,allocated=allocated,alias_output=alias,phase=phase,mode=mode,seed=seed);initial=fixture(c);mcopy,calls,obs=call_reference(initial,replace(c,mode=0));args=obs[0][0]
   # Only the two local copies precede the original provider; mock public effects are discarded.
   for a in initial:
    if not STACK-2048<=a<STACK+512:mcopy[a]=initial[a]
   expected,pcalls,pobs,result=provider_reference(mcopy,args,c,STACK+phase-96);pair=[]
   for target in(self.truth,self.words,self.raw):
    m=EffectOracle(target,initial,c,connected={source.EFFECT+i*4:w for i,w in enumerate(provider)}).run();pair.append(m);provider_seen.update(m.visits)
   for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
   self.assertEqual((public(pair[0].memory),pair[0].calls,pair[0].factory_observations,pair[0].r[2]),(public(expected),calls+pcalls,pobs,result));integration+=1
  # Broaden only the original provider argument flags and signed halfword boundary.
  for first,second,duration,owner,allocated in itertools.product((0,1,255),(0,1,255),(0,0xFFFF8000,0xFFFFFFFF,32767),(0,OWNER),(False,True)):
   c=Case(owner=owner,allocated=allocated);initial=fixture(c);args=(owner,255,source.VEC_A,source.VEC_B,0x80000000,255,duration,1,2,3,4,first,0xA5,second,255,0xFFFFFFFF)
   for i,v in enumerate(args[4:],4):put(initial,STACK+i*4,v)
   expected,calls,obs,result=provider_reference(initial,args,c,STACK);m=EffectOracle(provider,initial,c,entry=source.EFFECT,arguments=args[:4]).run();provider_seen.update(m.visits);self.assertEqual((public(m.memory),m.calls,m.factory_observations,m.r[2]),(public(expected),calls,obs,result));integration+=1
  self.assertTrue(set(range(source.EFFECT,source.EFFECT+340,4))<=provider_seen)
  self.receipt['integration']=dict(original_caller_windows=3,caller_window_cases=count,caller_words=50,all_caller_window_words_visited=True,registered_index=36,table_entries=58,provider_words=85,provider_cases=integration,all_provider_words_visited=True,parent_and_provider_C_placeholders_uncredited=True,bounded_providers=['func_151602C0','memcpy'],null_owner_allocation_failure_and_success=True,payload_bytes=40,padding_preserved=True)
 def test_04_native32_16_arguments_defined_C_and_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());rows=[]
  for opt in('-O0','-O2','-O3'):
   target=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+[str(p),'-o',str(target)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stdout+build.stderr);run=subprocess.run([str(target)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stdout,run.stderr));rows.append(dict(profile=opt,cases=65536,negative_controls=18,UBSan_trap=True,quiet_NaN_and_finite_values=True,local_source_and_owner_effects=True))
  self.receipt['native']=rows
 def test_05_fault_prefixes_and_bounded_helper_order(self):
  cuts=0
  for c in(Case(),Case(owner=0),Case(mode=7,seed=19,phase=8)):
   good=self.compare(c)
   for cut in range(good.all_accesses):
    pair=[]
    for words in(self.truth,self.words,self.raw):
     m=EffectOracle(words,fixture(c),c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(m.current_pc,m.delay_of))
    cuts+=1
  provider=list(struct.unpack_from('>85I',self.rom,0x18E18C));connected={source.EFFECT+i*4:w for i,w in enumerate(provider)};integrated=0
  for c in(Case(owner=0),Case(allocated=False),Case(alias_output=True,mode=1)):
   good=EffectOracle(self.truth,fixture(c),c,connected=connected).run()
   for cut in range(good.all_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=EffectOracle(words,fixture(c),c,connected=connected);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);integrated+=1
  self.receipt['faults']=dict(prefix_triples=cuts,integrated_provider_prefix_pairs=integrated,complete_state_trace_PC_delay_equal=True,portable_C_fault_semantics_claimed=False)
 def test_06_padder_GNU_rebases_and_relocation_rejections(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'))
  for damaged,bindings in((raw[:-4],rs),(raw[:60]+bytes([raw[60]^1])+raw[61:],rs),(raw,{**rs,172:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.normalized_payload(damaged,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,(entry,a,b,param)in enumerate(((source.ENTRY,source.VEC_A,source.VEC_B,source.PARAM),(0x17007FFC,0x80017FFC,0x80028000,0x80037FFC),(0x2500FFFC,0x8001FFFC,0x80030000,0x80048000))):
   s=dict(D_800A5970=a,D_800A597C=b,D_800A5E58=param,func_15160CDC=source.EFFECT if j==0 else entry+0x10004);images=[self.rebased(p,entry,s,'rebase-%d-%d'%(j,k))for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_179F30.c.o',self.out/'selected.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for owner,seed,mode,phase in itertools.product((0,OWNER),(0,1,19),(0,7),(0,8)):self.compare(Case(owner=owner,seed=seed,mode=mode,phase=phase),images,entry,s);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,bindings=7,guards=0,actual_Make_raw_and_retail=True,HI16_LO16_carries=True,raw_binding_rejections=3)
 def test_07_actually_compiled_semantic_negatives(self):
  witnesses=(Case(),Case(owner=0),Case(seed=19,mode=7))
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,oracle.symbols(),'negative-link-'+name);effective=False
   for c in witnesses:
    initial=fixture(c);wanted,calls,obs=call_reference(initial,c)
    try:m=EffectOracle(words,initial,c).run();different=(public(m.memory),m.calls,m.effect_observations)!=(public(wanted),calls,obs)
    except (AssertionError,KeyError):different=True
    if different:effective=True;break
   self.assertTrue(effective,name)
  self.receipt['compiled_control']=dict(IDO_negatives=18,all_16_argument_positions_checked=True,local_copy_and_null_call_controls=True)
 def test_08_strict_entire_image_and_named_metadata_permutations(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+196];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,196);named={n:(p,f)for p,n,f,_ in source.symbol_rows(before)};positions=[20,at,at+180,at+196,source.elf_slot_offset(before,source.TABLE,232)+144,named[source.FUNCTION][0]+8]
  groups=(('D_80099530','D_80095B30','D_8009EF30'),('D_800A5E58','D_800A1B58'),('func_1502AAF8','D_8009E7F0'),('D_800A5970','D_800A1670','D_80097C20'))
  off=struct.unpack_from('>I',before,32)[0];sz,count=struct.unpack_from('>HH',before,46);hs=[struct.unpack_from('>10I',before,off+i*sz)for i in range(count)];sym=next(h for h in hs if h[1]==2);strings=hs[sym[6]]
  for group in groups:
   for n in group:positions.append(named[n][0]+4)
   positions.append(strings[4]+named[group[0]][1][0])
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(v['conker/retail_word_patches.us.csv'],(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),226);self.receipt['image']=dict(changed_bytes=226,code_bytes=149,symbol_bytes=36,string_bytes=41,closed_symbol_groups=4,exclusions=0,effective_corruptions=len(positions)+1,all_named_definitions_preserved_except_target_extent=True,entire_guard_manifest_unchanged=True,new_guards=0,protected_bytes=189088)
