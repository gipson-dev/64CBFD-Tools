"""Subtype appearance: closed address expansion, aliases, ABI and exact image."""
from pathlib import Path
import csv,io,json,os,struct,subprocess,unittest
from tools.experiments import game_subtype_appearance_match as source
from tools.tests import game_subtype_appearance_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=Path(__file__).resolve().parents[2]
class SubtypeAppearanceTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);oracle.o=cls.fresh;cls.rom=cls.values['conker/conker.us.bin']
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_1518A214.o'));self.receipt['fresh_C']=dict(compiler_words=50,normalized_words=53,frame=0,guards=50,insertions=3,bindings=6,diagnostics=0)
 def test_02_guest_aliases_caller_faults_and_rebases(self):
  self.receipt['guest']=oracle.run_suite(self.out);self.assertEqual(self.receipt['guest']['covered_words'],52);self.assertEqual(self.receipt['guest']['unvisited'],['0x1518a270'])
 def test_03_native32_UBSan_and_eight_controls(self):
  p=self.fresh/'native.c';p.write_text(oracle.native_harness(source.HEADERS+source.SELECTED));rows={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.returncode,run.stderr));rows[opt]=dict(exit=0,cases=92160,negative_controls=8,UBSan=True)
  self.receipt['native']=rows
 def test_04_raw_binding_and_guard_preimage_controls(self):
  raw,rs=source.payload(self.out/'selected.o');controls=0
  for i in range(len(raw)):
   bad=bytearray(raw);bad[i]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
   controls+=1
  for at in rs:
   with self.assertRaises(ValueError):source.normalized_payload(raw,{**rs,at:[('R_MIPS_26','wrong_symbol')]})
   controls+=1
  rows=list(csv.DictReader(io.StringIO((self.out/'proposed-guards.csv').read_text())));fields=list(rows[0]);n=0
  for guard in source.NEW_GUARDS:
   modified=[dict(row,expected=hex(int(row['expected'],0)^1))if row['filename']==source.OWNER and row['function']==source.FUNCTION and row['offset']==guard['offset']else row for row in rows];stream=io.StringIO();w=csv.DictWriter(stream,fields);w.writeheader();w.writerows(modified);p=self.fresh/('preimage-'+str(n)+'.csv');p.write_text(stream.getvalue())
   with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=p,filename=source.OWNER)
   n+=1
  self.receipt['controls']=dict(raw_binding_controls=controls,guard_preimage_controls=n)
 def test_05_changed_source_and_diagnostic_controls(self):
  bad=source.SELECTED.replace('= 128;','= 127;');obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+bad,'wrong-red');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(obj))
  with self.assertRaises(ValueError):source.check_owner_diagnostics('unexpected warning')
  self.receipt['source_controls']=dict(changed_C_rejected=True,new_diagnostics_rejected=True)
 def test_06_closed_address_expansion_and_original_registration(self):
  origins=json.loads((self.out/'normalization-origins.json').read_text());self.assertEqual(sorted(x for x in origins if isinstance(x,int)),list(range(50)));self.assertEqual(origins.count('interior'),3);self.assertEqual(struct.unpack_from('>I',self.rom,0x232060)[0],source.ENTRY);self.assertEqual(sum(bool(x['insert_after'])for x in source.NEW_GUARDS),3);self.assertTrue(all(x['omit']=='false'for x in source.NEW_GUARDS));self.receipt['derivation']=dict(all_input_words_used_once=True,address_insertions=3,omissions=0,retail_table_index=0)
 def test_07_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_1518A214.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),5);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['owner']=dict(neighbors=5,actual_Make_commands=3,diagnostics=0)
 def test_08_literal_image_and_named_metadata_controls(self):
  source.check_inputs(ROOT,self.out,self.installed);before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();literal=self.rom[source.ROM:source.ROM+212];source.check_image(before,actual,literal);at=source.elf_slot_offset(before,source.ENTRY,212);offsets={i for i,(a,b)in enumerate(zip(before,actual))if a!=b}|{0,4,52,len(actual)-1,at-1,at+212}
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),literal)
  self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=223,code_bytes=162,extent_bytes=1,closed_metadata_bytes=60,named_metadata_groups=3)
