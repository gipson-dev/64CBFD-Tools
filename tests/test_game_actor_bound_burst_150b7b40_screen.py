"""Bounded parent recovery; these tests deliberately award no matching credit."""
import unittest
from tools.experiments import game_actor_bound_burst_150b7b40_screen as source
from tools.tests import game_actor_bound_burst_150b7b40_oracle as guest
from tools.tests import game_actor_bound_burst_150b7b40_native as native
from tools.tests import game_actor_bound_burst_150b7b40_callers as callers
from tools.tests import game_actor_bound_burst_150b7b40_frame as frame
class ActorBoundBurstScreen(unittest.TestCase):
 def test_01_source_and_original_assembly(self):self.assertTrue(source.qualify()['passes'])
 def test_02_complete_parent_guest(self):self.assertTrue(guest.main()['passes'])
 def test_03_effective_source_negatives(self):self.assertTrue(source.controls()['passes'])
 def test_04_native_exact_transcripts(self):self.assertTrue(native.main()['passes'])
 def test_05_genuine_actor_state_caller(self):self.assertTrue(callers.main()['passes'])
 def test_06_private_frame_ledger(self):
  report=frame.main();self.assertEqual([v['frame']for v in report['streams']],[616,600]);self.assertEqual([v['unmapped_touched_runs']for v in report['streams']],[[[-204,8]],[[-168,8]]])
 @classmethod
 def tearDownClass(cls):source.check_inputs()
if __name__=='__main__':unittest.main()
