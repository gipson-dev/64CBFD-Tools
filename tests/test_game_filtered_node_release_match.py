"""Direct filtered-node release, original cleanup/wrapper and whole-image gates."""
from pathlib import Path
import json,os,unittest
from tools.experiments import game_filtered_node_release_match as source
from tools.tests import game_filtered_node_release_oracle as oracle
from tools.tests import game_filtered_node_release_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
class FilteredNodeReleaseTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output);cls.values=source.snapshot(cls.output)
  cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];source.check_inputs(ROOT,cls.output,cls.installed)
  obj,diag=source.compile_owner(ROOT,cls.output,source.HEADERS+source.SELECTED,'public-fresh-selected');assert not diag
  cls.raw,cls.bindings=source.checked_payload(*source.payload(obj));assert (cls.raw,cls.bindings)==source.payload(cls.output/'selected-final.o')
  cls.guest=oracle.qualify(ROOT,cls.output);cls.helper=oracle.helper(ROOT,cls.output);cls.callers=oracle.callers(ROOT,cls.output);cls.native=native.qualify(ROOT,cls.output,source.SELECTED)
 def test_direct_words_bindings_and_corruption_controls(self):
  self.assertEqual(source.ENTRY,oracle.ENTRY);self.assertEqual((len(self.raw),len(self.bindings)),(212,3));self.assertFalse(source.NEW_GUARDS)
  self.assertEqual((self.raw,self.bindings),source.payload(self.output/'original-func_15030310.o'))
  for at in(0,12,48,68,100,148,208):
   bad=bytearray(self.raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.bindings)
  with self.assertRaises(ValueError):source.checked_payload(self.raw,{})
  with self.assertRaises(ValueError):source.recovered_owner(source.recovered_owner(self.values[source.SOURCE].decode()))
 def test_generated_owner_neighbors_pools_diagnostics_and_actual_make(self):
  for a,b in(('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):self.assertEqual(source.same_functions(self.output/a,self.output/b,(source.FUNCTION,)),39)
  self.assertEqual(source.normalized_pools(self.output/'before-padded.o'),source.normalized_pools(self.output/'qualified-padded.o'))
  self.assertEqual((self.output/'qualified-padded.o').read_bytes(),(self.output/'make-shadow/src/game/generated_5D2C0.c.o').read_bytes());self.assertEqual(len(json.loads((self.output/'Make-commands.json').read_text())),3)
  q=json.loads((self.output/'private-owner-qualification.json').read_text());self.assertEqual(q['diagnostics'],dict(before=0,after=0,removed=0));self.assertTrue(q['prototype_and_wrapper_cast_byte_identical'])
  self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
 def test_guest_live_key_cached_next_full_countdown_and_original_callers(self):
  q=self.guest;self.assertEqual((q['cases'],q['executions'],q['retail_words_covered']),(18144,36288,53));self.assertEqual(q['access_prefix_pairs'],113);self.assertEqual(q['independent_GNU_link_layouts'],3);self.assertTrue(q['original_private_full_machine_and_access_state_equal']);self.assertTrue(q['unsigned_countdown_and_FF_transition']);self.assertFalse(q['full_fault_register_equivalence_claim'])
  q=self.helper;self.assertEqual((q['cases'],q['executions'],q['helper_words_executed']),(288,576,83));self.assertEqual(len(q['unexecuted_helper_PCs']),19);self.assertTrue(q['immediate_zero_only']);self.assertTrue(q['original_unlink_head_prev_next_updates'])
  q=self.callers;self.assertEqual((q['cases'],q['executions'],q['all_static_direct_call_sites']),(768,1536,1));self.assertTrue(q['all_wrapper_words_covered']);self.assertTrue(q['wrapper_forces_FF_sentinel']);self.assertTrue(q['wrapper_C_void_result_not_claimed'])
 def test_native_complete_public_state_and_eight_effective_controls(self):
  self.assertEqual(len(self.native),3)
  for q in self.native:
   self.assertEqual((q['cases'],q['executions'],len(q['controls'])),(3024,27216,8));self.assertTrue(q['all_eight_controls_effective']);self.assertTrue(q['UBSan']);self.assertTrue(q['complete_node_and_actor_bytes_checked'])
 def test_literal_entire_image_extent_map_and_rejection_controls(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);self.assertEqual(len(before),len(actual))
  self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
  q=json.loads((self.output/'private-image-qualification.json').read_text());self.assertEqual((q['functions'],q['other_bodies_fixed']),(6052,6051));self.assertTrue(q['all_function_addresses_fixed']);self.assertEqual((q['old_symbol_bytes'],q['new_symbol_bytes']),(12,212))
  definitions={n:f for _,n,f,_ in source.symbol_rows(actual)};self.assertEqual(definitions[source.FUNCTION][1:3],(source.ENTRY,212))
  for at in(0x100,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,212)+4):
   bad=bytearray(actual);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
