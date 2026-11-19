"""Direct C, callback/factory ABI, native32 and strict image qualification."""
import unittest
from tools.experiments import game_extended_emitter_150bb498_match as s
from tools.tests import game_extended_emitter_150bb498_oracle as g
class ExtendedEmitterTests(unittest.TestCase):
 def test_01_owner_padders_rebases_and_registry(self):
  self.assertEqual(s.qualify_source()['raw_words'],151);self.assertTrue(s.census()['passes'])
  row=s.padders();self.assertEqual((row['gnu_links'],row['source_binding_corruptions_rejected'],row['guards']),(12,173,0))
 def test_02_guest_semantics(self):self.assertEqual(g.run()['cases'],512)
 def test_03_actual_caller_and_factory(self):self.assertTrue(g.caller()['passes']);self.assertTrue(g.factory()['passes'])
 def test_04_sdk32_native_with_effective_controls(self):
  from tools.tests import game_extended_emitter_150bb498_native as native
  row=native.run();self.assertEqual((row['cases_per_positive_run'],row['positive_runs'],row['effective_negatives']),(256,3,12))
 def test_05_actual_Make_and_strict_image(self):s.qualify_image()
 @classmethod
 def tearDownClass(cls):s.check_inputs()
if __name__=='__main__':unittest.main()
