"""Complete owner, private-cache, caller, native and linked-image gates."""
import unittest
from tools.experiments import game_attachment_surface_effect_150babe0_match as s
from tools.tests import game_attachment_surface_effect_150babe0_oracle as g
class AttachmentSurfaceEffectTests(unittest.TestCase):
 def test_01_owner_padders_rebases_census_and_guard_controls(self):
  self.assertEqual(s.qualify_source()['raw_words'],259);self.assertTrue(s.census()['passes'])
  row=s.padders();self.assertEqual((row['gnu_links'],row['source_binding_corruptions_rejected'],row['guards']),(12,286,4))
  self.assertEqual(s.guard_controls()['negative_controls'],24)
 def test_02_guest_semantics_and_closed_private_cache_trace(self):self.assertEqual(g.run()['cases'],896)
 def test_03_literal_callers_and_constructor_abi(self):self.assertTrue(g.callers()['passes']);self.assertTrue(g.constructor_prefix()['passes'])
 def test_04_sdk32_native_with_effective_controls(self):
  from tools.tests import game_attachment_surface_effect_150babe0_native as native
  row=native.run();self.assertEqual((row['cases_per_positive_run'],row['positive_runs'],row['effective_negatives']),(448,3,12))
 def test_05_actual_Make_and_strict_image(self):s.qualify_image()
 @classmethod
 def tearDownClass(cls):s.check_inputs()
if __name__=='__main__':unittest.main()
