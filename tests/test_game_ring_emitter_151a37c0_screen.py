"""Regression gate for a private full-C emitter and its bounded setup transfer."""
import json,unittest
from tools.experiments import game_ring_emitter_151a37c0_screen as m
from tools.tests import game_ring_emitter_151a37c0_setup_screen as p
class EmitterSetupScreenTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not(m.FROZEN/'fingerprints.json').exists():raise unittest.SkipTest('prepared immutable screen inputs absent')
  cls.source=m.compile_and_check();cls.programs=m.programs()
 def test_complete_C_is_explicitly_uncredited(self):
  self.assertEqual(self.source['slot_words'],265);self.assertEqual(self.source['owners'][0]['words'],266)
  self.assertFalse(self.source['source_installed']);self.assertFalse(self.source['whole_function_qualified']);self.assertEqual(self.source['c_match_credit'],0)
 def test_eight_ordered_setup_paths_and_live_roles(self):
  result=p.prove_words(self.programs['selected']);self.assertEqual(result['paths'],8);self.assertTrue(result['live_loop_inputs'])
  (m.OUT/'setup-report.json').write_text(json.dumps(result,indent=2)+'\n')
 def test_same_length_frame_candidate_rejects_FP_order(self):
  self.assertEqual(len(self.programs['rejected']),265)
  with self.assertRaisesRegex(AssertionError,'FP trace'):p.prove_words(self.programs['rejected'])
 def test_effective_negatives_and_independent_renaming(self):
  result=p.controls(self.programs['selected']);self.assertEqual(len(result['effective_negatives']),4)
  (m.OUT/'controls-report.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':unittest.main()
