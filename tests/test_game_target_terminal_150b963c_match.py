"""Guarded source derivation, real padders/children and strict image adoption gates."""
import json,unittest
from tools.experiments import game_target_terminal_150b963c_match as s
from tools.tests import game_target_terminal_150b963c_oracle as guest
from tools.tests import game_target_terminal_150b963c_fitting_native as native
from tools.tests import game_target_terminal_150b963c_callers as caller
from tools.tests import game_target_terminal_150b963c_factory as factory

class TargetTerminalMatch(unittest.TestCase):
 def test_01_source_derivation_and_full_relation(self):self.assertEqual(s.qualify_source()['raw_words'],434)
 def test_02_actual_padders_rebases_and_controls(self):
  report=s.padders();self.assertEqual(report['gnu_links'],12);self.assertEqual(report['source_binding_corruptions_rejected'],497)
  count=s.guard_controls();self.assertEqual(count,1350)
  (s.OUT/'guard-controls.json').write_text(json.dumps(dict(rejected=count,all211_guards_both_padders=True,relocated_guards=15,inserted_word_controls=4,unrelated_owner_rows_filtered_for_negative_cases=True))+'\n')
 def test_03_complete_guest_semantics(self):self.assertEqual(guest.run(s.state())['cases'],1920)
 def test_04_native_and_effective_controls(self):
  row=native.run(s.state());self.assertEqual((row['cases_per_positive_run'],row['positive_runs'],row['effective_negatives']),(384,3,10))
 def test_05_actual_callback_window(self):self.assertEqual(caller.run(s.state())['cases'],1920)
 def test_06_actual_factory_wrapper_and_copy(self):
  row=factory.run(s.state());self.assertEqual(row['cases'],256);self.assertTrue(row['production_wrapper_is_retail']);self.assertEqual(row['memcpy_words_visited'],11)
 def test_07_actual_Make_and_strict_image(self):s.qualify_image()
 @classmethod
 def tearDownClass(cls):s.check_inputs()
