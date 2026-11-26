import unittest
from tools.experiments import game_trail_fade_tick_151b6420_match as packet,game_trail_fade_tick_151b6420_make as make,game_trail_fade_tick_151b6420_image as image
from tools.tests import game_trail_fade_tick_151b6420_guest as guest,game_trail_fade_tick_151b6420_native as native,game_trail_fade_tick_151b6420_callers as callers,game_trail_fade_tick_151b6420_boundaries as boundaries
class TrailFadeTickTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(109,0,5,16));self.assertFalse(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['fault_prefix_quintuples'],105)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['unguarded_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(208,6,20))
 def test_04_original_indexed_caller_and_return(self):self.assertTrue(callers.main()['actual_unsigned_first_selector11_JALR_and_zero_result_consumer'])
 def test_05_native_typed_arenas_and_FP(self):self.assertEqual(len(native.main()['effective_controls']),7)
if __name__=='__main__':unittest.main()
