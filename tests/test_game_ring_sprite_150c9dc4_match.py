"""Sparse ring particle C, complete owner, callback ABI and independent image."""
import unittest
from tools.experiments import game_ring_sprite_150c9dc4_match as packet
from tools.experiments import game_ring_sprite_150c9dc4_make as make,game_ring_sprite_150c9dc4_image as image
from tools.tests import game_ring_sprite_150c9dc4_guest as guest,game_ring_sprite_150c9dc4_boundaries as boundaries,game_ring_sprite_150c9dc4_callers as callers,game_ring_sprite_150c9dc4_native as native
class RingSpriteTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(174,7,18));self.assertEqual(make.main()['commands'],4);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertEqual(guest.main()['executed_words'],174)
 def test_03_slot_limits_and_GNU(self):
  q=boundaries.main();self.assertEqual(q['GNU_links'],16);self.assertEqual(q['literal_pool_corruptions_rejected'],18)
 def test_04_actual_callback_window(self):self.assertEqual(callers.main()['actual_caller_cases'],192)
 def test_05_native_SDK32_and_effective_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),12)
if __name__=='__main__':unittest.main(verbosity=2)
