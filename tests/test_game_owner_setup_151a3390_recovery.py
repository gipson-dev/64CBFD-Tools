"""Prepared direct owner-setup match: representation, callers and production."""
import unittest
from tools.experiments import game_owner_setup_151a3390_recovery as source
class OwnerSetupTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not(source.FROZEN/'fingerprints.json').exists():raise unittest.SkipTest('prepared immutable owner-setup baseline absent')
  source.compile_and_check()
  from tools.experiments import game_owner_setup_151a3390_match as match
  cls.report=match.main()
 def test_direct_words_both_padders_corruptions_and_rebases(self):
  self.assertEqual((self.report['raw_words'],self.report['normalized_words'],self.report['guards']),(93,93,0))
  self.assertEqual(self.report['raw_and_binding_corruptions'],102)
  self.assertEqual(self.report['real_CSV_negatives'],2)
 def test_independent_guest_descriptor_frame_and_five_calls(self):
  from tools.tests import game_owner_setup_151a3390_oracle as guest
  guest.main()
 def test_native_defined_bytes_and_effective_source_errors(self):
  from tools.tests import game_owner_setup_151a3390_native as native
  native.main()
 def test_instruction_identity_and_semantic_controls(self):
  from tools.tests import game_owner_setup_151a3390_proof as proof
  self.assertTrue(proof.main()['whole_function'])
 def test_three_actual_callers_and_provider_ABIs(self):
  from tools.tests import game_owner_setup_151a3390_callers as callers
  callers.main()
if __name__=='__main__':unittest.main()
