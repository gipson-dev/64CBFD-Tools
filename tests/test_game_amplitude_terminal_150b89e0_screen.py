"""Complete semantic screen; no production installation or matching credit."""
import unittest
from tools.experiments import game_amplitude_terminal_150b89e0_screen as s
from tools.tests import game_amplitude_terminal_150b89e0_oracle as guest
from tools.tests import game_amplitude_terminal_150b89e0_native as native
from tools.tests import game_amplitude_terminal_150b89e0_callers as callers

class AmplitudeTerminalScreen(unittest.TestCase):
 def test_01_owner_and_unproved_frame_boundary(self):
  state=s.prepare();self.assertEqual(s.frame_diagnostic(state)['remaining_differences'],25)
 def test_02_guest_complete_semantics(self):
  result=guest.run(s.state());self.assertEqual((result['cases'],result['retail_words_visited'],result['unvisited_words']),(2304,344,[259]))
 def test_03_native_and_effective_controls(self):
  result=native.run(s.state());self.assertEqual((result['cases_per_positive_run'],result['positive_runs'],result['effective_negatives']),(288,3,12))
 def test_04_complete_real_terrain_dispatcher(self):
  result=callers.run(s.state());self.assertEqual((result['cases'],result['complete_parent_words_visited']),(1152,80))
 def test_05_other_real_dispatch_window(self):self.assertEqual(callers.other_window(s.state())['cases'],96)
 @classmethod
 def tearDownClass(cls):s.check_inputs()
if __name__=='__main__':unittest.main()
