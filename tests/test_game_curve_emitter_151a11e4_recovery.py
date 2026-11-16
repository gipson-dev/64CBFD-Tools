"""Prepared full-emitter source, matching, proof, caller and native gates."""
import unittest
from tools.experiments import game_curve_emitter_151a11e4_recovery as source
class CurveEmitterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not(source.FROZEN/'fingerprints.json').exists():raise unittest.SkipTest('prepared immutable emitter baseline absent')
  source.compile_and_check()
  from tools.experiments import game_curve_emitter_151a11e4_match as match
  cls.match_report=match.main()
 def test_exact_operation_projection_and_padders(self):
  self.assertEqual((self.match_report['raw_words'],self.match_report['normalized_words'],self.match_report['omissions']),(344,350,0))
  self.assertEqual(self.match_report['real_CSV_negatives'],8)
 def test_full_guest_and_independent_model(self):
  from tools.tests import game_curve_emitter_151a11e4_oracle as guest
  guest.main()
 def test_native32_and_effective_source_controls(self):
  from tools.tests import game_curve_emitter_151a11e4_native as native
  native.main()
 def test_inductive_ordered_FP_and_full_private_frame(self):
  from tools.tests import game_curve_emitter_151a11e4_proof as proof
  q=proof.main();self.assertTrue(q['whole_function']);self.assertEqual(q['paths'],{'prefix':2,'loop':512})
 def test_actual_slot2_parent_and_expiry_routes(self):
  from tools.tests import game_curve_emitter_151a11e4_callers as callers
  callers.main()
if __name__=='__main__':unittest.main()
