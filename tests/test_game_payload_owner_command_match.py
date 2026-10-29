"""Owner command: guarded epilogue, typed events, original dispatch and pair service."""
from pathlib import Path
from dataclasses import replace
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_payload_owner_command_match as source
from tools.tests import game_payload_owner_command_oracle as oracle
from tools.tests.game_payload_owner_command_oracle import *
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 q=dict(wrong_release_command=b.replace('command == 60','command == 61'),wrong_clear_command=b.replace('command == 4)','command == 5)'),and_gate=b.replace(' || link[4]',' && link[4]'),wrong_identity=b.replace('event[4]','event[5]'),narrow_key=b.replace('*(s32 *)link == *(s32 *)event','(u8)*(s32 *)link == (u8)*(s32 *)event'),wrong_bit=b.replace('&= ~1','&= ~2'),wrong_flag_byte=b.replace('link[0x10]','link[0x11]'),wrong_value_argument=b.replace('command, (s32)link,','command, (s32)(link + 4),'),wrong_owner_argument=b.replace('(s32)(link + 4), (s32)owner','(s32)(link + 4), 0'),missing_release=b.replace('func_1516972C((struct102 *)owner);','(void)owner;'))
 assert all(v!=b for v in q.values());return q

def native_harness(values):
 pair=values['conker/src/game_1944C0.c'].decode();pair=pair[slice(*source.function_span(pair,'func_15169850'))]
 wrapper=values['conker/src/game/done/game_1765E0.c'].decode();wrapper=wrapper[slice(*source.function_span(wrapper,'func_15149514'))].replace('func_15149514','real_wrapper')
 t=source.HEADERS+source.DECLARATIONS+r"""
static u8*arena;static u8 expected[128];static u32 releases,wrappers,bad,mode;
typedef struct{s32 first,second;u8 firstTag,secondTag,pad[2];}Event;
static Event event;
static void putword(u8*p,s32 value){u32 i;const u8*v=(const u8*)&value;for(i=0;i<4;i++)p[i]=v[i];}
static void*allocate(u32 size){u32 old,got,begin,end;__asm__ volatile("int $0x80":"=a"(old):"0"(45),"b"(0):"memory","cc");begin=(old+15)&~15u;end=begin+size;__asm__ volatile("int $0x80":"=a"(got):"0"(45),"b"(end):"memory","cc");return got<end?0:(void*)begin;}
void func_1516972C(struct102*p){releases++;if(p!=(struct102*)(arena+16)){bad=1;return;}if(mode&1)((u8*)p)[49]^=85;if(mode&2)*(s32*)((u8*)p+40)=0x26000;}
"""+pair+'\n'+wrapper+r"""
void func_15149514(s32 ev,u8 command,s32 value,s32 tag,s32 owner){wrappers++;if(ev!=(s32)&event||value!=(s32)(arena+56)||tag!=(s32)(arena+60)||owner!=(s32)(arena+16)){bad=1;return;}real_wrapper(ev,command,value,tag,owner);}
"""
 for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('void '+source.FUNCTION,'static void '+name)+'\n'
 t+=r"""
typedef void(*Handler)(struct260*,s32,u8);
static int check(Handler fn){u32 command,byte,relation,plan,i,wantFree,wantWrap;u8*owner=arena+16,*link=owner+40;const u32 vals[]={0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678};s32 first,second,current;u8 identity;
 for(command=0;command<256;command++)for(byte=0;byte<256;byte++)for(relation=0;relation<5;relation++)for(plan=0;plan<2;plan++){
  for(i=0;i<128;i++)arena[i]=(u8)(i*13+byte);event.first=(s32)vals[byte%6];event.second=event.first^(s32)0x87654321u;if(relation==4)event.second=event.first;event.firstTag=18;event.secondTag=231;event.pad[0]=event.pad[1]=0xA5;
  first=event.first;second=event.second;current=relation==0||relation==4?first:relation==1?second:first^0x01000000;*(s32*)link=current;identity=(u8)(((u8*)&event)[4]^(relation==3?0:1));link[4]=identity;link[16]=(u8)byte;
  for(i=0;i<128;i++)expected[i]=arena[i];mode=plan?3:0;wantFree=0;wantWrap=command!=4&&command!=60;
  if(command==60){if(current==first||identity==((u8*)&event)[4])wantFree=1;}
  else if(command==4){if(current==first||identity==((u8*)&event)[4])expected[16+56]&=254;}
  else if(command==0){if(current==first||identity==((u8*)&event)[4])wantFree=1;}
  else if(command==45){if(current==first){putword(expected+56,second);expected[60]=event.secondTag;}else if(current==second){putword(expected+56,first);expected[60]=event.firstTag;}}
  if(wantFree){if(mode&1)expected[16+49]^=85;if(mode&2)putword(expected+56,0x26000);}
  releases=wrappers=bad=0;fn((struct260*)owner,(s32)&event,(u8)command);if(bad||releases!=wantFree||wrappers!=wantWrap)return 1;for(i=0;i<128;i++)if(arena[i]!=expected[i])return 1;
 }return 0;}
static int run(void){arena=allocate(128);if(!arena)return 9;if(check(selected))return 10;
"""
 for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START

class PayloadOwnerCommandTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>51I',cls.rom,source.ROM));cls.words=cls.rebase(cls.out/'qualified-padded.o',source.ENTRY,source.FREE,source.WRAPPER,'setup-fitted');cls.raw=cls.rebase(cls.out/'selected.o',source.ENTRY,source.FREE,source.WRAPPER,'setup-raw')
 @classmethod
 def rebase(cls,obj,entry,free,wrapper,label):
  text,fs,rs=parse_object(obj);assembly,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,dict(func_1516972C=free,func_15149514=wrapper));assert not unknown
  p=cls.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'--defsym=func_1516972C=0x%X'%free,'--defsym=func_15149514=0x%X'%wrapper,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
  return list(struct.unpack_from('>%dI'%(fs[source.FUNCTION]['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,free=source.FREE,wrapper=source.WRAPPER):
  initial=fixture(c);wanted,calls=reference(initial,c);calls=[({source.FREE:free,source.WRAPPER:wrapper}.get(t,t),a)for t,a in calls];pair=[]
  for words in images or(self.truth,self.words,self.raw):
   m=CommandOracle(words,initial,c,entry,free,wrapper).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls),c);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def test_01_owner_actual_Make_typed_ABI_and_table(self):
  self.assertEqual(self.words,self.truth);self.assertEqual((len(self.raw),self.words[0]),(50,0x27BDFFD8));self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),28)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),27);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_200930.c.o.compact'),28);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22F46C]);self.assertEqual(struct.unpack_from('>I',self.rom,0x22F398+53*4)[0],source.ENTRY)
  proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),proposed);self.assertEqual(proposed.count('#pragma GLOBAL_ASM'),19);self.assertIn('extern void (*D_8008A8D8[74])(struct260*, s32, u8);',self.values['conker/include/variables.h'].decode())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(raw_words=50,words=51,frame=40,bindings=2,guards=6,neighbors=27,compact_functions=28,GLOBAL_ASM_routines=19,Make_commands=5,arguments=3,void_return=True,registered_table_slot=53,no_diagnostics=True)
 def test_02_guest_commands_flags_aliases_and_short_circuit(self):
  count=0;seen=set()
  for c in corpus():m=self.compare(c);seen.update(m.visits);count+=1
  self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+204,4))-{source.ENTRY+96})
  self.receipt['guest']=dict(cases=count,reachable_words=50,unreachable_duplicate_constant_offset=96,all256_command_identity_flag_bytes=True,seven_event_alias_layouts=True,high_command_homes=True,raw_C_public_memory_and_calls_equal=True,normalized_complete_state_and_trace_equal=True,raw_fault_schedule_not_equated=True)
 def test_03_complete_original_dispatcher_and_pair_helpers(self):
  old=self.values['conker/build/conker.us.elf'];parent=list(struct.unpack_from('>23I',self.rom,0x1768E4));at=source.elf_slot_offset(old,source.PARENT,92);self.assertEqual(old[at:at+92],struct.pack('>23I',*parent));table=list(struct.unpack_from('>74I',self.rom,0x22F398));self.assertEqual(table[53],source.ENTRY);count=0;seen=set()
  for selector,command,relation,phase in itertools.product((0,53,74,255),(0,4,45,60,255),range(5),(0,8)):
   c=Case(command,relation,phase=phase);initial=fixture(c);initial[OWNER+19]=selector
   for i,value in enumerate(table):put(initial,source.TABLE+4*i,value)
   chosen=selector if selector<74 else 0;wanted=dict(initial);calls=[]
   if table[chosen]:
    calls=[(table[chosen],(OWNER,event_address(c),command))]
    if chosen==53:wanted,more=reference(initial,c);calls+=more
   pair=[]
   for words in(self.truth,self.words):
    m=CommandOracle(parent,initial,c,entry=source.PARENT,connected=dict(zip(range(source.ENTRY,source.ENTRY+204,4),words)),callbacks=table).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls));seen.update(m.visits);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
  self.assertTrue(set(range(source.PARENT,source.PARENT+92,4))<=seen);helpers=((source.WRAPPER,0x1769C4,12),(source.PAIR,0x196D00,41));connected={};visits=set();hcount=0
  for entry,pos,n in helpers:
   body=list(struct.unpack_from('>%dI'%n,self.rom,pos));at=source.elf_slot_offset(old,entry,n*4);self.assertEqual(old[at:at+n*4],struct.pack('>%dI'%n,*body));connected.update(zip(range(entry,entry+n*4,4),body))
  for command,relation,alias,phase in itertools.product((0,4,45,60,255),range(5),(0,1,2,4),(0,8)):
   c=Case(command,relation,alias=alias,phase=phase,mode=3);initial=fixture(c);wanted,calls=reference(initial,c,connected=True);pair=[]
   for words in(self.truth,self.words):
    m=CommandOracle(words,initial,c,connected=connected).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls));visits.update(m.visits);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));hcount+=1
  self.assertTrue(set(connected)-{source.PAIR+124}<=visits);self.receipt['integration']=dict(parent_words=23,parent_cases=count,all_parent_words_visited=True,retained_parent_exact=True,table_entries=74,unsigned_selector_and_slot0_fallback=True,helper_cases=hcount,retained_helpers_words=53,reachable_helper_words=52,wrapper_words=12,pair_words=41,pair_alignment_tail_words=3,release_provider_bounded=True,full_release_heap_or_gameplay=False)
 def test_04_native32_actual_pair_C_and_effective_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness(self.values))
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run(native_command('-'+opt)+['-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(subprocess.run([str(exe)],timeout=60).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=655360,effective_controls=10,trapping_UBSan=True,actual_C_wrapper_and_pair_helper=True,all256_commands_identity_flag_bytes=True,fresh_untyped_aligned_owner_storage=True,typed_event_and_owner_fences=True,no_guest_stack_alias_or_raw_fault_claim=True)
 def test_05_fired_normalized_access_prefixes_and_lazy_fields(self):
  cuts=0;delays=0
  for c in(Case(),Case(command=4),Case(command=4,relation=2),Case(command=0),Case(command=45,relation=1),Case(alias=1),Case(alias=5),Case(alias=6)):
   good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=CommandOracle(words,fixture(c),c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1;delays+=pair[0].delay_of is not None
  for command in(1,2,44,46,255):
   c=Case(command=command);initial=fixture(c)
   for words in(self.truth,self.words,self.raw):m=CommandOracle(words,initial,c,arguments=(0xDEADC000,0xBEEF0000,command)).run();self.assertEqual(len(m.calls),1)
  self.receipt['faults']=dict(prefix_pairs=cuts,delay_slot_cuts=delays,normalized_full_state_trace_PC_delay=True,ignored_commands_need_no_owner_event_mapping=True,raw_fault_schedule_not_equated=True,portable_C_fault_claimed=False)
 def test_06_six_real_padder_guards_and_independent_GNU_rebases(self):
  raw,bindings=source.payload(self.out/'selected.o');self.assertEqual(len(raw),200);self.assertEqual(source.normalized_payload(raw,bindings),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  base=(self.out/'after-owner.o').read_bytes();_,fs,_=parse_object(self.out/'after-owner.o');start=fs[source.FUNCTION]['value'];shoff=struct.unpack_from('>I',base,32)[0];shsize,shcount,shnames=struct.unpack_from('>HHH',base,46);headers=[struct.unpack_from('>10I',base,shoff+i*shsize)for i in range(shcount)];strings=base[headers[shnames][4]:headers[shnames][4]+headers[shnames][5]];sec={strings[h[0]:].split(b'\0',1)[0].decode():h for h in headers};text_at=sec['.text'][4];rel=sec['.rel.text'];rejections=0
  for row in source.NEW_GUARDS:
   offset=int(row['offset'],0);bad=bytearray(base);bad[text_at+start+offset]^=1;p=self.fresh/('bad-word-%X.o'%offset);p.write_bytes(bad)
   with self.assertRaises(ValueError):source.emit_padded_assembly(p,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER)
   rejections+=1;bad=bytearray(base);hits=[]
   for at in range(rel[4],rel[4]+rel[5],8):
    if struct.unpack_from('>I',base,at)[0]==start+80:hits.append(at)
   self.assertEqual(len(hits),1);struct.pack_into('>I',bad,hits[0],start+offset);p=self.fresh/('bad-relocation-%X.o'%offset);p.write_bytes(bad)
   with self.assertRaises(ValueError):source.emit_padded_assembly(p,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER)
   rejections+=1
  count=0
  for j,(entry,free,wrapper)in enumerate(((source.ENTRY,source.FREE,source.WRAPPER),(0x17007FFC,0x1716972C,0x17149514),(0x2500FFFC,0x2516972C,0x25149514))):
   images=[self.rebase(self.out/n,entry,free,wrapper,'layout-%d-%d'%(j,k))for k,n in enumerate(('original-'+source.FUNCTION+'.o','qualified-padded.o','selected.o'))];self.assertEqual(images[0],images[1])
   for c in(Case(),Case(command=4),Case(command=45),Case(command=0),Case(alias=5),Case(alias=6)):self.compare(c,images,entry,free,wrapper);count+=1
  self.receipt['guards']=dict(rows=6,inserted_RA_reload_words=1,omitted_words=0,flag_store_branch_reordered=True,crossing_branches_retargeted=4,raw_wrapper_call_offset=172,normalized_wrapper_call_offset=176,stale_word_and_relocation_rejections=rejections)
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_and_fitted_public_equal=True,original_and_padded_complete_equal=True)
 def test_07_independently_compiled_semantic_controls(self):
  for name,body in controls().items():
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.rebase(obj,source.ENTRY,source.FREE,source.WRAPPER,'negative-link-'+name);c=Case(command=4 if name in('wrong_clear_command','wrong_bit','wrong_flag_byte')else 45 if name in('wrong_value_argument','wrong_owner_argument')else 60,relation=2 if name=='narrow_key'else 3 if name in('and_gate','wrong_identity')else 0);m=CommandOracle(words,fixture(c),c).run();wanted,calls=reference(fixture(c),c);self.assertNotEqual((public(m.memory),m.calls),(public(wanted),calls),name)
  self.receipt['compiled_controls']=dict(count=len(controls()),observable_state_or_call_mismatches=True)
 def test_08_strict_entire_image_and_append_only_manifest(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+204];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,204);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+100,at+204,source.elf_slot_offset(before,0x80082B20,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(x!=y for x,y in zip(before,expected)),150);self.assertTrue((self.out/'proposed-guards.csv').read_bytes().startswith(v['conker/retail_word_patches.us.csv']));self.receipt['image']=dict(changed_bytes=150,code_bytes=149,extent_bytes=1,metadata_bytes=0,exclusions=0,corruptions=6,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088,new_guard_rows=6,inherited_manifest_prefix_fixed=True)
