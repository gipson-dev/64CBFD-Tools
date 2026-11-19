"""Qualification of the private attached-actor accumulator recovery."""
import unittest
from tools.experiments import game_attached_accumulator_150ba55c_recovery as s
from tools.tests import game_attached_accumulator_150ba55c_oracle as g
class AttachedAccumulatorRecoveryTests(unittest.TestCase):
 def test_01_complete_owner_and_callback_census(self):
  self.assertTrue(s.qualify()['passes']);self.assertEqual(s.census()['index'],82)
 def test_02_guest_and_mutable_retained_buffers(self):self.assertTrue(g.run(s.state())['passes'])
 def test_03_complete_original_dispatcher(self):
  from tools.tests import game_attached_accumulator_150ba55c_caller as caller
  self.assertTrue(caller.main()['passes'])
 def test_04_native_sdk32_with_effective_controls(self):
  from tools.tests import game_attached_accumulator_150ba55c_native as native
  self.assertTrue(native.run(s.state())['passes'])
 def test_05_complete_private_and_finite_loop_relation(self):
  from tools.tests import game_attached_accumulator_150ba55c_proof as proof
  self.assertTrue(proof.run(s.state())['passes'])
if __name__=='__main__':unittest.main()
