"""Direct words, pool/guard audit, original call windows and SDK32."""
import unittest
from tools.experiments import game_surface_angular_effect_15194408_match as packet
from tools.tests import game_surface_angular_effect_15194408_guest as guest
from tools.tests import game_surface_angular_effect_15194408_boundaries as boundaries
from tools.tests import game_surface_angular_effect_15194408_callers as callers
from tools.tests import game_surface_angular_effect_15194408_native as native
class SurfaceAngularEffect(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_owner_pool_guard_and_literal_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal'])
  self.assertEqual((self.report['words'],self.report['target_guards'],self.report['exclusions']),(96,0,0))
  self.assertEqual(self.report['unchanged_padded_neighbors'],28)
 def test_02_mutating_guest_and_fault_prefixes(self):self.assertEqual(guest.main()['covered_words'],96)
 def test_03_both_padders_GNU_rebases_and_table_boundaries(self):self.assertEqual(boundaries.main()['GNU_rebased_links'],16)
 def test_04_both_original_caller_windows(self):self.assertTrue(callers.main()['two_actor_pointer_ABI'])
 def test_05_defined_SDK32_and_source_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),10)
if __name__=='__main__':unittest.main(verbosity=2)
