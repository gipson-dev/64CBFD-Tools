import unittest
from tools.experiments import game_phase_height_update_1511f788_match as packet,game_phase_height_update_1511f788_make as make,game_phase_height_update_1511f788_image as image
from tools.tests import game_phase_height_update_1511f788_guest as guest,game_phase_height_update_1511f788_native as native,game_phase_height_update_1511f788_callers as callers,game_phase_height_update_1511f788_boundaries as boundaries
class PhaseHeightUpdateTests(unittest.TestCase):
 def test_01_complete_mixed_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['normalized_words'],q['frame'],q['guards'],q['raw_neighbors']),(105,105,48,52,83));self.assertTrue(q['both_complete_padders_equal']);self.assertTrue(q['structural_derivation']['divisor_60_proved_stable']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_wrapped_duration_ordered_FP_and_literal_faults(self):
  q=guest.main();self.assertEqual((q['cases_per_stream'],q['executed_reachable_words'],q['literal_full_private_fault_quadruples']),(771,101,106));self.assertEqual(len(q['effective_comparison_controls']),6);self.assertEqual(q['unreachable_preserved_offsets'],['0x5C','0x6C','0x70','0x74']);self.assertTrue(q['no_frame_or_private_home_remap'])
 def test_03_words_bindings_carries_and_jump_regions(self):
  q=boundaries.main();self.assertEqual((q['guard_corruptions_rejected'],q['unguarded_word_corruptions_visible'],q['unguarded_binding_corruptions_visible'],q['guard_binding_corruptions_rejected'],q['GNU_links']),(104,106,8,4,20));self.assertEqual(q['oversized'],['rejected','rejected'])
 def test_04_complete_original_dispatcher_installer_activation(self):
  q=callers.main();self.assertEqual((q['parent_words_pinned'],q['parent_words_executed'],q['cases_per_stream'],q['connected_children_per_stream']),(127,127,144,147));self.assertEqual((q['installer_words'],q['row'],q['activation_slot_words']),(22,65,8));self.assertTrue(q['void_one_argument_callback_ABI_qualified']);self.assertTrue(q['original_parent_current_production_is_retained_12_byte_stub'])
 def test_05_native_actual_C_target_wrap_contract(self):
  q=native.main();self.assertEqual(len(q['effective_controls']),12);self.assertEqual(q['cases_per_profile'],4096);self.assertTrue(q['actual_C_void_one_argument_ABI']);self.assertTrue(q['native_fwrapv_required_for_pinned_N64_signed_integer_semantics']);self.assertTrue(q['independent_reference_product_is_unsigned_32bit']);self.assertTrue(q['no_signal_or_trap_counted_as_control'])
if __name__=='__main__':unittest.main()
