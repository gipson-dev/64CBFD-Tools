"""Closed121word timed-target qualification; no assembly normalization."""
import unittest
from tools.experiments import game_billboard_target_update_1514a19c_match as packet,game_billboard_target_update_1514a19c_make as make,game_billboard_target_update_1514a19c_image as image
from tools.tests import game_billboard_target_update_1514a19c_guest as guest,game_billboard_target_update_1514a19c_native as native,game_billboard_target_update_1514a19c_callers as callers,game_billboard_target_update_1514a19c_boundaries as boundaries,game_billboard_target_update_1514a19c_helpers as helpers
class BillboardTargetTests(unittest.TestCase):
 def test_01_direct_C_complete_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors']),(121,32,0,35));self.assertTrue(q['raw_byte_exact']);self.assertTrue(q['both_complete_padders_equal']);self.assertEqual(make.main()['new_diagnostics'],0);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_ordered_FP_private_faults_and_original_RNG(self):
  q=guest.main();self.assertEqual((q['cases_per_stream'],q['streams'],q['executed_words'],q['fault_prefix_quintuples']),(1096,5,121,144));self.assertEqual(len(q['effective_controls']),6);self.assertTrue(q['all_literal_full_private_states_equal']);h=helpers.main();self.assertEqual((h['cases_per_stream'],h['streams']),(384,2));self.assertTrue(h['all43_helper_words_executed']);self.assertTrue(h['actual_helpers_only_write_seed'])
 def test_03_words_bindings_carries_and_jump_regions(self):
  q=boundaries.main();self.assertEqual((q['all_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links'],q['guest_rebase_runs']),(242,40,20,100));self.assertTrue(q['signed_HI16_LO16_carry_boundaries']);self.assertEqual(q['oversized'],['visible overflow','rejected'])
 def test_04_complete_original_dispatcher_and_boolean_return(self):
  q=callers.main();self.assertEqual((q['original_parent_words_pinned'],q['original_parent_words_executed'],q['cases_per_stream'],q['connected_children_per_stream']),(195,115,1024,256));self.assertEqual(q['table_index'],4);self.assertTrue(q['production_parent_all195words_retail_exact']);self.assertTrue(q['actor_pointer_and_boolean_return_ABI'])
 def test_05_native_actual_C_and_effective_controls(self):
  q=native.main();self.assertEqual(len(q['effective_controls']),9);self.assertEqual(q['cases_per_profile'],8192);self.assertTrue(q['actual_C_byte_pointer_ABI_and_typed_344byte_prefix_72byte_targets']);self.assertTrue(q['strict_aliasing_UBSan_traps_LTO_types']);self.assertTrue(q['no_signal_or_trap_counted_as_control'])
if __name__=='__main__':unittest.main()
