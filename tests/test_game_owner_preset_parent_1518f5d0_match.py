import unittest
from tools.experiments import game_owner_preset_parent_1518f5d0_match as packet,game_owner_preset_parent_1518f5d0_make as make,game_owner_preset_parent_1518f5d0_image as image
from tools.tests import game_owner_preset_parent_1518f5d0_guest as guest,game_owner_preset_parent_1518f5d0_native as native,game_owner_preset_parent_1518f5d0_callers as callers,game_owner_preset_parent_1518f5d0_boundaries as boundaries
class OwnerPresetParentTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(125,200,0,60));self.assertTrue(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['fault_prefix_quintuples'],781)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['all_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(250,14,20))
 def test_04_complete_wrapper_and_passthrough_return(self):self.assertTrue(callers.main()['independent_semantic_parent_provider_counterpart'])
 def test_05_native_typed_arenas_and_FP(self):self.assertEqual(len(native.main()['effective_controls']),10)
if __name__=='__main__':unittest.main()
