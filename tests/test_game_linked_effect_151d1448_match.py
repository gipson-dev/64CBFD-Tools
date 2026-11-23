"""Five gates for the complete direct owner-linked effect constructor."""
import unittest
from tools.experiments import game_linked_effect_151d1448_match as p
from tools.experiments import game_linked_effect_151d1448_qualification as q
from tools.tests import game_linked_effect_151d1448_guest as g
from tools.tests import game_linked_effect_151d1448_native as n
class LinkedEffect(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],297);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],[]);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_direct_instructions_and_independent_packet_semantics(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],584);self.assertTrue(v['direct_instruction_and_binding_identity']);self.assertTrue(v['independent_public_memory_calls_and_both_packets_equal']);self.assertTrue(v['all_guest_private_bytes_and_saved_registers_equal']);self.assertEqual(v['unexecuted_original_words'],[36])
 def test_03_fault_prefixes_caller_window_and_guest_overlaps(self):
  v=g.faults();self.assertEqual(v['full_state_and_dispatched_word_access_prefix_quadruples'],213);v=g.callers();self.assertEqual(v['original_caller_window_words'],6);self.assertEqual(v['cases_per_stream'],49);self.assertEqual(v['unrecovered_full_caller_credit'],0);self.assertEqual(g.aliases()['guest_only_public_payload_overlap_cases'],3)
 def test_04_actual_SDK32_native_C_and_effective_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==576 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['backing_guard_bytes_checked']for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),8);self.assertEqual(v['excluded_synthetic_guest_return_addresses'],8);self.assertTrue(all(not x['padding_bits_compared']for x in v['profiles'].values()))
 def test_05_direct_bindings_GNU_links_and_guest_padding(self):
  v=q.main();self.assertTrue(v['raw_is_exact_retail_words_and_bindings']);self.assertTrue(v['both_padders_byte_exact']);self.assertEqual((v['guards'],v['insertions'],v['omissions']),(0,0,0));self.assertEqual(v['effective_wrong_word_or_binding_controls'],204);self.assertEqual(v['GNU_target_links'],12);self.assertEqual(v['guest_rebase_runs'],96);self.assertTrue(v['effective_zero_padding_guest_control']);self.assertFalse(v['native_padding_bits_claimed'])
if __name__=='__main__':unittest.main(verbosity=2)
