"""Motion integration: ordered IEEE arithmetic, guards, ABI and complete image gates."""
from pathlib import Path
import csv,io,itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_kinematic_twin_match as source
from tools.tests import game_kinematic_twin_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ROOT=Path(__file__).resolve().parents[2]
class KinematicTwinTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);oracle.o=cls.fresh;cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>53I',cls.rom,source.ROM));cls.words=oracle.linked(cls.out/'qualified-padded.o','qualified');cls.raw=oracle.linked(cls.out/'selected.o','raw');assert cls.words==cls.truth
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def assemble(self,p):subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_150CBE88.o'));original=oracle.view(self.out/'original-func_150CBE88.o');self.assertEqual(oracle.view(obj),original)
  bad=source.SELECTED.replace('    {\n        f32 delta = acceleration * D_800BE9A4;\n\n        *(f32 *)(record + 0x48) = verticalVelocity + delta;\n    }','    *(f32 *)(record + 0x48) = verticalVelocity + acceleration * D_800BE9A4;');self.assertNotEqual(bad,source.SELECTED);control,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+bad,'rejected-operand');self.assertFalse(diag);self.assertNotEqual(oracle.view(control),original);self.receipt['fresh_C']=dict(words=53,frame=0,guards=33,bindings=2,ordered_symbolic_graph_equal=True,operand_negative_control=True)
 def test_02_guest_boundaries_mutations_and_payloads(self):
  count=0;visited=set()
  for dt,pattern,alias,phase in itertools.product((0,0x80000000,0x3F800000,0xBF800000,0x3EAAAAAB,0x42C80000,1,0x007FFFFF,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345),range(6),(-1,0x20,0x24,0x28,0x38,0x3C,0x40,0x48,0x5C),(0,8)):
   c=oracle.Case(dt,pattern,alias,phase);initial=oracle.fixture(c);want=oracle.reference(initial,c);pair=[]
   for words in (self.truth,self.words,self.raw):
    m=oracle.Oracle(words,initial,c).run();self.assertEqual((m.memory,m.r[2],m.calls),(want,1,[]));pair.append(m)
   self.assertEqual((pair[0].r,pair[0].f,pair[0].events,pair[0].trace),(pair[1].r,pair[1].f,pair[1].events,pair[1].trace));visited.update(pair[0].visits);count+=1
  self.assertEqual(len(visited),53);self.receipt['guest']=dict(cases=count,executions=count*3,covered_words=53,global_record_aliases=True,ordered_quiet_NaN_payloads=True,normalized_full_state_equivalence=True,hardware_FCSR_claimed=False)
 def test_03_original_dispatch_window_and_registration(self):
  self.assertEqual(struct.unpack_from('>I',self.rom,0x22E378)[0],source.ENTRY);window=list(struct.unpack_from('>13I',self.rom,0x15F6F4));count=0
  class Caller(oracle.Oracle):
   def __init__(self,words,memory,c,connected):oracle.FactoryOracle.__init__(self,words,memory,c,entry=0x15132244,s=dict(D_800BE9A4=oracle.TIME),connected=connected,arguments=(c.record,))
   def record_call(self,t):
    assert t==source.ENTRY;args=tuple(self.arguments(1));assert args==(self.case.record,);self.calls.append((t,args));self.events.append(('CALL',t,args))
  for dt,pattern,index,flag,phase in itertools.product((0,0x3F800000,0xBF800000,0x7FC12345),(0,3,5),(0,2),(0,1),(0,8)):
   c=oracle.Case(dt,pattern,-1,phase);initial=oracle.fixture(c);initial[c.record+0x71]=index;oracle.put(initial,0x800898B8,source.ENTRY);want=oracle.reference(initial,c)if index else dict(initial)
   if index:want[oracle.STACK+phase+0x23]=flag
   calls=[(source.ENTRY,(c.record,))]if index else[]
   for words in(self.truth,self.words,self.raw):
    connected=dict(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words));connected.update({0x15132278:0,0x1513227C:0});m=Caller(window,initial,c,connected);m.r[16]=c.record;m.r[5]=flag;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(0x15132278,0x1513227C)
    with self.assertRaises(WindowBoundary):m.run()
    self.assertEqual((m.memory,m.r[2],m.r[5],m.calls),(want,1 if index else 0,flag,calls))
   count+=1
  self.receipt['caller']=dict(words=13,cases=count,table='D_800898B0',index=2,index_zero_skip=True,earlier_gate_precondition=True,complete_parent_claimed=False)
 def test_04_native32_UBSan_and_six_controls(self):
  p=self.fresh/'native.c';p.write_text(oracle.native_harness(source.HEADERS+source.SELECTED));rows={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-ffp-contract=off',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.returncode,run.stderr));rows[opt]=dict(exit=0,cases=648,negative_controls=6,UBSan=True,native_NaN_payload_claimed=False)
  self.receipt['native']=rows
 def test_05_access_prefixes_and_sparse_skips(self):
  count=0
  for c in (oracle.Case(),oracle.Case(0xBF800000,0,0x38,0),oracle.Case(0x7FC12345,5,0x48,8)):
   initial=oracle.fixture(c);full=oracle.Oracle(self.truth,initial,c).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=oracle.Oracle(words,initial,c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual((pair[0].r,pair[0].f,pair[0].memory,pair[0].events,pair[0].trace),(pair[1].r,pair[1].f,pair[1].memory,pair[1].events,pair[1].trace));count+=1
  self.receipt['faults']=dict(prefix_pairs=count,raw_C_fault_equivalence_claimed=False)
 def test_06_rebases_and_effective_guard_controls(self):
  previous=(oracle.ENTRY,oracle.TIME);count=0
  try:
   for k,(entry,time)in enumerate(((0x15001000,0x80007FF0),(0x1F008000,0x80008000),(0x1000FFF0,0x8000FFF0))):
    oracle.ENTRY,oracle.TIME=entry,time;a=oracle.linked(self.out/'original-func_150CBE88.o','original-layout'+str(k));n=oracle.linked(self.out/'qualified-padded.o','qualified-layout'+str(k));raw=oracle.linked(self.out/'selected.o','raw-layout'+str(k));self.assertEqual(a,n)
    for dt,pattern,alias,phase in itertools.product((0x3EAAAAAB,0x7FC12345),(0,3,5),(-1,0x38,0x48),(0,8)):
     c=oracle.Case(dt,pattern,alias,phase);initial=oracle.fixture(c);want=oracle.reference(initial,c)
     for words in(a,n,raw):m=oracle.Oracle(words,initial,c).run();self.assertEqual((m.memory,m.r[2],m.calls),(want,1,[]))
     count+=1
  finally:oracle.ENTRY,oracle.TIME=previous
  raw,rs=source.payload(self.out/'selected.o');controls=0
  for i in range(len(raw)):
   bad=bytearray(raw);bad[i]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   controls+=1
  for at in rs:
   with self.assertRaises(ValueError):source.checked_payload(raw,{**rs,at:[('R_MIPS_26','wrong_symbol')]})
   controls+=1
  rows=list(csv.DictReader(io.StringIO((self.out/'proposed-guards.csv').read_text())));fields=list(rows[0]);guard_controls=0
  for i,guard in enumerate(source.NEW_GUARDS):
   modified=[dict(row,expected=hex(int(row['expected'],0)^1))if row['filename']==source.OWNER and row['function']==source.FUNCTION and row['offset']==guard['offset']else row for row in rows];p=self.fresh/('preimage-'+str(i)+'.csv');stream=io.StringIO();writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(modified);p.write_text(stream.getvalue())
   with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=p,filename=source.OWNER)
   guard_controls+=1
  self.receipt['layouts']=dict(layouts=3,cases=count,raw_binding_controls=controls,guard_controls=guard_controls)
 def test_07_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_150CBE88.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),9);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER));self.assertEqual(self.assemble(p).read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['owner']=dict(neighbors=9,actual_Make_commands=3,generated_padder=True,guards=33,diagnostics=0)
 def test_08_literal_image_and_named_metadata_controls(self):
  source.check_inputs(ROOT,self.out,self.installed);before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();literal=self.rom[source.ROM:source.ROM+212];source.check_image(before,actual,literal);at=source.elf_slot_offset(before,source.ENTRY,212);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+212),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),literal)
  self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=158,closed_metadata_bytes=0)
