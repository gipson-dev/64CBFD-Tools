"""Qualify the entire ordered normal execution without assigning matching credit."""
import unittest
from unittest.mock import patch
from tools.experiments import game_actor_burst_150bbb5c_full as source
from tools.experiments import game_actor_burst_150bbb5c_recovery as previous
from tools.experiments import game_actor_burst_150bbb5c_ordered as ordered
from tools.tests import game_actor_burst_150bbb5c_oracle as guest
from tools.tests import game_actor_burst_150bbb5c_native as native
from tools.tests import game_actor_burst_150bbb5c_caller as caller

class FullActorBurstTests(unittest.TestCase):
 def test_01_owner_and_full_normal_relation(self):
  row=source.qualify_source()
  self.assertEqual((row['raw_words'],row['frame'],row['symbolic_paths']),(591,624,80))
  self.assertTrue(row['full_normal_execution_relation_proved'])
  self.assertFalse(row['physical_byte_match'])
 def test_02_guest_values_and_early_fault(self):
  with patch.object(previous,'state',source.state):
   self.assertEqual(guest.run()['cases'],274)
   self.assertEqual(guest.faults()['programs'],2)
 def test_03_native_sdk32_with_controls(self):
  with patch.object(previous,'PIN',dict(previous.PIN,body=source.PIN['body'])):
   self.assertEqual(native.run()['cases_per_positive_run'],384)
 def test_04_original_caller_connection(self):
  with patch.object(ordered,'state',source.state):
   self.assertEqual(caller.run()['cases'],3072)
   self.assertEqual(caller.controls()['effective_controls'],6)
 def test_05_effective_full_relation_controls(self):
  self.assertEqual(source.full_controls()['effective_controls'],13)
 @classmethod
 def tearDownClass(cls):source.check_inputs()
if __name__=='__main__':unittest.main()
