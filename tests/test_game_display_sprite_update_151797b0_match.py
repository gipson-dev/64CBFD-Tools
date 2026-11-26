import unittest
from tools.experiments import game_display_sprite_update_151797b0_match as packet,game_display_sprite_update_151797b0_make as make,game_display_sprite_update_151797b0_image as image
from tools.tests import game_display_sprite_update_151797b0_guest as guest,game_display_sprite_update_151797b0_native as native,game_display_sprite_update_151797b0_callers as callers,game_display_sprite_update_151797b0_boundaries as boundaries
class DisplaySpriteUpdateTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(194,56,9,8));self.assertTrue(q['normalized_byte_exact']);self.assertFalse(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_faults_and_raw_live_roles(self):
  q=guest.main();self.assertEqual((q['cases_per_stream'],q['preserved_words'],q['executed_words'],q['normalized_fault_prefix_quadruples'],q['raw_fault_memory_FP_and_restricted_GPR_relations']),(960,194,194,159,159));self.assertTrue(q['raw_full_private_GPR_identity_not_claimed'])
 def test_03_guarded_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['guard_corruptions_rejected'],q['unguarded_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(18,370,36,20))
 def test_04_complete_parent_on_zero_frame_speed_paths(self):
  q=callers.main();self.assertTrue(q['independent_complete_parent_reference_on_qualified_paths']);self.assertEqual((q['parent_words_pinned'],q['parent_words_executed'],q['cases_per_stream'],q['connected_children_per_stream']),(111,27,648,216));self.assertTrue(q['entry_void_SpriteFrameState_pointer_ABI_and_ignored_result'])
 def test_05_native_typed_record_and_FP(self):
  q=native.main();self.assertEqual(len(q['effective_controls']),15);self.assertEqual(q['cases_per_profile'],4096);self.assertTrue(q['actual_C_canonical_SpriteFrameState_pointer_entry_and_u8_wave_prototypes'])
if __name__=='__main__':unittest.main()
