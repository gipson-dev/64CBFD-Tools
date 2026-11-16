"""Whole ring updater: exact code, finite memory semantics and actual callback."""
import unittest
from tools.experiments import game_ring_update_151a361c_recovery as source
class RingUpdateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not(source.FROZEN/'fingerprints.json').exists():raise unittest.SkipTest('prepared immutable ring baseline absent')
  source.compile_and_check()
  from tools.experiments import game_ring_update_151a361c_match as match
  cls.report=match.main()
 def test_direct_owner_corruption_and_GNU_rebases(self):
  self.assertEqual((self.report['raw_words'],self.report['normalized_words'],self.report['guards']),(105,105,0))
  self.assertEqual(self.report['raw_and_binding_corruptions'],109);self.assertEqual(self.report['real_CSV_negatives'],2)
 def test_guest_ring_boundaries_and_aliases(self):
  from tools.tests import game_ring_update_151a361c_oracle as guest
  guest.main()
 def test_native_wrapping_and_effective_source_errors(self):
  from tools.tests import game_ring_update_151a361c_native as native
  native.main()
 def test_all_word_identity_and_semantic_controls(self):
  from tools.tests import game_ring_update_151a361c_proof as proof
  self.assertTrue(proof.main()['whole_function'])
 def test_actual_parent_callback_and_release(self):
  from tools.tests import game_ring_update_151a361c_callers as callers
  callers.main()
if __name__=='__main__':unittest.main()
