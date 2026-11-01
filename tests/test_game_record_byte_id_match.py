"""Direct C byte-ID search: ABI windows, native reference, rebases and whole-image audit."""
from pathlib import Path
import json,os,subprocess,unittest
from tools.experiments import game_record_byte_id_match as source
from tools.tests import game_record_byte_id_oracle as oracle
from tools.tests import game_record_byte_id_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class RecordByteIdTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
  cls.raw,diag=source.compile_owner(ROOT,cls.fresh,source.HEADERS+source.SELECTED,'fresh-selected')
  if diag:raise AssertionError(diag)
  oracle.configure(ROOT,cls.fresh,cls.raw);cls.guest=oracle.run_suite()
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_direct_C_bindings_and_rejection_controls(self):
  source.check_inputs(ROOT,self.out,self.installed);raw,bindings=source.checked_payload(*source.payload(self.raw))
  self.assertEqual((raw,bindings),source.payload(self.out/'original-func_15004BF0.o'));self.assertEqual(source.NEW_GUARDS,[])
  for offset in range(len(raw)):
   bad=bytearray(raw);bad[offset]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),bindings)
  for offset in bindings:
   changed=dict(bindings);changed[offset]=[(bindings[offset][0][0],'foreign')]
   with self.assertRaises(ValueError):source.normalized_payload(raw,changed)
  for kw in (dict(owner='foreign'),dict(function='foreign')):
   with self.assertRaises(ValueError):source.normalized_payload(raw,bindings,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),self.values['conker/retail_word_patches.us.csv'])
  self.receipt['direct_C']=dict(words=60,bindings=12,guards=0,rejection_controls=254)
 def test_02_independent_set_reference_and_actual_caller_windows(self):
  self.assertEqual((self.guest['root_cases'],self.guest['retail_reachable_words'],self.guest['caller_cases']),(604,60,27));self.assertEqual(self.guest['sparse_executions'],6)
  rom=self.values['conker/conker.us.bin'];jal=(0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');literal=source.ENTRY.to_bytes(4,'big')
  self.assertEqual([i for i in range(0,len(rom)-3,4) if rom[i:i+4]==jal],[0x31444,0x31654,0x319C8]);self.assertEqual([i for i in range(0,len(rom)-3,4) if rom[i:i+4]==literal],[])
  self.receipt['guest']=self.guest
 def test_03_native32_UBSan_and_effective_semantic_controls(self):
  result=native.run_native(ROOT,self.fresh,source.HEADERS+source.SELECTED);self.assertEqual(result,json.loads((self.out/'native-byte-id.json').read_text()));self.receipt['native']=result
 def test_04_independent_relocations_and_carry_boundaries(self):
  result=oracle.run_rebases();self.assertEqual((result['profiles'],result['executions']),(3,18));self.receipt['rebases']=result
 def test_05_fired_prefixes_and_guest_alias(self):
  result=oracle.run_prefixes_and_alias();self.assertGreater(result['fired_prefix_cases'],20);self.assertEqual(result['guest_start_byte_record_aliases'],1);self.receipt['prefix_alias']=result
 def test_06_complete_owner_padding_and_actual_Make_evidence(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');self.assertFalse(diag)
  self.assertEqual(source.payload(obj),source.payload(self.raw));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),8)
  self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj))
  path=self.fresh/'padded.s';path.write_text(source.emit_padded_assembly(obj,ROOT/source.LAYOUT,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'))
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],capture_output=True,check=True)
  self.assertEqual(path.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
  self.receipt['owner']=dict(neighbors=8,new_diagnostics=0,actual_Make_commands=3,actual_Make_reused_with_exact_fingerprints=True)
 def test_07_literal_full_image_and_protected_data(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth)
  at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(row[0] for row in source.symbol_rows(before) if row[1]==source.FUNCTION)
  for offset in (0,4,len(actual)-1,at,at+239,symbol+8):
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  data=source.audit(ROOT,self.out)['game_data'] if self.installed else source.audit_layout(self.out/'first-linked.elf',ROOT/'conker')
  self.assertEqual((data['exact'],data['bytes'],data['owner_count']),(True,189088,720));self.receipt['image']=dict(strict=True,exclusions=0,changed_bytes=sum(a!=b for a,b in zip(before,actual)),protected_bytes=189088,owners=720)
