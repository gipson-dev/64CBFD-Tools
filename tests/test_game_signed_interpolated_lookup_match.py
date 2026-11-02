"""Direct interpolation: complete body, table boundaries and entire linked image."""
from pathlib import Path
from collections import Counter
import json,os,struct,unittest
from tools.experiments import game_signed_interpolated_lookup_match as source
from tools.tests import game_signed_interpolated_lookup_oracle as oracle
from tools.tests import game_signed_interpolated_lookup_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class SignedInterpolatedLookupTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));cls.guest=oracle.qualify(ROOT,cls.output);cls.native=native.qualify(ROOT,cls.output,source.SELECTED,oracle)

 def test_direct_body_bindings_and_effective_payload_controls(self):
  self.assertEqual(source.payload(self.output/'original-func_150488C8.o'),(self.raw,self.bindings));self.assertEqual(source.payload(self.output/'qualified-padded.o'),(self.raw,self.bindings))
  self.assertEqual(len(self.raw),220);self.assertEqual(len(self.bindings),8)
  for at in range(0,220,4):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  self.assertNotIn(b',func_150488C8,',self.values['conker/retail_word_patches.us.csv'])
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.output/'proposed-owner.c').read_text())
  with self.assertRaises(ValueError):source.recovered_owner((self.output/'proposed-owner.c').read_text())
  self.assertIn('f32 func_150488C8(f32 arg0);',' '.join(self.values['conker/include/functions.h'].decode().split()))

 def test_two_neighbors_pools_padding_and_actual_make(self):
  for a,b in (('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):
   self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),2);self.assertEqual(source.normalized_pools(self.output/a),source.normalized_pools(self.output/b))
  self.assertEqual((self.output/'qualified-padded.o').read_bytes(),(self.output/'make-shadow/src/game_75C90.c.o').read_bytes())
  self.assertEqual(len(json.loads((self.output/'Make-commands.json').read_text())),3)
  self.assertEqual(source.check_owner_diagnostics((self.output/'before-owner-diagnostics.txt').read_text(),(self.output/'after-owner-diagnostics.txt').read_text()),dict(before=0,after=0,removed=0))
  self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])

 def test_guest_cells_signs_rebases_faults_and_caller_inventory(self):
  q=self.guest
  self.assertEqual((q['guest_cases'],q['inputs'],q['tables'],q['layouts'],q['all_cells'],q['reachable_words']),(24576,4096,2,3,256,47))
  self.assertEqual(q['unreachable_offsets'],[0x4C,0x50,0x54,0x78,0x7C,0x80,0x84,0x88])
  self.assertEqual((q['fault_prefixes'],q['out_of_domain_guest_only_prefixes']),(72,6))
  self.assertEqual(q['direct_ROM_transfers'],[]);self.assertEqual(q['aligned_ROM_function_pointers'],[]);self.assertTrue(q['indirect_callers_unknown'])
  self.assertTrue(q['NaN_FCSR_hardware_gameplay_not_qualified'])

 def test_native_typed_calls_and_seven_effective_controls_at_three_profiles(self):
  q=self.native;self.assertTrue(q['success']);self.assertEqual((q['inputs_per_table'],q['tables'],q['effective_controls_per_profile']),(4096,2,7));self.assertEqual(q['profiles'],['O0','O2','O3'])
  self.assertTrue(q['UBSan']);self.assertTrue(q['typed_function_pointer']);self.assertTrue(q['stack_realigned']);self.assertEqual(len(q['results']),24)

 def test_literal_image_closed_metadata_groups_and_rejection_controls(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes()
  source.check_image(before,actual,truth);self.assertEqual(source.sha(actual),'c1ba81dadb31b6a5e1cbbb16d5444ebca6bd85da0b4326ab78e5059a70997e34')
  q=json.loads((self.output/'private-owner-image-v11.json').read_text());self.assertEqual((q['functions'],q['other_bodies_fixed'],q['strict_exclusions'],q['metadata_groups'],q['metadata_records']),(6052,6051,0,4,13));self.assertTrue(q['all_function_addresses_fixed']);self.assertTrue(q['entire_named_definition_multiset_verified'])
  rows={n:(at,f)for at,n,f,_ in source.symbol_rows(actual)};self.assertEqual(rows[source.FUNCTION][1][1:3],(source.ENTRY,220))
  expected=Counter((n,f[1],220 if n==source.FUNCTION else f[2],*f[3:])for _,n,f,_ in source.symbol_rows(before));self.assertEqual(expected,Counter((n,*f[1:])for _,n,f,_ in source.symbol_rows(actual)))
  for at in (0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,232)+0x40,rows[source.FUNCTION][0]+8,rows['D_80099010'][0]+4):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(AssertionError):source.serialize_metadata(actual)
  with self.assertRaises(ValueError):source.predict(before,b'bad')
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
