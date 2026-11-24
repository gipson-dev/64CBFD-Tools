"""Five fresh direct scene-view qualification gates."""
import unittest
from tools.experiments import game_scene_view_setup_150fca30_match as p
from tools.experiments import game_scene_view_setup_150fca30_qualification as q
from tools.tests import game_scene_view_setup_150fca30_guest as g
from tools.tests import game_scene_view_setup_150fca30_native as n
class SceneViewSetup(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],328);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],p.MANIFEST['metadata_permuted_records']);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_instructions_and_independent_guest_semantics(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],182);self.assertTrue(v['direct_complete_identity']);self.assertTrue(v['independent_public_semantics_equal']);self.assertTrue(v['unwritten_packet_bytes_preserved']);self.assertTrue(v['live_count_mutations']);self.assertEqual(v['unexecuted_original_words'],[]);self.assertFalse(v['void_result_compared'])
 def test_03_fault_prefixes_bounded_caller_and_original_copy(self):
  v=g.faults();self.assertEqual(v['four_stream_full_state_and_dispatched_access_prefixes'],164);v=g.callers();self.assertEqual((v['original_bounded_caller_words'],v['cases_per_stream']),(4,4));self.assertTrue(v['continuation_value_from_caller_stack']);self.assertFalse(v['complete_dispatcher_claim']);v=g.connected();self.assertEqual((v['cases_per_stream'],v['full_eight_byte_copy_cases']),(40,4));self.assertTrue(v['seeded_unwritten_bytes_copied']);self.assertFalse(v['full_transitive_provider_claim'])
 def test_04_SDK32_native_C_and_effective_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==182 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['actual_eight_byte_memcpy']and not x['portable_unwritten_byte_identity_claim']for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),13);self.assertTrue(all(x['comparison_exit']in range(10,17)for x in v['effective_source_controls']));self.assertTrue(v['no_signal_or_UBSan_trap_counted']);self.assertTrue(v['callback_address_codec_verified'])
 def test_05_direct_identity_corruption_visibility_and_rebases(self):
  v=q.main();self.assertEqual((v['guards'],v['insertions'],v['omissions']),(0,0,0));self.assertEqual(v['effective_wrong_word_or_binding_controls'],224);self.assertEqual(v['GNU_target_links'],12);self.assertEqual(v['guest_rebase_runs'],96);self.assertEqual((v['source_words_covered'],v['source_binding_sites_covered']),(100,12));self.assertTrue(v['raw_is_exact_retail_words_and_bindings'])
if __name__=='__main__':unittest.main(verbosity=2)
