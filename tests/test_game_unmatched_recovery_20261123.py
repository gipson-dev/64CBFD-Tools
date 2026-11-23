"""Private recovery screens: passing these tests does not credit a match."""
import unittest
from tools.experiments import game_unmatched_recovery_20261123 as p
from tools.tests import game_unmatched_pair_lookup_20261123_guest as g
class UnmatchedRecovery(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=p.screen()
 def test_01_complete_owner_payloads_and_unmatched_counts(self):
  rows=self.report['targets'];self.assertEqual([(q['words'],q['frame'],q['retail_words'],q['neighbors'])for q in rows],[(147,96,150,68),(87,8,91,56)]);self.assertTrue(all(q['matching_credit']==0 and q['source_installed']is False and q['differences']>0 and q['pools_equal']for q in rows));self.assertTrue(self.report['production_image_unchanged'])
 def test_02_pair_lookup_semantics_and_actual_caller(self):
  g.main();g.callers();import json
  v=json.loads((g.o/'guest.json').read_text());self.assertEqual(v['cases_per_stream'],680);self.assertTrue(v['raw_and_retail_independent_public_memory_and_return_equal']);self.assertEqual(v['ordered_public_access_trace_differences'],0);self.assertEqual(v['retail_unexecuted_words'],[81]);self.assertTrue(v['unexecuted_word_81_statically_unreachable_from_normal_entry']);self.assertEqual(v['matching_credit'],0);v=json.loads((g.o/'callers.json').read_text());self.assertEqual((v['actual_caller_window_words'],v['cases_per_stream']),(15,170));self.assertTrue(v['four_arguments_stack_output_pairs_skip_gate_and_boolean_result_branch'])
 def test_03_effective_semantic_controls(self):
  self.assertEqual(len(p.controls()['effective_output_comparison_controls']),5);v=p.normalization_outline();self.assertEqual((v['raw_core_words'],v['retail_core_words']),(79,79));self.assertTrue(v['opcode_immediate_zero_role_and_binding_multisets_equal']);self.assertEqual(v['matching_credit'],0)
if __name__=='__main__':unittest.main(verbosity=2)
