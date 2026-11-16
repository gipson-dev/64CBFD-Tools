"""Prepared growth emitter source, fitting, proof, guest, native and caller gates."""
import unittest
from tools.experiments import game_growth_curve_151a1fb4_recovery as source
class GrowthCurveTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not(source.FROZEN/'fingerprints.json').exists():raise unittest.SkipTest('prepared immutable growth-emitter baseline absent')
  source.compile_and_check()
  from tools.experiments import game_growth_curve_151a1fb4_match as match
  cls.match_report=match.main()
 def test_projection_and_both_owner_padders(self):
  self.assertEqual((self.match_report['raw_words'],self.match_report['normalized_words'],self.match_report['omissions']),(314,317,0))
  self.assertEqual(self.match_report['real_CSV_negatives'],10)
 def test_full_guest_and_independent_model(self):
  from tools.tests import game_growth_curve_151a1fb4_oracle as guest
  guest.main()
 def test_native32_and_effective_source_controls(self):
  from tools.tests import game_growth_curve_151a1fb4_native as native
  native.main()
 def test_inductive_FP_frame_and_exact_width_identities(self):
  from tools.tests import game_growth_curve_151a1fb4_proof as proof
  q=proof.main();self.assertTrue(q['whole_function']);self.assertEqual(q['paths'],{'prefix':2,'loop':256})
 def test_actual_slot4_parent_and_expiry_routes(self):
  from tools.tests import game_growth_curve_151a1fb4_callers as callers
  callers.main()
if __name__=='__main__':unittest.main()
