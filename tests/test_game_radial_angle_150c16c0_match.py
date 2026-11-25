import unittest
from tools.experiments import game_radial_angle_150c16c0_match as packet
from tools.experiments import game_radial_angle_150c16c0_make as make,game_radial_angle_150c16c0_image as image
from tools.tests import game_radial_angle_150c16c0_guest as guest,game_radial_angle_150c16c0_boundaries as boundaries,game_radial_angle_150c16c0_callers as callers,game_radial_angle_150c16c0_native as native
class RadialAngleTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(174,76,2));self.assertEqual(make.main()['commands'],3);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertEqual(guest.main()['executed_words'],172)
 def test_03_slot_limits_and_GNU(self):self.assertEqual(boundaries.main()['binding_pins'],21)
 def test_04_original_registry_and_helpers(self):self.assertEqual(callers.main()['retail_parent_cases'],384)
 def test_05_native_SDK32_and_effective_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),25)
if __name__=='__main__':unittest.main()
