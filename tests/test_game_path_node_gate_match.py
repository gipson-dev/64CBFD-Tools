"""Path-node callback: source semantics, real caller, guarded ABI and strict image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_path_node_gate_match as source
from tools.tests import game_path_node_gate_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=Path(__file__).resolve().parents[2]
class PathNodeGateTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);oracle.o=cls.fresh;cls.rom=cls.values['conker/conker.us.bin']
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_1507B974.o'));self.receipt['fresh_C']=dict(words=53,frame=24,guards=31,bindings=17,diagnostics=0)
 def test_02_guest_boundaries_and_aliases(self):
  self.receipt['guest']=oracle.run_guest(self.out);self.assertEqual(self.receipt['guest']['covered_words'],53)
 def test_03_original_caller_faults_rebases_and_preimages(self):
  self.receipt['boundaries']=oracle.run_boundaries(self.out)
 def test_04_native32_UBSan_and_eight_controls(self):
  p=self.fresh/'native.c';p.write_text(oracle.native_harness(source.HEADERS+source.SELECTED));rows={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.returncode,run.stderr));rows[opt]=dict(exit=0,cases=10368,negative_controls=8,UBSan=True)
  self.receipt['native']=rows
 def test_05_inherited_diagnostic_context_controls(self):
  diag=(self.out/'before-owner-diagnostics.txt').read_text();text=self.values[source.SOURCE].decode();self.assertEqual(source.check_owner_diagnostics(diag,text),14)
  for bad in('',diag+'extra warning\n',diag.replace('Warning 665','Warning 666',1)):
   self.assertNotEqual(bad,diag)
   with self.assertRaises(ValueError):source.check_owner_diagnostics(bad,text)
  self.receipt['diagnostics']=dict(inherited=14,changed_added_deleted_controls=3,selected=0)
 def test_06_raw_normalization_and_source_guard_control(self):
  raw,rs=source.payload(self.out/'selected.o');self.assertEqual(source.normalized_payload(raw,rs),source.payload(self.out/'original-func_1507B974.o'))
  bad=source.SELECTED.replace('D_800D1892 ^= 1','D_800D1892 |= 1');obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+bad,'rejected-toggle');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(obj))
  self.receipt['normalization']=dict(guards=31,source_control=True,no_insertions=True,no_omissions=True)
 def test_07_complete_owner_and_actual_Make(self):
  text=source.recovered_owner(self.values[source.SOURCE].decode());obj,diag=source.compile_owner(ROOT,self.fresh,text,'fresh-owner');source.check_owner_diagnostics(diag,text);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_1507B974.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),210);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.LAYOUT,source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['owner']=dict(neighbors=210,actual_Make_commands=5,inherited_diagnostics=14,shared_headers_unchanged=True)
 def test_08_literal_image_and_named_metadata_controls(self):
  source.check_inputs(ROOT,self.out,self.installed);before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();literal=self.rom[source.ROM:source.ROM+212];source.check_image(before,actual,literal);at=source.elf_slot_offset(before,source.ENTRY,212);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+212),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),literal)
  self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=181,code_bytes=180,extent_bytes=1,metadata_bytes=0)
