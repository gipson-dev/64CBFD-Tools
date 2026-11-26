import unittest
from tools.experiments import game_display_sprite_slot_15179600_match as packet,game_display_sprite_slot_15179600_make as make,game_display_sprite_slot_15179600_image as image
from tools.tests import game_display_sprite_slot_15179600_guest as guest,game_display_sprite_slot_15179600_native as native,game_display_sprite_slot_15179600_callers as callers,game_display_sprite_slot_15179600_boundaries as boundaries
class DisplaySpriteSlotTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(108,248,12,8));self.assertTrue(q['normalized_byte_exact']);self.assertFalse(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_faults_and_raw_live_roles(self):
  q=guest.main();self.assertEqual((q['cases_per_stream'],q['preserved_words'],q['executed_words'],q['normalized_fault_prefix_quadruples'],q['raw_fault_prefix_role_relations']),(856,108,108,127,127));self.assertTrue(q['raw_full_private_fault_GPR_identity_not_claimed'])
 def test_03_guarded_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['guard_corruptions_rejected'],q['unguarded_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(24,192,28,20))
 def test_04_complete_parent_on_fill_loop_paths(self):
  q=callers.main();self.assertTrue(q['independent_complete_parent_reference_on_qualified_paths']);self.assertEqual((q['parent_words_pinned'],q['parent_words_executed'],q['cases_per_stream'],q['connected_children_per_stream']),(304,80,320,944));self.assertTrue(q['entry_void_two_word_ABI_parent_arguments_one_one_and_ignored_result'])
 def test_05_native_typed_arenas_and_FP(self):
  q=native.main();self.assertEqual(len(q['effective_controls']),11);self.assertEqual(q['initialized_bytes_observed'],109);self.assertTrue(q['initially_unknown59_source_bytes_not_read_before_definition'])
if __name__=='__main__':unittest.main()
