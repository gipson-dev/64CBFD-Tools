"""Guarded match: complete relation, real padders, semantic checks and linked image."""
import json,unittest
from tools.experiments import game_amplitude_terminal_150b89e0_match as s
from tools.tests import game_amplitude_terminal_150b89e0_oracle as guest
from tools.tests import game_amplitude_terminal_150b89e0_native as native
from tools.tests import game_amplitude_terminal_150b89e0_callers as callers
from tools.tests import game_amplitude_terminal_150b89e0_factory as factory

class AmplitudeTerminalMatch(unittest.TestCase):
 def test_01_source_and_complete_relation(self):self.assertEqual(s.qualify_source()['raw_words'],345)
 def test_02_padders_rebases_and_guard_controls(self):
  result=s.padders();self.assertEqual(result['gnu_links'],12);count=s.guard_controls();self.assertEqual(count,608)
  (s.OUT/'guard-controls.json').write_text(json.dumps(dict(rejected=count,all100_guards_both_padders=True,relocated_guards=2))+'\n')
 def test_03_guest_complete_semantics(self):self.assertEqual(guest.run(s.state())['cases'],2304)
 def test_04_native_and_controls(self):
  result=native.run(s.state());self.assertEqual((result['cases_per_positive_run'],result['positive_runs'],result['effective_negatives']),(288,3,12))
 def test_05_complete_real_terrain_caller(self):self.assertEqual(callers.run(s.state())['complete_parent_words_visited'],80)
 def test_06_other_dispatch_window(self):self.assertEqual(callers.other_window(s.state())['cases'],96)
 def test_07_actual_wrapper_and_memcpy(self):
  result=factory.run(s.state());self.assertEqual(result['cases'],128);self.assertTrue(result['production_wrapper_is_retail']);self.assertEqual(result['memcpy_words_visited'],11)
 def test_08_actual_Make_and_strict_image(self):s.qualify_image()
 @classmethod
 def tearDownClass(cls):s.check_inputs()
if __name__=='__main__':unittest.main()
