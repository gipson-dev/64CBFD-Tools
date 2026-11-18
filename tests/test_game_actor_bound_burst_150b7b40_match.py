"""Full source, proof, native, caller, real-child and strict image gates."""
import unittest
from tools.experiments import game_actor_bound_burst_150b7b40_match as source
from tools.tests import game_actor_bound_burst_150b7b40_match_proof as proof
from tools.tests import game_actor_bound_burst_150b7b40_match_native as native
from tools.tests import game_actor_bound_burst_150b7b40_match_callers as callers
from tools.tests import game_actor_bound_burst_150b7b40_match_children as children
from tools.tests import game_actor_bound_burst_150b7b40_oracle as guest
class ActorBoundBurstMatch(unittest.TestCase):
 def test_01_source_and_original(self):source.qualify_source()
 def test_02_complete_relation_and_controls(self):self.assertTrue(proof.main()['passes'])
 def test_03_real_padders_and_guard_controls(self):
  source.padders();self.assertTrue(source.guard_controls()['passes'])
 def test_04_complete_guest_streams(self):
  previous=guest.p;guest.p=source.OUT
  try:self.assertTrue(guest.main(source.programs())['passes'])
  finally:guest.p=previous
 def test_05_native_exact_transcripts(self):self.assertTrue(native.main()['passes'])
 def test_06_genuine_dispatcher(self):self.assertTrue(callers.main()['passes'])
 def test_07_both_actual_children_and_controls(self):
  self.assertTrue(children.main()['passes']);self.assertTrue(children.controls()['passes'])
 def test_08_actual_Make_and_strict_image(self):source.qualify_image()
 @classmethod
 def tearDownClass(cls):source.check_inputs()
if __name__=='__main__':unittest.main()