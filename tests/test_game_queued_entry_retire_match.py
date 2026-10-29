"""Qualify queued retirement against retail, original helpers, ABI and full image."""
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_queued_entry_retire_match as source
from tools.tests import game_queued_entry_retire_oracle as oracle
from tools.tests.game_queued_entry_retire_oracle import Case,RetireOracle,fixture,reference,public
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 return dict(inclusive_timer=b.replace('queue + 0x22) < 0','queue + 0x22) <= 0'),wrong_flag=b.replace('queue[0x24] & 1','queue[0x24] & 2'),skip_callback=b.replace('if (entry[0x1C] != 0)','if (0)'),signed_selector=b.replace('D_8008D5C0[entry[0x1C]]','D_8008D5C0[*(s8 *)(entry + 0x1C)]'),cached_link=b.replace('*(u8 **)(queue + 0x14) = *(u8 **)(entry + 0x18);','*(u8 **)(queue + 0x14) = next;'),skip_release=b.replace('func_1516972C((struct102 *)entry);',';'),increment_count=b.replace(' -= 1',' += 1'),cached_count=b.replace('    u8 *entry;','    u8 *entry;\n    u32 count = *(u32 *)(queue + 0x1C);').replace('*(u32 *)(queue + 0x1C) -= 1;','*(u32 *)(queue + 0x1C) = count - 1;'),wrong_argument=b.replace('(*(u8 **)(entry + 0x10));','(entry);'))

