"""Direct owner timeout C: caller/helper integration, wrap, aliases, native32 and strict image."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_owner_timeout_transition_match as source
from tools.tests import game_owner_timeout_transition_oracle as oracle
from tools.tests.game_owner_timeout_transition_oracle import Case,fixture,reference,public,TimeoutOracle,RECORD,OWNER,ALT,RESULT,EXIT_TABLE,RESET,EFFECT,FACTORY,STACK,put,read,half,faults
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 return dict(inverted_live=b.replace('*(s32 *)payload->owner == 0','*(s32 *)payload->owner != 0'),wrong_identity=b.replace('owner[0x3B]','owner[0x3A]'),wrong_state=b.replace('!= 0x7C','!= 0x7D'),no_tick=b.replace('(u32)payload->elapsed + (u32)D_800BE9E4','(u32)payload->elapsed'),subtract_tick=b.replace('+ (u32)D_800BE9E4','- (u32)D_800BE9E4'),unsigned_threshold=b.replace('payload->elapsed > 200','(u32)payload->elapsed > 200U'),early_threshold=b.replace('payload->elapsed > 200','payload->elapsed >= 200'),wrong_duration=b.replace('payload->owner, 300,','payload->owner, 299,'),wrong_group=b.replace('record[0xC], record[1]','record[1], record[1]'),keep_global=b.replace('D_800E0920 = NULL;',''),wrong_lifetime=b.replace('= -1;','= 0;'),wrong_flag=b.replace('record[0xD] |= 1','record[0xD] |= 2'))

def native_harness():
 prefix,body=source.SELECTED.split('void '+source.FUNCTION,1)
 t=source.HEADERS+source.DECLARATIONS+prefix+r'''
s32 D_800BE9E4;u8 *D_800E0920;
typedef struct{s32 live;u8 pad4[55];u8 id;u8 pad3C[72];u16 state;u8 tail[26];}Owner;
typedef struct{u8 kind,context,pad2[10],group,flags;s16 life;u8 pad10[24];OwnerTimeoutPayload1CA420 payload;u8 tail[28];}Record;
typedef char ABI[(sizeof(void*)==4&&sizeof(Record)==80&&sizeof(Owner)==160&&sizeof(OwnerTimeoutPayload1CA420)==12&&__builtin_offsetof(Record,payload)==40&&__builtin_offsetof(Record,flags)==13&&__builtin_offsetof(Record,life)==14&&__builtin_offsetof(Owner,id)==59&&__builtin_offsetof(Owner,state)==132)?1:-1];
static struct{u32 left[4];Record record;u32 right[4];}actual,expected;
static struct{u32 left[4];Owner owner;u32 right[4];}linked,saved;static Owner other;
static u32 mode,calls,error,wantedGroup,wantedContext;static u8*wantedOwner;
static void effect(Record*r){if(mode&1){r->flags^=128;r->life=123;}if(mode&2){r->payload.owner=(u8*)&other;r->group^=85;r->context^=170;r->payload.elapsed=(s32)0x87654321u;}}
void func_1519E3BC(u8*p,s16 duration,u8 group,s32 context){calls++;if(p!=wantedOwner||duration!=300||group!=wantedGroup||context!=(s32)wantedContext)error=1;effect(&actual.record);if(mode&16)D_800E0920=(u8*)&other;}
'''
 for n,b in dict(selected=source.SELECTED,**controls()).items():t+='void test_'+n+b.split('void '+source.FUNCTION,1)[1]+'\n'
 t+=r'''
typedef void(*Update)(u8*);
static int check(Update fn){const u32 values[]={0,1,199,200,201,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};u32 n,k,i,retire,submit;u8*p=(u8*)&actual,*q=(u8*)&expected;u8*wantedGlobal;
 for(n=0;n<65536;n++)for(k=0;k<8;k++){
  for(i=0;i<sizeof(actual);i++)p[i]=(u8)(i*13+n*7+k);for(i=0;i<sizeof(linked);i++)((u8*)&linked)[i]=(u8)(i*17+n);
  linked.owner.live=k==0?0:(s32)(1u<<((n>>8)&31));linked.owner.id=(u8)(n>>8);linked.owner.state=k==2?124:k==3?125:k==4?123:k==5?65535:0;saved=linked;
  actual.record.payload.owner=(u8*)&linked.owner;actual.record.payload.identity=(u8)(linked.owner.id^(k==1));actual.record.payload.elapsed=(s32)values[(n>>8)&7];actual.record.life=(s16)n;actual.record.flags=(u8)n;actual.record.group=(u8)(n*17u);actual.record.context=(u8)(n*31u+3);mode=((n>>1)&3)|((k&1)?16:0);D_800BE9E4=(s32)values[(n>>11)&7];D_800E0920=(u8*)&actual.record;
  expected=actual;retire=!linked.owner.live||actual.record.payload.identity!=linked.owner.id;submit=0;wantedGlobal=(u8*)&actual.record;
  if(!retire){expected.record.payload.elapsed=(s32)((u32)expected.record.payload.elapsed+(u32)D_800BE9E4);if(linked.owner.state!=124){retire=1;submit=expected.record.payload.elapsed>200;}}
  if(submit){wantedOwner=expected.record.payload.owner;wantedGroup=expected.record.group;wantedContext=expected.record.context;effect(&expected.record);if(mode&16)wantedGlobal=(u8*)&other;}
  if(retire){wantedGlobal=0;expected.record.life=-1;expected.record.flags|=1;}
  calls=error=0;fn((u8*)&actual.record);if(error||calls!=submit||D_800E0920!=wantedGlobal)return 1;
  for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 1;for(i=0;i<sizeof(linked);i++)if(((u8*)&linked)[i]!=((u8*)&saved)[i])return 1;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,n in enumerate(controls()):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START

class OwnerTimeoutTransitionTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>49I',cls.rom,source.ROM));cls.images=[]
  for filename in('qualified-padded.o','selected.o'):
   local=cls.fresh/filename;local.write_bytes((cls.out/filename).read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.images.append(list(struct.unpack_from('>49I',data,functions[source.FUNCTION]['value'])))
  cls.words,cls.raw=cls.images
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,helper=source.HELPER,ticks=source.TICKS,slot=source.SLOT):
  initial=fixture(c,ticks,slot);wanted,calls=reference(initial,c,ticks=ticks,slot=slot);calls=[(helper if t==source.HELPER else t,a)for t,a in calls];pair=[]
  for words in images or(self.truth,self.words,self.raw):
   m=TimeoutOracle(words,initial,c,entry,helper=helper,slot=slot).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);data=sections(p.with_suffix('.elf'))['.text'][1];length=functions[source.FUNCTION]['size'];return list(struct.unpack('>%dI'%(length//4),data[:length]))
 def test_01_owner_Make_census_and_source_ABI(self):
  self.assertEqual(self.words,self.truth);self.assertEqual(self.raw,self.truth);self.assertEqual(source.payload(self.out/'selected.o'),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),23)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),22);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(proposed,source.recovered_owner(self.values[source.SOURCE].decode()));self.assertIn('void func_1519E754(u8 *record)',proposed);self.assertNotIn('#pragma GLOBAL_ASM',proposed);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22EFCC]);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws))
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(raw_words=49,body_words=49,frame=40,bindings=5,guards=0,neighbors=22,compact_functions=23,Make_commands=3,selected_diagnostics=0,owner_diagnostics=0,arguments=1,void_return=True,callback_table='D_8008A4E8',callback_slot=9)
 def test_02_guest_wrap_lazy_reads_aliases_and_saved_retire(self):
  count=0;visits=set()
  for live,same,state,elapsed,ticks,phase in itertools.product((0,1),(False,True),(0,124,65535),(0,199,200,201,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,0xFFFFFFFF,0x80000000),(0,8)):
   m=self.compare(Case(live=live,same=same,state=state,elapsed=elapsed,ticks=ticks,phase=phase));visits.update(m.visits);count+=1
  for byte in range(256):self.compare(Case(flags=byte,byte=byte,lifetime=byte*257));count+=1
  for mode,phase in itertools.product(range(32),(0,8)):self.compare(Case(mode=mode,phase=phase));count+=1
  for alias,live,same,state in itertools.product(range(1,4),(0,1),(False,True),(0,124)):self.compare(Case(alias=alias,live=live,same=same,state=state));count+=1
  self.assertTrue(set(range(source.ENTRY,source.ENTRY+196,4))<=visits);self.receipt['guest']=dict(cases=count,visited_words=49,all_flag_and_group_context_bytes=True,owner_record_alias_layouts=4,signed_timer_and_unsigned_wrap=True,helper_public_mutations=True,saved_retire_byte_mutation_guest_only=True,direct_C_complete_state_and_trace_equal=True)
 def test_03_complete_original_dispatcher_and_retained_effect_helper(self):
  table=list(struct.unpack_from('>98I',self.rom,0x22EFA8));exits=list(struct.unpack_from('>10I',self.rom,0x22EF80));self.assertEqual(table[9],source.ENTRY);elf=self.values['conker/build/conker.us.elf'];parent=list(struct.unpack_from('>45I',self.rom,0x176714));helper=list(struct.unpack_from('>42I',self.rom,0x1CB86C))
  for va,rom_at,size in((source.PARENT,0x176714,180),(source.TABLE,0x22EFA8,392),(source.HELPER,0x1CB86C,168)):
   at=source.elf_slot_offset(elf,va,size);self.assertEqual(elf[at:at+size],self.rom[rom_at:rom_at+size])
  count=0;seen=set()
  for selector,destructor,flags,life,ticks,state,elapsed in itertools.product((-1,9),(-1,0),(0,1),(-1,0,32767),(0,1,30),(0,124),(199,201)):
   c=Case(flags=flags,lifetime=life,ticks=ticks,state=state,elapsed=elapsed);initial=fixture(c);initial[RECORD+17]=selector&255;initial[RECORD+16]=destructor&255
   for i,v in enumerate(table):put(initial,source.TABLE+i*4,v)
   for i,v in enumerate(exits):put(initial,EXIT_TABLE+i*4,v)
   wanted=dict(initial);calls=[]
   if flags&1:put(wanted,RECORD+14,(life-ticks)&65535,2)
   if selector!=-1:calls.append((source.ENTRY,(RECORD,)));wanted,more=reference(wanted,c,STACK+c.phase-24);calls+=more
   if half(read(wanted,RECORD+14,2))<0:
    if destructor!=-1:calls.append((exits[destructor],(RECORD,)))
    calls.append((source.FREE,(RECORD,)));oracle.free_effect(wanted,RECORD)
   pair=[]
   for w in(self.truth,self.words):
    m=TimeoutOracle(parent,initial,c,source.PARENT,{source.ENTRY+4*i:v for i,v in enumerate(w)},callbacks=exits).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls));seen.update(m.visits);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
  self.assertTrue(set(range(source.PARENT,source.PARENT+180,4))<=seen);hcount=0;hseen=set()
  for byte,mode,phase in itertools.product((0,1,127,128,255),(0,1,2,3,16),(0,8)):
   c=Case(byte=byte,mode=mode,phase=phase);initial=fixture(c);wanted,calls=reference(initial,c);actor,duration,group,context=calls[0][1];calls.extend(((RESET,()),(EFFECT,(actor,3,300,0,group,context)),(EFFECT,(actor,4,300,0,group,context)),(FACTORY,(300,6,0xFFFFFFFF,1,3,0,group,context))));pair=[]
   for w in(self.truth,self.words):
    m=TimeoutOracle(w,initial,c,connected={source.HELPER+4*i:v for i,v in enumerate(helper)}).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls));hseen.update(m.visits);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));hcount+=1
  self.assertEqual(len(hseen&set(range(source.HELPER,source.HELPER+168,4))),42);self.receipt['caller']=dict(original_parent_words=45,original_parent_cases=count,all_parent_words_visited=True,retained_parent_exact=True,table_entries=98,exit_table_entries=10,slot9_and_disable_routes=True,original_helper_words=42,helper_cases=hcount,all_helper_words_visited=True,retained_helper_exact=True,reset_presets_and_factory_bounded=True,no_whole_game_recovery_claim=True)
 def test_04_native32_canonical_record_and_effective_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run([*native_command('-'+opt,True),'-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.stderr))
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=524288,effective_controls=12,all65536_lifetime_encodings=True,canonical_owner_record_fields_and_void_pointer_ABI=True,whole_record_and_owner_fences=True,trapping_UBSan=True,helper_private_spill_mutations_guest_only=True)
 def test_05_fired_access_prefixes_and_lazy_fields(self):
  cuts=0
  for live,same,state,elapsed,mode in itertools.product((0,1),(False,True),(0,124),(199,201),(0,1)):
   c=Case(live=live,same=same,state=state,elapsed=elapsed,mode=mode);good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=TimeoutOracle(words,fixture(c),c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
  c=Case(live=0);initial=fixture(c)
  for at in(*range(source.TICKS,source.TICKS+4),OWNER+0x84,OWNER+0x85,*range(RECORD+0x30,RECORD+0x34)):initial.pop(at)
  for w in(self.truth,self.words):self.assertFalse(TimeoutOracle(w,initial,c).run().calls)
  initial.pop(OWNER+0x3B)
  for w in(self.truth,self.words):
   with self.assertRaises(AssertionError):TimeoutOracle(w,initial,c).run()
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,retail_and_direct_C_complete_state_trace_PC_delay=True,invalid_owner_skips_timer_and_state_but_still_reads_identity=True)
 def test_06_direct_payload_padder_and_GNU_rebases(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));self.assertEqual(source.normalized_payload(raw,rs),source.payload(self.out/('original-'+source.FUNCTION+'.o')));self.assertEqual(source.NEW_GUARDS,[]);self.assertEqual(rs,source.BINDINGS)
  for damaged,bindings in((raw[:-4],rs),(raw[:120]+bytes([raw[120]^1])+raw[121:],rs),(raw,{**rs,132:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.checked_payload(damaged,bindings)
  manifest=self.fresh/'guards.csv';manifest.write_bytes(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=manifest,filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  layouts=((source.ENTRY,source.TICKS,source.SLOT),(0x17007FFC,0x80017FFC,0x80028000),(0x2500FFFC,0x8001FFFC,0x80030000),(source.ENTRY,RECORD+0x30,source.SLOT),(source.ENTRY,source.TICKS,RECORD+0x28),(source.ENTRY,source.TICKS,RECORD+0xC))
  for j,(entry,ticks,slot)in enumerate(layouts):
   helper=source.HELPER if entry==source.ENTRY else entry+0x10004;symbols=dict(func_1519E3BC=helper,D_800BE9E4=ticks,D_800E0920=slot);images=[self.rebased(p,entry,symbols,'rebase-%d-%d'%(j,k))for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_1CA420.c.o',self.out/'selected.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for live,same,state,elapsed in itertools.product((0,1),(False,True),(0,124),(199,201)):self.compare(Case(live=live,same=same,state=state,elapsed=elapsed),images,entry,helper,ticks,slot);count+=1
  self.receipt['rebases']=dict(layouts=len(layouts),guest_cases=count,bindings=5,original_raw_and_actual_Make=True,raw_binding_controls=3,guards=0,HI16_LO16_carries=True,global_record_alias_layouts=3)
 def test_07_actually_compiled_semantic_controls(self):
  witnesses=[Case(),Case(live=0),Case(same=False),Case(state=124),Case(elapsed=199),Case(elapsed=0x7FFFFFFF),Case(flags=0,byte=0),Case(state=125),Case(elapsed=0xFFFFFFFF,ticks=2)]
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,dict(func_1519E3BC=source.HELPER,D_800BE9E4=source.TICKS,D_800E0920=source.SLOT),'negative-link-'+name);effective=False
   for c in witnesses:
    wanted,calls=reference(fixture(c),c);m=TimeoutOracle(words,fixture(c),c).run()
    if(public(m.memory),m.calls)!=(public(wanted),calls):effective=True;break
   self.assertTrue(effective,name)
  self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=12,semantic_value_call_wrap_and_retirement_failures=True)
 def test_08_strict_entire_image_extent_guards_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+196];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,196);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+196,source.elf_slot_offset(before,source.TABLE,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  manifest=source.guard_manifest(v['conker/retail_word_patches.us.csv']);self.assertEqual(manifest,v['conker/retail_word_patches.us.csv']);self.assertEqual(manifest,(self.out/'proposed-guards.csv').read_bytes());count=sum(x!=y for x,y in zip(before,expected));q=json.loads((self.out/'preparation.json').read_text());self.assertEqual(count,q['changed_bytes']);self.receipt['image']=dict(changed_bytes=count,code_bytes=q['code_bytes'],size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,entire_guard_manifest_unchanged=True,shared_headers_helpers_current_parent_unchanged=True)
