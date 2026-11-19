"""Complete guarded C, actual callers, SDK32 and literal production-image gates."""
import unittest
from tools.experiments import game_actor_attached_emitter_150bb760_match as s
from tools.tests import game_actor_attached_emitter_150bb760_oracle as g
class ActorAttachedEmitterTests(unittest.TestCase):
 def test_01_owner_padders_rebases_registry_and_guard_controls(self):
  row=s.qualify_source();self.assertEqual((row['raw_words'],row['slot_words'],row['frame'],row['guards']),(254,255,248,38));self.assertTrue(s.census()['passes'])
  row=s.padders();self.assertEqual((row['gnu_links'],row['source_binding_corruptions_rejected'],row['guards']),(12,286,38));self.assertTrue(s.guard_controls()['passes'])
 def test_02_guest_semantics_and_early_fault(self):self.assertEqual(g.run()['cases'],1026)
 def test_03_complete_caller_and_factory_wrapper(self):self.assertEqual(g.caller()['cases'],264);self.assertEqual(g.factory()['cases'],128)
 def test_04_sdk32_native_with_effective_controls(self):
  from tools.tests import game_actor_attached_emitter_150bb760_native as native
  row=native.run();self.assertEqual((row['cases_per_positive_run'],row['positive_runs'],row['effective_negatives']),(512,3,18))
 def test_05_actual_Make_and_strict_image(self):s.qualify_image()
 @classmethod
 def tearDownClass(cls):s.check_inputs()
if __name__=='__main__':unittest.main()
