"""Complete original scene callers, exact mapped RAM and effective controls."""
import json,unittest
from tools.experiments import game_strip_constructor_151acbd4_caller_qualification as m
from tools.tests import game_strip_constructor_151acbd4_callers as callers
class StripConstructorCallerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):m.compile_and_check()
 def tearDown(self):m.check_inputs()
 def test_01_complete_owner_and_fingerprinted_semantic_reuse(self):
  r=json.loads((m.OUT/'source-report.json').read_text());self.assertEqual((r['raw_words'],r['retail_words'],r['frame'],r['neighbors_unchanged']),(388,360,64,32))
  reuse=json.loads((m.OUT/'reused-evidence.json').read_text());self.assertEqual(reuse['unchanged_prior_inputs'],1486);self.assertTrue(reuse['prior_ordered_semantic_gates_reused']);self.assertFalse(reuse['fresh_semantic_suite_claimed'])
 def test_02_all_three_complete_callers_and_six_sites(self):
  callers.main();r=json.loads((m.OUT/'caller-report.json').read_text());self.assertEqual(r['complete_original_callers'],3);self.assertEqual(r['static_call_sites'],6);self.assertEqual(set(r['cases_per_stream'].values()),{384});self.assertTrue(r['complete_mapped_RAM_and_private_stack_compared'])
 def test_03_six_argument_controls_and_two_output_controls(self):
  self.assertEqual(len(callers.controls()),8)
if __name__=='__main__':unittest.main()
