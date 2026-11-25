import unittest
from tools.experiments import game_composite_preset_150b5a3c_match as packet,game_composite_preset_150b5a3c_make as make,game_composite_preset_150b5a3c_image as image
from tools.tests import game_composite_preset_150b5a3c_guest as guest,game_composite_preset_150b5a3c_boundaries as boundaries,game_composite_preset_150b5a3c_callers as callers,game_composite_preset_150b5a3c_helpers as helpers,game_composite_preset_150b5a3c_native as native
class CompositePresetTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(127,51,11));self.assertEqual(make.main()['commands'],3);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertTrue(guest.main()['all127_words_visited'])
 def test_03_slot_limits_and_GNU(self):self.assertEqual(boundaries.main()['binding_pins'],9)
 def test_04_original_caller_and_helpers(self):
  self.assertEqual(callers.main()['cases_per_stream'],1152);self.assertEqual(helpers.main()['cases_per_helper'],128)
 def test_05_native_SDK32_and_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),11)
if __name__=='__main__':unittest.main()
