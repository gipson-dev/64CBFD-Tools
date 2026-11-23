"""Five focused direct preset source, ABI and independent full-image gates."""
import unittest
from tools.experiments import game_effect_preset_150c04c0_match as packet
from tools.experiments import game_effect_preset_150c04c0_qualification as qualification
from tools.tests import game_effect_preset_150c04c0_guest as guest
from tools.tests import game_effect_preset_150c04c0_native as native
class EffectPreset(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_complete_Make_and_independent_strict_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],476);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],packet.MANIFEST['metadata_permuted_records']);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_complete_target_packet_and_local_lifetimes(self):
  q=guest.main();self.assertEqual(q['cases_per_stream'],128);self.assertEqual(q['guest_alias_cases_per_stream'],4);self.assertEqual(len(q['streams']),3);self.assertFalse(q['unexecuted_target_words']);self.assertTrue(q['padding_preserved'])
 def test_03_original_complete_caller_and_full_fault_prefixes(self):
  q=guest.callers();self.assertEqual(q['original_complete_caller_words'],32);self.assertEqual(q['cases_per_stream'],10);q=guest.faults();self.assertGreater(q['full_memory_GPR_FPR_HI_LO_trace_calls_prefix_triples'],100)
 def test_04_SDK32_full_source_and_effective_controls(self):
  q=native.main();self.assertEqual(set(q['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==196608 and v['SDK32']and v['UBSan']and v['strict_aliasing']and v['all_named_fields_and_typed_locals_compared']for v in q['profiles'].values()));self.assertEqual(len(q['effective_output_comparison_controls']),6)
 def test_05_both_padders_independent_bindings_and_negatives(self):
  q=qualification.main();self.assertTrue(q['both_padders_byte_exact']);self.assertEqual((q['guards'],q['insertions'],q['omissions']),(0,0,0));self.assertEqual(q['GNU_links'],12);self.assertEqual(q['guest_rebase_runs'],96);self.assertEqual(q['oversized_body_comparison_rejections'],2);self.assertEqual(q['effective_wrong_word_or_binding_controls'],4)
if __name__=='__main__':unittest.main(verbosity=2)
