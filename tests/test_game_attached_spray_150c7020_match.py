"""Direct C owner, sparse packet semantics, SDK32, callers and complete ELF."""
import unittest
from tools.experiments import game_attached_spray_150c7020_match as packet
from tools.experiments import game_attached_spray_150c7020_make as make,game_attached_spray_150c7020_image as image
from tools.tests import game_attached_spray_150c7020_guest as guest,game_attached_spray_150c7020_boundaries as boundaries,game_attached_spray_150c7020_callers as callers,game_attached_spray_150c7020_connected as connected,game_attached_spray_150c7020_native as native
class AttachedSprayTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(104,0,1));self.assertEqual(make.main()['commands'],4);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertEqual(guest.main()['executed_words'],104)
 def test_03_slot_limits_and_GNU(self):self.assertEqual(boundaries.main()['GNU_links'],16)
 def test_04_actual_callers_and_original_RNG(self):
  self.assertEqual(callers.main()['caller_routes'],2);self.assertEqual(connected.main()['seed_transitions_per_case'],4)
 def test_05_native_SDK32_and_effective_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),10)
if __name__=='__main__':unittest.main(verbosity=2)
