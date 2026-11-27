import unittest
from tools.experiments import game_view_quad_flags_15149fd0_match as packet,game_view_quad_flags_15149fd0_make as make,game_view_quad_flags_15149fd0_image as image
from tools.tests import game_view_quad_flags_15149fd0_guest as guest,game_view_quad_flags_15149fd0_native as native,game_view_quad_flags_15149fd0_callers as callers,game_view_quad_flags_15149fd0_boundaries as boundaries
class ViewQuadTests(unittest.TestCase):
 def test_01_direct_C_complete_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors']),(115,72,0,35));self.assertTrue(q['raw_byte_exact']);self.assertTrue(q['both_complete_padders_equal']);self.assertEqual(make.main()['new_diagnostics'],0);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_ordered_FP_private_state_and_faults(self):
  q=guest.main();self.assertEqual((q['cases_per_stream'],q['streams'],q['executed_words'],q['fault_prefix_quintuples']),(1008,5,115,526));self.assertEqual(len(q['effective_controls']),7);self.assertTrue(q['all_literal_full_private_states_equal']);self.assertTrue(q['flag_stores_and_FP_products_interleaved_in_reference'])
 def test_03_words_bindings_carries_and_jump_regions(self):
  q=boundaries.main();self.assertEqual((q['all_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links'],q['guest_rebase_runs']),(230,14,20,100));self.assertTrue(q['signed_HI16_LO16_carry_boundaries']);self.assertEqual(q['oversized'],['visible overflow','rejected'])
 def test_04_complete_original_dispatcher_and_pointer_return(self):
  q=callers.main();self.assertEqual((q['original_parent_words_pinned'],q['original_parent_words_executed'],q['cases_per_stream'],q['connected_children_per_stream']),(295,293,306,144));self.assertEqual(q['table_index'],2);self.assertTrue(q['production_parent_verified_12_byte_stub']);self.assertTrue(q['signed16_view_and_pointer_return_ABI'])
 def test_05_native_actual_C_and_effective_controls(self):
  q=native.main();self.assertEqual(len(q['effective_controls']),9);self.assertEqual(q['cases_per_profile'],8192);self.assertTrue(q['actual_C_u8_owner_s16_view_pointer_return_ABI']);self.assertTrue(q['typed_owner272_vertex16_all_offsets_asserted']);self.assertTrue(q['all_four_vertex_flags_cleared']);self.assertTrue(q['no_signal_or_trap_counted_as_control']);self.assertIn('-fsanitize=undefined,float-cast-overflow',q['compiler_command_prefix'])
if __name__=='__main__':unittest.main()
