import unittest
from tools.experiments import game_effect_transition_150db9e0_match as packet,game_effect_transition_150db9e0_make as make,game_effect_transition_150db9e0_image as image
from tools.tests import game_effect_transition_150db9e0_guest as guest,game_effect_transition_150db9e0_native as native,game_effect_transition_150db9e0_callers as callers,game_effect_transition_150db9e0_boundaries as boundaries
class EffectTransitionTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(160,208,7,11));self.assertTrue(q['normalized_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['fault_prefix_quintuples'],163)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['unguarded_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(306,48,20))
 def test_04_signed_transition_caller_and_void_return(self):self.assertTrue(callers.main()['independent_semantic_leaf_provider_counterpart'])
 def test_05_native_typed_arenas_and_FP(self):self.assertEqual(len(native.main()['effective_controls']),8)
if __name__=='__main__':unittest.main()
