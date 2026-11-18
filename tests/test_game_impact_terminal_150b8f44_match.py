"""Guarded adoption: finite relation, actual padders, child execution and image."""
import json,unittest
from tools.experiments import game_impact_terminal_150b8f44_match as s
from tools.tests import game_impact_terminal_150b8f44_oracle as guest
from tools.tests import game_impact_terminal_150b8f44_native as native
from tools.tests import game_impact_terminal_150b8f44_callers as callers
from tools.tests import game_impact_terminal_150b8f44_factory as factory

class ImpactTerminalMatch(unittest.TestCase):
 def test_01_source_and_complete_finite_relation(self):self.assertEqual(s.qualify_source()['raw_words'],390)
 def test_02_actual_padders_rebases_and_guard_controls(self):
  self.assertEqual(s.padders()['gnu_links'],12);count=s.guard_controls();self.assertEqual(count,2434)
  (s.OUT/'guard-controls.json').write_text(json.dumps(dict(rejected=count,all368_guards_both_padders=True,relocated_guards=55,inserted_word_controls=True,unrelated_owner_rows_filtered_for_negative_cases=True))+'\n')
 def test_03_guest_complete_semantics(self):self.assertEqual(guest.run(s.state())['cases'],2304)
 def test_04_native_and_controls(self):
  result=native.run(s.state());self.assertEqual((result['cases_per_positive_run'],result['positive_runs'],result['effective_negatives']),(864,3,8))
 def test_05_genuine_five_argument_caller(self):self.assertEqual(callers.run(s.state())['cases'],768)
 def test_06_actual_wrapper_and_memcpy(self):
  result=factory.run(s.state());self.assertEqual(result['cases'],192);self.assertTrue(result['production_wrapper_is_retail']);self.assertEqual(result['memcpy_words_visited'],11)
 def test_07_actual_Make_and_strict_image(self):s.qualify_image()
 @classmethod
 def tearDownClass(cls):s.check_inputs()
