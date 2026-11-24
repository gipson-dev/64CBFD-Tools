"""Five fresh gates for the descriptor matrix-history restoration."""
import unittest
from tools.experiments import game_descriptor_matrix_history_15188f84_match as p
from tools.experiments import game_descriptor_matrix_history_15188f84_qualification as q
from tools.tests import game_descriptor_matrix_history_15188f84_guest as g
from tools.tests import game_descriptor_matrix_history_15188f84_native as n
class DescriptorMatrixHistory(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual((self.report['changed_bytes'],self.report['exclusions']),(330,0));self.assertEqual(self.report['metadata_permuted_records'],p.MANIFEST['metadata_permuted_records']);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_instructions_and_independent_guest_semantics(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],392);self.assertTrue(v['independent_public_effects_calls_and_live_observations_equal']);self.assertTrue(v['padded_retail_all_private_bytes_and_registers_equal']);self.assertEqual(v['unexecuted_original_words'],[]);self.assertFalse(v['raw_private_or_fault_identity_claim']);self.assertFalse(v['void_result_compared'])
 def test_03_fault_prefixes_original_JALR_and_original_bcopy(self):
  v=g.faults();self.assertEqual(v['padded_retail_full_state_and_dispatched_access_prefix_triples'],143);v=g.callers();self.assertEqual((v['original_JALR_window_words'],v['cases_per_stream'],v['actual_table_slot']),(9,4,1));self.assertTrue(v['continuation_timer_and_opacity_verified']);self.assertFalse(v['complete_dispatcher_claim']);v=g.connected();self.assertEqual((v['cases_per_stream'],v['actual_original_bcopy_words']),(24,196));self.assertTrue(v['overlap_both_directions_and_all_byte_alignments'])
 def test_04_SDK32_native_callback_and_effective_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==324 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['compatible_callback_type']for x in v['profiles'].values()));self.assertEqual(v['guest_only_unaligned_or_partial_matrix_alias_cases'],68);self.assertEqual(len(v['effective_source_controls']),12);self.assertTrue(v['no_signal_or_UBSan_trap_counted']);self.assertTrue(all(x['comparison_exit']in(10,11,12,13,14)for x in v['effective_source_controls']))
 def test_05_independent_lifetimes_strict_guards_and_rebases(self):
  v=q.main();self.assertEqual((v['guards'],v['identity_guards'],v['insertions'],v['omissions']),(101,83,0,0));self.assertEqual(v['effective_failclosed_word_or_binding_controls'],232);self.assertEqual((v['GNU_target_links'],v['guest_rebase_runs']),(12,96));proof=v['independent_instruction_relation'];self.assertTrue(proof['all_role_reads_dominated_by_definitions']);self.assertTrue(proof['incoming_registers_saved_before_overwrite']);self.assertTrue(proof['named_saved_homes_and_epilogue_identical']);self.assertFalse(proof['private_addresses_escape']);self.assertTrue(proof['independent_commutative_positive_control_accepted']);self.assertEqual(len(proof['structural_controls']),4)
if __name__=='__main__':unittest.main(verbosity=2)
