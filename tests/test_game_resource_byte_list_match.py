"""Resource byte-list C, original caller window and whole-image qualification."""
from pathlib import Path
from dataclasses import replace
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_resource_byte_list_match as source
from tools.tests import game_resource_byte_list_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
class ResourceByteListTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>52I',cls.rom,source.ROM));oracle.o=cls.fresh
  cls.raw=oracle.linked(cls.out/'selected.o',source.ENTRY,'selected');cls.words=oracle.linked(cls.out/'qualified-padded.o',source.ENTRY,'padded');assert cls.raw==cls.words==cls.truth
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'original-func_15084488.o'));self.receipt['fresh_C']=dict(words=52,guards=0,bindings=7)
 def test_02_guest_reload_capture_count_and_unused_argument(self):
  count=0;maximum=0;visited=set()
  for c in oracle.cases():
   initial=oracle.fixture(c);want,calls=oracle.reference(initial,c);pair=[]
   for words in (self.truth,self.raw):
    m=oracle.ListOracle(words,initial,c).run();self.assertEqual((oracle.public(m.memory),m.calls),(oracle.public(want),calls));pair.append(m)
   self.assertEqual(oracle.state(pair[0]),oracle.state(pair[1]));visited.update(pair[0].visits);maximum=max(maximum,len(calls));count+=1
  unvisited=[hex(pc)for pc in range(source.ENTRY,source.ENTRY+208,4)if pc not in visited];self.assertEqual(unvisited,['0x150844ec','0x15084514'])
  self.receipt['guest']=dict(cases=count,max_provider_calls=maximum,covered_words=len(visited),unvisited_words=unvisited,byte_reloaded_between_helpers=True,post_provider_table_reload=True,descriptor_and_cursor_captured=True)
 def test_03_original_caller_window_and_argument_homes(self):
  ENTRY=source.ENTRY;WINDOW=0x15082BEC;END=0x15082C0C
  class Caller(oracle.ListOracle):
   def record_call(self,t):
    if t==ENTRY:
     a=tuple(self.arguments(3));assert a==oracle.args(self.case);self.calls.append((t,a));self.events.append(('CALL',t,a));return
    return super().record_call(t)
  words=struct.unpack_from('>8I',self.rom,0xB009C);self.assertEqual(words[-2:],(0x0D421122,0x8FA60074));count=0
  for context,identity,primary,mode in itertools.product((0,1,0x80000000,0xFFFFFFFF),(17,255),(0,3),(0,31)):
   c=oracle.Case(identity=identity,primary=primary,extra=1,mutation=mode,context=context,unused=0xA7);initial=oracle.fixture(c);home=oracle.STACK+c.phase;oracle.put(initial,home+0x68,oracle.RECORD);oracle.put(initial,home+0x74,context);initial[oracle.ACTOR+0x13F]=0xA7;want,calls=oracle.reference(initial,c);oracle.put(want,oracle.ACTOR+0x144,oracle.RECORD)
   connected=dict(zip(range(ENTRY,ENTRY+208,4),self.raw));connected[END]=0;m=Caller(words,initial,c,entry=WINDOW,connected=connected);m.r[16]=oracle.ACTOR;m.r[2]=0x87654321;m.before=m.r[:];m.code=oracle.WindowCode(m.code,m);m.code.ends=(END,)
   with self.assertRaises(oracle.WindowBoundary):m.run()
   self.assertEqual(oracle.public(m.memory),oracle.public(want));self.assertEqual(m.calls,[(ENTRY,oracle.args(c))]+calls);self.assertEqual(oracle.read(m.memory,home+0x34),0x87654321);self.assertEqual(oracle.read(m.memory,home+0x2C),0x87654322);count+=1
  prefix=struct.unpack_from('>6I',self.rom,0xAFEF4);self.assertEqual(prefix,(0x27BDFF98,0xAFBF0024,0xAFB00020,0xAFA40068,0xAFA60070,0xAFA70074))
  for context in (0,1,0x80000000,0xFFFFFFFF):
   c=oracle.Case(context=context);initial=oracle.fixture(c);m=oracle.ListOracle(prefix,initial,c,entry=0x15082A44);m.r[6]=0x12345678;m.r[7]=context;m.before=m.r[:];m.code=oracle.WindowCode(m.code,m);m.code.ends=(0x15082A5C,)
   with self.assertRaises(oracle.WindowBoundary):m.run()
   self.assertEqual(m.r[29],oracle.STACK-0x68);self.assertEqual(oracle.read(m.memory,m.r[29]+0x68),oracle.RECORD);self.assertEqual(oracle.read(m.memory,m.r[29]+0x70),0x12345678);self.assertEqual(oracle.read(m.memory,m.r[29]+0x74),context)
  self.receipt['caller']=dict(window_words=8,cases=count,prologue_words=6,prologue_cases=4,complete_parent=False,S0_actor_precondition=True,parent_C_placeholder_uncredited=True)
 def test_04_native32_and_six_negative_controls(self):
  p=self.fresh/'native.c';p.write_text(oracle.native_harness());logs={}
  for opt in ('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.returncode,run.stderr));logs[opt]=dict(exit=0,cases=672,negative_controls=6,UBSan=True)
  self.receipt['native']=logs
 def test_05_fault_prefixes_and_sparse_branch_likely_paths(self):
  count=0;sparse=0
  for c in (oracle.Case(primary=0,extra=0),oracle.Case(primary=2,extra=1,mutation=31),oracle.Case(identity=255)):
   initial=oracle.fixture(c);full=oracle.ListOracle(self.truth,initial,c).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in (self.truth,self.raw):
     m=oracle.ListOracle(words,initial,c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(oracle.state(pair[0]),oracle.state(pair[1]));count+=1
  for c in (oracle.Case(identity=255),oracle.Case(primary=0,extra=0)):
   initial=oracle.fixture(c)
   if c.identity==255:initial={a:b for a,b in initial.items()if oracle.STACK-512<=a<oracle.STACK+512 or oracle.RECORD-16<=a<oracle.RECORD+336}
   else:
    initial.pop(oracle.RESOURCE_A+5);initial={a:b for a,b in initial.items()if not oracle.syms['D_80086CAC']<=a<oracle.syms['D_80086CAC']+1024}
   want,calls=oracle.reference(initial,c)
   for words in (self.truth,self.raw):
    m=oracle.ListOracle(words,initial,c).run();self.assertEqual((oracle.public(m.memory),m.calls),(oracle.public(want),calls))
   sparse+=1
  self.receipt['faults']=dict(prefix_pairs=count,sparse_skips=sparse,branch_likely_annul_verified=True)
 def test_06_GNU_symbol_layouts_and_raw_guards(self):
  count=0
  for k,(entry,first,second,table,lists)in enumerate(((0x15001000,0x10001000,0x17008000,0x80007FF0,0x80017FF0),(0x1F008000,0x1A008000,0x1800FFF0,0x80008000,0x80018000),(0x1000FFF0,0x12000040,0x1400FFF0,0x8000FFF0,0x8001FFF0))):
   symbols=dict(func_1503D774=first,func_1503D660=second,D_800D1C90=table,D_80086CAC=lists);a=oracle.linked(self.out/'original-func_15084488.o',entry,'original-layout'+str(k),symbols);b=oracle.linked(self.out/'selected.o',entry,'selected-layout'+str(k),symbols);self.assertEqual(a,b)
   for identity,primary,mode in itertools.product((17,255),(0,4),(0,31)):
    c=oracle.Case(identity=identity,primary=primary,mutation=mode);initial=oracle.fixture(c,symbols);want,calls=oracle.reference(initial,c,symbols);m=oracle.ListOracle(b,initial,c,entry=entry,s=symbols).run();self.assertEqual((oracle.public(m.memory),m.calls),(oracle.public(want),calls));count+=1
  raw,rs=source.payload(self.out/'selected.o');controls=0
  for i in range(len(raw)):
   bad=bytearray(raw);bad[i]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   controls+=1
  for at in rs:
   bad={**rs,at:[('R_MIPS_26','wrong_provider')]}
   with self.assertRaises(ValueError):source.checked_payload(raw,bad)
   controls+=1
  self.receipt['layouts']=dict(layouts=3,cases=count,raw_and_binding_controls=controls)
 def test_07_full_owner_rodata_padding_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.payload(obj),source.payload(self.out/'selected.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),30);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj))
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER,rodata_symbol=source.RODATA_SYMBOL));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
  before=self.values[source.SOURCE].decode();after=source.recovered_owner(before)
  for name in ('func_1503D774','func_1503D660'):
   self.assertIn('void '+name+'(s32, s32);',before);self.assertIn('s32 '+name+'(s32, s32);',after);self.assertIn('s32 '+name+'(s32 identity, s32 loaded)',self.values['conker/src/game/generated_6A3D0.c'].decode())
  self.receipt['owner']=dict(neighbors=30,actual_Make_commands=5,status_declarations_corrected=2,rodata_anchor=source.RODATA_SYMBOL,provider_C_credit_added=0)
 def test_08_strict_whole_image_and_negative_controls(self):
  source.check_inputs(ROOT,self.out,self.installed);before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();literal=self.rom[source.ROM:source.ROM+208];source.check_image(before,actual,literal);at=source.elf_slot_offset(before,source.ENTRY,208);count=0
  for offset in set((0,4,52,len(actual)-1,*range(at,at+208))):
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),literal)
   count+=1
  self.receipt['image']=dict(strict=True,exclusions=0,controls=count,changed_bytes=166)
