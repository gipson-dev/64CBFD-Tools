"""Record-key association: literal frame state, bounded provider and complete image."""
from pathlib import Path
import csv,io,json,os,struct,subprocess,unittest
from tools.experiments import game_record_key_chain_match as source
from tools.tests import game_record_key_chain_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=Path(__file__).resolve().parents[2]
class RecordKeyChainTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);oracle.o=cls.fresh;cls.rom=cls.values['conker/conker.us.bin']
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_15195D00.o'));self.receipt['fresh_C']=dict(words=53,frame=40,guards=4,bindings=10,void_interface=True,diagnostics=0)
 def test_02_guest_aliases_caller_frame_faults_and_rebases(self):
  self.receipt['guest']=oracle.run_suite(self.out);self.assertEqual(self.receipt['guest']['covered_words'],53);self.assertEqual(self.receipt['guest']['unvisited'],[])
 def test_03_native32_UBSan_and_eight_controls(self):
  p=self.fresh/'native.c';p.write_text(oracle.native_harness(source.HEADERS+source.SELECTED));rows={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.returncode,run.stderr));rows[opt]=dict(exit=0,cases=8448,negative_controls=8,UBSan=True)
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
  bad=source.SELECTED.replace('cursor[0xE] = mode;','cursor[0xE] = mode ^ 1;');obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+bad,'wrong-mode');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(obj))
  with self.assertRaises(ValueError):source.check_owner_diagnostics('unexpected warning')
  self.receipt['source_controls']=dict(changed_C_rejected=True,new_diagnostics_rejected=True)
 def test_06_unchanged_frame_and_closed_record_home(self):
  q=json.loads((self.out/'selected-v9.json').read_text());self.assertEqual((q['frame'],q['raw_record_spill'],q['retail_record_spill']),(40,32,36));self.assertTrue(q['no_frame_or_argument_home_change']);self.assertEqual(q['saved_offsets'],[20,24,28]);self.assertEqual(q['incoming_homes'],[40,52]);self.assertEqual(q['outgoing_home_extent'],16);self.assertEqual({int(x['offset'],0)for x in source.NEW_GUARDS},{140,144,180,184});self.assertTrue(all(not x['insert_after']and x['omit']=='false'for x in source.NEW_GUARDS));self.receipt['frame']=dict(bytes=40,saved_offsets=[20,24,28],incoming_homes=[40,52],outgoing_home_extent=16,record_spill=36,frame_adjustments=0,insertions=0,omissions=0)
 def test_07_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.normalized_payload(*source.payload(obj)),source.payload(self.out/'original-func_15195D00.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),68);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.receipt['owner']=dict(neighbors=68,actual_Make_commands=3,diagnostics=0)
 def test_08_literal_image_and_named_metadata_controls(self):
  source.check_inputs(ROOT,self.out,self.installed);before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();literal=self.rom[source.ROM:source.ROM+212];source.check_image(before,actual,literal);at=source.elf_slot_offset(before,source.ENTRY,212);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets={0,4,52,len(actual)-1,*range(at,at+212),*range(symbol[0],symbol[0]+16)}
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),literal)
  self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=168,code_bytes=167,extent_bytes=1,metadata_bytes=0)
