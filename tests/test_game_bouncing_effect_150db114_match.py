import unittest
from tools.experiments import game_bouncing_effect_150db114_match as packet,game_bouncing_effect_150db114_make as make,game_bouncing_effect_150db114_image as image
from tools.tests import game_bouncing_effect_150db114_guest as guest,game_bouncing_effect_150db114_native as native,game_bouncing_effect_150db114_callers as callers,game_bouncing_effect_150db114_boundaries as boundaries
class BouncingEffectTickTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(113,0,0,5));self.assertTrue(q['normalized_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['fault_prefix_quintuples'],193)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['all_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(226,16,20))
 def test_04_original_indexed_caller_and_return(self):self.assertTrue(callers.main()['status_return_controls_expiration'])
 def test_05_native_typed_arenas_and_FP(self):self.assertEqual(len(native.main()['effective_controls']),7)
if __name__=='__main__':unittest.main()
