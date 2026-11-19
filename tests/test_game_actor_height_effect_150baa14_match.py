"""Direct source identity, ABI semantics and strict linked-image qualification."""
import unittest
from tools.experiments import game_actor_height_effect_150baa14_match as s
from tools.tests import game_actor_height_effect_150baa14_oracle as g
class ActorHeightEffectTests(unittest.TestCase):
 def test_01_direct_owner_padders_rebases_and_census(self):
  self.assertEqual(s.qualify_source()['raw_words'],114);self.assertTrue(s.census()['passes'])
  report=s.padders();self.assertEqual((report['gnu_links'],report['source_binding_corruptions_rejected'],report['guards']),(12,127,0))
 def test_02_complete_guest_semantics(self):self.assertEqual(g.run(s.state())['cases'],1024)
 def test_03_caller_and_actual_callee_parameter_loads(self):
  self.assertEqual(g.caller(s.state())['cases'],128);self.assertEqual(g.indirect_callers(s.state())['cases'],576);self.assertEqual(g.callee_prefix(s.state())['cases'],128)
 def test_04_sdk32_native_with_effective_controls(self):
  from tools.tests import game_actor_height_effect_150baa14_native as native
  row=native.run(s.state());self.assertEqual((row['cases_per_positive_run'],row['positive_runs'],row['effective_negatives']),(512,3,11))
 def test_05_actual_Make_and_strict_image(self):s.qualify_image()
 @classmethod
 def tearDownClass(cls):s.check_inputs()
if __name__=='__main__':unittest.main()
