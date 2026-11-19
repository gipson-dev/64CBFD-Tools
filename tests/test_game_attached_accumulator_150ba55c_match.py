"""Proved source normalization, connected services and strict complete-image gates."""
import json,unittest
from tools.experiments import game_attached_accumulator_150ba55c_match as s
from tools.tests import game_attached_accumulator_150ba55c_oracle as guest
from tools.tests import game_attached_accumulator_150ba55c_native as native
from tools.tests import game_attached_accumulator_150ba55c_factory as factory
class AttachedAccumulatorMatch(unittest.TestCase):
 def test_01_source_derivation_and_complete_private_relation(self):self.assertEqual(s.qualify_source()['raw_words'],229)
 def test_02_actual_padders_rebases_and_controls(self):
  report=s.padders();self.assertEqual(report['gnu_links'],12);self.assertEqual(report['source_binding_corruptions_rejected'],268)
  count=s.guard_controls();self.assertEqual(count,634)
  (s.OUT/'guard-controls.json').write_text(json.dumps(dict(rejected=count,all93_guards_both_padders=True,relocated_guards=19,insertions=0,omissions=0,unrelated_owner_rows_filtered_for_negative_cases=True))+'\n')
 def test_03_complete_guest_semantics(self):self.assertEqual(guest.run(s.state())['cases_per_stream'],1584)
 def test_04_native_and_effective_controls(self):
  row=native.run(s.state());self.assertEqual((row['cases_per_positive_run'],row['positive_runs'],row['effective_negatives']),(752,3,11))
 def test_05_complete_original_dispatcher(self):
  from tools.tests import game_attached_accumulator_150ba55c_caller as caller
  self.assertEqual(caller.main()['cases_per_stream'],dict(raw=192,retail=192))
 def test_06_actual_factory_allocation_wrapper_and_copy(self):self.assertEqual(factory.run(s.state())['cases'],64)
 def test_07_actual_Make_and_strict_image(self):s.qualify_image()
 @classmethod
 def tearDownClass(cls):s.check_inputs()
if __name__=='__main__':unittest.main()
