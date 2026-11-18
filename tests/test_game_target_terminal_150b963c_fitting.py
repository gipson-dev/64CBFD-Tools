"""Fresh changed-source semantic checks and complete bounded finite/private relation."""
import unittest
from tools.experiments import game_target_terminal_150b963c_fitting as s
from tools.tests import game_target_terminal_150b963c_oracle as guest
from tools.tests import game_target_terminal_150b963c_fitting_native as native
from tools.tests import game_target_terminal_150b963c_callers as caller
from tools.tests import game_target_terminal_150b963c_proof as proof

class TargetTerminalFitting(unittest.TestCase):
 def test_01_changed_source_owner_and_retail(self):self.assertEqual(len(s.prepare()['raw_words']),434)
 def test_02_complete_guest_semantics(self):self.assertEqual(guest.run(s.state())['cases'],1920)
 def test_03_changed_native_and_controls(self):
  row=native.run(s.state());self.assertEqual((row['cases_per_positive_run'],row['positive_runs'],row['effective_negatives']),(384,3,10))
 def test_04_actual_callback_window(self):self.assertEqual(caller.run(s.state())['cases'],1920)
 def test_05_complete_finite_private_relation(self):
  row=proof.main(s.state());self.assertEqual((row['complete_paths'],row['related_private_and_incoming_bytes'],len(row['effective_negatives'])),(77,400,16))
 @classmethod
 def tearDownClass(cls):s.check_inputs()
