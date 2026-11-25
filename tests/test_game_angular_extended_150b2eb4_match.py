import unittest
from tools.experiments import game_angular_extended_150b2eb4_match as packet,game_angular_extended_150b2eb4_make as make,game_angular_extended_150b2eb4_image as image
from tools.tests import game_angular_extended_150b2eb4_guest as guest,game_angular_extended_150b2eb4_boundaries as boundaries,game_angular_extended_150b2eb4_callers as callers,game_angular_extended_150b2eb4_native as native
class AngularExtendedTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(181,29,5));self.assertEqual(make.main()['commands'],3);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertEqual(guest.main()['executed_words'],181)
 def test_03_slot_limits_and_GNU(self):self.assertEqual(boundaries.main()['binding_pins'],20)
 def test_04_original_registry_and_helpers(self):self.assertEqual(callers.main()['retail_parent_cases'],384)
 def test_05_native_SDK32_and_effective_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),21)
if __name__=='__main__':unittest.main()
