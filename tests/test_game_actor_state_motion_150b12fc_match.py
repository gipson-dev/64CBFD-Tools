"""Five gates for the complete actor state-motion callback."""
import unittest
from tools.experiments import game_actor_state_motion_150b12fc_match as p
from tools.experiments import game_actor_state_motion_150b12fc_qualification as q
from tools.tests import game_actor_state_motion_150b12fc_guest as g
from tools.tests import game_actor_state_motion_150b12fc_native as n
class ActorStateMotion(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],318);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],[{'index': 5459, 'before': 'D_8009F8C0', 'after': 'D_800964C0'}, {'index': 5460, 'before': 'D_800964C0', 'after': 'D_8009F8C0'}]);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_instructions_and_independent_guest_semantics(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],1056);self.assertTrue(v['padded_retail_complete_identity']);self.assertTrue(v['independent_public_effects_arguments_and_observations_equal']);self.assertTrue(v['padded_retail_all_private_bytes_and_registers_equal']);self.assertFalse(v['raw_private_or_fault_identity_claim']);self.assertEqual(v['unexecuted_original_words'],[57])
 def test_03_fault_prefixes_and_actual_dispatch_window(self):
  v=g.faults();self.assertEqual(v['padded_retail_full_state_and_dispatched_access_prefix_triples'],125);v=g.callers();self.assertEqual(v['actual_complete_dispatch_window_words'],14);self.assertEqual(v['callback_table_index'],7);self.assertEqual(v['cases_per_stream'],45);self.assertEqual((v['called_cases'],v['disabled_cases'],v['null_entry_cases']),(15,15,15));self.assertTrue(v['all_four_streams_arguments_state_and_boundary_equal']);self.assertTrue(v['post_callback_actor_kind_reload_verified']);self.assertFalse(v['whole_1504A730_execution_claim'])
 def test_04_SDK32_native_C_and_effective_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==256 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['all_public_and_guard_bytes_compared']for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),10);self.assertTrue(all(x['comparison_exit']in(10,11,12,13,14)for x in v['effective_source_controls']));self.assertEqual(v['excluded_guest_only_cases'],{'public_alias_cases':768,'nonfinite_float_cases':32})
 def test_05_independent_proof_guards_and_rebases(self):
  v=q.main();self.assertEqual((v['guards'],v['insertions'],v['omissions']),(98,0,0));self.assertEqual(v['effective_failclosed_word_or_binding_controls'],218);self.assertEqual(v['GNU_target_links'],12);self.assertEqual(v['guest_rebase_runs'],96);self.assertEqual(len(v['proof_controls']['negative_controls']),9);self.assertTrue(v['proof_controls']['FP12_FP14_alpha_rename_accepted']);self.assertTrue(v['proof_controls']['first_LHU_to_LH_equivalence_accepted']);self.assertTrue(v['independent_symbolic_proof']['independent_public_memory_and_call_states_equal'])
if __name__=='__main__':unittest.main(verbosity=2)
