"""Original helper/tail return evidence, with no function-matching credit."""
import unittest
from tools.experiments import game_camera_transition_15128030_return_audit as audit
class CameraTransitionReturnAudit(unittest.TestCase):
 def test_original_helper_and_completion_returns(self):
  report=audit.run()
  self.assertEqual((report['connected_float_helper_cases'],report['original_tail_window_cases']),(180,120))
  self.assertEqual(report['effective_controls'],['angle-helper-clobbered-V0'])
  self.assertTrue(all(not h['V0_written'] and h['original_equals_current'] for h in report['helpers']))
  self.assertEqual(report['matching_credit'],0)
if __name__=='__main__':unittest.main(verbosity=2)
