"""Five fresh source, tables, whole-image, alias, caller and relocation gates."""
import unittest
from tools.experiments import game_base_color_output_1513137c_match as p
from tools.experiments import game_base_color_output_1513137c_qualification as q
from tools.tests import game_base_color_output_1513137c_guest as g
from tools.tests import game_base_color_output_1513137c_native as n
class BaseColorOutput(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.qualify()
 def test_01_actual_Make_and_independent_complete_image(self):
  v=self.report;self.assertTrue(v['strict_predicted_ELF_equal']);self.assertEqual(v['changed_bytes'],260);self.assertEqual(v['exclusions'],0);self.assertEqual(v['metadata_permuted_records'],p.MANIFEST['metadata_permuted_records']);self.assertTrue(v['protected_data_audit']['exact']);self.assertEqual(v['protected_data_audit']['bytes'],189088);self.assertTrue(v['all_30_reference_neighbors_fixed'])
 def test_02_all_modes_aliases_and_private_table_correspondence(self):
  v=g.main();self.assertEqual(v['cases_per_stream'],5888);self.assertTrue(v['all_256_selector_bytes']);self.assertTrue(v['distinct_private_and_protected_tables']);self.assertTrue(v['all_registers_and_all_memory_equal']);self.assertTrue(v['HI_LO_products_independently_verified']);self.assertTrue(v['all_102_words_visited']);self.assertFalse(v['native_void_result_claim'])
 def test_03_prefixes_and_complete_original_wrapper(self):
  v=g.faults();self.assertEqual(v['normalized_retail_prefix_triples'],372);self.assertTrue(v['raw_private_table_prefix_excluded']);self.assertFalse(v['portable_C_fault_claim']);v=g.callers();self.assertEqual([x['original_window_words']for x in v['parent_windows']],[8,16]);self.assertTrue(all(x['cases_per_stream']==512 for x in v['parent_windows']));self.assertEqual((v['original_wrapper_words'],v['original_color_helper_words'],v['complete_wrapper_cases_per_stream']),(24,78,2048));self.assertTrue(v['all_nine_arguments_and_late_reloads_verified']);self.assertEqual(v['typed_wrapper_additional_matching_credit'],0);self.assertFalse(v['parent_full_function_claim'])
 def test_04_native_canvas_relay_and_observed_controls(self):
  v=n.main();self.assertEqual(set(v['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==5120 and x['complete_C_relay_cases']==2048 and x['SDK32']and x['strict_aliasing']and x['UBSan']and x['observed_control_comparison_bytes']==[1]*12 for x in v['profiles'].values()));self.assertEqual(len(v['effective_source_controls']),12);self.assertTrue(v['no_signal_or_UBSan_trap_counted']);self.assertTrue(v['void_result_not_compared'])
 def test_05_tables_corruption_visibility_and_GNU_carry(self):
  v=q.main();self.assertEqual((v['guards'],v['insertions'],v['omissions']),(2,0,0));self.assertEqual((v['whole_source_pin_controls'],v['failclosed_address_word_or_binding_controls'],v['non_address_word_corruption_visibility_controls']),(104,8,200));self.assertEqual(v['total_effective_word_or_binding_controls'],208);self.assertEqual((v['GNU_target_links'],v['guest_rebase_runs']),(16,96));self.assertEqual((v['source_words_covered'],v['source_binding_sites_covered']),(102,2));self.assertTrue(v['HI_carry_and_negative_LO_exercised']);self.assertEqual(v['table_provenance']['new_eight_entry_table_offset'],36);self.assertEqual(v['table_provenance']['instruction_order_patches'],0)
if __name__=='__main__':unittest.main(verbosity=2)
