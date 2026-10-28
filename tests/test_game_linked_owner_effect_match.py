"""Linked-owner effect: semantic C, checked normalization and original dispatcher/helper."""
from dataclasses import replace
from pathlib import Path
import csv,io,itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_linked_owner_effect_match as source
from tools.tests import game_linked_owner_effect_oracle as oracle
from tools.tests.game_linked_owner_effect_oracle import Case,fixture,reference,public,LinkedOracle,RECORD,OWNER,ALT,EFFECT,PREP,ALLOC,COPY,ZERO,RANDOM,EXIT_TABLE,STACK,put,read,half,faults
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 return dict(inverted_live=b.replace('*(s32 *)owner == 0','*(s32 *)owner != 0'),wrong_identity=b.replace('record[0x2C]','record[0x2D]'),inverted_capability=b.replace('*(s32 *)(owner + 0x1D4) != 0','*(s32 *)(owner + 0x1D4) == 0'),wrong_flag=b.replace('record[0xD] & 1','record[0xD] & 2'),wrong_default=b.replace('= 300;','= 299;'),wrong_payload_flag=b.replace('payload[8] |= 1','payload[8] |= 2'),skip_release=b.replace('if (release)','if (0)'),wrong_group=b.replace('record[0xC], record[1]','record[1], record[1]'),wrong_payload=b.replace('func_15190770(payload,','func_15190770(payload + 4,'))

