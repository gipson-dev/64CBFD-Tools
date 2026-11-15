"""Qualified projected renderer, full semantic, CFG and installed-input gates."""
import unittest
from tools.tests import test_game_side_ring_renderer_1519fe6c_recovery as old
from tools.experiments import game_side_ring_renderer_1519fe6c_match as match
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
class SideRingRendererMatchTests(old.SideRingRendererRecoveryTests):
 @classmethod
 def setUpClass(cls):
  match.main();g.programs=match.programs
 def test_complete_private_source(self):
  from tools.tests import game_side_ring_renderer_1519fe6c_callers as callers
  from tools.tests import game_side_ring_renderer_1519fe6c_native as native
  match.check_inputs();g.main();callers.main();native.main();match.check_inputs()
 def test_complete_cut_composition_and_CFG(self):
  from tools.tests import game_side_ring_renderer_1519fe6c_coverage as coverage
  from tools.tests import game_side_ring_renderer_1519fe6c_composition as proof
  coverage.main();proof.main();match.check_inputs()
if __name__=='__main__':unittest.main()
