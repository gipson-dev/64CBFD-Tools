"""Five source, ABI, guest/native, caller and independent image gates."""
import unittest
from tools.experiments import game_indexed_matrix_renderer_15168c4c_match as packet
from tools.experiments import game_indexed_matrix_renderer_15168c4c_qualification as qualification
from tools.tests import game_indexed_matrix_renderer_15168c4c_guest as guest
from tools.tests import game_indexed_matrix_renderer_15168c4c_native as native
from tools.tests import game_indexed_matrix_renderer_15168c4c_callers as callers
class IndexedMatrixRenderer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_complete_owner_Make_and_literal_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['changed_bytes'],382);self.assertEqual(self.report['exclusions'],0);self.assertFalse(self.report['metadata_permuted_records']);self.assertEqual(packet.sha(packet.ROOT/'conker/retail_word_patches.us.csv'),packet.MANIFEST['guards_sha256'])
 def test_02_complete_direct_guest_and_private_residue(self):
  q=guest.main();self.assertEqual(q['cases_per_stream'],864);self.assertEqual(q['guest_private_residue_cases_per_stream'],32);self.assertEqual(set(q['streams']),{'raw','padded','retail'});self.assertFalse(q['unexecuted_words']);self.assertEqual(q['complete_actual_mode_helper_words'],34)
 def test_03_actual_SDK32_and_effective_source_controls(self):
  q=native.main();self.assertEqual(set(q['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(v['cases']==864 and v['SDK32']and v['UBSan']and v['strict_aliasing']for v in q['profiles'].values()));self.assertEqual(len(q['effective_source_controls']),18);self.assertTrue(q['record_output_cache_canaries'])
 def test_04_actual_constructor_and_complete_parent(self):
  q=callers.main();self.assertEqual(q['constructor']['cases'],192);self.assertEqual(q['constructor']['constructed_then_drawn_cases'],48);self.assertFalse(q['constructor']['constructor_unexecuted']);self.assertEqual(q['constructor']['actual_upstream_guest_residue_modes'],[0]);self.assertEqual(q['parent']['cases_per_stream'],336);self.assertEqual(q['parent']['leaf_invocations_per_stream'],480);self.assertEqual(q['parent']['private_mode_two_to_zero_carry_cases'],24);self.assertTrue(q['parent']['all_leaf_return_boundaries_checked'])
 def test_05_both_padders_carry_faults_and_real_mode_zero(self):
  q=qualification.main();self.assertEqual(q['objects']['guards'],0);self.assertTrue(q['objects']['raw_direct_byte_exact']);self.assertEqual(q['boundaries']['GNU_links'],12);self.assertEqual(q['boundaries']['effective_wrong_word_and_binding_output_controls'],4);self.assertEqual(q['faults']['full_raw_padded_retail_access_prefix_triples'],337);self.assertEqual(q['rebases']['guest_rebase_runs'],96);self.assertEqual(q['mode_control']['effective_source_control'],'invented-mode-zero-default');self.assertTrue(q['upstream']['mode_zero_is_real_upstream_input'])
if __name__=='__main__':unittest.main(verbosity=2)
