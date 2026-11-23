"""Five direct source, request relay, ABI, fault and independent image gates."""
import unittest
from tools.experiments import game_owner_phase_update_150bf760_match as packet
from tools.experiments import game_owner_phase_update_150bf760_qualification as qualification
from tools.tests import game_owner_phase_update_150bf760_guest as guest
from tools.tests import game_owner_phase_update_150bf760_native as native
class OwnerPhaseUpdate(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_complete_owners_Make_and_independent_strict_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],626);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],packet.MANIFEST['metadata_permuted_records']);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_raw_C_full_state_and_independent_phase_effects(self):
  q=guest.main();self.assertEqual(q['cases_per_stream'],1580);self.assertEqual(len(q['streams']),3);self.assertTrue(q['complete_state_and_access_trace_equal']);self.assertTrue(q['independent_public_semantics_equal']);self.assertEqual(q['unmapped_null_fault_cases'],144);self.assertEqual(q['explicit_guest_only_zero_page_cases'],8);self.assertTrue(q['actual_16_word_request_relay_connected']);self.assertFalse(q['unexecuted_target_words'])
 def test_03_actual_setup_callers_and_fired_fault_prefixes(self):
  q=guest.callers();self.assertEqual((q['real_table_setup_window_words'],q['table_setup_cases'],q['table_index']),(22,3,8));self.assertEqual((q['real_indirect_caller_windows'],q['words_per_window'],q['cases_per_stream']),(2,4,100));q=guest.faults();self.assertEqual(q['raw_padded_retail_full_state_access_prefix_triples'],159);self.assertTrue(q['includes_actual_relay_and_null_read_cut'])
 def test_04_actual_SDK32_parent_return_relay_and_effective_controls(self):
  q=native.main();self.assertEqual(set(q['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==1428 and v['SDK32']and v['UBSan']and v['strict_aliasing']and v['independent_vector_fields_and_events']and v['actual_parent_and_return_relay_C']for v in q['profiles'].values()));self.assertEqual(len(q['effective_output_comparison_controls']),10);self.assertEqual(q['excluded_guest_fault_or_zero_page_cases'],152)
 def test_05_direct_padders_rebases_relay_and_unmatched_controls(self):
  q=qualification.main();self.assertTrue(q['raw_is_exact_retail_words_and_bindings']);self.assertTrue(q['both_padders_byte_exact']);self.assertEqual((q['guards'],q['insertions'],q['omissions']),(0,0,0));self.assertEqual((q['GNU_target_links'],q['GNU_relay_links'],q['guest_rebase_runs']),(12,8,96));self.assertEqual(q['effective_wrong_word_or_binding_controls'],4);self.assertEqual(q['generated_oversized_rejection'],1);self.assertEqual(q['generic_overflow_preserved_but_unmatched'],1);self.assertTrue(q['complete_relay_payload_unchanged'])
if __name__=='__main__':unittest.main(verbosity=2)
