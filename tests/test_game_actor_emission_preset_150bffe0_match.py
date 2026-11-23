"""Five source, normalized instruction, ABI and independent linked-image gates."""
import unittest
from tools.experiments import game_actor_emission_preset_150bffe0_match as packet
from tools.experiments import game_actor_emission_preset_150bffe0_qualification as qualification
from tools.tests import game_actor_emission_preset_150bffe0_guest as guest
from tools.tests import game_actor_emission_preset_150bffe0_native as native
class ActorEmissionPreset(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_complete_Make_and_independent_strict_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],481);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],packet.MANIFEST['metadata_permuted_records']);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_raw_C_effects_normalized_state_and_packet_fields(self):
  q=guest.main();self.assertEqual(q['cases_per_stream'],128);self.assertEqual(len(q['streams']),3);self.assertTrue(q['raw_C_packet_public_effects_and_final_private_state_equal']);self.assertTrue(q['normalized_retail_full_state_and_trace_equal']);self.assertEqual(q['raw_trace_differences_observed'],128);self.assertFalse(q['unexecuted_target_words'])
 def test_03_actual_caller_and_full_normalized_fault_prefixes(self):
  q=guest.callers();self.assertEqual(q['real_caller_window_words'],4);self.assertEqual(q['cases_per_stream'],32);q=guest.faults();self.assertEqual(q['normalized_retail_full_memory_GPR_FPR_HI_LO_trace_calls_prefix_pairs'],195);self.assertEqual(q['raw_private_prefix_differences'],156)
 def test_04_actual_SDK32_C_and_effective_source_controls(self):
  q=native.main();self.assertEqual(set(q['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==8192 and v['SDK32']and v['UBSan']and v['strict_aliasing']and v['separate_float32_rounding']and v['pre_call_snapshots_and_all_fields']for v in q['profiles'].values()));self.assertEqual(len(q['effective_output_comparison_controls']),7)
 def test_05_closed_normalization_padders_bindings_and_fail_closed_inputs(self):
  q=qualification.main();self.assertTrue(q['both_padders_byte_exact']);self.assertTrue(q['register_erased_instruction_and_binding_multiset_equal']);self.assertEqual((q['guards'],q['insertions'],q['omissions']),(45,0,0));self.assertEqual(q['GNU_links'],12);self.assertEqual(q['guest_rebase_runs'],96);self.assertEqual(q['oversized_body_rejections'],2);self.assertEqual(q['effective_wrong_word_or_binding_controls'],4);self.assertEqual(q['strict_expected_word_and_binding_rejections'],4)
if __name__=='__main__':unittest.main(verbosity=2)
