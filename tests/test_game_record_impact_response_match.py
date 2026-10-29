"""Impact response: exact C, native o32 fields, original callback and effect helpers."""
from pathlib import Path
from dataclasses import replace
import itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_record_impact_response_match as source
from tools.tests import game_record_impact_response_oracle as oracle
from tools.tests.game_record_impact_response_oracle import *
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED;live=b.replace('selector = func_151D8E20();','selector = func_151D8E20();\n    payload = *(u8 **)(actor + 0x98);')
 q=dict(unsigned_cursor=b.replace('*(s8 *)(actor + 0x2D)','*(u8 *)(actor + 0x2D)'),wrong_height=b.replace('position[1] = height','position[1] = previousY'),wrong_scale=b.replace('* 7.0f','* 6.0f'),wrong_alpha=b.replace('payload[0x1B]','payload[0x1A]'),wrong_result=b.replace('(s32)result, position','0, position'),wrong_group=b.replace('position, actor[0xC], actor[1]','position, actor[1], actor[1]'),wrong_context=b.replace('position, actor[0xC], actor[1]','position, actor[0xC], actor[0xC]'),wrong_state=b.replace('payload[0x20] = 4','payload[0x20] = 5'),wrong_return=b.replace('return 1;','return 0;'),live_payload=live)
 assert all(v!=b for v in q.values());return q

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+r"""
typedef struct{f32 scale;u8 pad4[23];u8 alpha;u8 pad1C[4];u8 state;u8 tail[31];}Payload;
typedef struct{u8 bytes[148];ImpactMotionRecord*records;Payload*payload;}Actor;
typedef char ABI[(sizeof(void*)==4&&sizeof(ImpactMotionRecord)==20&&__builtin_offsetof(Actor,records)==148&&__builtin_offsetof(Actor,payload)==152&&__builtin_offsetof(Payload,alpha)==27&&__builtin_offsetof(Payload,state)==32)?1:-1];
static struct{u32 pre[4];Actor actor;u32 post[4];}actual,expected;
static struct{u32 pre[4];Payload payload;u32 post[4];}payload,wantedPayload,other,wantedOther;
static struct{u32 pre[4];ImpactMotionRecord rows[512];u32 post[4];}records,alternate;
static u32 mode,selectorCalls,effectCalls,bad,wantedSelector,wantedGroup,wantedContext,wantedScale,wantedHeight,wantedX,wantedZ;static s16 wantedAlpha;static s32 wantedResult;
static f32 real(u32 v){union{f32 f;u32 u;}x;x.u=v;return x.f;}
static u32 word(f32 f){union{f32 f;u32 u;}x;x.f=f;return x.u;}
u8 func_151D8E20(void){selectorCalls++;if(mode&1){payload.payload.scale=3.25f;payload.payload.alpha^=85;actual.actor.bytes[12]^=170;actual.actor.bytes[1]^=85;}if(mode&2){actual.actor.payload=&other.payload;actual.actor.records=&alternate.rows[128];actual.actor.bytes[45]=1;}return(u8)wantedSelector;}
void func_151DBCBC(u8 selector,f32 scale,s16 alpha,s32 result,void*vector,u8 group,s32 context){f32*p=vector;effectCalls++;if(selector!=wantedSelector||word(scale)!=wantedScale||alpha!=wantedAlpha||result!=wantedResult||group!=wantedGroup||(u32)context!=wantedContext||word(p[0])!=wantedX||word(p[1])!=wantedHeight||word(p[2])!=wantedZ)bad=1;if(mode&2){actual.actor.payload=&other.payload;payload.payload.state=119;}p[0]=9.0f;}
"""
 for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('s32 '+source.FUNCTION,'static s32 '+name)+'\n'
 t+=r"""
typedef s32(*Response)(u8*,f32,f32,f32,f32,void*);
static int check(Response fn){u32 cursor,byte,mutation,i;u8*a=(u8*)&actual,*e=(u8*)&expected,*p=(u8*)&payload,*q=(u8*)&wantedPayload,*o=(u8*)&other,*w=(u8*)&wantedOther;const u32 f[]={0,0x80000000,0x3F800000,0xC0200000,0x3FA00000,0xBF400000,0x0DA24260,0x60AD78EC};s32 index;
 for(i=0;i<512;i++){records.rows[i].x=(f32)i*0.25f;records.rows[i].y=(f32)i;records.rows[i].z=-(f32)(i+1)*0.5f;records.rows[i].velocityY=1.25f;records.rows[i].other=-2.5f;alternate.rows[i]=records.rows[i];alternate.rows[i].x+=1000.0f;}
 for(cursor=0;cursor<256;cursor++)for(byte=0;byte<256;byte++)for(mutation=0;mutation<4;mutation++){
  for(i=0;i<sizeof(actual);i++)a[i]=(u8)(i*13+byte);for(i=0;i<sizeof(payload);i++)p[i]=(u8)(i*17+cursor);for(i=0;i<sizeof(other);i++)o[i]=(u8)(i*19+cursor);
  actual.actor.records=&records.rows[128];actual.actor.payload=&payload.payload;actual.actor.bytes[45]=(u8)cursor;actual.actor.bytes[12]=(u8)(byte*17+3);actual.actor.bytes[1]=(u8)(255-byte);payload.payload.scale=real(f[byte&7]);payload.payload.alpha=(u8)byte;
  for(i=0;i<sizeof(actual);i++)e[i]=a[i];for(i=0;i<sizeof(payload);i++)q[i]=p[i];for(i=0;i<sizeof(other);i++)w[i]=o[i];mode=mutation;index=(s8)cursor;wantedX=word(records.rows[128+index].x);wantedZ=word(records.rows[128+index].z);wantedHeight=f[(byte+3)&7];wantedSelector=byte;wantedResult=(s32)(byte&1?0x12345678u:0u);
  if(mode&1){wantedPayload.payload.scale=3.25f;wantedPayload.payload.alpha^=85;expected.actor.bytes[12]^=170;expected.actor.bytes[1]^=85;}
  if(mode&2){expected.actor.payload=&other.payload;expected.actor.records=&alternate.rows[128];expected.actor.bytes[45]=1;}
  wantedScale=word(wantedPayload.payload.scale*7.0f);wantedAlpha=wantedPayload.payload.alpha;wantedGroup=expected.actor.bytes[12];wantedContext=expected.actor.bytes[1];wantedPayload.payload.state=4;
  selectorCalls=effectCalls=bad=0;if(fn((u8*)&actual.actor,real(f[(byte+1)&7]),real(f[(byte+2)&7]),real(f[(byte+4)&7]),real(wantedHeight),(void*)wantedResult)!=1||bad||selectorCalls!=1||effectCalls!=1)return 1;
  for(i=0;i<sizeof(actual);i++)if(a[i]!=e[i])return 1;for(i=0;i<sizeof(payload);i++)if(p[i]!=q[i])return 1;for(i=0;i<sizeof(other);i++)if(o[i]!=w[i])return 1;
 }return 0;}
static int run(void){if(check(selected))return 10;
"""
 for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START

class RecordImpactResponseTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>51I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>51I',data,fs[source.FUNCTION]['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,selector=source.SELECTOR,effect=source.EFFECT):
  initial=fixture(c);wanted,calls,packet=reference(initial,c);calls=[({source.SELECTOR:selector,source.EFFECT:effect}[t],a)for t,a in calls];pair=[]
  for words in images or(self.truth,self.words):
   m=ImpactOracle(words,initial,c,entry,selector,effect).run();self.assertEqual((public(m.memory),m.calls,m.packets,m.r[2]),(public(wanted),calls,[packet],1),c);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def linked(self,obj,entry,selector,effect,label):
  p=self.fresh/label;p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'--defsym=func_151D8E20=0x%X'%selector,'--defsym=func_151DBCBC=0x%X'%effect,'-o',str(p.with_suffix('.elf')),str(obj)],capture_output=True,check=True);return list(struct.unpack_from('>51I',sections(p.with_suffix('.elf'))['.text'][1]))
 def test_01_owner_actual_Make_six_argument_ABI_and_table(self):
  self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFB8)
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),33)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),32);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_1D92F0.c.o.compact'),33);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22EF18]);self.assertEqual(struct.unpack_from('>I',self.rom,0x22EF10+2*4)[0],source.ENTRY)
  proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),proposed);self.assertEqual(proposed.count('#pragma GLOBAL_ASM'),6);self.assertIn('extern s32 (*D_8008A450[])(u8 *, f32, f32, f32, f32, void *);',self.values['conker/src/game/generated_175250.c'].decode())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=51,frame=72,bindings=2,guards=0,neighbors=32,compact_functions=33,GLOBAL_ASM_routines=6,Make_commands=5,arguments=6,return_value=1,signed_cursor=True,registered_table_slot=2,no_diagnostics=True)
 def test_02_guest_signed_cursors_float_words_and_provider_aliases(self):
  count=0;visited=set()
  for c in corpus():m=self.compare(c);visited.update(m.visits);count+=1
  self.assertEqual(visited,set(range(source.ENTRY,source.ENTRY+204,4)));self.receipt['guest']=dict(cases=count,all51words_visited=True,all256_signed_cursors_and_unsigned_arguments=True,raw_XYZ_height_words=True,two_actor_and_three_payload_layouts=True,all64_provider_modes=True,selector_precedes_scale_alpha_group_context_loads=True,captured_records_and_payload_retained=True,stack_argument_and_payload_home_mutations_guest_only=True,full_state_access_trace=True)
 def test_03_original_typed_caller_and_complete_retained_helpers(self):
  count=0;visited=set()
  for cursor,mode,phase,enabled in itertools.product((-128,-1,0,127),(0,1,2,4,8,16,32),(0,8),(False,True)):
   c=Case(cursor=cursor,mode=mode,phase=phase);pair=[]
   for words in(self.truth,self.words):
    m,(wanted,calls,packets,result)=caller_machine(self.rom,words,c,enabled)
    with self.assertRaises(WindowBoundary):m.run()
    self.assertEqual((public(m.memory),m.calls,m.packets,m.r[2]),(public(wanted),calls,packets,result));visited.update(m.visits);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
  self.assertTrue(set(range(WINDOW,0x15148D74,4))<=visited);old=self.values['conker/build/conker.us.elf'];parent_at=source.elf_slot_offset(old,source.PARENT,572);self.assertEqual(old[parent_at:parent_at+572],self.rom[0x176054:0x176290]);table_at=source.elf_slot_offset(old,source.TABLE,32);self.assertEqual(old[table_at:table_at+32],self.rom[0x22EF10:0x22EF30])
  descriptions=((source.SELECTOR,0x2062D0,19),(source.EFFECT,0x20916C,113));connected={};seen={e:set()for e,_,_ in descriptions}
  for entry,pos,n in descriptions:
   code=list(struct.unpack_from('>%dI'%n,self.rom,pos));at=source.elf_slot_offset(old,entry,n*4);self.assertEqual(old[at:at+n*4],struct.pack('>%dI'%n,*code));connected.update(zip(range(entry,entry+n*4,4),code))
  colors_at=source.elf_slot_offset(old,COLORS,768);colors=old[colors_at:colors_at+768];hcount=0
  for state,query,byte,result,phase in itertools.product((0,1),(0,1),(0,37,255),(0,1),(0,8)):
   c=Case(byte=byte,selector=byte,state=state,query=query,result=result,phase=phase);initial=fixture(c);put(initial,STATE,state);put(initial,BYTE,byte,1)
   for i,v in enumerate(colors):initial[COLORS+i]=v
   selected=10 if state==0 and query==0 else byte;want,_,packet=reference(initial,c,selected=selected);pair=[]
   for words in(self.truth,self.words):
    m=ImpactOracle(words,initial,c,connected=connected).run();self.assertEqual((public(m.memory),m.packets,m.r[2]),(public(want),[packet],1));actual=next(a for t,a in m.calls if t==source.EFFECT);self.assertEqual(actual[0],selected);creates=[(t,a)for t,a in m.calls if t in(CREATE_A,CREATE_B)];self.assertEqual(len(creates),1);t,a=creates[0];self.assertEqual(t,CREATE_A if result else CREATE_B);self.assertEqual(a[1:4],(0,0,result));self.assertEqual(a[4:9],(*packet,actual[1],actual[1]));self.assertEqual(a[11:],(0,actual[5],actual[6]));self.assertEqual(m.random_calls,3 if result else 0)
    descriptor=m.descriptors[0];self.assertEqual(descriptor[:12],struct.pack('>I H BB I',0x67B02,300,56,0,0));self.assertEqual(descriptor[12:16],struct.pack('>I',0x8000));self.assertEqual(descriptor[16:24],bytes((byte,255,*colors[selected*3:selected*3+3],255,0,6)));self.assertEqual(descriptor[24:32],struct.pack('>II',0x440001,0));self.assertEqual(descriptor[32],255);self.assertEqual(descriptor[34:38],struct.pack('>HH',1,255))
    for entry,_,n in descriptions:seen[entry].update(v for v in m.visits if entry<=v<entry+n*4)
    pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));hcount+=1
  self.assertEqual([len(seen[e])for e,_,_ in descriptions],[19,113]);self.receipt['integration']=dict(original_caller_window_words=19,caller_cases=count,complete_parent_words=143,retained_parent_exact=True,slot2_six_arguments_zero_selector_skip_and_result_consumed=True,helper_cases=hcount,retained_original_helpers_words=132,helper_coverage=[19,113],effect_descriptor_and_all14_constructor_arguments=True,query_random_and_constructors_bounded=True,full_parent_or_provider_or_gameplay=False)
 def test_04_native32_six_argument_values_and_effective_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run(native_command('-'+opt)+['-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(subprocess.run([str(exe)],timeout=60).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=262144,effective_controls=10,trapping_UBSan=True,all256_signed_cursors_and_byte_fields=True,typed20byte_records=True,six_argument_callback_and_seven_argument_service=True,captured_payload_after_actor_redirect=True,actor_payload_alternate_fences=True,valid_backing_for_negative_indices_and_controls=True,no_portable_guest_home_mutation_or_FCSR_claim=True)
 def test_05_fired_access_prefixes_and_argument_homes(self):
  cuts=0;delays=0
  for c in(Case(),Case(cursor=-128),Case(mode=63),Case(actor_layout=1),Case(payload_layout=1),Case(payload_layout=2),Case(mode=4),Case(mode=16)):
   good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=ImpactOracle(words,fixture(c),c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1;delays+=pair[0].delay_of is not None
  self.receipt['faults']=dict(prefix_pairs=cuts,delay_slot_cuts=delays,full_state_trace_PC_delay=True,portable_C_fault_claimed=False)
 def test_06_actual_padder_raw_corruptions_and_GNU_rebases(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
  for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,rs|{96:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.checked_payload(b,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,(entry,selector,effect)in enumerate(((source.ENTRY,source.SELECTOR,source.EFFECT),(0x17007FFC,0x171D8E20,0x171DBCBC),(0x2500FFFC,0x251D8E20,0x251DBCBC))):
   images=[self.linked(self.out/n,entry,selector,effect,'layout-%d-%d'%(j,k))for k,n in enumerate(('original-'+source.FUNCTION+'.o','selected.o'))];self.assertEqual(*images)
   for c in(Case(),Case(cursor=-128),Case(mode=63),Case(actor_layout=1),Case(payload_layout=1),Case(mode=16)):self.compare(c,images,entry,selector,effect);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=3,original_and_compiled_GNU_objects_equal=True,two_call_bindings_preserved=True,guards=0)
 def test_07_independently_compiled_semantic_controls(self):
  for name,body in controls().items():
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(cursor=-128,mode=2,pattern=4);m=ImpactOracle(words,fixture(c),c).run();want,calls,packet=reference(fixture(c),c);self.assertNotEqual((public(m.memory),m.calls,m.packets,m.r[2]),(public(want),calls,[packet],1),name)
  self.receipt['compiled_controls']=dict(count=len(controls()),observable_state_calls_packet_or_return_mismatches=True)
 def test_08_strict_entire_image_metadata_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+204];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,204);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+100,at+204,source.elf_slot_offset(before,0x80082B20,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(x!=y for x,y in zip(before,expected)),152);self.receipt['image']=dict(changed_bytes=152,code_bytes=151,extent_bytes=1,metadata_bytes=0,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088,exclusions=0,corruptions=6,guards_and_shared_headers_unchanged=True)
