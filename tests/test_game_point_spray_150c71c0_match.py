"""Direct words, sealed pool, ordered RNGs, callback ABI and native SDK32."""
import unittest
from tools.experiments import game_point_spray_150c71c0_match as packet
from tools.experiments import game_point_spray_150c71c0_make as make
from tools.experiments import game_point_spray_150c71c0_image as image
from tools.tests import game_point_spray_150c71c0_guest as guest
from tools.tests import game_point_spray_150c71c0_boundaries as boundaries
from tools.tests import game_point_spray_150c71c0_callers as callers
from tools.tests import game_point_spray_150c71c0_connected as connected
from tools.tests import game_point_spray_150c71c0_native as native
class PointSprayTests(unittest.TestCase):
 def test_01_owner_pool_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(99,0,1));self.assertEqual(make.main()['commands'],4);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_ordered_guest_and_access_faults(self):self.assertEqual(guest.main()['executed_words'],95)
 def test_03_pool_controls_padders_and_GNU(self):self.assertEqual(boundaries.main()['GNU_links'],16)
 def test_04_caller_window_and_original_RNGs(self):
  self.assertEqual(callers.main()['callback_index'],1);self.assertEqual(connected.main()['seed_transitions_per_case'],5)
 def test_05_native_SDK32_and_effective_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),10)
if __name__=='__main__':unittest.main(verbosity=2)
