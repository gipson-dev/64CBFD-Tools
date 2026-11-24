"""Five fresh menu transition source, owner, image and behavior gates."""
import unittest
from tools.experiments import game_menu_transition_init_151e53e8_match as p
from tools.experiments import game_menu_transition_init_151e53e8_qualification as q
from tools.tests import game_menu_transition_init_151e53e8_guest as g
from tools.tests import game_menu_transition_init_151e53e8_native as n
class MenuTransitionInitializer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],328);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],p.MANIFEST['metadata_permuted_records']);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088);self.assertTrue(self.report['all_59_reference_neighbors_fixed'])
 def test_02_complete_guest_identity_and_public_semantics(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],246);self.assertTrue(v['direct_complete_identity']);self.assertTrue(v['independent_public_semantics_equal']);self.assertTrue(v['signed_rows_and_count']);self.assertTrue(v['full_word_defer']);self.assertTrue(v['live_count_and_menu_aliases']);self.assertEqual(v['unexecuted_original_words'],[]);self.assertFalse(v['void_result_compared']);self.assertFalse(v['opaque_helper_implementation_claim'])
 def test_03_fault_prefixes_and_three_original_caller_windows(self):
  v=g.faults();self.assertEqual(v['four_stream_full_state_and_dispatched_access_prefixes'],159);self.assertFalse(v['portable_C_fault_claim']);v=g.callers();self.assertEqual([x['original_words']for x in v['windows']],[4,4,9]);self.assertTrue(all(x['cases_per_stream']==4 for x in v['windows']));self.assertTrue(v['full_script_argument']);self.assertTrue(v['void_target_result_ignored']);self.assertFalse(v['complete_dispatcher_claim']);self.assertTrue(v['second_helper_opaque'])
 def test_04_native_SDK32_and_effective_source_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==240 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['real_actor_views']for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),11);self.assertTrue(all(x['comparison_exit']in range(10,19)for x in v['effective_source_controls']));self.assertTrue(v['no_signal_or_UBSan_trap_counted']);self.assertTrue(v['callback_address_codec_verified'])
 def test_05_direct_corruption_visibility_and_independent_GNU_links(self):
  v=q.main();self.assertEqual((v['guards'],v['insertions'],v['omissions']),(0,0,0));self.assertEqual(v['effective_wrong_word_or_binding_controls'],276);self.assertEqual(v['GNU_target_links'],12);self.assertEqual(v['guest_rebase_runs'],96);self.assertEqual((v['source_words_covered'],v['source_binding_sites_covered']),(101,37));self.assertTrue(v['raw_is_exact_retail_words_and_bindings'])
if __name__=='__main__':unittest.main(verbosity=2)
