"""Five bounded adoption gates for live resource-cache cleanup."""
import unittest
from tools.experiments import game_resource_cache_sweep_15114a1c_match as p
from tools.experiments import game_resource_cache_sweep_15114a1c_qualification as q
from tools.tests import game_resource_cache_sweep_15114a1c_guest as g
from tools.tests import game_resource_cache_sweep_15114a1c_native as n
class ResourceCacheSweep(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_whole_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['exclusions'],0);self.assertEqual(self.report['predicted_ELF_sha256'],p.MANIFEST['predicted_ELF_sha256']);self.assertEqual(self.report['changed_bytes'],p.MANIFEST['changed_bytes']);self.assertTrue(self.report['protected_data_audit']['exact']);self.assertEqual(self.report['protected_data_audit']['bytes'],189088)
 def test_02_symbolic_loop_and_guest_public_contract(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],576);self.assertEqual(v['streams'],4);self.assertEqual(v['symbolic']['entry_paths'],2);self.assertEqual(v['symbolic']['inductive_iteration_paths'],16);self.assertTrue(v['independent_public_memory_and_ordered_calls_equal']);self.assertTrue(v['normalized_full_register_private_memory_and_trace_equal']);self.assertEqual(v['unexecuted_original_words'],[51,68])
 def test_03_normalized_access_prefixes_and_literal_caller(self):
  v=g.faults();self.assertGreater(v['normalized_complete_access_prefix_triples'],200);self.assertFalse(v['raw_C_fault_identity_claimed']);v=g.callers();self.assertEqual(v['cases_per_stream'],48);self.assertEqual(v['actual_caller_window_address'],'0x15018ccc');self.assertTrue(v['complete_caller_owner_code_bindings_and_production_object_unchanged'])
 def test_04_defined_native_SDK32_and_semantic_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==576 and x['SDK32']and x['UBSan']and x['strict_aliasing']and x['typed_resource_and_pointer_arrays']for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),7)
 def test_05_closed_guards_relocations_and_independent_proof_controls(self):
  v=q.main();self.assertEqual((v['guards'],v['insertions'],v['omissions']),(92,2,0));self.assertEqual(v['effective_word_and_binding_guard_rejections'],220);self.assertEqual(v['source_binding_sites_covered'],18);self.assertEqual(v['GNU_target_links'],12);self.assertEqual(v['guest_rebase_runs'],64);self.assertEqual(len(v['effective_symbolic_controls']),15);self.assertTrue(v['independent_temporary_reallocation_accepted'])
if __name__=='__main__':unittest.main(verbosity=2)