def native_harness(body):
 return source.HEADERS+r"""
typedef char Pointer32[sizeof(void*)==4?1:-1];
static union {u32 align[768];u8 b[3072];} storage;
static u8 expected[3072];
static void (*backing[512])(u8*);
#define D_8008D5C0 (backing+256)
s32 D_800BE9E4;
static u32 mode,layout,selector,events[8],expectedEvents[8],eventCount;
static u8 *queue,*entry,*next,*argument;
static void callback(u8*p,u32 tag){events[eventCount++]=tag;events[eventCount++]=(u32)p;
 if(mode&1){*(u32*)(queue+0x1C)=7;*(u8**)(queue+0x14)=storage.b+2560;}
 if(mode&2){*(u8**)(entry+0x10)=storage.b+2048;*(u8**)(entry+0x18)=storage.b+2560;}}
static void positive(u8*p){callback(p,1);}static void second(u8*p){callback(p,2);}static void negative(u8*p){callback(p,3);}
void func_1516972C(struct102*p){events[eventCount++]=4;events[eventCount++]=(u32)p;if(mode&4)*(u32*)(queue+0x1C)=0;}
static void setup(u32 n){u32 i;static const u32 counts[]={0,1,3,0x80000000u,0xFFFFFFFFu};static const s16 timers[]={-32768,-1,0,1,32767};static const u32 ticks[]={0,1,0xFFFFFFFFu,0x7FFFFFFFu,0x80000000u};
 for(i=0;i<sizeof(storage);i++)storage.b[i]=(u8)(i*29+n);queue=storage.b+16;entry=storage.b+512;argument=storage.b+1536;layout=n%5;
 next=layout==0?storage.b+1024:layout==1?entry+4:layout==2?queue:layout==3?0:entry;
 mode=(n/5)%8;selector=(n/40)%256;
 *(u8**)(queue+0x10)=storage.b+2560;*(u8**)(queue+0x14)=entry;*(u32*)(queue+0x1C)=counts[(n/10240)%5];*(s16*)(queue+0x22)=timers[(n/51200)%5];queue[0x24]=(u8)(n/256000);
 *(u8**)(entry+0x10)=argument;*(u8**)(entry+0x18)=next;entry[0x1C]=(u8)selector;D_800BE9E4=(s32)ticks[(n/1024000)%5];eventCount=0;for(i=0;i<8;i++)events[i]=0;
}
static void model(u8*q){u8*e,*n;u32 count=*(u32*)(q+28);s32 timer;if(!count)return;timer=*(s16*)(q+34);
 if(timer>=0){if(q[36]&1)*(s16*)(q+34)=(s16)((u32)timer-(u32)D_800BE9E4);return;}
 e=*(u8**)(q+20);n=*(u8**)(e+24);
 if(!n){*(u32*)(q+16)=0;*(u32*)(q+20)=0;}else{*(u32*)(n+20)=0;*(u8**)(q+20)=*(u8**)(e+24);}
 if(e[28]){u8*a=*(u8**)(e+16);callback(a,e[28]==2?2:1);}func_1516972C((struct102*)e);*(u32*)(q+28)=*(u32*)(q+28)-1u;
}
"""+body+r"""
static void(*volatile selected)(u8*)=func_1518AA10;
static int trial(u32 n){u32 i,count;setup(n);model(queue);for(i=0;i<sizeof(storage);i++)expected[i]=storage.b[i];for(i=0;i<8;i++)expectedEvents[i]=events[i];count=eventCount;setup(n);selected(queue);
 if(eventCount!=count)return 1;for(i=0;i<8;i++)if(events[i]!=expectedEvents[i])return 2;for(i=0;i<sizeof(storage);i++)if(storage.b[i]!=expected[i])return 3;return 0;}
static int run(void){u32 i,n;for(i=0;i<512;i++)backing[i]=i<256?negative:i==258?second:positive;
 /* All selector encodings and alias/effect combinations, with a live count. */
 for(n=10240;n<20480;n++)if(trial(n))return 10;
 /* Orthogonal boundary timers, count words, flag bytes and clocks. */
 for(i=0;i<2048;i++){n=(i*7919u)%5120000u;if(trial(n))return 11;}return 0;}
"""+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
class QueuedEntryRetireTests(unittest.TestCase):
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
  for words in images or(self.truth,self.words):
   m=RetireOracle(words,initial,c,entry=entry,s=s,connected=code,real=connected).run();self.assertEqual((public(m.memory),m.calls),(public(wanted[0]),wanted[1]),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(oracle.fullstate(pair[0]),oracle.fullstate(m))
  return pair[0]
 def test_01_owner_Make_and_callback_ABI(self):
  self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.linked(self.out/'selected.o',source.ENTRY,'raw'));self.assertEqual(self.truth[0],0x27BDFFE0)
  self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/'original-func_1518AA10.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),4)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),3)
  self.assertEqual(source.same_functions(self.out/'before-padded.o',self.out/'qualified-padded.o',(source.FUNCTION,)),3)
  self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  self.assertEqual((self.out/'make-shadow/src/game/generated_1B7EC0.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==0x0C000000|(source.ENTRY>>2&0x3FFFFFF)],[]);self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x23054C]);self.assertEqual(oracle.REGISTRY+29*52,0x8008BA8C)
  self.assertEqual(struct.unpack_from('>4I',self.rom,0x232080),(0,oracle.CB1,oracle.CB2,0))
  self.assertIn('s32 func_151670C0() {\n    return 0;\n}',self.values['conker/src/game_1944C0.c'].decode())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=51,frame=32,bindings=5,guards=0,neighbors=3,Make_commands=3,diagnostics=0,signature='void (u8 *queue)',registry_category=29,descriptor_stride=52,descriptor_offset=0,only_two_nonnull_retail_optional_callbacks=True,current_parent_stub_unchanged=True)
 def test_02_guest_order_aliases_signs_and_saved_homes(self):
  visited=set();count=0
  for c in oracle.corpus():visited.update(self.compare(c).visits);count+=1
  self.assertEqual(visited,set(range(source.ENTRY,source.ENTRY+204,4))-{source.ENTRY+0x44,source.ENTRY+0x9C})
  for c in(Case(count=0),Case(timer=0,flags=0)):
   m=self.compare(c);self.assertFalse(m.calls);self.assertFalse(any(e[0]=='R'and e[1]in(oracle.ENTRY_NODE+0x18,oracle.symbols()['D_800BE9E4'])for e in m.trace))
  self.receipt['guest']=dict(cases=count,reachable_words=49,unreachable_original_words_retained=[68,156],all256_unsigned_selectors=True,synthetic_high_selector_and_home_probes_guest_only=True,six_alias_layouts=True,full_state_and_access_trace=True,entry_SP18_queue_home_SP20=True,volatile_registers_and_outgoing_homes_clobbered=True)
 def test_03_original_callbacks_release_and_dispatch_window(self):
  before=self.values['conker/build/conker.us.elf'];visited=set();count=callers=0
  for e,n in oracle.HELPERS:
   at=source.elf_slot_offset(before,e,n*4);pos=e-0x14FD2B50;self.assertEqual(before[at:at+n*4],self.rom[pos:pos+n*4])
  for selector,category,cleanup,scan_count,layout in itertools.product((0,1,2),(0,1,30),(0,1),(-1,0,2),(0,5)):
   c=Case(selector=selector,category=category,cleanup=cleanup,scan_count=scan_count,layout=layout);visited.update(self.compare(c,connected=True).visits);count+=1
  coverage=[sum(pc in visited for pc in range(e,e+n*4,4))for e,n in oracle.HELPERS];self.assertEqual(coverage,[18,7,28,20,8])
  for selector,timer,flags,cleanup,real in itertools.product((0,1,2),(-1,0,32767),(0,1),(0,1),(False,True)):
   c=Case(selector=selector,timer=timer,flags=flags,cleanup=cleanup);pair=[]
   for words in(self.truth,self.words):
    m,wanted=oracle.caller_machine(self.rom,words,c,real)
    with self.assertRaises(oracle.WindowBoundary):m.run()
    self.assertEqual((public(m.memory),m.calls,m.r[16]),(public(wanted[0]),*wanted[1:]));pair.append(m)
   self.assertEqual(oracle.fullstate(pair[0]),oracle.fullstate(pair[1]));callers+=1
  self.receipt['integration']=dict(connected_cases=count,caller_cases=callers,helper_words=81,helper_coverage=coverage,linked_helpers_byte_exact=True,original_caller_words=12,explicit_A0_and_ignored_result=True,scan_empty_and_replacement_paths=True,bounded_services=['func_15168B10','func_1513F6C0','synthetic_cleanup'],full_parent_or_gameplay=False)
 def test_04_native32_SDK_and_effective_controls(self):
  def run(body,label,opt):
   p=self.fresh/(label+opt+'.c');exe=p.with_suffix('.elf');p.write_text(native_harness(body));build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr);self.assertFalse(build.stderr);return subprocess.run([str(exe)],capture_output=True,timeout=45).returncode
  logs={}
  for opt in('-O0','-O2','-O3'):logs[opt]=run(source.SELECTED,'native',opt);self.assertEqual(logs[opt],0,opt)
  for name,body in controls().items():self.assertIn(run(body,'negative-'+name,'-O2'),(10,11),name)
  self.receipt['native']=dict(cases_per_profile=12288,profiles=logs,controls=len(controls()),SDK=True,pointers32=True,trapping_UBSan=True,valid_aligned_backing_and_all_bytes_checked=True,synthetic_512_cell_callback_table=True,strict_aliasing_disabled_for_byte_owner_access=True,guest_home_mutations_not_native_claim=True)
 def test_05_direct_connected_and_caller_fault_prefixes(self):
  count=delay=0
  for c,connected,parent in((Case(mode=63),False,False),(Case(layout=1),False,False),(Case(count=0),False,False),(Case(timer=32767),False,False),(Case(selector=1),True,False),(Case(selector=2,cleanup=1),True,False),(Case(),True,True)):
   def machine(words):return oracle.caller_machine(self.rom,words,c,connected)[0]if parent else RetireOracle(words,fixture(c),c,connected=oracle.helper_code(self.rom)if connected else None,real=connected)
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
    self.assertEqual(oracle.fullstate(pair[0]),oracle.fullstate(pair[1]));self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(pair[1].current_pc,pair[1].delay_of,cut));count+=1;delay+=pair[0].delay_of is not None
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
   defs=oracle.symbols()if not j else dict(D_8008D5C0=(0x80417FFC,0x80528004)[j-1],D_800BE9E4=(0x80428004,0x80537FFC)[j-1],func_1516972C=entry+0x10000)
   paths=(self.out/'original-func_1518AA10.o',self.out/'make-shadow/src/game/generated_1B7EC0.c.o',self.out/'qualified-padded.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),defs)for k,p in enumerate(paths)];self.assertTrue(all(x==images[0]for x in images))
   for layout,timer,selector,mode in itertools.product((0,1),(-1,0),(0,128),(0,7)):self.compare(Case(layout=layout,timer=timer,selector=selector,mode=mode),images,entry,defs);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,original_Make_padded_raw_equal=True,guards=0,signed_low_address_carry=True)
 def test_07_compiled_semantic_negatives(self):
  evidence={}
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name)
   for c in(Case(timer=t,selector=s,mode=m,layout=l)for t,s,m,l in itertools.product((-1,0,1),(0,2,128),(0,1,4),(0,1))):
    initial=fixture(c);m=RetireOracle(words,initial,c).run();wanted=reference(initial,c)
    if(public(m.memory),m.calls)!=(public(wanted[0]),wanted[1]):evidence[name]=dict(timer=c.timer,selector=c.selector,mode=c.mode,layout=c.layout);break
   self.assertIn(name,evidence)
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,terminated_public_value_or_calls_failure=True)
 def test_08_strict_whole_image_and_inputs(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+204];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,204);named={n:(p,f,loc)for p,n,f,loc in source.symbol_rows(before)}
  positions=[20,at-4,at+204,source.elf_slot_offset(before,oracle.WINDOW,48),source.elf_slot_offset(before,0x8008D5C0,4)]+list(range(at,at+204))+list(range(named[source.FUNCTION][0],named[source.FUNCTION][0]+16))
  for n in('D_80099804','D_8009EE54','D_8008D5C0','D_80088820'):positions.extend((named[n][0]+4,named[n][2]))
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),182)
  with self.assertRaises(ValueError):source.guard_manifest(v['conker/retail_word_patches.us.csv']+b'\n')
  self.receipt['image']=dict(changed_bytes=182,code_bytes=157,extent_bytes=1,metadata_bytes=24,closed_symbol_bucket_swaps=2,exclusions=0,corruptions=len(positions)+1,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v))
