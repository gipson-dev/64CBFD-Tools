"""Owner payload ABI, padding, original allocation/copy and complete image."""
from pathlib import Path
from dataclasses import replace
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_owner_float_payload_match as source
from tools.tests import game_owner_float_payload_oracle as oracle
from tools.tests.game_owner_float_payload_oracle import Case,fixture,reference,public,FactoryOracle,put,read,faults
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_character_effect_pair import WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
def controls():
 b=source.SELECTED
 return dict(wrong_identity=b.replace('owner[0x3B]','owner[0x3A]'),wrong_kind=b.replace('lifetime, -1, 0x1C','lifetime, -1, 0x1D'),wrong_size=b.replace('sizeof(payload), priority','16, priority'),wrong_zero=b.replace('payload.value0 = 0.0f','payload.value0 = D_800A2684'),wrong_second=b.replace('payload.value1 = D_800A2684','payload.value1 = D_800A2688'),short_copy=b.replace('&payload, sizeof(payload)','&payload, 16'),wrong_destination=b.replace('created + 0x28','created + 0x2C'),wrong_payload=b.replace('payload.owner = owner','payload.owner = NULL'),wrong_return=b.replace('return created;','return NULL;'),wrong_lifetime=b.replace('func_15149130(lifetime,','func_15149130(lifetime + 1,'))
def native_harness():
 t=source.HEADERS.replace('memcpy','test_copy')
 for n,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,'test_'+n).replace('memcpy','test_copy')+'\n'
 t+=r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(OwnerFloatPayload)==20&&__builtin_offsetof(OwnerFloatPayload,value0)==8)?1:-1];
