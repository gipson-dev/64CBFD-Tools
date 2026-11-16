"""Prepared constructor source, complete transfer, native/guest and caller gates."""
import unittest
from tools.experiments import game_composite_burst_151a3150_recovery as source
class CompositeBurstTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not(source.FROZEN/'fingerprints.json').exists():raise unittest.SkipTest('prepared immutable constructor baseline absent')
  source.compile_and_check()
  from tools.experiments import game_composite_burst_151a3150_match as match
  cls.report=match.main()
 def test_projection_and_both_owner_padders(self):
  self.assertEqual((self.report['raw_words'],self.report['normalized_words'],self.report['guards'],self.report['insertions'],self.report['omissions']),(142,142,17,0,0))
  self.assertEqual(self.report['real_CSV_negatives'],10)
 def test_complete_guest_packet_and_provider_effects(self):
  from tools.tests import game_composite_burst_151a3150_oracle as guest
  guest.main()
 def test_native32_defined_bytes_and_effective_errors(self):
  from tools.tests import game_composite_burst_151a3150_native as native
  native.main()
 def test_all_instruction_paths_FP_frame_and_controls(self):
  from tools.tests import game_composite_burst_151a3150_proof as proof
  report=proof.main();self.assertTrue(report['whole_function']);self.assertEqual(report['paths'],2)
 def test_actual_timed_parent_dispatch(self):
  from tools.tests import game_composite_burst_151a3150_callers as callers
  callers.main()
if __name__=='__main__':unittest.main()
