"""Five direct source, ABI, caller, fault and linked image adoption gates."""
import unittest
from tools.experiments import game_opposed_effect_spawn_150bef7c_match as packet
from tools.experiments import game_opposed_effect_spawn_150bef7c_qualification as qualification
from tools.tests import game_opposed_effect_spawn_150bef7c_guest as guest
from tools.tests import game_opposed_effect_spawn_150bef7c_native as native
class OpposedEffectSpawn(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_complete_Make_and_independent_strict_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],295);self.assertEqual(self.report['exclusions'],0);self.assertFalse(self.report['metadata_permuted_records']);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_complete_target_and_actual_factory_chain(self):
  q=guest.main();self.assertEqual(q['direct_cases_per_stream'],300);self.assertEqual(q['complete_factory_chain_cases_per_stream'],400);self.assertEqual(len(q['streams']),3);self.assertFalse(q['unexecuted_target_words']);self.assertEqual((q['factory_words'],q['allocator_wrapper_words']),(125,28))
 def test_03_actual_caller_windows_and_full_fault_prefixes(self):
  q=guest.callers();self.assertEqual(q['real_4_word_caller_windows'],2);self.assertEqual(q['cases_per_stream'],300);q=guest.faults();self.assertEqual(q['full_memory_GPR_FPR_HI_LO_trace_calls_prefix_triples'],548)
 def test_04_SDK32_full_wrapper_and_effective_controls(self):
  q=native.main();self.assertEqual(set(q['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==196608 and v['SDK32']and v['UBSan']and v['strict_aliasing']and v['all_49_typed_arguments_compared']for v in q['profiles'].values()));self.assertEqual(len(q['effective_output_comparison_controls']),6)
 def test_05_both_padders_independent_J26_bindings_and_negatives(self):
  q=qualification.main();self.assertTrue(q['both_padders_byte_exact']);self.assertEqual((q['guards'],q['insertions'],q['omissions']),(0,0,0));self.assertEqual(q['GNU_links'],12);self.assertEqual(q['guest_rebase_runs'],168);self.assertEqual(q['oversized_body_comparison_rejections'],2);self.assertEqual(q['effective_wrong_word_or_binding_controls'],4)
if __name__=='__main__':unittest.main(verbosity=2)
