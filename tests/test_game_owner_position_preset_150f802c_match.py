import unittest
from tools.experiments import game_owner_position_preset_150f802c_match as packet,game_owner_position_preset_150f802c_make as make,game_owner_position_preset_150f802c_image as image
from tools.tests import game_owner_position_preset_150f802c_guest as guest,game_owner_position_preset_150f802c_boundaries as boundaries,game_owner_position_preset_150f802c_callers as callers,game_owner_position_preset_150f802c_helpers as helpers,game_owner_position_preset_150f802c_native as native
class OwnerPositionPresetTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(100,49,16));self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertEqual(guest.main()['access_fault_quads'],213)
 def test_03_slot_limits_and_GNU(self):self.assertEqual(boundaries.main()['binding_pins'],6)
 def test_04_bounded_original_caller_and_helpers(self):
  self.assertEqual(callers.main()['bounded_cases_per_stream'],532);self.assertEqual(helpers.main()['cases'],378)
 def test_05_native_ABI_and_controls(self):self.assertEqual(len(native.main()['effective_controls']),12)
if __name__=='__main__':unittest.main()
