"""Five qualification gates for the complete scene-node render pass."""
import unittest
from tools.experiments import game_scene_node_render_15030e08_match as p
from tools.experiments import game_scene_node_render_15030e08_qualification as q
from tools.tests import game_scene_node_render_15030e08_guest as g
from tools.tests import game_scene_node_render_15030e08_native as n
class SceneNodeRender(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],p.MANIFEST['expected_changed_bytes']);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],p.MANIFEST['metadata_permuted_records']);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_instructions_and_independent_guest_semantics(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],1725);self.assertTrue(v['padded_retail_complete_identity']);self.assertTrue(v['independent_public_effects_arguments_observations_cursor_equal']);self.assertTrue(v['padded_retail_all_private_bytes_and_registers_equal']);self.assertFalse(v['raw_private_or_fault_identity_claim']);self.assertEqual(v['unexecuted_original_words'],[64,76])
 def test_03_fault_prefixes_and_actual_caller_window(self):
  v=g.faults();self.assertEqual(v['padded_retail_full_state_and_dispatched_access_prefix_triples'],184);v=g.callers();self.assertEqual(v['actual_complete_caller_window_words'],29);self.assertEqual(v['cases_per_stream'],42);self.assertEqual((v['called_cases'],v['bypassed_cases']),(21,21));self.assertTrue(v['all_three_mode_call_sites_executed']);self.assertTrue(v['all_four_streams_arguments_public_state_and_boundary_equal']);self.assertTrue(v['post_call_cursor_used_for_two_display_list_stores']);self.assertFalse(v['whole_1502BAD0_execution_claim'])
 def test_04_SDK32_native_C_and_effective_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==1501 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['all_public_and_guard_bytes_compared']for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),10);self.assertTrue(all(x['comparison_exit']in(10,11,12,13,14)for x in v['effective_source_controls']));self.assertEqual(v['excluded_node_actor_overlap_guest_only_cases'],224)
 def test_05_independent_proof_guards_and_rebases(self):
  v=q.main();self.assertEqual((v['guards'],v['insertions'],v['omissions']),(100,0,1));self.assertEqual(v['effective_failclosed_word_or_binding_controls'],210);self.assertEqual(v['GNU_target_links'],12);self.assertEqual(v['guest_rebase_runs'],96);self.assertEqual(len(v['proof_controls']['negative_controls']),14);self.assertTrue(v['proof_controls']['complete_T0_T1_alpha_rename_accepted']);self.assertTrue(v['independent_symbolic_proof']['independent_initial_dead_roles_and_provider_register_home_clobbers']);self.assertEqual(v['independent_symbolic_proof']['arbitrary_loop_iteration']['paths'],28)
if __name__=='__main__':unittest.main(verbosity=2)
