"""Owner phase-pair C: exact bytes, callback ABI, math and full-image gates."""
from dataclasses import replace
from pathlib import Path
import itertools,math,json,os,struct,subprocess,unittest
from tools.experiments import game_owner_phase_pair_match as source
from tools.tests import game_owner_phase_pair_oracle as oracle
from tools.tests.game_owner_phase_pair_oracle import Case,PhaseOracle,fixture,reference,public,bits,floating,put,read
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
def controls():
 b=source.SELECTED
 return dict(rate=b.replace('D_800A2474 * *delta','D_800A2470 * *delta'),skip_wrap=b.replace('state[3] = func_15144B68(state[3]);','state[3] = state[3];'),phase=b.replace('sinf(state[3])','sinf(state[2])'),amplitude=b.replace('sinf(state[3]) * D_800A247C','sinf(state[3]) * D_800A2478'),skip_timer=b.replace('    func_15108B80(owner);',''),skip_value=b.replace('    func_15108BC0(owner);',''),result=b.replace('return 1;','return 0;'),cached_clock=b.replace('    f32 *delta = &D_800BE9A4;','    f32 cached = D_800BE9A4;\n    f32 *delta = &cached;'))
def native_harness(body,cases):
 rows=[]
 for c in cases:
  initial=fixture(c);expected,calls,_=reference(initial,c);q=oracle.state(initial,oracle.OWNER)
  statearrays=[','.join('0x%Xu'%read(m,q+4*i)for i in range(8))for m in(initial,expected)]
  arrays=[','.join('0x%Xu'%v for v in values)for values in(c.scales,c.results,[v for _,v in calls[:4]],[read(expected,oracle.symbols()[n])for n in('D_800A2470','D_800A2474','D_800A2478','D_800A247C')])]
  rows.append('{{%s},{%s},{%s},{%s},{%s},{%s},0x%Xu,0x%Xu,%d,%d}'%(*statearrays,*arrays,c.clock,read(expected,oracle.OWNER+0x50),c.offset,c.mode))
 return source.HEADERS+r"""
typedef char Pointer32[sizeof(void*)==4?1:-1];
typedef struct {u32 initial[8],expected[8],scales[4],results[4],args[4],afterScales[4],clock,afterOffset;s32 offset,mode;} Item;
static const Item cases[]={"""+',\n'.join(rows)+r"""};
static union {u8 bytes[0x820];u32 words[0x208];f32 floats[0x208];} storage;
static const Item *item;static u8 *owner;static f32 *saved;static u32 ordinal,error;
f32 D_800BE9A4,D_800A2470,D_800A2474,D_800A2478,D_800A247C;
static f32 fp(u32 v){union{u32 w;f32 f;}x;x.w=v;return x.f;}
static u32 word(f32 v){union{u32 w;f32 f;}x;x.f=v;return x.w;}
static f32 helper(f32 value,u32 sine){u32 n=ordinal++;
 if(n>=4){error=1;return 0;}if(word(value)!=item->args[n]||sine!=(n>=2))error=1;
 if(n==0&&(item->mode&1)){saved[3]=2;*(s32*)(owner+0x50)=0x400;D_800A2478=3;}
 if(n==1&&(item->mode&2)){saved[2]=-.75f;D_800A247C=-3;}
 if(n==2&&(item->mode&4)){saved[3]=3.25f;D_800A2478=4;}
 if(n==3&&(item->mode&8))D_800A247C=.5f;
 return fp(item->results[n]);}
__attribute__((noinline,noclone)) f32 func_15144B68(f32 x){return helper(x,0);}
__attribute__((noinline,noclone)) f32 sinf(f32 x){return helper(x,1);}
void func_15108B80(u8*p){if(ordinal++!=4||p!=owner)error=1;p[0x30]=0x85;}
void func_15108BC0(u8*p){if(ordinal++!=5||p!=owner)error=1;p[0x31]=0x86;}
"""+body+r"""
static s32(*volatile callback)(u8*)=func_15108AB4;
static int run(void){u32 n,i;u8*p;u32 start;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  item=&cases[n];ordinal=error=0;for(i=0;i<sizeof(storage);i++)storage.bytes[i]=0xA5;
  owner=storage.bytes+16;*(s32*)(owner+0x50)=item->offset;saved=(f32*)(owner+item->offset+0xF8);start=(u8*)saved-storage.bytes;
  for(i=0;i<8;i++)((u32*)saved)[i]=item->initial[i];
  D_800BE9A4=fp(item->clock);D_800A2470=fp(item->scales[0]);D_800A2474=fp(item->scales[1]);D_800A2478=fp(item->scales[2]);D_800A247C=fp(item->scales[3]);
  if(callback(owner)!=1||error||ordinal!=6)return 1;
  for(i=0;i<8;i++)if(((u32*)saved)[i]!=item->expected[i])return 2;
  if(*(u32*)(owner+0x50)!=item->afterOffset||owner[0x30]!=0x85||owner[0x31]!=0x86)return 3;
  if(word(D_800BE9A4)!=item->clock||word(D_800A2470)!=item->afterScales[0]||word(D_800A2474)!=item->afterScales[1]||word(D_800A2478)!=item->afterScales[2]||word(D_800A247C)!=item->afterScales[3])return 4;
  p=storage.bytes;for(i=0;i<sizeof(storage);i++)if(!(i>=start&&i<start+32)&&!(i>=0x60&&i<0x64)&&i!=0x40&&i!=0x41&&p[i]!=0xA5)return 5;
 }return 0;}
"""+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
class OwnerPhasePairTests(unittest.TestCase):
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
  initial=fixture(c,s);wanted=reference(initial,c,s,real=connected);pair=[];code=oracle.helper_code(self.rom)if connected else None
  for words in images or(self.truth,self.words,self.raw):
   m=PhaseOracle(words,initial,c,entry=entry,s=s,connected=code,real=connected).run();self.assertEqual((public(m.memory),m.calls,m.r[2]),(public(wanted[0]),wanted[1],1),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(oracle.fullstate(pair[0]),oracle.fullstate(m))
  return pair[0]
 def test_01_owner_actual_Make_and_caller_ABI(self):
  self.assertEqual(self.truth,self.words);self.assertEqual([i for i,(a,b)in enumerate(zip(self.truth,self.raw))if a!=b],[11]);self.assertEqual(self.raw[0],0x27BDFFE0)
  self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/'original-func_15108AB4.o'))
  for label in('before','after'):
   for kind,count in(('owner',11),('caller',13)):
    obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-'+kind+'.c')).read_text(),'fresh-'+label+'-'+kind);self.assertEqual(source.same_functions(obj,self.out/(label+'-'+kind+'.o')),count)
    if kind=='owner':self.assertEqual(source.check_owner_diagnostics(diag),0)
    else:self.assertEqual(diag.count('cfe: Warning'),4)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),10)
  self.assertEqual(source.same_functions(self.out/'before-padded.o',self.out/'qualified-padded.o',(source.FUNCTION,)),10)
  self.assertEqual(source.same_functions(self.out/'before-caller.o',self.out/'after-caller.o'),13)
  for kind in('owner','caller'):self.assertEqual(source.normalized_pools(self.out/('before-'+kind+'.o')),source.normalized_pools(self.out/('after-'+kind+'.o')))
  self.assertEqual((self.out/'make-shadow/src/game_168A90.c.o').read_bytes(),self.values[source.CALLER_OBJECT]);self.assertEqual({k:len(v)for k,v in json.loads((self.out/'Make-commands.json').read_text()).items()},{'owner':3,'caller':3})
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==0x0C000000|(source.ENTRY>>2&0x3FFFFFF)],[]);self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22E6D8])
  image=self.values['conker/build/conker.us.elf']
  for entry,pos,n in(*oracle.HELPERS,(source.CALLER,0x168C48,41)):
   at=source.elf_slot_offset(image,entry,n*4);self.assertEqual(image[at:at+n*4],self.rom[pos:pos+n*4])
  for at,value in {**oracle.trig.GLOBALS,oracle.BOUND:0x40C90FDB,**dict(zip(range(0x800A2470,0x800A2480,4),Case().scales))}.items():self.assertEqual(struct.unpack_from('>I',image,source.elf_slot_offset(image,at,4))[0],value)
  self.assertEqual(source.recovered_caller(self.values[source.CALLER_SOURCE].decode()).encode(),(self.out/'proposed-caller.c').read_bytes())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=51,frame=32,bindings=16,guards=1,neighbors=10,caller_compact_functions_unchanged=13,caller_object_unchanged=True,Make_commands=6,new_diagnostics=0,caller_warnings_preserved=4,original_direct_calls=0,table_slot=0,signature='s32 (u8 *owner)',linked_helpers_and_caller_exact=True)
 def test_02_guest_order_aliases_and_owner_reload(self):
  visited=set();count=0
  for c in oracle.corpus():visited.update(self.compare(c).visits);count+=1
  self.assertTrue(set(range(source.ENTRY,source.ENTRY+204,4))<=visited)
  self.receipt['guest']=dict(cases=count,all_target_words=51,three_bodies=True,full_state_and_access_trace=True,saved_S0_and_RA=True,clock_aliases=4,volatile_GPR_FPR_HI_LO_clobbered=True,home_mutations_guest_only=True,FCSR_hardware_parity=False)
 def test_03_original_helpers_and_complete_caller(self):
  visited=set();count=caller_count=0
  for angle,clock,index,timer,ticks,gate in itertools.product((0.,-0.,.00001,-.25,3.5,6.2831855,25.,-25.),(0.,1.),(999,2,-1),(0,3),(-1,1),(0,1)):
   c=Case(phases=(bits(angle),bits(-angle)),clock=bits(clock),index=index,timer=timer,ticks=ticks,gate=gate);visited.update(self.compare(c,connected=True).visits);count+=1
  coverage=[sum(pc in visited for pc in range(e,e+4*n,4))for e,_,n in oracle.HELPERS]
  self.assertEqual(coverage[1:],[24,16,30])
  for flags,lifetime,index,mode,real in itertools.product((0,1,128,255),(-32768,-1,0,1,32767),(-1,0),(0,15),(False,True)):
   c=Case(mode=0 if real else mode);pair=[]
   for words in(self.truth,self.words,self.raw):
    m,wanted=oracle.caller_machine(self.rom,words,c,flags,lifetime,index,real);m.run();self.assertEqual((public(m.memory),m.calls),wanted);pair.append(m)
   for m in pair[1:]:self.assertEqual(oracle.fullstate(pair[0]),oracle.fullstate(m))
   caller_count+=1
  self.receipt['integration']=dict(connected_cases=count,caller_cases=caller_count,original_caller_words=41,helper_words=174,helper_coverage=coverage,complete_original_helpers=True,explicit_owner_forwarding=True,lifetime_and_disabled_callback_paths=True,infinite_wrap_completion=False,FCSR_or_gameplay=False)
 def test_04_native32_SDK_and_effective_controls(self):
  cases=[Case(phases=(bits((i%17-8)*.25),bits((i%23-11)*.5)),clock=bits((0.,.125,-.25,1.)[i%4]),offset=(-128,0,256)[i%3],mode=i%16)for i in range(128)];logs={}
  def run(body,label,opt):
   path=self.fresh/(label+opt+'.c');exe=path.with_suffix('.elf');path.write_text(native_harness(body,cases));p=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(path),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);self.assertFalse(p.stderr);return subprocess.run([str(exe)],capture_output=True).returncode
  for opt in('-O0','-O2','-O3'):logs[opt]=run(source.SELECTED,'native',opt);self.assertEqual(logs[opt],0,opt)
  for name,body in controls().items():
   if name=='cached_clock':continue
   self.assertGreater(run(body,'negative-'+name,'-O2'),0,name)
  self.receipt['native']=dict(cases_per_optimization=len(cases),optimizations=logs,controls=7,SDK=True,pointers32=True,trapping_UBSan=True,valid_owner_backing=True,canaries_checked=True,strict_aliasing_disabled_for_byte_based_owner_access=True,scripted_math=True,guest_aliases_not_native_claim=True)
 def test_05_complete_guest_fault_prefixes(self):
  count=delay=caller_count=0
  for c,connected in((Case(),False),(Case(mode=63),False),(Case(alias=8),False),(Case(),True)):
   initial=fixture(c);code=oracle.helper_code(self.rom)if connected else None;full=PhaseOracle(self.truth,initial,c,connected=code,real=connected).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in(self.truth,self.words,self.raw):
     m=PhaseOracle(words,initial,c,connected=code,real=connected);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    for m in pair[1:]:self.assertEqual(oracle.fullstate(pair[0]),oracle.fullstate(m));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(m.current_pc,m.delay_of))
    count+=1;delay+=pair[0].delay_of is not None
  for flags,lifetime,index in((0,10,0),(1,0,0),(0,1,-1)):
   full,_=oracle.caller_machine(self.rom,self.truth,Case(),flags,lifetime,index);full.run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in(self.truth,self.words,self.raw):
     m,_=oracle.caller_machine(self.rom,words,Case(),flags,lifetime,index);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    for m in pair[1:]:self.assertEqual(oracle.fullstate(pair[0]),oracle.fullstate(m));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(m.current_pc,m.delay_of))
    caller_count+=1
  self.receipt['faults']=dict(direct_connected_prefixes=count,caller_prefixes=caller_count,delay_slot_cuts=delay,complete_state_PC_trace=True,portable_C_fault_claimed=False)
 def test_06_guard_rejections_and_GNU_rebases(self):
  raw,rs=source.payload(self.out/'selected.o');rejects=0
  for at in range(0,len(raw),4):
   b=bytearray(raw);b[at+3]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(b),rs)
   rejects+=1
  for at in rs:
   b=dict(rs);b[at]=[(rs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):source.checked_payload(raw,b)
   rejects+=1
  count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   s=oracle.symbols()
   if j:s={n:(entry+0x10000*(i+1)if n in('sinf','func_15144B68','func_15108B80','func_15108BC0')else(0x80417FFC if j==1 else 0x80528004)+i*0x10000)for i,(n,a)in enumerate(s.items())}
   images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate((self.out/'original-func_15108AB4.o',self.out/'make-shadow/src/game/generated_135D00.c.o',self.out/'selected.o'))];self.assertEqual(images[0],images[1])
   for mode,alias in itertools.product((0,15,16,32,63),(None,8)):
    self.compare(Case(mode=mode,alias=alias),images,entry,s);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,bindings=16,all_three_objects_linked=True,one_ADDU_operand_guard=True,no_insertions_omissions_or_relocation_changes=True)
 def test_07_compiled_semantic_controls(self):
  evidence={}
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name)
   for c in(Case(mode=mode,alias=alias)for mode,alias in itertools.product((0,1,15),(None,8))):
    initial=fixture(c);m=PhaseOracle(words,initial,c).run();wanted=reference(initial,c)
    if(public(m.memory),m.calls,m.r[2])!=(public(wanted[0]),wanted[1],1):evidence[name]=dict(mode=c.mode,alias=c.alias);break
   self.assertIn(name,evidence)
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,guest_only=['cached_clock'],private_stack_addresses_excluded=True)
 def test_08_strict_whole_image_and_inputs(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+204];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth)
  positions=set([20,source.elf_slot_offset(before,source.ENTRY+204,4),source.elf_slot_offset(before,source.CALLER,164),source.elf_slot_offset(before,oracle.TABLE,4),2917604,3176542]);positions.update(i for i,(a,b)in enumerate(zip(before,expected))if a!=b)
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(a!=b for a,b in zip(before,expected)),181)
  self.receipt['image']=dict(changed_bytes=181,code_bytes=166,extent_bytes=1,metadata_bytes=14,exclusions=0,corruptions=len(positions)+1,new_guards=1,inherited_guard_prefix_unchanged=True,protected_Game_bytes=189088,focused_inputs=len(v),caller_helpers_and_other_bodies_unchanged=True)
