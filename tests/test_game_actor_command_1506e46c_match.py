"""Five gates for the actor command resolver and its three actual callers."""
import unittest
from tools.experiments import game_actor_command_1506e46c_match as p
from tools.experiments import game_actor_command_1506e46c_qualification as q
from tools.tests import game_actor_command_1506e46c_guest as g
from tools.tests import game_actor_command_1506e46c_native as n
class ActorCommand(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],299);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],p.MANIFEST['metadata_permuted_records']);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_instructions_and_independent_guest_semantics(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],2124);self.assertTrue(v['padded_retail_complete_identity']);self.assertTrue(v['independent_public_effects_calls_observations_results_equal']);self.assertTrue(v['padded_retail_all_private_bytes_and_registers_equal']);self.assertFalse(v['raw_private_or_fault_identity_claim']);self.assertEqual(v['unexecuted_original_words'],[35])
 def test_03_fault_prefixes_and_actual_original_callers(self):
  v=g.faults();self.assertEqual(v['padded_retail_full_state_and_dispatched_access_prefix_triples'],89);v=g.callers();self.assertEqual(v['actual_original_callers'],3);self.assertEqual(v['words_per_caller'],16);self.assertEqual(v['cases_per_stream'],24);self.assertEqual((v['post_action_called_cases'],v['post_action_bypassed_cases']),(10,14));self.assertTrue(v['all_four_streams_complete_caller_state_and_arguments_equal']);self.assertTrue(v['caller_boolean_result_consumption_verified']);self.assertFalse(v['transitive_provider_execution_claim'])
 def test_04_SDK32_native_C_aliases_and_effective_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==2096 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['all_public_and_guard_bytes_compared']and x['full_row_outside_window_canaries']for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),12);self.assertTrue(all(x['comparison_exit']in(10,11,12,13,14)for x in v['effective_source_controls']));self.assertEqual(v['excluded_pointer_word_object_alias_guest_only_cases'],28)
 def test_05_independent_proof_guards_and_rebases(self):
  v=q.main();self.assertEqual((v['guards'],v['insertions'],v['omissions']),(95,8,3));self.assertEqual(v['effective_failclosed_word_or_binding_controls'],204);self.assertEqual(v['GNU_target_links'],12);self.assertEqual(v['guest_rebase_runs'],96);self.assertEqual(len(v['proof_controls']['negative_controls']),20);self.assertTrue(v['proof_controls']['complete_T0_T1_alpha_rename_accepted']);self.assertTrue(v['proof_controls']['independent_index_options_private_home_swap_accepted']);self.assertTrue(v['independent_symbolic_proof']['independent_dead_registers_and_provider_home_clobbers']);self.assertEqual(v['independent_symbolic_proof']['paths'],68)
if __name__=='__main__':unittest.main(verbosity=2)
