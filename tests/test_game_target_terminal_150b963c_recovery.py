"""Private semantic recovery gates; matching and installation remain separate."""
import unittest
from tools.experiments import game_target_terminal_150b963c_screen as s
from tools.tests import game_target_terminal_150b963c_oracle as guest
from tools.tests import game_target_terminal_150b963c_native as native
from tools.tests import game_target_terminal_150b963c_callers as caller

class TargetTerminalRecovery(unittest.TestCase):
 def test_01_full_owner_source_and_retail(self):self.assertEqual(len(s.prepare()['raw_words']),437)
 def test_02_complete_guest_semantics(self):self.assertEqual(guest.run(s.state())['cases'],1920)
 def test_03_native_and_effective_controls(self):
  row=native.run(s.state());self.assertEqual((row['cases_per_positive_run'],row['positive_runs'],row['effective_negatives']),(384,3,10))
 def test_04_original_callback_dispatch(self):self.assertEqual(caller.run(s.state())['cases'],1920)
 @classmethod
 def tearDownClass(cls):s.check_inputs()
