"""Guarded words, original classifier/dispatch, private faults and SDK32."""
import unittest
from tools.experiments import game_source_heading_trail_151945cc_match as packet
from tools.tests import game_source_heading_trail_151945cc_guest as guest
from tools.tests import game_source_heading_trail_151945cc_boundaries as boundaries
from tools.tests import game_source_heading_trail_151945cc_callers as callers
from tools.tests import game_source_heading_trail_151945cc_connected as connected
from tools.tests import game_source_heading_trail_151945cc_native as native
class SourceHeadingTrail(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_owner_guard_history_and_complete_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal'])
  self.assertEqual((self.report['words'],self.report['guards'],self.report['exclusions']),(114,9,0))
  self.assertEqual(self.report['unchanged_owner_functions'],28)
 def test_02_mutating_double_single_guest_and_faults(self):self.assertEqual(guest.main()['covered_words'],114)
 def test_03_padders_rebases_and_effective_guard_controls(self):self.assertEqual(boundaries.main()['GNU_rebased_links'],16)
 def test_04_original_dispatch_and_classifier(self):
  self.assertTrue(callers.main()['source_actor_context_ABI'])
  self.assertEqual(connected.main()['covered_classifier_words'],63)
 def test_05_defined_SDK32_and_effective_source_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),10)
if __name__=='__main__':unittest.main(verbosity=2)
