"""Ring updater C, guard boundaries, callback ABI and independent linked image."""
import unittest
from tools.experiments import game_ring_updater_150c8a68_match as packet
from tools.experiments import game_ring_updater_150c8a68_make as make,game_ring_updater_150c8a68_image as image
from tools.tests import game_ring_updater_150c8a68_guest as guest,game_ring_updater_150c8a68_boundaries as boundaries,game_ring_updater_150c8a68_callers as callers,game_ring_updater_150c8a68_native as native
class RingUpdaterTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(212,32,18));self.assertEqual(make.main()['commands'],4);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertEqual(guest.main()['executed_words'],211)
 def test_03_slot_limits_and_GNU(self):
  q=boundaries.main();self.assertEqual(q['GNU_links'],16);self.assertEqual(q['literal_pool_corruptions_rejected'],18)
 def test_04_actual_caller_window(self):self.assertEqual(callers.main()['actual_caller_cases'],128)
 def test_05_native_SDK32_and_effective_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),11)
if __name__=='__main__':unittest.main(verbosity=2)
