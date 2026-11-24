"""Five fresh qualification gates for group actor restoration."""
import unittest
from tools.experiments import game_group_actor_restore_15022398_match as p
from tools.experiments import game_group_actor_restore_15022398_qualification as q
from tools.tests import game_group_actor_restore_15022398_guest as g
from tools.tests import game_group_actor_restore_15022398_native as n
class GroupActorRestore(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],311);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],p.MANIFEST['metadata_permuted_records']);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_instructions_and_independent_guest_semantics(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],764);self.assertTrue(v['padded_retail_complete_identity']);self.assertTrue(v['independent_public_effects_calls_observations_equal']);self.assertTrue(v['padded_retail_all_private_bytes_and_registers_equal']);self.assertFalse(v['raw_private_or_fault_identity_claim']);self.assertFalse(v['void_return_value_compared']);self.assertEqual(v['unexecuted_original_words'],[])
 def test_03_fault_prefixes_and_complete_original_caller(self):
  v=g.faults();self.assertEqual(v['padded_retail_full_state_and_dispatched_access_prefix_triples'],86);v=g.callers();self.assertEqual((v['words'],v['frame'],v['cases_per_stream']),(39,40,12));self.assertEqual((v['target_calls'],v['post_calls']),(25,25));self.assertTrue(v['live_count_shrink_and_growth']);self.assertTrue(v['all_four_streams_complete_caller_state_equal']);self.assertTrue(v['void_callback_result_ignored']);self.assertFalse(v['transitive_provider_execution_claim'])
 def test_04_SDK32_native_C_aliases_and_effective_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==648 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['all_public_and_guard_bytes_compared']and x['shared_record_rows']for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),14);self.assertTrue(all(x['comparison_exit']in(10,11,12,13)for x in v['effective_source_controls']));self.assertEqual(v['excluded_mixed_type_row_actor_alias_or_modular_negative_descriptor_cases_guest_only'],116);self.assertTrue(v['void_result_not_compared'])
 def test_05_independent_relation_guards_and_rebases(self):
  v=q.main();self.assertEqual((v['guards'],v['identity_guards'],v['insertions'],v['omissions']),(100,96,0,0));self.assertEqual(v['effective_failclosed_word_or_binding_controls'],236);self.assertEqual(v['GNU_target_links'],12);self.assertEqual(v['guest_rebase_runs'],96);proof=v['independent_instruction_relation'];self.assertEqual((proof['raw_home'],proof['retail_home'],proof['CFG_states_checked']),(40,44,84));self.assertTrue(proof['private_reloads_dominated_by_stores']);self.assertFalse(proof['private_addresses_escape']);self.assertTrue(proof['independent_unused_home_move_accepted']);self.assertTrue(proof['structural_controls_not_counted_as_semantic_source_controls']);self.assertEqual(len(proof['structural_controls']),3)
if __name__=='__main__':unittest.main(verbosity=2)
