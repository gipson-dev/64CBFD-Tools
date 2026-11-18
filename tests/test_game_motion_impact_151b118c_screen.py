"""Bounded semantic qualification; these drafts are not installed matches."""
import unittest
from tools.experiments import game_motion_impact_151b118c_screen as source
from tools.tests import game_motion_impact_151b118c_oracle as guest
from tools.tests import game_motion_impact_151b118c_native as native
from tools.tests import game_motion_impact_151b118c_callers as callers
class MotionImpactScreen(unittest.TestCase):
 def test_01_source_and_neighbors(self):self.assertEqual(source.qualify_source()['c_match_credit'],0)
 def test_02_guest_semantics(self):self.assertTrue(guest.main()['passes'])
 def test_03_native_source_and_controls(self):self.assertTrue(native.main()['passes'])
 def test_04_original_dispatch_window(self):self.assertTrue(callers.main()['passes'])
 @classmethod
 def tearDownClass(cls):source.check_inputs()
if __name__=='__main__':unittest.main()
