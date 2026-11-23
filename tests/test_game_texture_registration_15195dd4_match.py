"""Five gates for direct texture registration and its retail first-miss path."""
import unittest
from tools.experiments import game_texture_registration_15195dd4_match as p
from tools.experiments import game_texture_registration_15195dd4_qualification as q
from tools.tests import game_texture_registration_15195dd4_guest as g
from tools.tests import game_texture_registration_15195dd4_native as n
class TextureRegistration(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],370);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],p.MANIFEST['metadata_permuted_records']);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_all_instructions_and_independent_guest_semantics(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],816);self.assertTrue(v['complete_state_and_access_trace_equal']);self.assertTrue(v['independent_public_semantics_and_return_equal']);self.assertEqual(v['guest_only_uninitialized_first_miss_returns'],122);self.assertFalse(v['unexecuted_target_words'])
 def test_03_full_fault_prefixes_and_actual_owner_relay(self):
  v=g.faults();self.assertEqual(v['full_state_access_prefix_triples'],177);v=g.callers();self.assertEqual(v['original_owner_relay_words'],16);self.assertEqual(v['cases_per_stream'],102);self.assertTrue(v['seven_full_word_arguments_and_full_return'])
 def test_04_actual_SDK32_native_C_and_effective_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==694 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['typed_link_and_key_objects']for x in v['profiles'].values()));self.assertEqual(len(v['effective_output_comparison_controls']),8);self.assertEqual(v['excluded_first_miss_uninitialized_C_cases'],122)
 def test_05_direct_bindings_and_effective_first_miss_control(self):
  v=q.main();self.assertTrue(v['raw_is_exact_retail_words_and_bindings']);self.assertTrue(v['both_padders_byte_exact']);self.assertEqual((v['guards'],v['insertions'],v['omissions']),(0,0,0));self.assertEqual(v['GNU_target_links'],12);self.assertEqual(v['guest_rebase_runs'],96);self.assertTrue(v['effective_zero_initializer_guest_control']);self.assertEqual(v['effective_wrong_word_or_binding_controls'],4)
if __name__=='__main__':unittest.main(verbosity=2)
