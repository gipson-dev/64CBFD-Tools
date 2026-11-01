"""Direct C X=-Z interpolation: finite arithmetic, alias order and entire image."""
from pathlib import Path
import hashlib,json,os,subprocess,unittest
from tools.experiments import game_negative_xz_plane_interpolation_match as source
from tools.tests import game_negative_xz_plane_interpolation_oracle as oracle
from tools.tests import game_negative_xz_plane_interpolation_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class NegativeXZPlaneInterpolationTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
  cls.raw,diag=source.compile_owner(ROOT,cls.fresh,source.HEADERS+source.SELECTED,'fresh-selected');assert not diag
  oracle.configure(ROOT,cls.fresh,cls.raw)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_direct_C_bindings_and_fail_closed_controls(self):
  source.check_inputs(ROOT,self.out,self.installed);raw,bindings=source.checked_payload(*source.payload(self.raw))
  self.assertEqual((raw,bindings),source.payload(self.out/'original-func_1518557C.o'));self.assertEqual(source.NEW_GUARDS,[])
  for offset in range(len(raw)):
   bad=bytearray(raw);bad[offset]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),bindings)
  for offset in bindings:
   changed=dict(bindings);changed[offset]=[(bindings[offset][0][0],'foreign')]
   with self.assertRaises(ValueError):source.normalized_payload(raw,changed)
  for kw in (dict(owner='foreign'),dict(function='foreign')):
   with self.assertRaises(ValueError):source.normalized_payload(raw,bindings,**kw)
  with self.assertRaises(ValueError):source.checked_payload(raw,{0:[('R_MIPS_26','foreign')]})
  self.receipt['direct_C']=dict(words=64,slot_words=64,alignment_words=0,bindings=0,guards=0,rejection_controls=259)
 def test_02_guest_interpolation_aliases_and_store_order(self):
  result=oracle.run_suite();self.assertEqual((result['cases'],result['reachable_words']),(894,64));self.receipt['guest']=result
 def test_03_complete_original_parent_classifiers_and_table(self):
  rom=self.values['conker/conker.us.bin'];jal=(0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big')
  self.assertEqual([i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal],[])
  self.assertEqual([i for i in range(0,len(rom)-3,4)if rom[i:i+4]==source.ENTRY.to_bytes(4,'big')],[0x231F5C])
  for name in ('conker/asm/1B1600.s','conker/asm/data/231EA0.rodata.s'):self.assertEqual((ROOT/name).read_bytes(),self.values[name])
  result=oracle.run_callers();self.assertEqual((result['cases'],result['parent_reachable_words']),(21,84));self.receipt['callers']=result
 def test_04_native32_UBSan_and_effective_controls(self):
  result=native.run_native(ROOT,self.fresh,source.HEADERS+source.SELECTED,oracle)
  self.assertEqual(result,json.loads((self.out/'native-interpolation.json').read_text()));self.receipt['native']=result
 def test_05_rebases_fired_prefixes_and_guest_aliases(self):
  result=oracle.run_prefixes_and_rebases();self.assertEqual((result['relocated_code_profiles'],result['fired_prefix_cases'],result['relocated_table_caller_executions']),(2,57,4));self.receipt['rebases_prefixes']=result
 def test_06_complete_owner_padding_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');self.assertFalse(diag)
  self.assertEqual(source.payload(obj),source.payload(self.raw));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),31)
  self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj))
  path=self.fresh/'padded.s';path.write_text(source.emit_padded_assembly(obj,ROOT/source.LAYOUT,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'))
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],capture_output=True,check=True)
  self.assertEqual(path.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),self.values['conker/retail_word_patches.us.csv'])
  self.receipt['owner']=dict(neighbors=31,new_diagnostics=0,actual_Make_commands=3,actual_Make_reused_with_exact_fingerprints=True)
 def test_07_literal_full_image_and_protected_data(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth)
  at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(row[0]for row in source.symbol_rows(before)if row[1]==source.FUNCTION)
  for offset in (0,4,len(actual)-1,at,at+255,symbol+8):
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  data=source.audit(ROOT,self.out)['game_data']if self.installed else source.audit_layout(self.out/'first-linked.elf',ROOT/'conker')
  self.assertEqual((data['exact'],data['bytes'],data['owner_count']),(True,189088,720));self.receipt['image']=dict(strict=True,exclusions=0,changed_bytes=sum(a!=b for a,b in zip(before,actual)),protected_bytes=189088,owners=720)
