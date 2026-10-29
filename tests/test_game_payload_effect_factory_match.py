"""Payload factory: byte-lane ABI, allocation chain, snapshot copy and full image."""
from pathlib import Path
from dataclasses import replace
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_payload_effect_factory_match as source
from tools.tests import game_payload_effect_factory_oracle as oracle
from tools.tests.game_payload_effect_factory_oracle import Case,fixture,reference,public,FactoryOracle,put,read,faults
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
 return dict(wrong_kind=b.replace('header.unk4 = 0x21','header.unk4 = 0x20'),wrong_duration=b.replace('header.unk2 = 300','header.unk2 = 301'),wrong_flags=b.replace('header.unk0 = 2','header.unk0 = 3'),wrong_position=b.replace('position.unk0 = 0','position.unk0 = 1'),wrong_size=b.replace('0xFF, 0, 4,','0xFF, 0, 8,'),signed_byte=b.replace('(u8 arg0,','(s8 arg0,'),short_copy=b.replace('&payload, 4);','&payload, 3);'),wrong_payload=b.replace('payload = owner;','payload = NULL;'),wrong_return=b.replace('return created;','return NULL;'))
def native_harness():
 t=source.HEADERS.replace('memcpy','test_copy')
 for n,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,'test_'+n).replace('memcpy','test_copy')+'\n'
 t+='struct225 *adapt_signed_byte(u8 a,u8 b,u8 c,u8 d,void *owner,u8 e,s32 f){return test_signed_byte((s8)a,b,c,d,owner,e,f);}\n'
 t+=r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(u32)==4&&sizeof(Header)==6&&sizeof(Header2)==12)?1:-1];
