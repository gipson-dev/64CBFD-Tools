"""Direct selector payload C: full owner, semantic, native32, original helpers and image gates."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_selector_payload_effect_match as source
from tools.tests import game_selector_payload_effect_oracle as oracle
from tools.tests.game_selector_payload_effect_oracle import Case,fixture,reference,public,SelectorOracle,ACTOR,EFFECT,RECORD,FIND,ALLOC,STACK,put,read,faults
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 return dict(wrong_category=b.replace('== 6','== 5'),wrong_ids=b.replace('command - 0x49','0'),wrong_row=b.replace('variant = 1','variant = 0'),ignore_lookup=b.replace(' != 0',' == 0'),wrong_kind=b.replace('= 23;','= 22;'),wrong_duration=b.replace('= 300;','= 299;'),wrong_size=b.replace('sizeof(payload), 255','sizeof(payload)-4, 255'),wrong_slot=b.replace(', 255,',', 254,'),wrong_context=b.replace(', 255, 1',', 255, 0'),skip_copy=b.replace('if (effect != NULL)','if (effect == NULL)'),short_copy=b.replace('&payload, sizeof(payload));','&payload, sizeof(payload)-4);'),wrong_destination=b.replace('+ 0x18','+ 0x14'))

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+r'''
EffectSelectorTable36680 D_80082BEC;s32 D_800BE9F0;
typedef char ABI[(sizeof(void*)==4&&sizeof(UnkB060C)==24&&sizeof(Header)==6&&sizeof(EffectSelectorTable36680)==6&&__builtin_offsetof(UnkB060C,record)==8&&__builtin_offsetof(Header,unk2)==2&&__builtin_offsetof(Header,pad5)==5&&__builtin_offsetof(struct225,unk14)==20)?1:-1];
static union {u32 align;u8 b[160];} actor,output,expected;
static u32 mode,seed,calls,error,lookupOK,allocated,wantedId;static UnkB060C *savedPayload;
s32 func_150B060C(u8 id,UnkB060C*p){u32 i;calls++;savedPayload=p;if(calls!=1||id!=wantedId)error=1;for(i=0;i<24;i++)((u8*)p)[i]=(u8)(i*29+seed+id);if(mode&1)D_800BE9F0=(s32)0x87654321u;if(mode&2)for(i=0;i<6;i++)((u8*)&D_80082BEC)[i]^=255;if(mode&4)actor.b[3]^=85;return lookupOK?(s32)lookupOK:0;}
struct225 *func_1516037C(Header*h,struct226*a,s32 size,u8 slot,s32 context){u32 i;calls++;if(calls!=2||h->unk0||h->unk1!=23||h->unk2!=300||h->unk4||a!=(struct226*)actor.b||size!=24||slot!=255||context!=1)error=1;if(mode&8)for(i=0;i<24;i++)((u8*)savedPayload)[i]^=165;return allocated?(struct225*)(output.b+32):0;}
void *memcpy(void*a,const void*b,u32 n){u32 i;calls++;if(calls!=3||a!=output.b+56||b!=savedPayload||n!=24){error=1;return a;}for(i=0;i<n;i++)((u8*)a)[i]=((const u8*)b)[i];return a;}
'''
 for name,body in dict(selected=source.SELECTED,**controls()).items():t+=body.replace('void '+source.FUNCTION,'void test_'+name)+'\n'
 t+=r'''
typedef void(*Fn)(struct226*,s32);
static int check(Fn fn){u32 n,i,j,command,cat,wantCalls;u8 oldIds[6];
 for(n=0;n<256;n++)for(j=0;j<192;j++){
  seed=n;mode=j&15;lookupOK=(j&16)?0:(j&32)?0xFFFFFFFFu:1;allocated=(j&64)!=0;command=0x49+(j%3);cat=(j%4)==0?6:(j%4)==1?0:(j%4)==2?5:0xFFFFFFFFu;
  for(i=0;i<160;i++){actor.b[i]=(u8)(i*13+n);output.b[i]=(u8)(i*17+n);expected.b[i]=output.b[i];}
  for(i=0;i<6;i++){oldIds[i]=(u8)(n+i*71);((u8*)&D_80082BEC)[i]=oldIds[i];}D_800BE9F0=(s32)cat;wantedId=oldIds[(cat==6?3:0)+command-0x49];
  wantCalls=1+(lookupOK?1+allocated:0);if(lookupOK&&allocated)for(i=0;i<24;i++)expected.b[56+i]=(u8)((i*29+seed+wantedId)^((mode&8)?165:0));
  calls=error=0;fn((struct226*)actor.b,(s32)command);if(error||calls!=wantCalls)return 1;
  for(i=0;i<160;i++)if(output.b[i]!=expected.b[i]||actor.b[i]!=(u8)((i*13+n)^((i==3&&(mode&4))?85:0)))return 1;
  if((u32)D_800BE9F0!=((mode&1)?0x87654321u:cat))return 1;for(i=0;i<6;i++)if(((u8*)&D_80082BEC)[i]!=(u8)(oldIds[i]^((mode&2)?255:0)))return 1;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,name in enumerate(controls()):t+='if(!check(test_'+name+'))return '+str(i+20)+';\n'
 return t+'return 0;}\n'+START

class SelectorPayloadEffectTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>49I',cls.rom,source.ROM));cls.images=[]
  for filename in('qualified-padded.o','selected.o'):
   local=cls.fresh/filename;local.write_bytes((cls.out/filename).read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.images.append(list(struct.unpack_from('>49I',data,functions[source.FUNCTION]['value'])))
  cls.words,cls.raw=cls.images
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,ids=source.IDS,category=source.CATEGORY,lookup=source.LOOKUP,factory=source.FACTORY,copy=source.COPY):
  initial=fixture(c,ids,category);wanted,calls,observations=reference(initial,c,ids=ids,category=category,lookup=lookup,factory=factory,copy=copy);pair=[]
  for words in images or(self.truth,self.words,self.raw):
   m=SelectorOracle(words,initial,c,entry,ids=ids,category=category,lookup=lookup,factory=factory,copy=copy).run();self.assertEqual((public(m.memory),m.calls,m.header_observations),(public(wanted),calls,observations),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);data=sections(p.with_suffix('.elf'))['.text'][1];length=functions[source.FUNCTION]['size'];return list(struct.unpack('>%dI'%(length//4),data[:length]))
 def test_01_owner_Make_census_and_source_ABI(self):
  self.assertEqual(self.words,self.truth);self.assertEqual(self.raw,self.truth);self.assertEqual(source.payload(self.out/'selected.o'),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),6);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),82)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),81);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(proposed,source.recovered_owner(self.values[source.SOURCE].decode()));self.assertIn('void func_1500A6D8(struct226 *actor, s32 command)',proposed);self.assertEqual(proposed.count('#pragma GLOBAL_ASM'),1);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x2277E0,0x2277E4,0x2277E8]);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws))
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(raw_words=49,frame=80,bindings=7,guards=0,neighbors=81,compact_functions=82,Make_commands=5,selected_diagnostics=0,inherited_owner_warnings=6,additional_warnings=0,legacy_cast_calls=3,arguments=2,void_return=True,callback_slots=[73,74,75])
 def test_02_guest_selection_null_mutations_and_payload(self):
  count=0;visits=set()
  for command,category,lookup,allocated,phase in itertools.product((73,74,75),(0,5,6,7,0x80000000,0xFFFFFFFF),(0,1,0xFFFFFFFF),(False,True),(0,8)):
   m=self.compare(Case(command=command,category=category,lookup=lookup,allocated=allocated,phase=phase));visits.update(m.visits);count+=1
  for seed,command in itertools.product(range(256),(73,74,75)):self.compare(Case(command=command,seed=seed));count+=1
  for mode,alias,lookup,allocated in itertools.product(range(16),(False,True),(0,1),(False,True)):self.compare(Case(mode=mode,alias=alias,lookup=lookup,allocated=allocated));count+=1
  self.assertTrue(set(range(source.ENTRY,source.ENTRY+196,4))<=visits);self.receipt['guest']=dict(cases=count,visited_words=49,all_selector_bytes=True,header_padding_retained=True,helper_side_effects_and_output_alias=True,complete_state_and_trace_equal=True)
 def test_03_complete_original_caller_and_helpers(self):
  parent=list(struct.unpack_from('>17I',self.rom,0x37DFC));lookup=list(struct.unpack_from('>39I',self.rom,0xDDABC));factory=list(struct.unpack_from('>32I',self.rom,0x18D82C));table=list(struct.unpack_from('>89I',self.rom,0x2276BC));self.assertEqual(table[73:76],[source.ENTRY]*3)
  for va,at,size in((source.PARENT,0x37DFC,68),(source.TABLE,0x2276BC,356),(source.LOOKUP,0xDDABC,156),(source.FACTORY,0x18D82C,128)):
   pos=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],va,size);self.assertEqual(self.values['conker/build/conker.us.elf'][pos:pos+size],self.rom[at:at+size])
  count=0;visited=set();helper_words=set()
  for command,category,lookup_ok,allocated,phase in itertools.product((-1,0,73,74,75,89),(0,6),(0,1),(False,True),(0,8)):
   c=Case(command=command,category=category,lookup=lookup_ok,allocated=allocated,phase=phase);initial=fixture(c)
   for i,v in enumerate(table):put(initial,source.TABLE+i*4,v)
   pair=[]
   for target in(self.truth,self.words):
    m=SelectorOracle(parent,initial,c,source.PARENT,connected={base+i*4:w for base,body in ((source.ENTRY,target),(source.LOOKUP,lookup),(source.FACTORY,factory)) for i,w in enumerate(body)}).run();pair.append(m);visited.update(m.visits)
   self.assertEqual(complete(pair[0]),complete(pair[1]));m=pair[0];expected=dict(initial)
   if command in(73,74,75):
    self.assertEqual(m.calls[0],(source.ENTRY,(ACTOR,command)));self.assertEqual(m.calls[1],(source.LOOKUP,((7,8,9,8,9,10)[(3 if category==6 else 0)+command-73],STACK+phase-56)))
    self.assertEqual(m.calls[2][0],FIND)
    if lookup_ok and allocated:
     p=EFFECT;entered=STACK+phase-24;header=entered-8
     for i,v in enumerate((0,23,1,44,0,initial[header+5])):expected[p+14+i]=v
     put(expected,p+20,ACTOR)
     for i,v in enumerate((0xC3160000,0x40900000,RECORD,0xC7000000,0xBF800000,0x46FFFE00)):put(expected,p+24+i*4,v)
     self.assertIn((ALLOC,(53,1,48,1,255,1)),m.calls)
    else:self.assertFalse(any(t==source.COPY and a[2]==24 for t,a in m.calls))
   else:self.assertFalse(m.calls)
   self.assertEqual(public(m.memory),public(expected));count+=1
  for start,size in((source.ENTRY,196),(source.LOOKUP,156),(source.FACTORY,128)):self.assertTrue(set(range(start,start+size,4))<=visited)
  # A valid null callback takes the caller's branch-likely delay slot.
  c=Case(command=73);initial=fixture(c)
  for i in range(89):put(initial,source.TABLE+i*4,0)
  m=SelectorOracle(parent,initial,c,source.PARENT).run();visited.update(m.visits);self.assertFalse(m.calls);self.assertTrue(set(range(source.PARENT,source.PARENT+68,4))<=visited)
  self.receipt['integration']=dict(cases=count+1,parent_words=17,lookup_words=39,factory_words=32,all_words_visited=True,actual_callback_arguments=True,three_callback_slots=True,providers_bounded=['func_151149AC','func_15167A68','memcpy'],signed_coordinate_endpoints=True)
 def test_04_native32_optimization_and_semantic_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());rows=[]
  for opt in('-O0','-O2','-O3'):
   target=self.fresh/('native'+opt);cmd=native_command(opt)+[str(p),'-o',str(target)];build=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stdout+build.stderr);run=subprocess.run([str(target)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stdout,run.stderr));rows.append(dict(profile=opt,cases=49152,negative_controls=12,UBSan_trap=True))
  self.receipt['native']=rows
 def test_05_fault_prefixes_and_lazy_failure_paths(self):
  cuts=0
  for c in(Case(lookup=0),Case(allocated=False),Case(),Case(command=75,mode=15,alias=True,phase=8)):
   good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=SelectorOracle(words,fixture(c),c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
  for lookup,allocated in((0,False),(1,False)):
   c=Case(lookup=lookup,allocated=allocated);m=fixture(c)
   for i in range(24):m.pop(EFFECT+24+i)
   for w in(self.truth,self.words):SelectorOracle(w,m,c).run()
  self.receipt['faults']=dict(prefix_pairs=cuts,complete_state_trace_PC_delay_equal=True,failed_paths_do_not_touch_output=True)
 def test_06_direct_payload_padder_and_GNU_rebases(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));self.assertEqual(source.normalized_payload(raw,rs),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for damaged,bindings in((raw[:-4],rs),(raw[:120]+bytes([raw[120]^1])+raw[121:],rs),(raw,{**rs,96:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.checked_payload(damaged,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/'conker/retail_layout.us.txt',source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  layouts=((source.ENTRY,source.IDS,source.CATEGORY),(0x17007FFC,0x80017FFC,0x80028000),(0x2500FFFC,0x8001FFFC,0x80030000))
  for j,(entry,ids,category)in enumerate(layouts):
   lookup,factory,copy=(source.LOOKUP,source.FACTORY,source.COPY)if j==0 else(entry+0x10004,entry+0x20008,entry+0x3000C);symbols=dict(func_150B060C=lookup,func_1516037C=factory,memcpy=copy,D_80082BEC=ids,D_800BE9F0=category);images=[self.rebased(p,entry,symbols,'rebase-%d-%d'%(j,k))for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game_36680.c.o',self.out/'selected.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for command,cat,found,allocated in itertools.product((73,74,75),(0,6),(0,1),(False,True)):self.compare(Case(command=command,category=cat,lookup=found,allocated=allocated),images,entry,ids,category,lookup,factory,copy);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,bindings=7,guards=0,actual_Make_and_raw=True,HI16_LO16_carries=True,raw_binding_negatives=3)
 def test_07_compiled_IDO_semantic_negatives(self):
  witnesses=[Case(),Case(category=0),Case(command=74),Case(command=75),Case(lookup=0),Case(allocated=False)]
  symbols=dict(func_150B060C=source.LOOKUP,func_1516037C=source.FACTORY,memcpy=source.COPY,D_80082BEC=source.IDS,D_800BE9F0=source.CATEGORY)
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,symbols,'negative-link-'+name);effective=False
   for c in witnesses:
    wanted,calls,obs=reference(fixture(c),c)
    try:m=SelectorOracle(words,fixture(c),c).run();different=(public(m.memory),m.calls,m.header_observations)!=(public(wanted),calls,obs)
    except (AssertionError,KeyError):different=True
    if different:effective=True;break
   self.assertTrue(effective,name)
  self.receipt['compiled_control']=dict(IDO_semantic_negatives=12,independent_reference_failures=True)
 def test_08_strict_entire_image_extent_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+196];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,196);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+196,source.elf_slot_offset(before,source.TABLE,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),v['conker/retail_word_patches.us.csv']);self.assertEqual(sum(x!=y for x,y in zip(before,expected)),149);self.receipt['image']=dict(changed_bytes=149,code_bytes=148,size_bytes=1,exclusions=0,effective_corruptions=6,all_named_definitions_checked=True,protected_bytes=189088,guard_manifest_unchanged=True)
