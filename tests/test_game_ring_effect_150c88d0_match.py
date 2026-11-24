"""Ring C/guard boundaries, independent models, callers and strict linked image."""
import unittest
from tools.experiments import game_ring_effect_150c88d0_match as packet
from tools.experiments import game_ring_effect_150c88d0_make as make,game_ring_effect_150c88d0_image as image
from tools.tests import game_ring_effect_150c88d0_guest as guest,game_ring_effect_150c88d0_boundaries as boundaries,game_ring_effect_150c88d0_callers as callers,game_ring_effect_150c88d0_native as native
class RingEffectTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(102,22,18));self.assertEqual(make.main()['commands'],3);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertEqual(guest.main()['executed_words'],102)
 def test_03_slot_limits_and_GNU(self):self.assertEqual(boundaries.main()['GNU_links'],16)
 def test_04_actual_callers(self):self.assertEqual(callers.main()['caller_routes'],2)
 def test_05_native_SDK32_and_effective_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),10)
if __name__=='__main__':unittest.main(verbosity=2)
