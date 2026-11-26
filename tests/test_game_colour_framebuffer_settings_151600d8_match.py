import unittest
from tools.experiments import game_colour_framebuffer_settings_151600d8_match as packet,game_colour_framebuffer_settings_151600d8_make as make,game_colour_framebuffer_settings_151600d8_image as image
from tools.tests import game_colour_framebuffer_settings_151600d8_guest as guest,game_colour_framebuffer_settings_151600d8_native as native,game_colour_framebuffer_settings_151600d8_callers as callers,game_colour_framebuffer_settings_151600d8_boundaries as boundaries
class ColourFrameBufferSettingsTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['frame'],q['guards'],q['neighbors']),(103,48,0,5));self.assertTrue(q['raw_byte_exact']);self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_literal_and_direct_guest(self):self.assertEqual(guest.main()['fault_prefix_quintuples'],89)
 def test_03_unmasked_words_bindings_and_rebases(self):
  q=boundaries.main();self.assertEqual((q['all_word_corruptions_visible'],q['all_binding_corruptions_visible'],q['GNU_links']),(206,66,20))
 def test_04_original_indexed_caller_and_return(self):self.assertTrue(callers.main()['source_owner_argument_now_explicit_with_parent_bytes_unchanged'])
 def test_05_native_typed_arenas_and_FP(self):self.assertEqual(len(native.main()['effective_controls']),8)
if __name__=='__main__':unittest.main()
