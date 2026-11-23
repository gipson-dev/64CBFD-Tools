"""Five gates for the complete direct effect-update callback."""
import unittest
from tools.experiments import game_linked_effect_update_151d1138_match as p
from tools.experiments import game_linked_effect_update_151d1138_qualification as q
from tools.tests import game_linked_effect_update_151d1138_guest as g
from tools.tests import game_linked_effect_update_151d1138_native as n
class LinkedEffectUpdate(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],361);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['metadata_permuted_records'],[]);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_direct_instructions_and_independent_semantics(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],884);self.assertTrue(v['complete_direct_instruction_and_binding_identity']);self.assertTrue(v['independent_public_memory_calls_and_float_gates_equal']);self.assertTrue(v['all_guest_private_bytes_and_saved_registers_equal']);self.assertEqual(v['unexecuted_original_words'],[115])
 def test_03_fault_prefixes_and_complete_actual_dispatcher(self):
  v=g.faults();self.assertEqual(v['full_state_and_dispatched_word_access_prefix_quadruples'],224);v=g.callers();self.assertEqual(v['complete_original_dispatcher_words'],45);self.assertEqual(v['cases_per_stream'],81);self.assertEqual(v['callback_table_index'],95);self.assertEqual(v['pre_callback_lifetime_underflow_cases'],10);self.assertEqual(v['final_retirement_cases'],15);self.assertTrue(v['all_four_streams_and_full_caller_return_equal'])
 def test_04_SDK32_native_C_and_effective_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==776 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['all_backing_and_guard_bytes_compared']for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),9);self.assertEqual(v['excluded_guest_only_cases'],{'owner_actor_alias':31,'signaling_NaN_float_return':77})
 def test_05_direct_bindings_rebases_and_late_reload(self):
  v=q.main();self.assertEqual((v['guards'],v['insertions'],v['omissions']),(0,0,0));self.assertEqual(v['effective_wrong_word_or_binding_controls'],260);self.assertEqual(v['GNU_target_links'],12);self.assertEqual(v['guest_rebase_runs'],96);self.assertTrue(v['effective_stale_distance_guest_control'])
if __name__=='__main__':unittest.main(verbosity=2)
