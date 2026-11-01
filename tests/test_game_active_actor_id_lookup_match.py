"""Direct actor ID lookup, signed argument, reserved slot and four original callers."""
from pathlib import Path
import json,os,unittest
from tools.experiments import game_active_actor_id_lookup_match as source
from tools.tests import game_active_actor_id_lookup_oracle as oracle
from tools.tests import game_active_actor_id_lookup_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class ActiveActorIdLookupTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));assert (cls.raw,cls.bindings)==source.payload(cls.output/'selected-final.o')
  cls.guest=oracle.qualify(ROOT,cls.output);cls.callers=oracle.callers(ROOT,cls.output);cls.native=native.qualify(ROOT,cls.output,source.SELECTED)
 def test_direct_words_link_aliases_and_payload_controls(self):
  self.assertEqual(source.ENTRY,oracle.ENTRY);self.assertEqual((len(self.raw),len(self.bindings)),(220,8));self.assertFalse(source.NEW_GUARDS)
  # Retail names its first-slot ID and slot-one addresses as separate aliases.
  self.assertNotEqual((self.raw,self.bindings),source.payload(self.output/'original-func_1505F0AC.o'))
  for at in(0,12,24,44,100,192,216):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  with self.assertRaises(ValueError):source.recovered_owner(source.recovered_owner(self.values[source.SOURCE].decode()))
 def test_owner_pools_inherited_diagnostics_and_make(self):
  for a,b in(('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),88)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'qualified-padded.o').read_bytes(),(self.output/'make-shadow/src/game_83300.c.o').read_bytes());self.assertEqual(len(json.loads((self.output/'Make-commands.json').read_text())),5)
  q=json.loads((self.output/'private-owner-qualification.json').read_text());self.assertEqual(q['diagnostics'],dict(before=8,after=8,removed=0));self.assertTrue(q['retail_linked_payload_equal'])
  self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
 def test_guest_full_argument_readonly_trace_and_original_callers(self):
  q=self.guest;self.assertEqual((q['cases'],q['executions'],q['covered_words']),(14288,28576,52));self.assertEqual(q['unreachable_offsets'],[88,124,160]);self.assertTrue(q['literal_full_state_equal']);self.assertTrue(q['read_only']);self.assertTrue(q['reserved_slot_25_excluded']);self.assertTrue(q['all_256_ID_bytes']);self.assertTrue(q['full_s32_search_argument']);self.assertEqual(q['access_prefix_pairs'],108);self.assertEqual(q['rebase_layouts'],3)
  q=self.callers;self.assertEqual((q['original_call_sites'],q['executions'],q['complete_small_parents']),(4,640,2));self.assertTrue(q['actual_argument_setup_and_return_pointer_consumers']);self.assertTrue(q['null_guarded_caller_paths']);self.assertTrue(q['unguarded_callers_qualified_only_for_nonnull_results']);self.assertEqual(q['sparse_first_slot_executions'],2);self.assertFalse(q['larger_parent_claims'])
 def test_native_full_table_immutability_and_seven_controls(self):
  q=self.native;self.assertEqual(q['cases'],3572);self.assertEqual(q['negative_controls'],7);self.assertTrue(q['UBSan'])
  self.assertEqual(len(q['profiles']),10)
  for name,row in q['profiles'].items():self.assertEqual(row['exit'],0 if name.startswith('selected-')else 1)
 def test_literal_entire_image_extent_and_unchanged_map(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+220];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(len(before),len(actual))
  self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
  q=json.loads((self.output/'private-image-qualification.json').read_text());self.assertEqual((q['functions'],q['other_bodies_fixed']),(6052,6051));self.assertTrue(q['all_function_addresses_fixed']);self.assertEqual((q['old_symbol_bytes'],q['new_symbol_bytes']),(16,220))
  definitions={n:f for _,n,f,_ in source.symbol_rows(actual)};self.assertEqual(definitions[source.FUNCTION][1:3],(source.ENTRY,220))
  for at in(0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,220)+4):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