static struct225 output;static u8 owners[16];static s32 outcome,mutation,bad,calls,copies;static u8 bytes[5];static s32 last;static void *wanted_owner;
__attribute__((noinline,noclone)) struct225 *func_151602C0(Header*h,Header2*p,s32 a,s32 b,s32 c,s32 d,u8 e,u8 f,s32 size,u8 priority,s32 g){
calls++;if(h->unk0!=2||h->unk1!=-1||h->unk2!=300||h->unk4!=33||p->unk0||p->unk4||p->unk8||a!=bytes[0]||b!=bytes[1]||c!=bytes[2]||d!=bytes[3]||e!=255||f||size!=4||priority!=bytes[4]||g!=last)bad=1;
if(mutation){h->unk4^=0x55;p->unk0=(s32)0x87654321;owners[0]^=0xA5;}return outcome==2?&output:NULL;}
__attribute__((noinline,noclone)) void *test_copy(void*d,const void*s,unsigned int n){u32 i;copies++;if(d!=(u8*)&output+24||n!=4)bad=1;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];return d;}
typedef struct225*(*Fn)(u8,u8,u8,u8,void*,u8,s32);
static const u32 values[]={0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF};
static int check(Fn fn){s32 bi,field,oi,vi;u32 i;struct225 *answer;void *actual;
for(bi=0;bi<256;bi++)for(field=0;field<5;field++)for(outcome=0;outcome<3;outcome++)for(mutation=0;mutation<2;mutation++)for(oi=0;oi<3;oi++)for(vi=0;vi<5;vi++){
for(i=0;i<5;i++)bytes[i]=(u8)(i*51);bytes[field]=(u8)bi;last=(s32)values[vi];wanted_owner=oi==0?NULL:oi==1?(void*)owners:(void*)(owners+15);for(i=0;i<sizeof(output);i++)((u8*)&output)[i]=0xA5;bad=calls=copies=0;
answer=fn(bytes[0],bytes[1],bytes[2],bytes[3],wanted_owner,bytes[4],last);
if(bad||calls!=1||copies!=(outcome==2)||answer!=(outcome==2?&output:NULL))return 1;
if(outcome==2){for(i=0;i<4;i++)((u8*)&actual)[i]=((u8*)&output)[24+i];if(actual!=wanted_owner)return 2;}
for(i=0;i<sizeof(output);i++)if(!(outcome==2&&i>=24&&i<28)&&((u8*)&output)[i]!=0xA5)return 3;
}return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,n in enumerate(controls()):t+='if(!check('+('adapt_signed_byte'if n=='signed_byte'else'test_'+n)+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
class PayloadEffectFactoryTests(unittest.TestCase):
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
  initial=fixture(c);wanted=reference(initial,c,s,connected);pair=[];code=oracle.helper_code(self.rom)if connected else None
  for words in images or(self.truth,self.words,self.raw):
   m=FactoryOracle(words,initial,c,entry=entry,s=s,connected=code).run();self.assertEqual((public(m.memory),m.calls,m.r[2],m.factory_observations),(public(wanted[0]),wanted[1],wanted[2],wanted[3]),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0]
 def test_01_owner_Make_and_original_call_contract(self):
  self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/'original-func_150F0198.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),44)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),43);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertFalse(source.NEW_GUARDS)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertEqual([4*i for i,w in enumerate(ws)if w==jal],[0x11C804]);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertIn('s32 func_150EEF80() {\n    return 0;\n}',self.values[source.SOURCE].decode())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(body_words=50,frame=88,bindings=2,guards=0,neighbors=43,compact_functions=44,Make_commands=3,new_diagnostics=0,original_direct_calls=1,signature_arguments=7,return_contract='struct225 pointer')
 def test_02_guest_byte_lanes_snapshots_and_copy_gate(self):
  cases=[replace(Case(),**{field:0xA5A50000|i},seed=i)for field,i in itertools.product(('a','b','c','d','fifth'),range(256))]
  cases.extend(Case(owner=owner,sixth=last,outcome=outcome,mutation=mu,phase=phase,seed=last&255)for owner,last,outcome,mu,phase in itertools.product((0,oracle.OWNER,0xFFFFFFFF,0x80000000),(0,0x7FFFFFFF,0x80000000,0xFFFFFFFF),range(3),range(4),(0,8)))
  visited=set()
  for c in cases:
   m=self.compare(c);visited.update(m.visits)
   if c.outcome!=2:self.assertEqual(len(m.calls),1)
  self.assertEqual(len(visited),50);self.receipt['guest']=dict(cases=len(cases),covered_words=50,all_five_byte_lanes=True,payload_snapshot=True,null_copy_gate=True,header_padding_preserved=True,incoming_home_mutation_guest_only=True)
 def test_03_original_factory_wrapper_and_caller_window(self):
  visited=set();count=callers=0
  for outcome,mu,last,phase in itertools.product(range(3),range(4),(0,0x80000000,0xFFFFFFFF),(0,8)):
   m=self.compare(Case(outcome=outcome,mutation=mu,sixth=last,phase=phase),connected=True);visited.update(m.visits);count+=1
  coverage=[sum(pc in visited for pc in range(entry,entry+4*n,4))for entry,_,n in oracle.HELPERS];self.assertEqual(coverage,[47,32])
  for outcome,mu,byte,last in itertools.product(range(3),range(4),(0,128,255),(0,0xFFFFFFFF)):
   c=Case(outcome=outcome,mutation=mu,fifth=byte,sixth=last);pair=[]
   for words in(self.truth,self.words,self.raw):
    m,wanted=oracle.caller_machine(self.rom,words,c)
    with self.assertRaises(WindowBoundary):m.run()
    self.assertEqual((public(m.memory),m.calls,m.r[2],m.factory_observations),(public(wanted[0]),wanted[1],wanted[2],wanted[3]));pair.append(m)
   for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
   callers+=1
  self.receipt['integration']=dict(connected_cases=count,caller_cases=callers,caller_windows=1,caller_words=9,helper_words=79,helper_coverage=coverage,allocation_outcomes=3,cleanup_on_object_failure=True,parent_current_C_placeholder=True,full_parent_or_gameplay=False,bounded_services=['func_1515D5F8','func_15167A68','func_1515F10C','memcpy'])
 def test_04_native32_SDK_and_effective_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());logs={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);built=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=built.stderr)
  self.receipt['native']=dict(optimizations=logs,cases_per_optimization=256*5*3*2*3*5,controls=9,SDK=True,pointers32=True,trapping_UBSan=True,valid_owner_and_output_backing=True,indeterminate_header_padding_not_asserted=True)
 def test_05_fault_prefixes_for_direct_connected_and_caller(self):
  count=caller_count=delay=0
  for c,connected in((Case(outcome=0),False),(Case(mutation=3),False),(Case(outcome=0),True),(Case(outcome=1,mutation=3),True),(Case(mutation=3),True)):
   initial=fixture(c);code=oracle.helper_code(self.rom)if connected else None;full=FactoryOracle(self.truth,initial,c,connected=code).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in(self.truth,self.words,self.raw):
     m=FactoryOracle(words,initial,c,connected=code);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(m.current_pc,m.delay_of,cut))
    count+=1;delay+=pair[0].delay_of is not None
  c=Case(mutation=3);full,_=oracle.caller_machine(self.rom,self.truth,c)
  with self.assertRaises(WindowBoundary):full.run()
  for cut in range(full.all_accesses):
   pair=[]
   for words in(self.truth,self.words):
    m,_=oracle.caller_machine(self.rom,words,c);m.cut=cut
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
   s=oracle.symbols()if j==0 else{n:entry+0x10000+i*0x1000 for i,n in enumerate(oracle.symbols())};paths=(self.out/'original-func_150F0198.o',self.out/'make-shadow/src/game/generated_11C2B0.c.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for outcome,mu,phase in itertools.product(range(3),range(4),(0,8)):self.compare(Case(outcome=outcome,mutation=mu,phase=phase),images,entry,s);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,bindings=2,all_three_objects_linked=True,no_guards=True,padded_object_reproduced=True)
 def test_07_compiled_semantic_negatives(self):
  evidence={}
  def semantic(memory,calls,result,observations):
   visible=public(memory);visible.pop(oracle.OUTPUT+19,None)
   normalized=[(t,a[2:]if t==oracle.FACTORY else(a[0],a[2]))for t,a in calls]
   return visible,normalized,result,[(h[:5],p,a[2:])for h,p,a in observations]
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name)
   for c in(Case(a=byte,outcome=outcome)for byte,outcome in itertools.product((0,128,255),range(3))):
    initial=fixture(c);m=FactoryOracle(words,initial,c).run();wanted=reference(initial,c)
    if semantic(m.memory,m.calls,m.r[2],m.factory_observations)!=semantic(wanted[0],wanted[1],wanted[2],wanted[3]):evidence[name]=dict(first_byte=c.a,outcome=c.outcome);break
   self.assertIn(name,evidence)
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,private_stack_addresses_and_padding_excluded_from_semantic_negative_decision=True)
 def test_08_strict_whole_image_and_inputs(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+200];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,200);named={n:(p,f)for p,n,f,_ in source.symbol_rows(before)}
  positions=[20,at,at+200,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.WINDOW,36),0x2BA144,0x2D4E84,0x2FBC30]
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),152)
  self.receipt['image']=dict(changed_bytes=152,code_bytes=151,extent_bytes=1,metadata_bytes=0,exclusions=0,corruptions=9,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v),caller_and_all_other_bodies_unchanged=True)