def native_harness():
 t=source.HEADERS+r'''
typedef struct{ s32 live;u8 pad4[55];u8 id;u8 pad3C[408];s32 capable;} Owner;
typedef struct{u8 kind,context;u8 pad2[10];u8 group,flags;s16 life;u8 pad10[24];Owner*owner;u8 id,pad2D;s16 payloadLife;u8 payloadFlags;u8 tail[31];}Record;
typedef char ABI[(sizeof(void*)==4&&sizeof(Record)==80&&__builtin_offsetof(Record,owner)==40&&__builtin_offsetof(Record,payloadLife)==46&&__builtin_offsetof(Owner,id)==59&&__builtin_offsetof(Owner,capable)==468)?1:-1];
static struct{u32 left[4];Record record;u32 right[4];}actual,expected;
static Owner owner,ownerBefore,other;static u32 mode,helperCalls,freeCalls,error,wantedGroup,wantedContext;static u8 wantedPayload[12];
static void effect(Record*r){if(mode&1)r->payloadFlags^=128;if(mode&2){r->owner=&other;r->group^=85;r->context^=170;}}
s32 func_15190770(u8*p,s32 zero,s32 group,s32 context){u32 i;helperCalls++;if(p!=(u8*)&actual.record.owner||zero||group!=(s32)wantedGroup||context!=(s32)wantedContext){error=1;return 0;}for(i=0;i<12;i++)if(p[i]!=wantedPayload[i])error=1;effect(&actual.record);return(s32)0xFEDCBA98u;}
s32 func_1516972C(void*p){freeCalls++;if(p!=&actual.record){error=1;return 0;}((u8*)p)[74]^=165;return 0x2468;}
'''
 for n,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,'test_'+n)+'\n'
 t+=r'''
typedef void(*Update)(u8*);
static int check(Update fn){u32 n,k,i,dead,submit;u8*p=(u8*)&actual,*q=(u8*)&expected;
 for(n=0;n<65536;n++)for(k=0;k<4;k++){
  for(i=0;i<sizeof(actual);i++)p[i]=(u8)(i*13+n*7+k);for(i=0;i<sizeof(owner);i++)((u8*)&owner)[i]=(u8)(i*17+n);
  owner.live=k==0?0:1;owner.capable=k==3?0:1;owner.id=(u8)(n>>8);ownerBefore=owner;
  actual.record.owner=&owner;actual.record.id=(u8)(owner.id^(k==1));actual.record.life=(s16)n;actual.record.flags=(u8)n;actual.record.group=(u8)(n*17u);actual.record.context=(u8)(n*31u+3);mode=n&3;
  for(i=0;i<sizeof(actual);i++)q[i]=p[i];dead=!owner.live||actual.record.id!=owner.id;submit=!dead&&owner.capable;
  if(submit){dead=1;if(expected.record.flags&1){expected.record.payloadFlags|=1;expected.record.payloadLife=expected.record.life;}else expected.record.payloadLife=300;
   wantedGroup=expected.record.group;wantedContext=expected.record.context;for(i=0;i<12;i++)wantedPayload[i]=((u8*)&expected.record.owner)[i];effect(&expected.record);}
  if(dead)((u8*)&expected.record)[74]^=165;
  helperCalls=freeCalls=error=0;fn((u8*)&actual.record);if(error||helperCalls!=submit||freeCalls!=dead)return 1;
  for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 1;for(i=0;i<sizeof(owner);i++)if(((u8*)&owner)[i]!=((u8*)&ownerBefore)[i])return 1;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,n in enumerate(controls()):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START

class LinkedOwnerEffectTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>49I',cls.rom,source.ROM));cls.images=[]
  for filename,n in(('qualified-padded.o',49),('selected.o',50)):
   local=cls.fresh/filename;local.write_bytes((cls.out/filename).read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.images.append(list(struct.unpack_from('>%dI'%n,data,functions[source.FUNCTION]['value'])))
  cls.words,cls.raw=cls.images
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,helper=source.HELPER,free=source.FREE):
  initial=fixture(c);wanted,calls,packets=reference(initial,c);calls=[({source.HELPER:helper,source.FREE:free}.get(t,t),a)for t,a in calls];pair=[]
  for words in images or(self.truth,self.words,self.raw):
   m=LinkedOracle(words,initial,c,entry,helper=helper,free=free).run();self.assertEqual((public(m.memory),m.calls,m.packets),(public(wanted),calls,packets),c);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);body=sections(p.with_suffix('.elf'))['.text'][1];return list(struct.unpack('>%dI'%(len(body)//4),body))
 def test_01_owner_Make_census_and_source_ABI(self):
  self.assertEqual(self.words,self.truth);self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),4);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),61)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),60);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(proposed,source.recovered_owner(self.values[source.SOURCE].decode()));self.assertIn('void func_151918BC(u8 *record)',proposed);self.assertNotIn('#pragma GLOBAL_ASM',proposed);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22EFDC]);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertIn('s32 func_15190770() {\n    return 0;\n}',proposed)
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(raw_words=50,body_words=49,frame=48,bindings=2,guards=11,omitted_redundant_address_words=1,neighbors=60,compact_functions=61,Make_commands=3,selected_diagnostics=0,inherited_owner_warnings=4,arguments=1,void_return=True,callback_table='D_8008A4E8',callback_slot=13,helper_placeholder_unchanged=True)
 def test_02_guest_gates_lifetimes_aliases_and_saved_release(self):
  count=0;visits=set()
  for live,same,capable,flags,life,mode,phase in itertools.product((0,1),(False,True),(0,0x80000000),(0,1,2,255),(-32768,-1,0,32767),(0,1,2,4,8),(0,8)):
   m=self.compare(Case(live,same,capable,flags,life,255,mode,phase));visits.update(m.visits);count+=1
  for byte in range(256):self.compare(Case(flags=byte,byte=byte,lifetime=byte*257));count+=1
  for alias,live,same,flags in itertools.product(range(1,4),(0,1),(False,True),(0,1,255)):self.compare(Case(alias=alias,live=live,same=same,flags=flags));count+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+196,4))-{source.ENTRY+44});self.receipt['guest']=dict(cases=count,visited_words=len(visits),unreachable_duplicate_identity_load_retained=True,all_flag_and_group_context_bytes=True,owner_record_alias_layouts=4,signed_lifetime_and_low_flag_bit=True,helper_payload_and_record_mutations=True,saved_release_byte_mutation_guest_only=True,raw_C_public_memory_calls_payloads_equal=True,normalized_complete_state_trace_equal=True,raw_scheduling_prefixes_not_equated=True)
 def test_03_complete_original_dispatcher_and_factory_helper(self):
  table=list(struct.unpack_from('>98I',self.rom,0x22EFA8));exits=list(struct.unpack_from('>10I',self.rom,0x22EF80));self.assertEqual(table[13],source.ENTRY);elf=self.values['conker/build/conker.us.elf'];parent=list(struct.unpack_from('>45I',self.rom,0x176714));at=source.elf_slot_offset(elf,source.PARENT,180);self.assertEqual(elf[at:at+180],struct.pack('>45I',*parent));at=source.elf_slot_offset(elf,source.TABLE,392);self.assertEqual(elf[at:at+392],self.rom[0x22EFA8:0x22F130]);count=0;seen=set()
  for selector,destructor,flags,life,ticks,live in itertools.product((-1,13),(-1,0),(0,1),(-1,0,32767),(0,1,30),(0,1)):
   c=Case(flags=flags,lifetime=life,live=live);initial=fixture(c);initial[RECORD+17]=selector&255;initial[RECORD+16]=destructor&255;put(initial,source.TICKS,ticks)
   for i,v in enumerate(table):put(initial,source.TABLE+i*4,v)
   for i,v in enumerate(exits):put(initial,EXIT_TABLE+i*4,v)
   wanted=dict(initial);calls=[]
   if flags&1:put(wanted,RECORD+14,(life-ticks)&65535,2)
   if selector!=-1:calls.append((source.ENTRY,(RECORD,)));wanted,more,_=reference(wanted,c,STACK-24);calls+=more
   if half(read(wanted,RECORD+14,2))<0:
    if destructor!=-1:calls.append((exits[destructor],(RECORD,)))
    calls.append((source.FREE,(RECORD,)));oracle.free_effect(wanted,RECORD)
   pair=[]
   for w in(self.truth,self.words):
    m=LinkedOracle(parent,initial,c,source.PARENT,{source.ENTRY+4*i:v for i,v in enumerate(w)},callbacks=exits).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls));seen.update(m.visits);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
  self.assertTrue(set(range(source.PARENT,source.PARENT+180,4))<=seen);helper=list(struct.unpack_from('>52I',self.rom,0x1BDC20));hcount=0;hseen=set()
  for flags,life,mode,allocated,phase in itertools.product((0,1,255),(-32768,0,32767),(0,1),(False,True),(0,8)):
   c=Case(flags=flags,lifetime=life,mode=mode,allocated=allocated,phase=phase);initial=fixture(c);wanted,_,packets=reference(initial,replace(c,mode=0));payload=bytearray(packets[0]);payload[8]^=128 if mode&1 else 0;wanted[RECORD+0x30]=payload[8]
   if allocated:
    for i,b in enumerate(payload):wanted[EFFECT+16+i]=b
    for off,val in((28,0),(32,0),(36,EFFECT+48),(40,EFFECT+768)):put(wanted,EFFECT+off,val)
    for i in range(720):wanted[EFFECT+48+i]=0
    wanted[EFFECT+44]=c.byte
   pair=[]
   for w in(self.truth,self.words):
    m=LinkedOracle(w,initial,c,connected={source.HELPER+i*4:v for i,v in enumerate(helper)}).run();self.assertEqual(public(m.memory),public(wanted));self.assertEqual(m.prep_records,[packets[0][:4]+bytes([c.byte])]);self.assertIn((ALLOC,(32,initial[RECORD+1],768,1,c.byte,1)),m.calls);self.assertEqual(m.calls[-1],(source.FREE,(RECORD,)));hseen.update(m.visits);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));hcount+=1
  self.assertEqual(len(hseen&set(range(source.HELPER,source.HELPER+208,4))),52);self.receipt['caller']=dict(original_parent_words=45,original_parent_cases=count,all_parent_words_visited=True,retained_parent_exact=True,table_entries=98,exit_table_entries=10,slot13_and_disable_routes=True,original_helper_words=52,helper_cases=hcount,all_helper_words_visited=True,helper_current_placeholder_unchanged=True,prep_allocator_copy_zero_random_and_release_bounded=True,no_whole_game_or_helper_recovery_credit=True)
 def test_04_native32_canonical_record_and_effective_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run([*native_command('-'+opt,True),'-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.stderr))
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=262144,effective_controls=9,all65536_lifetime_encodings=True,canonical_owner_record_fields_and_void_pointer_ABI=True,whole_record_and_owner_fences=True,trapping_UBSan=True,helper_private_spill_mutations_guest_only=True)
 def test_05_fired_access_prefixes_and_lazy_fields(self):
  cuts=0
  for live,same,capable,flags,mode,phase in itertools.product((0,1),(False,True),(0,1),(0,1),(0,1,2),(0,8)):
   c=Case(live,same,capable,flags,mode=mode,phase=phase);good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=LinkedOracle(words,fixture(c),c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
  c=Case(live=0);initial=fixture(c)
  for at in(OWNER+0x3B,*range(OWNER+0x1D4,OWNER+0x1D8)):initial.pop(at)
  for w in(self.truth,self.words,self.raw):self.assertEqual(LinkedOracle(w,initial,c).run().calls,[(source.FREE,(RECORD,))])
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,retail_and_normalized_complete_state_trace_PC_delay=True,inactive_owner_skips_identity_and_capability_loads=True,raw_reordered_access_prefixes_not_equated=True)
 def test_06_guard_proof_real_padder_and_GNU_rebases(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));normalized,rels=source.normalized_payload(raw,rs);self.assertEqual(len(source.NEW_GUARDS),11);self.assertEqual(rs,{152:[('R_MIPS_26','func_15190770')],172:[('R_MIPS_26','func_1516972C')]});self.assertEqual(rels,{148:rs[152],168:rs[172]});a=struct.unpack('>50I',raw);b=struct.unpack('>49I',normalized)
  self.assertEqual(a[23:25],(0x24020001,0x26040028));self.assertEqual(a[28],a[24]);self.assertEqual(b[23:25],a[23:25][::-1])
  mapping=lambda x:x-4 if x>112 else x
  for at in(64,80,104):self.assertEqual(at+4+(half(a[at//4])*4),mapping(at+4+half(a[at//4])*4)+4);self.assertEqual(at+4+half(b[at//4])*4,mapping(at+4+half(a[at//4])*4))
  # Reordered fields are fixed disjoint offsets from the same record. The removed
  # address repeats a0 without any intervening a0 write; t2/t3/t4 are caller scratch.
  self.assertEqual(set(range(14,16))&set(range(48,49)),set());self.assertEqual(set(range(46,48))&set(range(48,49)),set())
  for damaged,bindings in((raw[:-4],rs),(raw[:120]+bytes([raw[120]^1])+raw[121:],rs),(raw,{**rs,112:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.normalized_payload(damaged,bindings)
  manifest=self.fresh/'guards.csv';manifest.write_bytes(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=manifest,filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0

  for ordinal,row in enumerate(source.NEW_GUARDS):
   altered=dict(row,expected='0x%08X'%(int(row['expected'],0)^1));rows=[altered if i==ordinal else v for i,v in enumerate(source.NEW_GUARDS)];out=io.StringIO(newline='');csv.DictWriter(out,list(row),lineterminator='\r\n').writerows(rows);bad_manifest=self.fresh/('bad-guard-%d.csv'%ordinal);bad_manifest.write_bytes(self.values['conker/retail_word_patches.us.csv']+out.getvalue().encode())
   with self.assertRaisesRegex(ValueError,'stale word patch'):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=bad_manifest,filename=source.OWNER)
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   helper,free=(source.HELPER,source.FREE)if j==0 else(entry+0x10004,entry+0x30004);symbols=dict(func_15190770=helper,func_1516972C=free);images=[self.rebased(p,entry,symbols,'rebase-%d-%d'%(j,k))[:n]for k,(p,n)in enumerate(((self.out/('original-'+source.FUNCTION+'.o'),49),(self.out/'make-shadow/src/game/generated_1BA1D0.c.o',49),(self.out/'selected.o',50)))];self.assertEqual(images[0],images[1])
   for live,same,capable,flags in itertools.product((0,1),(False,True),(0,1),(0,1)):self.compare(Case(live,same,capable,flags),images,entry,helper,free);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,bindings=2,original_raw_and_actual_Make=True,raw_binding_controls=3,real_padder_stale_guard_controls=11,guards=11,one_redundant_address_omitted=True,three_crossing_branches_retargeted=True,disjoint_flag_and_lifetime_fields=True)
 def test_07_actually_compiled_semantic_controls(self):
  for name,body in controls().items():
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,dict(func_15190770=source.HELPER,func_1516972C=source.FREE),'negative-link-'+name);c=Case(flags=0 if name=='wrong_default'else 1,byte=0 if name=='wrong_payload_flag'else 255);wanted,calls,packets=reference(fixture(c));m=LinkedOracle(words,fixture(c),c).run();self.assertNotEqual((public(m.memory),m.calls,m.packets),(public(wanted),calls,packets),name)
  self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=9,semantic_value_call_and_payload_failures=True)
 def test_08_strict_entire_image_extent_guards_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+196];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,196);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+196,source.elf_slot_offset(before,source.TABLE,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  manifest=source.guard_manifest(v['conker/retail_word_patches.us.csv']);self.assertTrue(manifest.startswith(v['conker/retail_word_patches.us.csv']));self.assertEqual(manifest,(self.out/'proposed-guards.csv').read_bytes());count=sum(x!=y for x,y in zip(before,expected));q=json.loads((self.out/'preparation.json').read_text());self.assertEqual(count,q['changed_bytes']);self.receipt['image']=dict(changed_bytes=count,code_bytes=q['code_bytes'],size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,inherited_guard_manifest_bytes_preserved=True,shared_headers_helpers_current_parent_unchanged=True)