f32 D_800A2684,D_800A2688;
static u8 owners[128],output[192];static u8 *wanted_owner;static s16 duration;static u8 priority;static s32 context,outcome,mutation,bad,calls,copies;
static f32 fp(u32 value){union{u32 u;f32 f;}v;v.u=value;return v.f;}
__attribute__((noinline,noclone)) void *func_15149130(s16 life,s8 first,s8 kind,s8 last,u8 active,u8 render,s32 size,u8 slot,s32 ctx){
 calls++;if(life!=duration||first!=-1||kind!=28||last!=-1||active!=1||render!=28||size!=20||slot!=priority||ctx!=context)bad=1;
 if(mutation){wanted_owner[0x3B]^=0x55;D_800A2684=fp(0xBF800000);D_800A2688=fp(0x40000000);}return outcome?output:NULL;
}
__attribute__((noinline,noclone)) void *test_copy(void*d,const void*s,u32 n){u32 i;copies++;if(d!=output+40||n!=20)bad=1;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];return d;}
typedef void*(*Fn)(u8*,s16,u8,s32);
static const s16 lives[]={-32768,-1,0,1,32767,1234};
static const u32 words[]={0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF};
static const u32 floats[]={0,0x80000000,0x3F800000,0x3E50E561,0x3F526E98};
static int check(Fn fn){s32 bi,field,oi,li,wi;u32 i;u8 identity,expected[192];OwnerFloatPayload packet;void *answer;
 for(bi=0;bi<256;bi++)for(field=0;field<2;field++)for(oi=0;oi<3;oi++)for(li=0;li<6;li++)for(wi=0;wi<5;wi++)for(outcome=0;outcome<2;outcome++)for(mutation=0;mutation<2;mutation++){
  for(i=0;i<192;i++)output[i]=0xA5;for(i=0;i<128;i++)owners[i]=0x5A;
  wanted_owner=oi==0?NULL:oi==1?owners+16:output+16;identity=field==0?(u8)bi:0x87;priority=field==1?(u8)bi:0xE1;duration=lives[li];context=(s32)words[wi];
  if(wanted_owner)wanted_owner[0x3B]=identity;
  D_800A2684=fp(floats[bi%5]);D_800A2688=fp(floats[(bi+2)%5]);
  packet.owner=wanted_owner;packet.ownerId=identity;packet.value0=0.0f;packet.value1=D_800A2684;packet.value2=D_800A2688;
  for(i=0;i<192;i++)expected[i]=output[i];if(oi==2&&mutation)expected[16+0x3B]^=0x55;
  if(wanted_owner&&outcome)for(i=0;i<20;i++)if(i<5||i>=8)expected[40+i]=((u8*)&packet)[i];
  bad=calls=copies=0;answer=fn(wanted_owner,duration,priority,context);
  if(bad||calls!=(wanted_owner!=NULL)||copies!=(wanted_owner!=NULL&&outcome)||answer!=(wanted_owner!=NULL&&outcome?output:NULL))return 1;
  for(i=0;i<192;i++)if(!(wanted_owner&&outcome&&i>=45&&i<48)&&output[i]!=expected[i])return 2;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,n in enumerate(controls()):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
class OwnerFloatPayloadTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>50I',cls.rom,source.ROM));cls.words=cls.linked(cls.out/'qualified-padded.o',source.ENTRY,'qualified');cls.raw=cls.linked(cls.out/'selected.o',source.ENTRY,'selected')
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 @classmethod
 def linked(cls,obj,entry,label,s=None):
  defs=oracle.symbols()if s is None else s;text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION];assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,defs);assert not unknown;p=cls.fresh/label
  p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
  return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
 def compare(self,c=Case(),images=None,entry=None,s=None,connected=False):
  initial=fixture(c,s);wanted=reference(initial,c,s,connected);pair=[];code=oracle.helper_code(self.rom)if connected else None
  for words in images or(self.truth,self.words,self.raw):
   m=FactoryOracle(words,initial,c,entry=entry,s=s,connected=code).run();self.assertEqual((public(m.memory),m.calls,m.r[2],m.copy_observations),(public(wanted[0]),wanted[1],wanted[2],wanted[3]),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0]
 def test_01_owner_Make_and_original_call_contract(self):
  self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/'original-func_1510A344.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),10)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),9);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertFalse(source.NEW_GUARDS)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertEqual([4*i for i,w in enumerate(ws)if w==jal],[0x54B30]);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertIn('s32 func_150265CC() {\n    return 0;\n}',self.values['conker/src/game/generated_50D80.c'].decode())
  image=self.values['conker/build/conker.us.elf']
  for entry,rom,n in oracle.HELPERS:
   at=source.elf_slot_offset(image,entry,n*4);self.assertEqual(image[at:at+n*4],self.rom[rom:rom+n*4])
  for va,rom,word in((0x800A2684,0x247144,0x3E50E561),(0x800A2688,0x247148,0x3F526E98)):
   at=source.elf_slot_offset(image,va,4);self.assertEqual(image[at:at+4],self.rom[rom:rom+4]);self.assertEqual(struct.unpack_from('>I',image,at)[0],word)
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(body_words=50,frame=72,bindings=6,guards=0,neighbors=9,compact_functions=10,Make_commands=3,new_diagnostics=0,original_direct_calls=1,signature_arguments=4,return_contract='opaque allocated pointer',shared_provider_size_pointer_spelling_not_changed=True)
 def test_02_guest_lanes_null_gate_and_snapshot(self):
  cases=[replace(Case(),**{field:0xA5A50000|i},seed=i)for field,i in itertools.product(('identity','priority'),range(256))]
  cases.extend(Case(lifetime=life,priority=slot,arg3=ctx,outcome=outcome,mutation=mu,phase=phase)for life,slot,ctx,outcome,mu,phase in itertools.product((0,1,0x7FFF,0x8000,0xFFFF,0x12348001,0xFFFF0001),(0,128,255),(0,0x80000000,0xFFFFFFFF),range(2),range(4),(0,8)))
  cases.extend(Case(owner=owner,outcome=outcome,mutation=mu,phase=phase)for owner,outcome,mu,phase in itertools.product((0,oracle.OUTPUT,oracle.OUTPUT+16),range(2),range(4),(0,8)))
  cases.extend(Case(first=w,second=w^0x80000000,outcome=outcome)for w,outcome in itertools.product((0,0x80000000,1,0x7F800000,0xFF800000,0x7FC12345,0x7F812345,0xFFFFFFFF),range(2)))
  visited=set()
  for c in cases:
   m=self.compare(c);visited.update(m.visits)
   if not c.owner:self.assertFalse(m.calls)
  self.assertEqual(len(visited),50);self.receipt['guest']=dict(cases=len(cases),covered_words=50,signed_halfword_and_unsigned_byte_lanes=True,payload_snapshot=True,null_owner_and_copy_gates=True,padding_preserved=True,owner_output_aliases=True,incoming_home_mutation_guest_only=True,float_bits_without_arithmetic=True)
 def test_03_original_factory_copy_and_caller_window(self):
  visited=set();count=callers=0
  for owner,outcome,mu,life,phase in itertools.product((oracle.OWNER,oracle.OUTPUT+16),range(2),range(4),(0,0x8000,0xFFFF),(0,8)):
   m=self.compare(Case(owner=owner,outcome=outcome,mutation=mu,lifetime=life,phase=phase),connected=True);visited.update(m.visits);count+=1
  coverage=[sum(pc in visited for pc in range(entry,entry+4*n,4))for entry,_,n in oracle.HELPERS]
  self.assertEqual(coverage,[47,11])
  missing=[hex(pc)for entry,_,n in oracle.HELPERS for pc in range(entry,entry+4*n,4)if pc not in visited]
  # This caller fixes flags=1; the factory's flags&2 category-95 arm is unreachable.
  self.assertEqual(missing,['0x15149164','0x15149168'])
  self.assertEqual(struct.unpack_from('>2I',self.rom,0x176614),(0x10000002,0x2402005F))
  for owner,outcome,mu,life,slot,phase in itertools.product((0,oracle.OWNER,oracle.OUTPUT+16),range(2),range(4),(0x8000,0x7FFF),(0,128,255),(0,8)):
   c=Case(owner=owner,outcome=outcome,mutation=mu,lifetime=life,priority=slot,phase=phase);pair=[]
   for words in(self.truth,self.words,self.raw):
    m,wanted=oracle.caller_machine(self.rom,words,c)
    with self.assertRaises(WindowBoundary):m.run()
    self.assertEqual((public(m.memory),m.calls,m.r[2],m.copy_observations),(public(wanted[0]),wanted[1],wanted[2],wanted[3]));pair.append(m)
   for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
   callers+=1
  self.receipt['integration']=dict(connected_cases=count,caller_cases=callers,caller_windows=1,caller_words=7,helper_words=60,helper_coverage=coverage,unvisited_helper_words=missing,allocation_outcomes=2,parent_current_C_placeholder=True,caller_ignores_pointer_and_returns_one=True,full_parent_or_gameplay=False,bounded_services=['func_15167A68','bzero'],original_memcpy_loop=True)
 def test_04_native32_SDK_and_effective_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());logs={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);built=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=built.stderr)
  self.receipt['native']=dict(optimizations=logs,cases_per_optimization=256*2*3*6*5*2*2,controls=10,SDK=True,pointers32=True,trapping_UBSan=True,valid_owner_and_output_backing=True,owner_output_alias=True,indeterminate_padding_not_asserted=True,guest_home_mutations_not_portable_C_claim=True)
 def test_05_fault_prefixes_for_direct_connected_and_caller(self):
  count=caller_count=delay=0
  for c,connected in((Case(owner=0),False),(Case(outcome=0,mutation=3),False),(Case(mutation=3),False),(Case(owner=0),True),(Case(outcome=0,mutation=3),True),(Case(mutation=3),True)):
   initial=fixture(c);code=oracle.helper_code(self.rom)if connected else None;full=FactoryOracle(self.truth,initial,c,connected=code).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in(self.truth,self.words,self.raw):
     m=FactoryOracle(words,initial,c,connected=code);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(m.current_pc,m.delay_of,cut))
    count+=1;delay+=pair[0].delay_of is not None
  full,_=oracle.caller_machine(self.rom,self.truth,Case(mutation=3))
  with self.assertRaises(WindowBoundary):full.run()
  for cut in range(full.all_accesses):
   pair=[]
   for words in(self.truth,self.words):
    m,_=oracle.caller_machine(self.rom,words,Case(mutation=3));m.cut=cut
    with self.assertRaises(faults.AccessBoundary):m.run()
    pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));caller_count+=1
  self.receipt['faults']=dict(direct_and_connected_prefixes=count,caller_prefixes=caller_count,delay_slot_cuts=delay,complete_state_PC_and_trace=True,portable_C_fault_claimed=False)
 def test_06_rejections_and_three_GNU_layouts(self):
  raw,rs=source.payload(self.out/'selected.o');rejects=0
  for at in range(0,len(raw),4):
   bad=bytearray(raw);bad[at+3]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   rejects+=1
  for at in rs:
   bad=dict(rs);bad[at]=[(rs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):source.checked_payload(raw,bad)
   rejects+=1
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   s=oracle.symbols()if j==0 else dict(D_800A2684=(0x80417FFC,0x80528004)[j-1],D_800A2688=(0x80418000,0x80528008)[j-1],func_15149130=entry+0x10000,memcpy=entry+0x20000)
   paths=(self.out/'original-func_1510A344.o',self.out/'make-shadow/src/game/generated_1368C0.c.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for owner,outcome,mu,phase in itertools.product((0,oracle.OWNER),range(2),range(4),(0,8)):self.compare(Case(owner=owner,outcome=outcome,mutation=mu,phase=phase),images,entry,s);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,bindings=6,all_three_objects_linked=True,no_guards=True,padded_object_reproduced=True,signed_low_constant_addresses=True)
 def test_07_compiled_semantic_negatives(self):
  evidence={}
  def semantic(memory,calls,result,observations):
   visible=public(memory)
   for i in(45,46,47):visible.pop(oracle.OUTPUT+i,None)
   normalized=[(t,(a[0],a[2])if t==oracle.COPY else a)for t,a in calls]
   return visible,normalized,result,[(packet[:5]+packet[8:],dest,n)for packet,dest,n in observations]
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name)
   for c in(Case(identity=byte,outcome=outcome,lifetime=0x8000)for byte,outcome in itertools.product((0,128,255),range(2))):
    initial=fixture(c);m=FactoryOracle(words,initial,c).run();wanted=reference(initial,c)
    if semantic(m.memory,m.calls,m.r[2],m.copy_observations)!=semantic(wanted[0],wanted[1],wanted[2],wanted[3]):evidence[name]=dict(identity=c.identity,outcome=c.outcome);break
   self.assertIn(name,evidence)
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,private_stack_addresses_and_padding_excluded_from_semantic_negative_decision=True)
 def test_08_strict_whole_image_and_inputs(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+200];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,200);named={n:(p,f)for p,n,f,_ in source.symbol_rows(before)}
  positions=[20,at,at+200,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.WINDOW,28),source.elf_slot_offset(before,0x800A2684,4),0x2D4E84,0x2FBC30]
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),154)
  self.receipt['image']=dict(changed_bytes=154,code_bytes=153,extent_bytes=1,metadata_bytes=0,exclusions=0,corruptions=9,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v),caller_helpers_constants_and_all_other_bodies_unchanged=True)
