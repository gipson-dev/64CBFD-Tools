"""Bounded parent recovery; these tests deliberately award no matching credit."""
import unittest
from tools.experiments import game_actor_bound_burst_150b7b40_screen as source
from tools.tests import game_actor_bound_burst_150b7b40_oracle as guest
class ActorBoundBurstScreen(unittest.TestCase):
 def test_01_source_and_original_assembly(self):self.assertTrue(source.qualify()['passes'])
 def test_02_complete_parent_guest(self):self.assertTrue(guest.main()['passes'])
 def test_03_effective_source_negatives(self):self.assertTrue(source.controls()['passes'])
 @classmethod
 def tearDownClass(cls):source.check_inputs()
if __name__=='__main__':unittest.main()
