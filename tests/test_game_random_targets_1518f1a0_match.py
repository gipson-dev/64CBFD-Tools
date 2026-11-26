import unittest
from tools.experiments import game_random_targets_1518f1a0_match as packet,game_random_targets_1518f1a0_make as make,game_random_targets_1518f1a0_image as image
from tools.tests import game_random_targets_1518f1a0_guest as guest,game_random_targets_1518f1a0_native as native,game_random_targets_1518f1a0_callers as callers,game_random_targets_1518f1a0_boundaries as boundaries
class RandomTargetsTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(121,32,14,60));self.assertFalse(q['raw_byte_exact']);self.assertTrue(q['normalized_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['normalized_fault_prefix_quadruples'],144)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['unguarded_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(214,34,20))
 def test_04_complete_wrapper_and_passthrough_return(self):self.assertTrue(callers.main()['independent_complete_parent_reference'])
 def test_05_native_typed_arenas_and_FP(self):self.assertEqual(len(native.main()['effective_controls']),8)
if __name__=='__main__':unittest.main()
