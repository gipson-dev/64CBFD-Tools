"""Five acceptance gates for the complete ground-burst death callback."""
import unittest
from tools.experiments import game_ground_burst_callback_150df334_match as p
from tools.experiments import game_ground_burst_callback_150df334_qualification as q
from tools.tests import game_ground_burst_callback_150df334_guest as g
from tools.tests import game_ground_burst_callback_150df334_native as n
class GroundBurstCallback(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],284);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],[]);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_instructions_and_independent_guest_semantics(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],272);self.assertTrue(v['padded_retail_complete_identity']);self.assertTrue(v['independent_public_effects_and_escaped_buffer_observations_equal']);self.assertTrue(v['padded_retail_all_private_bytes_and_saved_registers_equal']);self.assertTrue(v['raw_private_address_relation_only']);self.assertEqual(v['unexecuted_original_words'],[])
 def test_03_fault_prefixes_and_complete_actual_dispatcher(self):
  v=g.faults();self.assertEqual(v['padded_retail_full_state_and_dispatched_word_access_prefix_triples'],157);self.assertFalse(v['raw_private_or_fault_identity_claim']);v=g.callers();self.assertEqual(v['complete_original_dispatcher_words'],45);self.assertEqual(v['death_callback_table_index'],8);self.assertEqual(v['update_callback_index'],-1);self.assertEqual(v['cases_per_stream'],15);self.assertEqual(v['final_retirement_cases'],15);self.assertTrue(v['full_caller_returns_and_effects_equal'])
 def test_04_SDK32_native_C_and_effective_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==272 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['complete_public_and_guard_bytes_compared']for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),7);self.assertTrue(all(x['comparison_exit']in(10,11,12,13)for x in v['effective_source_controls']));self.assertEqual(v['excluded_uninitialized_ground_cases'],192);self.assertEqual(v['initialized_ground_supplement_cases'],192)
 def test_05_independent_proof_guards_and_rebases(self):
  v=q.main();self.assertEqual((v['guards'],v['insertions'],v['omissions']),(98,2,3));self.assertEqual(v['effective_failclosed_word_or_binding_controls'],206);self.assertEqual(v['GNU_target_links'],12);self.assertEqual(v['guest_rebase_runs'],64);self.assertEqual(len(v['proof_controls']['negative_controls']),8);self.assertTrue(v['proof_controls']['harmless_temporary_register_rename_accepted']);self.assertTrue(v['independent_symbolic_proof']['ordered_public_reads_and_calls_equal'])
if __name__=='__main__':unittest.main(verbosity=2)
