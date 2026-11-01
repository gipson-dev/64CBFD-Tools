"""Cash-label C, closed clamp guards, complete caller, Make and strict image."""
from pathlib import Path
import csv,io,json,os,struct,subprocess,unittest
from tools.experiments import game_lifetime_callback_fade_match as source
from tools.tests import game_lifetime_callback_fade_oracle as oracle
from tools.tests import game_lifetime_callback_fade_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class LifetimeCallbackFadeTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
  cls.raw,diag=source.compile_owner(ROOT,cls.fresh,source.HEADERS+source.SELECTED,'fresh-selected')
  if diag:raise AssertionError(diag)
  oracle.configure(ROOT,cls.fresh,cls.raw)
  cls.connected_result=oracle.run_suite()
 @classmethod
 def tearDownClass(cls):
  (cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_complete_C_and_closed_guards(self):
  source.check_inputs(ROOT,self.out,self.installed);raw,rs=source.checked_payload(*source.payload(self.raw))
  self.assertEqual(source.normalized_payload(raw,rs),source.payload(self.out/'original-func_15154C90.o'))
  for at in range(len(raw)):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
  for at in rs:
   changed=dict(rs);changed[at]=[(rs[at][0][0],'foreign')]
   with self.assertRaises(ValueError):source.normalized_payload(raw,changed)
  for kw in (dict(owner='foreign'),dict(function='foreign')):
   with self.assertRaises(ValueError):source.normalized_payload(raw,rs,**kw)
  self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes())
  self.receipt['fresh_C']=dict(words=60,guards=7,bindings=5,insertions=0,omissions=0,raw_byte_exact=False)
 def test_02_closed_register_cycle_and_fired_prefixes(self):
  result=oracle.run_closed_proof();self.assertEqual(result['exhaustive_low16_values'],65536)
  self.assertEqual(result['guards'],source.NEW_GUARDS);self.assertTrue(result['full_normalized_payload_equals_retail']);self.assertEqual(result['fired_prefix_cases'],101);self.receipt['closed_proof']=result
 def test_03_original_complete_parent_and_return_poisons(self):
  result=self.connected_result;self.assertEqual((result['root_cases'],result['parent_words']),(1200,74));self.assertTrue(result['parent_ignores_callback_word'])
  two=oracle.run_parent_two();self.assertEqual(two['parent_reachable_words'],74);self.assertEqual(two['return_poison_controls'],4)
  rom=self.values['conker/conker.us.bin'];literal=source.ENTRY.to_bytes(4,'big');jal=(0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big')
  self.assertEqual([i for i in range(0,len(rom)-3,4) if rom[i:i+4]==literal],[0x231114,0x23124C]);self.assertEqual([i for i in range(0,len(rom)-3,4) if rom[i:i+4]==jal],[])
  self.receipt['guest']=result;self.receipt['complete_parent']=two
 def test_04_sparse_paths_and_guest_global_overlaps(self):
  # run_suite emits a fresh linked compiler body for these bounded guest checks.
  if not (self.fresh/'raw-linked.elf').exists():oracle.run_suite()
  result=oracle.run_sparse_and_aliases();self.assertEqual((result['sparse_executions'],result['guest_global_overlap_cases']),(6,2));self.receipt['sparse_alias']=result
 def test_05_native32_UBSan_live_mutations_and_controls(self):
  result=native.run_native(ROOT,self.fresh,source.HEADERS+source.SELECTED)
  self.assertEqual(result,json.loads((self.out/'native-lifetime.json').read_text()));self.receipt['native']=result
 def test_06_fresh_owner_padding_and_frozen_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner')
  self.assertFalse(diag);self.assertEqual(source.payload(obj),source.payload(self.raw))
  self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),40)
  self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj))
  text=source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER)
  p=self.fresh/'padded.s';p.write_text(text)
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True)
  self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes())
  reader=csv.DictReader(io.StringIO((self.out/'proposed-guards.csv').read_text()));fields=reader.fieldnames;rows=list(reader);count=0
  for index,row in enumerate(rows):
   if (row['filename'],row['function'])!=(source.OWNER,source.FUNCTION):continue
   for field,value in (('expected','0xFFFFFFFF'),('expected_relocations','R_MIPS_26:foreign')):
    changed=[dict(x) for x in rows];changed[index][field]=value;bad=self.fresh/'bad-guards.csv'
    with bad.open('w',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(changed)
    with self.assertRaisesRegex(ValueError,'stale word patch|stale relocations'):source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=bad,filename=source.OWNER)
    count+=1
  self.assertEqual(count,14);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
  self.receipt['owner']=dict(fresh_full_owner_and_padding=True,neighbors=40,new_diagnostics=0,guard_preimage_controls=count,
   actual_Make_commands=5,actual_Make_reused_with_unchanged_fingerprints=True)
 def test_07_strict_whole_image_metadata_and_protected_data(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE]
  source.check_image(before,actual,truth)
  at=source.elf_slot_offset(before,source.ENTRY,source.SIZE)
  offsets={0,4,len(actual)-1,at,at+source.SIZE-1,0x2B1F14,0x2B1F24,0x2F52B2,0x2F52BD}
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  for offset in (0x2B1F14,0x2B1F24,0x2F52B2,0x2F52BD):
   bad=bytearray(before);bad[offset]^=1
   with self.assertRaises(ValueError):source.predicted_image(bytes(bad),truth)
  data=source.audit(ROOT,self.out)['game_data'] if self.installed else source.audit_layout(self.out/'first-linked.elf',ROOT/'conker')
  self.assertEqual((data['exact'],data['bytes'],data['owner_count']),(True,189088,720))
  self.receipt['image']=dict(strict=True,exclusions=0,changed_bytes=sum(a!=b for a,b in zip(before,actual)),
   named_BFD_symbol_string_pair_swaps=0,corruption_controls=len(offsets)+4,protected_Game_bytes=189088,protected_owners=720)
