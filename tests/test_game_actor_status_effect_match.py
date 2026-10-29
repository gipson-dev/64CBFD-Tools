"""Actor status effect: typed packet, aliases, original routes and complete-image gates."""
from pathlib import Path
from dataclasses import replace
import itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_actor_status_effect_match as source
from tools.tests import game_actor_status_effect_oracle as oracle
from tools.tests.game_actor_status_effect_oracle import (Case,fixture,reference,public,StatusOracle,caller_machine,corpus,RECORD,ACTOR,TIMER,EFFECT,ALT,RULE,PREP,ALLOC,COPY,ZERO,RANDOM,WINDOW,END,WINDOW_ROM,WindowBoundary,STACK,put,read,faults)
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 result=dict(missing_type150=b.replace(' || actor[4] == 150',''),extra_type5=b.replace(' || actor[4] == 150',' || actor[4] == 150 || actor[4] == 5'),wrong_identity=b.replace('packet.unk4 = actor[0x3B]','packet.unk4 = actor[0x3A]'),wrong_lifetime=b.replace('packet.unk6 = 300','packet.unk6 = 299'),wrong_mode=b.replace('packet.unkA = 3','packet.unkA = 2'),wrong_timer_gate=b.replace('actor[0x127] != 255','actor[0x127] == 255'),wrong_timer=b.replace('= 500;','= 499;'),wrong_group=b.replace('record[0xC], record[1]','record[1], record[1]'),wrong_actor=b.replace('packet.unk0 = (struct127 *)actor','packet.unk0 = (struct127 *)record'),missing_call=b.replace('func_15190770(&packet, 0, record[0xC], record[1]);','(void)&packet;'))
 assert all(v!=b for v in result.values());return result

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+r"""
typedef struct{u8 pad0[102];s16 value;}Timer;
typedef struct{u8 pad0[4];u8 kind;u8 pad5[54];u8 identity;u8 pad3C[235];u8 selector;u8 pad128[500];Timer*linked;}Actor;
typedef struct{u8 bytes[24];Actor*actor;u8 tail[4];}Record;
typedef char ABI[(sizeof(void*)==4&&sizeof(struct185)==12&&__builtin_offsetof(struct185,unk4)==4&&__builtin_offsetof(struct185,unk6)==6&&__builtin_offsetof(struct185,unkA)==10&&__builtin_offsetof(Actor,identity)==59&&__builtin_offsetof(Actor,selector)==295&&__builtin_offsetof(Actor,linked)==796&&__builtin_offsetof(Record,actor)==24&&__builtin_offsetof(Timer,value)==102)?1:-1];
static struct{u32 pre[4];Record record;u32 post[4];}actual,expected;
static struct{u32 pre[4];Actor actor;u32 post[4];}actor,savedActor;
static struct{u32 pre[4];Timer timer;u32 post[4];}timer,savedTimer;
static u32 calls,bad,mode,wantedIdentity,wantedGroup,wantedContext,wantedKind,wantedTimer;
void*func_15190770(struct185*p,s32 zero,u8 group,s32 context){
 if(calls++||zero||group!=wantedGroup||(u32)context!=wantedContext||p->unk0!=(struct127*)&actor.actor||p->unk4!=wantedIdentity||p->unk6!=300||p->unk8||p->unk9||p->unkA!=(wantedKind==150?3:0)||(u16)timer.timer.value!=wantedTimer)bad=1;
 if(mode){actual.record.bytes[1]^=85;actor.actor.identity^=170;}
 p->unk8^=(s8)128;return(void*)0x76543210;
}
"""
 for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('void '+source.FUNCTION,'static void '+name)+'\n'
 t+=r"""
typedef void(*Submit)(u8*);
static int check(Submit fn){u32 kind,byte,selector,mutation,i,enabled;u8*a=(u8*)&actual,*e=(u8*)&expected,*aa=(u8*)&actor,*sa=(u8*)&savedActor,*at=(u8*)&timer,*st=(u8*)&savedTimer;
 for(kind=0;kind<256;kind++)for(byte=0;byte<256;byte++)for(selector=0;selector<2;selector++)for(mutation=0;mutation<2;mutation++){
  for(i=0;i<sizeof(actual);i++)a[i]=(u8)(i*13+byte);for(i=0;i<sizeof(actor);i++)aa[i]=(u8)(i*17+kind);for(i=0;i<sizeof(timer);i++)at[i]=(u8)(i*19+byte);
  actual.record.actor=&actor.actor;actual.record.bytes[12]=(u8)(byte*17+3);actual.record.bytes[1]=(u8)(255-byte);actor.actor.kind=(u8)kind;actor.actor.identity=(u8)byte;actor.actor.selector=selector?255:0;actor.actor.linked=&timer.timer;
  for(i=0;i<sizeof(actual);i++)e[i]=a[i];for(i=0;i<sizeof(actor);i++)sa[i]=aa[i];for(i=0;i<sizeof(timer);i++)st[i]=at[i];
  enabled=kind<=4||kind==150;mode=mutation;wantedKind=kind;wantedIdentity=byte;wantedGroup=actual.record.bytes[12];wantedContext=actual.record.bytes[1];
  if(enabled&&!selector)savedTimer.timer.value=500;wantedTimer=(u16)savedTimer.timer.value;
  if(enabled&&mode){expected.record.bytes[1]^=85;savedActor.actor.identity^=170;}
  calls=bad=0;fn((u8*)&actual.record);if(bad||calls!=enabled)return 1;
  for(i=0;i<sizeof(actual);i++)if(a[i]!=e[i])return 1;for(i=0;i<sizeof(actor);i++)if(aa[i]!=sa[i])return 1;for(i=0;i<sizeof(timer);i++)if(at[i]!=st[i])return 1;
 }return 0;}
static int run(void){if(check(selected))return 10;
"""
 for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START

class ActorStatusEffectTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>51I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>51I',data,fs[source.FUNCTION]['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,helper=source.HELPER):
  initial=fixture(c);want,calls,packets=reference(initial,c);calls=[(helper,a)for _,a in calls];pair=[]
  for words in images or(self.truth,self.words):
   m=StatusOracle(words,initial,c,entry,helper).run();self.assertEqual((public(m.memory),m.calls,m.packets),(public(want),calls,packets),c);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def linked(self,obj,entry,helper,label):
  p=self.fresh/label;p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'--defsym=func_15190770=0x%X'%helper,'-o',str(p.with_suffix('.elf')),str(obj)],capture_output=True,check=True);return list(struct.unpack_from('>51I',sections(p.with_suffix('.elf'))['.text'][1]))
 def test_01_owner_Make_source_ABI_and_registration(self):
  self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFD0)
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),41)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),40);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_1D6E80.c.o.compact'),41);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22FAE4]);self.assertEqual(struct.unpack_from('>I',self.rom,0x22FA90+21*4)[0],source.ENTRY)
  proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),proposed);self.assertEqual(proposed.count('#pragma GLOBAL_ASM'),17);self.assertIn('void func_151AB854(u8 *record)',proposed);self.assertIn('struct185 packet;',proposed)
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=51,frame=48,bindings=1,guards=0,neighbors=40,compact_functions=41,GLOBAL_ASM_routines=17,Make_commands=5,existing_struct185_packet=True,registered_table_slot=21,no_diagnostics=True)
 def test_02_guest_all_types_packet_padding_aliases_and_lazy_paths(self):
  count=0;visited=set()
  for c in corpus():m=self.compare(c);visited.update(m.visits);count+=1
  self.assertEqual(visited,set(range(source.ENTRY,source.ENTRY+204,4))-{source.ENTRY+132})
  self.receipt['guest']=dict(cases=count,reachable_words=50,unreachable_duplicate_mode_store_offset=132,all256_actor_types_and_byte_arguments=True,packet_bytes=12,defined_packet_bytes=10,untouched_padding_offsets=[5,11],all_packet_bytes_compared_in_guest=True,actor_layouts=4,timer_layouts=6,late_type_and_incoming_record_reloads=True,full_private_state_and_access_trace=True)
 def test_03_original_dispatch_window_and_complete_effect_helper(self):
  count=0;visited=set()
  for kind,selector,mask,allowed,index,phase in itertools.product((0,5,150),(0,255),(0,1,0x80000000),(0,1,0xFFFFFFFF),(0,27),(0,8)):
   c=Case(kind=kind,selector=selector,phase=phase);pair=[]
   for words in(self.truth,self.words):
    m,(wanted,calls,packets,next_index)=caller_machine(self.rom,words,c,mask,allowed,index)
    with self.assertRaises(WindowBoundary):m.run()
    self.assertEqual((public(m.memory),m.calls,m.packets,m.r[16]),(public(wanted),calls,packets,next_index));visited.update(m.visits);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
  self.assertTrue(set(range(WINDOW,END,4))<=visited)
  old=self.values['conker/build/conker.us.elf'];table=source.elf_slot_offset(old,source.TABLE,92);self.assertEqual(old[table:table+92],self.rom[0x22FA90:0x22FAEC]);self.assertIn('s32 func_15158D2C() {\n    return 0;\n}',self.values['conker/src/game/generated_185560.c'].decode());self.assertIn('s32 func_15190770() {\n    return 0;\n}',self.values['conker/src/game/generated_1BA1D0.c'].decode())
  helper=list(struct.unpack_from('>52I',self.rom,0x1BDC20));connected=dict(zip(range(source.HELPER,source.HELPER+208,4),helper));hcount=0;seen=set()
  for kind,selector,byte,allocated,mode,phase in itertools.product((0,4,150),(0,255),(0,255),(False,True),(0,1,2),(0,8)):
   c=Case(kind,selector,byte,phase,mode=mode,allocated=allocated);initial=fixture(c);want,calls,packets=reference(initial,c,real=True);pair=[]
   for words in(self.truth,self.words):
    m=StatusOracle(words,initial,c,connected=connected).run();self.assertEqual((public(m.memory),m.packets),(public(want),packets));self.assertEqual(m.prep_records,[packets[0][:4]+bytes([initial[ACTOR+59]])]);a=calls[0][1];self.assertIn((ALLOC,(32,a[3],768,1,a[2],1)),m.calls)
    if allocated:self.assertEqual([x[0]for x in m.calls],[source.HELPER,PREP,ALLOC,COPY,ZERO,RANDOM])
    else:self.assertEqual([x[0]for x in m.calls],[source.HELPER,PREP,ALLOC])
    seen.update(m.visits);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));hcount+=1
  self.assertTrue(set(range(source.HELPER,source.HELPER+208,4))<=seen);self.receipt['integration']=dict(original_caller_words=11,caller_cases=count,all_window_words_visited=True,slot21_and_mask_skip=True,argument_forwarded_and_result_ignored=True,current_C_parent_stub=True,complete_original_helper_words=52,helper_cases=hcount,all_helper_words_visited=True,current_helper_stub=True,prep_allocation_copy_zero_random_bounded=True,full_parent_or_provider_or_gameplay=False)
 def test_04_native32_typed_packet_fields_and_effective_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run(native_command('-'+opt)+['-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(subprocess.run([str(exe)],timeout=60).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=262144,effective_controls=10,trapping_UBSan=True,all256_types_identities_groups_contexts=True,existing_struct185_ABI=True,defined_packet_fields_only=True,padding_not_read_or_fixed=True,actor_record_timer_fences=True,valid_disjoint_objects=True,no_portable_guest_fault_or_stack_alias_claim=True)
 def test_05_fired_access_prefixes_and_lazy_unsupported_types(self):
  cuts=0;delays=0
  for c in(Case(),Case(kind=5),Case(kind=0,selector=255),Case(actor_layout=3),Case(timer_layout=1),Case(timer_layout=2),Case(timer_layout=3),Case(timer_layout=4)):
   good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=StatusOracle(words,fixture(c),c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1;delays+=pair[0].delay_of is not None
  for c in(Case(kind=5),Case(selector=255)):
   initial=fixture(c);remove=[ACTOR+0x31C+i for i in range(4)]+[TIMER+102,TIMER+103]
   if c.kind==5:remove.extend((ACTOR+59,ACTOR+0x127))
   for address in remove:initial.pop(address)
   for words in(self.truth,self.words):m=StatusOracle(words,initial,c).run();self.assertEqual(len(m.calls),0 if c.kind==5 else 1)
  self.receipt['faults']=dict(prefix_pairs=cuts,delay_slot_cuts=delays,full_state_trace_PC_delay=True,unsupported_types_skip_identity_selector_linked_timer=True,selector255_skips_linked_timer=True,portable_C_fault_claimed=False)
 def test_06_actual_padder_raw_corruptions_and_GNU_rebases(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
  for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,{180:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.checked_payload(b,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,(entry,helper)in enumerate(((source.ENTRY,source.HELPER),(0x17007FFC,0x17190770),(0x2500FFFC,0x25190770))):
   images=[self.linked(self.out/n,entry,helper,'layout-%d-%d'%(j,k))for k,n in enumerate(('original-'+source.FUNCTION+'.o','selected.o'))];self.assertEqual(*images)
   for c in(Case(),Case(kind=5),Case(selector=255),Case(actor_layout=3),Case(timer_layout=3),Case(timer_layout=4)):self.compare(c,images,entry,helper);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=3,original_and_compiled_GNU_objects_equal=True,call_binding_preserved=True,guards=0)
 def test_07_independently_compiled_semantic_controls(self):
  for name,body in controls().items():
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(kind=5 if name=='extra_type5'else 150);m=StatusOracle(words,fixture(c),c).run();want,calls,packets=reference(fixture(c),c);self.assertNotEqual((public(m.memory),m.calls,m.packets),(public(want),calls,packets),name)
  self.receipt['compiled_controls']=dict(count=len(controls()),observable_state_calls_or_packet_mismatches=True)
 def test_08_strict_entire_image_metadata_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+204];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,204);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+100,at+204,source.elf_slot_offset(before,0x80082B20,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(x!=y for x,y in zip(before,expected)),155);self.receipt['image']=dict(changed_bytes=155,code_bytes=154,extent_bytes=1,metadata_bytes=0,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088,exclusions=0,corruptions=6,guards_and_shared_headers_unchanged=True)
