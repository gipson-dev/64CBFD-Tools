"""Qualification of an uninstalled semantic surface-impact recovery."""
import json,unittest
from tools.experiments import game_surface_impact_150b9ed0_screen as s
from tools.tests import game_surface_impact_150b9ed0_oracle as g

class SurfaceImpactRecoveryTests(unittest.TestCase):
 def test_01_complete_owner_and_caller_integrity_census(self):
  self.assertTrue(s.qualify()['passes']);self.assertEqual(s.census()['retail_integrity_sum'],'0x3843095e')
 def test_02_independent_guest_and_complete_descriptors(self):
  self.assertTrue(g.run(s.state())['passes'])
 def test_03_actual_caller_window(self):
  self.assertTrue(g.caller(s.state())['passes'])
 def test_04_sdk32_native_and_effective_controls(self):
  from tools.tests import game_surface_impact_150b9ed0_native as native
  self.assertTrue(native.run(s.state())['passes'])

if __name__=='__main__':unittest.main()
