"""Direct lifetime descriptor C, original caller/provider, ABI and image gates."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_owner_lifetime_descriptor_match as source
from tools.tests import game_owner_lifetime_descriptor_oracle as oracle
from tools.tests.game_owner_lifetime_descriptor_oracle import Case,LifetimeOracle,fixture,reference,public
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 return dict(identity=b.replace('owner[0x3B]','owner[0x3A]'),
  lifetime=b.replace('packet.lifetime = lifetime','packet.lifetime = 0'),
  callback=b.replace('updateCallback = -1','updateCallback = 0'),
  constant=b.replace('packet.value1C = D_800A1B70','packet.value1C = 0.0f'),
  mode=b.replace('packet.mode = 2','packet.mode = 1'),
  delay=b.replace('restartDelay = 16','restartDelay = 17'),
  result=b.replace('    return func_15134DAC((s32)&packet, 0);','    func_15134DAC((s32)&packet, 0);\n    return NULL;'),
  context=b.replace('(s32)&packet, 0','(s32)&packet, unusedContext'))

def native_harness():
 t=source.HEADERS+'\n'.join(b.replace(source.FUNCTION,'test_'+n)for n,b in dict(selected=source.SELECTED,**controls()).items())
 t+=r"""
f32 D_800A1B70;
typedef void *(*Fn)(u8 *,s16,s32,s32);
static u8 owner[128],output[160];static s16 lifetime;
static int calls,bad,outcome,mutation;static u32 globalBits;
static OwnerLifetimeDescriptor1228D0 expected;
static f32 fp(u32 b){union{u32 w;f32 f;}v;v.w=b;return v.f;}
void *func_15134DAC(s32 address,s32 context){
 u32 i;u8 *a=(u8*)address,*b=(u8*)&expected;
 if(calls++||context)bad=1;
 expected.owner_id=owner[0x3B];expected.owner=owner;expected.attachmentIndex=3;
 expected.zero0=expected.zero1=expected.zero2=expected.zero3=0.0f;
 expected.value1C=fp(globalBits);expected.value20=8.5f;expected.mode=2;
 expected.activeFrames=40;expected.restartDelay=16;expected.lifetime=lifetime;expected.value2C=0;
 expected.startCallback=5;expected.transformCallback=8;expected.updateCallback=-1;
 expected.rate=1.0f;expected.flags=0;expected.finishCallback=-1;
 for(i=0;i<60;i++)if(!(i>=1&&i<=3)&&!(i>=9&&i<=11)&&i!=37&&!(i>=49&&i<=51)&&i<58&&a[i]!=b[i])bad=2;
 if(mutation){owner[0x3B]^=0x55;D_800A1B70=-1.0f;}
 return outcome?output:NULL;
}
static u32 patterns[]={0,0x80000000,1,0x40966667,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345};
static s16 lifetimes[]={-32768,-32767,-1,0,1,32766,32767};
static int check(Fn fn){int byte,j;u32 i;void *answer;
 if(sizeof(void*)!=4||sizeof(expected)!=60)return 90;
 for(byte=0;byte<256;byte++)for(j=0;j<7;j++)for(outcome=0;outcome<2;outcome++)for(mutation=0;mutation<2;mutation++){
  for(i=0;i<sizeof(owner);i++)owner[i]=0x5A;for(i=0;i<sizeof(output);i++)output[i]=0xA5;
  owner[0x3B]=(u8)byte;lifetime=lifetimes[j];globalBits=patterns[byte%8];D_800A1B70=fp(globalBits);calls=bad=0;
  answer=fn(owner,lifetime,(-2147483647-1),1);
  if(bad||calls!=1||answer!=(outcome?output:NULL))return 1;
  for(i=0;i<sizeof(owner);i++)if(i!=0x3B&&owner[i]!=0x5A)return 2;
  for(i=0;i<sizeof(output);i++)if(output[i]!=0xA5)return 3;
 }return 0;
}
static int run(void){if(check(test_selected))return 10;
"""
 for i,n in enumerate(controls()):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class OwnerLifetimeDescriptorTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>51I',cls.rom,source.ROM));cls.words=cls.linked(cls.out/'qualified-padded.o',source.ENTRY,'qualified');cls.raw=cls.linked(cls.out/'selected.o',source.ENTRY,'selected')
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
   m=LifetimeOracle(words,initial,c,entry=entry,s=s,connected=code).run();self.assertEqual((public(m.memory),m.calls,m.r[2],m.packets,m.copies),(public(wanted[0]),*wanted[1:]),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(oracle.state(pair[0]),oracle.state(m))
  return pair[0]
 def test_01_owner_actual_Make_and_caller_ABI(self):
  self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(self.raw[0],0x27BDFFA8)
  self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/'original-func_150F6890.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),10);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),24)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),23)
  self.assertEqual(source.same_functions(self.out/'before-padded.o',self.out/'qualified-padded.o',(source.FUNCTION,)),23)
  self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes())
  commands=json.loads((self.out/'Make-commands.json').read_text());self.assertEqual(len(commands),3);self.assertEqual(commands[0][0],'../ido/ido5.3_recomp/cc');self.assertIn('-O2',commands[0]);self.assertIn('-g3',commands[0])
  self.assertEqual(source.check_owner_diagnostics((self.out/'actual-Make-diagnostics.txt').read_text()),10);self.assertFalse(source.NEW_GUARDS)
  with self.assertRaises(ValueError):source.check_owner_diagnostics((self.out/'actual-Make-diagnostics.txt').read_text()+'extra warning\n')
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertEqual([4*i for i,w in enumerate(ws)if w==jal],[0x54E1C]);self.assertNotIn(source.ENTRY,ws)
  image=self.values['conker/build/conker.us.elf']
  for entry,rom,n in(*oracle.HELPERS,(0x800A1B70,0x246630,1)):
   at=source.elf_slot_offset(image,entry,n*4);self.assertEqual(image[at:at+n*4],self.rom[rom:rom+n*4])
  self.assertIn(b's32 func_150265CC() {\n    return 0;\n}',self.values['conker/src/game/generated_50D80.c'])
  # The original reader uses signed loads for both disabled callback fields.
  for offset,wanted in((0x162438,0x82020048),(0x1626E4,0x82020051)):
   self.assertEqual(struct.unpack_from('>I',self.rom,offset)[0],wanted)
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(body_words=51,frame=88,bindings=3,guards=0,neighbors=23,compact_functions=24,Make_commands=3,inherited_warnings=10,new_warnings=0,caller_words=10,caller_return_discarded=True,constructor_and_copy_current_exact=True)
 def test_02_guest_descriptor_lifetime_and_padding(self):
  cases=[Case(identity=i,seed=i)for i in range(256)]
  cases += [Case(lifetime=life,priority=selector,arg3=ctx,outcome=result,mutation=mutation,phase=phase)for life,selector,ctx,result,mutation,phase in itertools.product((0,1,0x7FFF,0x8000,0xFFFF,0x80000000,0xFFFFFFFF),(0,0xFFFFFFFF),(0,0x80000000),range(2),(0,3),(0,8))]
  cases += [Case(value=w)for w in(0,0x80000000,1,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345)]
  cases += [Case(owner=owner,lifetime=life)for owner,life in itertools.product((0,0x80000000,0xFFFFFFFF,oracle.STACK+6-0x3B),(0,0x7FFF,0x8000,0xFFFF))]
  visited=set()
  for c in cases:visited.update(self.compare(c).visits)
  self.assertEqual(len(visited),51);self.receipt['guest']=dict(cases=len(cases),covered_words=51,all_60_packet_bytes=True,padding_preserved=True,raw_float_bits=True,signed_halfword_boundaries=True,sparse_and_home_aliases_guest_only=True)
 def test_03_original_constructor_copy_and_caller(self):
  visited=set();count=0
  for life,outcome,mutation,phase in itertools.product((0,1,0x7FFF,0x8000,0xFFFF),range(2),range(8),(0,8)):
   visited.update(self.compare(Case(lifetime=life,outcome=outcome,mutation=mutation,phase=phase),connected=True).visits);count+=1
  coverage=[sum(pc in visited for pc in range(entry,entry+4*n,4))for entry,_,n in oracle.HELPERS];self.assertEqual(coverage,[39,11]);parent_visits=set();callers=0
  for owner,gate,life,outcome,phase in itertools.product((0,oracle.OWNER),(-1,0,1),(0,0x7FFF,0x8000,0xFFFF),range(2),(0,8)):
   c=Case(owner=owner,gate=gate,lifetime=life,outcome=outcome,phase=phase);pair=[]
   for words in(self.truth,self.words):
    m,wanted,end=oracle.caller_machine(self.rom,words,c)
    with self.assertRaises(oracle.WindowBoundary):m.run()
    self.assertEqual((public(m.memory),m.calls,m.r[2],m.packets,m.copies),(public(wanted[0]),*wanted[1:]));pair.append(m);parent_visits.update(m.visits)
   self.assertEqual(oracle.state(pair[0]),oracle.state(pair[1]));callers+=1
  self.assertEqual(sum(pc in parent_visits for pc in range(oracle.WINDOW,oracle.WINDOW+40,4)),10)
  self.receipt['integration']=dict(connected_cases=count,helper_words=50,helper_coverage=coverage,caller_cases=callers,caller_words=10,null_and_nonpositive_gate=True,constructor_failure_propagated=True,caller_discards_pointer=True,bounded_service='func_15167A68',complete_parent_or_gameplay_claimed=False)
 def test_04_native32_SDK_and_semantic_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());logs={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);built=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=built.stderr)
  self.receipt['native']=dict(optimizations=logs,cases_per_profile=256*7*2*2,controls=len(controls()),SDK=True,pointers32=True,trapping_UBSan=True,defined_backing_and_canaries=True,indeterminate_padding_not_asserted=True)
 def test_05_direct_connected_and_caller_fault_prefixes(self):
  count=delay=0
  for c,connected,parent in((Case(mutation=3),False,False),(Case(outcome=0),True,False),(Case(mutation=7),True,False),(Case(),True,True),(Case(owner=0),True,True),(Case(gate=0),True,True)):
   def machine(words):return oracle.caller_machine(self.rom,words,c,connected)[0]if parent else LifetimeOracle(words,fixture(c),c,connected=oracle.helper_code(self.rom)if connected else None)
   full=machine(self.truth)
   if parent:
    with self.assertRaises(oracle.WindowBoundary):full.run()
   else:full.run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=machine(words);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(oracle.state(pair[0]),oracle.state(pair[1]));self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(pair[1].current_pc,pair[1].delay_of,cut));count+=1;delay+=pair[0].delay_of is not None
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
   defs=oracle.symbols()if j==0 else dict(D_800A1B70=(0x80417FFC,0x80528004)[j-1],func_15134DAC=entry+0x10000)
   paths=(self.out/'original-func_150F6890.o',self.out/'make-shadow/src/game/generated_1228D0.c.o',self.out/'qualified-padded.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),defs)for k,p in enumerate(paths)]
   self.assertTrue(all(x==images[0]for x in images))
   for life,outcome,mutation,phase in itertools.product((0,0x8000,0xFFFF),range(2),(0,3),(0,8)):self.compare(Case(lifetime=life,outcome=outcome,mutation=mutation,phase=phase),images,entry,defs);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,original_Make_padded_raw_equal=True,guards=0,signed_low_address_carry=True)
 def test_07_compiled_semantic_negatives(self):
  evidence={}
  def view(m,calls,value,packets,copies):return public(m),[(t,a[1:])for t,a in calls],value,[bytes(b for i,b in enumerate(p)if i not in oracle.PADDING)for p in packets]
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name)
   for c in(Case(identity=byte,outcome=outcome)for byte,outcome in itertools.product((0,128,255),range(2))):
    initial=fixture(c);m=LifetimeOracle(words,initial,c).run();wanted=reference(initial,c)
    if view(m.memory,m.calls,m.r[2],m.packets,m.copies)!=view(*wanted):evidence[name]=dict(identity=c.identity,outcome=c.outcome);break
   self.assertIn(name,evidence)
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,private_addresses_and_padding_excluded=True)
 def test_08_strict_whole_image_and_inputs(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+204];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,204);named={n:(p,f,loc)for p,n,f,loc in source.symbol_rows(before)}
  positions=[20,at-4,at+204,source.elf_slot_offset(before,oracle.WINDOW,40),source.elf_slot_offset(before,0x800A1B70,4)]
  positions+=list(range(at,at+204))+list(range(named[source.FUNCTION][0],named[source.FUNCTION][0]+16))
  for n in('D_800A1B70','D_800A1620','D_800A5920','D_80099478','D_80099828','D_8009EE78'):positions.extend((named[n][0]+4,named[n][2]))
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),185)
  with self.assertRaises(ValueError):source.guard_manifest(v['conker/retail_word_patches.us.csv']+b'\n')
  self.receipt['image']=dict(changed_bytes=185,code_bytes=156,extent_bytes=1,metadata_bytes=28,closed_symbol_bucket_rotations=2,exclusions=0,corruptions=len(positions)+1,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v))
