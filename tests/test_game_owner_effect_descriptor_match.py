"""Direct descriptor C, original notification/constructor/caller, native ABI and image."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_owner_effect_descriptor_match as source
from tools.tests import game_owner_effect_descriptor_oracle as oracle
from tools.tests.game_owner_effect_descriptor_oracle import Case,DescriptorOracle,fixture,reference,public
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
def controls():
 b=source.SELECTED
 return dict(notification=b.replace('(40, owner, 22)','(39, owner, 22)'),
  identity=b.replace('owner[0x3B]','owner[0x3A]'),attachment=b.replace('attachment = 1','attachment = 0'),
  zero=b.replace('vector[1] = 0.0f','vector[1] = 1.0f'),first=b.replace('value20 = D_800A9DCC','value20 = 0.0f'),
  duration=b.replace('duration = 320','duration = 321'),flags=b.replace('flags = 6','flags = 4'),
  kind=b.replace('kind = 10','kind = 11'),callback=b.replace('callback = -1','callback = 0'),
  mode=b.replace('mode = 9','mode = 8'),selector=b.replace('0, selector, category','0, selector ^ 1, category'),
  result=b.replace('    return created;','    return created == NULL ? NULL : owner;'))
def native_harness():
 t=source.HEADERS+'\n'.join(b.replace(source.FUNCTION,'test_'+n)for n,b in dict(selected=source.SELECTED,**controls()).items())
 t+=r'''
f32 D_800A9DCC,D_800A9DD0;
typedef void *(*Fn)(u8 *,u8,s32);
static u8 owner[0x200],result[0x80];
static u8 *wanted_owner;static u8 wanted_selector;static s32 wanted_category;
static int calls,bad,mutation,outcome,setup,state_effect;static OwnerEffectDescriptor1D92F0 expected;
static f32 fp(u32 b){union{u32 w;f32 f;}v;v.w=b;return v.f;}
void func_1516962C(s32 event,void *ptr,u8 kind){
 if(calls++!=0||event!=40||ptr!=wanted_owner||kind!=22)bad=1;
 if(mutation){owner[0x3B]^=0x55;D_800A9DCC=2.0f;D_800A9DD0=0.5f;}
}
void *func_1513418C(void *p,s32 size,u8 selector,s32 category){u32 i;u8 *a=p,*b=(u8*)&expected;
 if(calls++!=1||size||selector!=wanted_selector||category!=wanted_category)bad=2;
 expected.zero0=expected.zero4=0;expected.ownerIdentity=owner[0x3B];expected.owner=owner;expected.attachment=1;
 expected.vector[0]=expected.vector[1]=expected.vector[2]=0.0f;expected.value20=D_800A9DCC;expected.value24=D_800A9DD0;
 expected.duration=320;expected.flags=6;expected.kind=10;expected.callback=-1;expected.mode=9;
 for(i=0;i<48;i++)if(!(i>=9&&i<=11)&&!(i>=17&&i<=19)&&i<46&&a[i]!=b[i])bad=3;
 return outcome?result:NULL;
}
static u32 patterns[]={0,0x80000000,1,0x7F800000,0x7FA12345,0x411CCCCD};
static s32 contexts[]={0,1,-1,(-2147483647-1),2147483647};
static int check(Fn fn){s32 byte,field,ctx,nil;u32 i;void *answer;
 for(byte=0;byte<256;byte++)for(field=0;field<2;field++)for(ctx=0;ctx<5;ctx++)for(nil=0;nil<2;nil++)for(outcome=0;outcome<2;outcome++)for(mutation=0;mutation<2;mutation++){
  for(i=0;i<sizeof(owner);i++)owner[i]=0x5A;for(i=0;i<sizeof(result);i++)result[i]=0xA5;
  owner[0x3B]=field?(u8)0x87:(u8)byte;wanted_selector=field?(u8)byte:(u8)0xE1;wanted_category=contexts[ctx];wanted_owner=nil?NULL:owner;
  D_800A9DCC=fp(patterns[byte%6]);D_800A9DD0=fp(patterns[(byte+3)%6]);calls=bad=0;answer=fn(wanted_owner,wanted_selector,wanted_category);
  if(bad||calls!=(nil?0:2)||answer!=(!nil&&outcome?result:NULL))return 1;
  for(i=0;i<sizeof(result);i++)if(result[i]!=0xA5)return 2;
  for(i=0;i<sizeof(owner);i++)if(i!=0x3B&&owner[i]!=0x5A)return 3;
 }return 0;}
static void func_151B01B8(u8 *a,u8 *b){if(a!=result||b!=owner||setup++!=0)bad=4;}
static void func_151B09BC(u8 *a,u8 *b,s32 v,u8 sel,s32 tail){if(a!=result||b!=owner||v!=1000||sel!=255||tail||setup++!=1)bad=5;if(state_effect)owner[4]++;}
'''
 caller=source.function_span((ROOT/source.CALLER_SOURCE).read_text(),'func_15194794')
 text=(ROOT/source.CALLER_SOURCE).read_text();t+=text[caller[0]:caller[1]].replace(source.FUNCTION,'test_selected')
 t+=r'''
static int parent_check(void){int state;for(state=0;state<256;state++)for(state_effect=0;state_effect<2;state_effect++)for(outcome=0;outcome<2;outcome++)for(mutation=0;mutation<2;mutation++){
 owner[4]=(u8)state;owner[0x3B]=0x87;wanted_owner=owner;wanted_selector=255;wanted_category=1;D_800A9DCC=2.0f;D_800A9DD0=0.5f;calls=bad=setup=0;
 func_15194794(result,owner,123);if(bad||setup!=2||calls!=(owner[4]<5?2:0))return 1;
 }return 0;}
static int run(void){if(check(test_selected)||parent_check())return 10;
'''
 for i,n in enumerate(controls()):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
class OwnerEffectDescriptorTests(unittest.TestCase):
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
   m=DescriptorOracle(words,initial,c,entry=entry,s=s,connected=code).run();self.assertEqual((public(m.memory),m.calls,m.r[2],m.packets),(public(wanted[0]),wanted[1],wanted[2],wanted[3]),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0]
 def test_01_owner_Make_caller_and_binding_contract(self):
  self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/'original-func_151AF270.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),33)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),32);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertFalse(source.NEW_GUARDS)
  self.assertEqual(source.recovered_caller(self.values[source.CALLER_SOURCE].decode()).encode(),(self.out/'proposed-caller.c').read_bytes());self.assertEqual(self.values[source.CALLER_OBJECT],(self.out/'qualified-caller-padded.o').read_bytes());self.assertEqual(source.same_functions(self.out/'before-caller.o',self.out/'after-caller.o',()),29)
  self.assertEqual(len(json.loads((self.out/'caller-Make-commands.json').read_text())),5)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertEqual([4*i for i,w in enumerate(ws)if w==jal],[0x1C1CA8]);self.assertFalse(any(w==source.ENTRY for w in ws))
  image=self.values['conker/build/conker.us.elf']
  for entry,rom,n in (*oracle.HELPERS,(oracle.PARENT,oracle.PARENT_ROM,31),(0x800A82BC,0x24CD7C,5),(0x800A9DCC,0x24E88C,2)):
   at=source.elf_slot_offset(image,entry,n*4);self.assertEqual(image[at:at+n*4],self.rom[rom:rom+n*4])
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(body_words=50,frame=80,bindings=6,guards=0,neighbors=32,compact_functions=33,Make_commands=10,caller_functions=29,caller_words=31,caller_object_identical=True,caller_typed_pointer_return_ignored=True,old_caller_warning_retained=True)
 def test_02_guest_notification_order_and_descriptor(self):
  cases=[replace(Case(),**{field:0xA5A50000|i})for field,i in itertools.product(('identity','selector'),range(256))]
  cases.extend(Case(owner=owner,outcome=outcome,effect=effect,phase=phase,category=ctx)for owner,outcome,effect,phase,ctx in itertools.product((0,oracle.OWNER),range(2),range(8),(0,8),(0,1,0x80000000,0xFFFFFFFF)))
  cases.extend(Case(first=w,second=w^0x80000000)for w in(0,0x80000000,1,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345,0xFFFFFFFF))
  visited=set()
  for c in cases:
   m=self.compare(c);visited.update(m.visits)
   if not c.owner:self.assertFalse(m.calls)
  self.assertEqual(len(visited),50);self.receipt['guest']=dict(cases=len(cases),covered_words=50,notification_before_identity_and_float_reads=True,all_unsigned_byte_lanes=True,all_48_packet_bytes=True,padding_preserved=True,home_redirections_guest_only=True,raw_float_bits=True)
 def test_03_original_helpers_and_complete_caller(self):
  count=callers=0;visited=set();parent_visits=set()
  for outcome,valid,matrix,typ,al,effect in itertools.product(range(2),range(2),range(2),(0,15),range(2),(0,1,2,4)):
   m=self.compare(Case(outcome=outcome,valid=valid,matrix=matrix,actor_type=typ,allocation_effect=al,effect=effect),connected=True);visited.update(m.visits);count+=1
   self.assertEqual(len(m.notifications),1);self.assertEqual(m.notifications[0][:5],struct.pack('>IB',oracle.OWNER,0x87))
  for state,state_effect,outcome,phase in itertools.product(range(256),range(2),range(2),(0,8)):
   c=Case(state=state,state_effect=state_effect,outcome=outcome,phase=phase,effect=1);pair=[]
   for words in(self.truth,self.words):
    m,wanted=oracle.caller_machine(self.rom,words,c);m.run();self.assertEqual((public(m.memory),m.calls,m.r[2],m.packets),(public(wanted[0]),wanted[1],wanted[2],wanted[3]));pair.append(m);parent_visits.update(m.visits)
   self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);callers+=1
  coverage=[sum(pc in visited for pc in range(entry,entry+n*4,4))for entry,_,n in oracle.HELPERS]
  missing=[hex(pc)for entry,_,n in oracle.HELPERS for pc in range(entry,entry+n*4,4)if pc not in visited]
  self.assertEqual(coverage,[15,74,11]);self.assertEqual(missing,['0x15134234','0x15134284'])
  self.assertEqual(struct.unpack_from('>I',self.rom,0x1616E4)[0],0x8C4301D4);self.assertEqual(struct.unpack_from('>I',self.rom,0x161734)[0],0xA0EF003A)
  self.assertEqual(sum(pc in parent_visits for pc in range(oracle.PARENT,oracle.PARENT+124,4)),31)
  self.receipt['integration']=dict(connected_cases=count,caller_cases=callers,caller_words=31,helper_words=102,helper_coverage=coverage,unvisited_helper_words=missing,original_notification_wrapper=True,original_constructor=True,original_memcpy=True,caller_state_gate_after_second_setup=True,bounded_services=['func_1516944C','func_15167A68','func_1516972C','func_15143134','func_151B01B8','func_151B09BC'],gameplay_claimed=False)
 def test_04_native32_SDK_and_semantic_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());logs={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);built=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=built.stderr)
  self.receipt['native']=dict(optimizations=logs,direct_cases_per_profile=256*2*5*2*2*2,caller_cases_per_profile=256*2*2*2,controls=len(controls()),SDK=True,pointers32=True,trapping_UBSan=True,notification_mutations=True,valid_backing_and_canaries=True,indeterminate_padding_not_asserted=True)
 def test_05_direct_connected_and_parent_fault_prefixes(self):
  count=delay=0
  runs=[(Case(owner=0),False,False),(Case(effect=7),False,False),(Case(effect=7,outcome=False),True,False),(Case(effect=7,matrix=True),True,False),(Case(effect=1,matrix=True),True,True)]
  for c,connected,parent in runs:
   def machine(words):return oracle.caller_machine(self.rom,words,c,connected)[0]if parent else DescriptorOracle(words,fixture(c),c,connected=oracle.helper_code(self.rom)if connected else None)
   full=machine(self.truth).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=machine(words);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(pair[1].current_pc,pair[1].delay_of,cut));count+=1;delay+=pair[0].delay_of is not None
  self.receipt['faults']=dict(prefix_pairs=count,delay_slot_cuts=delay,complete_state_PC_trace=True,portable_C_fault_claimed=False)
 def test_06_rejections_padder_and_three_GNU_layouts(self):
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
   s=oracle.symbols()if j==0 else dict(D_800A9DCC=(0x80417FFC,0x80528004)[j-1],D_800A9DD0=(0x80418000,0x80528008)[j-1],func_1516962C=entry+0x10000,func_1513418C=entry+0x20000)
   paths=(self.out/'original-func_151AF270.o',self.out/'make-shadow/src/game/generated_1D92F0.c.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for owner,outcome,effect,phase in itertools.product((0,oracle.OWNER),range(2),range(8),(0,8)):self.compare(Case(owner=owner,outcome=outcome,effect=effect,phase=phase),images,entry,s);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,all_three_objects_linked=True,no_guards=True,signed_low_constant_addresses=True)
 def test_07_compiled_semantic_negatives(self):
  evidence={}
  def view(m,calls,value,packets):
   return public(m),[(t,(a[1:])if t==oracle.CREATE else a)for t,a in calls],value,[bytes(b for i,b in enumerate(p)if i not in oracle.PADDING)for p in packets]
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name)
   for c in(Case(identity=byte,outcome=outcome,effect=1)for byte,outcome in itertools.product((0,128,255),range(2))):
    initial=fixture(c);m=DescriptorOracle(words,initial,c).run();wanted=reference(initial,c)
    if view(m.memory,m.calls,m.r[2],m.packets)!=view(*wanted):evidence[name]=dict(identity=c.identity,outcome=c.outcome);break
   self.assertIn(name,evidence)
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,private_stack_addresses_and_padding_excluded=True)
 def test_08_strict_whole_image_and_inputs(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+200];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,200);named={n:(p,f,loc)for p,n,f,loc in source.symbol_rows(before)}
  positions=[20,at,at+200,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.PARENT,124),source.elf_slot_offset(before,0x800A9DCC,4)]
  for n in('D_800A9DD0','D_8009CDD0','D_800A9DCC','D_800AABFC','D_800994AC','D_8009EEAC'):positions.extend((named[n][0]+4,named[n][2]))
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),185)
  self.receipt['image']=dict(changed_bytes=185,code_bytes=152,extent_bytes=1,metadata_bytes=32,closed_named_symbol_swaps=3,exclusions=0,corruptions=len(positions)+1,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v))
