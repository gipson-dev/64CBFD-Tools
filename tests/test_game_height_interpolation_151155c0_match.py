import unittest
from tools.experiments import game_height_interpolation_151155c0_match as packet,game_height_interpolation_151155c0_make as make,game_height_interpolation_151155c0_image as image
from tools.tests import game_height_interpolation_151155c0_guest as guest,game_height_interpolation_151155c0_symbolic as symbolic,game_height_interpolation_151155c0_boundaries as boundaries,game_height_interpolation_151155c0_callers as callers,game_height_interpolation_151155c0_native as native
class HeightInterpolationTests(unittest.TestCase):
 def test_01_owner_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(103,76,83));self.assertTrue(make.main()['whole_padded_owner_equal']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertGreater(guest.main()['access_fault_quads'],0)
 def test_03_guards_and_GNU(self):
  q=boundaries.main();self.assertEqual((q['guarded_corruptions_rejected'],q['unguarded_corruptions_visible'],q['GNU_links']),(152,54,20))
 def test_04_structural_proof_and_original_caller(self):
  q=symbolic.main();self.assertEqual((q['ordinary']['paths'],q['guest_hold_read_perturbation']['paths']),(132,132));self.assertEqual(callers.main()['visited_parent_words'],127)
 def test_05_native_ABI_and_controls(self):self.assertEqual(len(native.main()['effective_controls']),7)
if __name__=='__main__':unittest.main()
