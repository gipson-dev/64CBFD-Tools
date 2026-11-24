"""Five fresh owner, linked-image, guest, native and guard gates."""
import unittest
from tools.experiments import game_particle_payload_150b3f5c_match as p
from tools.experiments import game_particle_payload_150b3f5c_qualification as q
from tools.tests import game_particle_payload_150b3f5c_guest as g
from tools.tests import game_particle_payload_150b3f5c_native as n
class ParticlePayload(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  v=self.report;self.assertTrue(v['strict_predicted_ELF_equal']);self.assertEqual(v['changed_bytes'],296);self.assertEqual(v['exclusions'],0);self.assertEqual(v['metadata_permuted_records'],p.MANIFEST['metadata_permuted_records']);self.assertTrue(v['protected_data_audit']['exact']);self.assertEqual(v['protected_data_audit']['bytes'],189088);self.assertTrue(v['all_9_reference_neighbors_fixed'])
 def test_02_complete_guest_and_seeded_padding(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],156);self.assertTrue(v['all_public_private_bytes_registers_calls_and_copied_bytes_equal']);self.assertTrue(v['raw_trace_equal_after_proved_store_commutation']);self.assertTrue(v['normalized_stream_complete_trace_identity']);self.assertEqual(v['unexecuted_original_words'],[]);self.assertTrue(v['unwritten_request_and_payload_bytes_preserved']);self.assertFalse(v['raw_fault_prefix_identity_claim'])
 def test_03_prefixes_factory_memcpy_and_caller_windows(self):
  v=g.faults();self.assertEqual(v['padded_retail_full_state_prefix_triples'],139);self.assertTrue(v['raw_prefix_excluded']);self.assertFalse(v['portable_C_fault_claim']);v=g.connected();self.assertEqual((v['cases_per_stream'],v['original_factory_words'],v['original_memcpy_words']),(7,115,11));self.assertFalse(v['original_RNG_or_audio_implementation_claim']);v=g.callers();self.assertEqual([x['original_words']for x in v['windows']],[4,11]);self.assertTrue(all(x['cases_per_stream']==4 for x in v['windows']));self.assertFalse(v['enclosing_full_function_claim']);self.assertFalse(v['caller_epilogue_execution_claim'])
 def test_04_native_and_effective_source_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==144 and x['SDK32']and x['UBSan']and x['strict_aliasing']for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),16);self.assertTrue(all(x['comparison_exit']in range(10,23)for x in v['effective_source_controls']));self.assertTrue(v['no_signal_or_UBSan_trap_counted']);self.assertTrue(v['unwritten_padding_not_compared'])
 def test_05_independent_store_proof_guards_and_GNU(self):
  v=q.main();self.assertEqual((v['guards'],v['identity_guards'],v['insertions'],v['omissions']),(99,97,0,0));self.assertEqual(v['effective_failclosed_word_or_binding_controls'],212);self.assertEqual((v['GNU_target_links'],v['guest_rebase_runs']),(12,96));self.assertEqual((v['source_words_covered'],v['source_binding_sites_covered']),(99,7));self.assertEqual(len(v['independent_instruction_relation']['structural_controls']),4);self.assertFalse(v['independent_instruction_relation']['raw_fault_prefix_identity_claim'])
if __name__=='__main__':unittest.main(verbosity=2)
