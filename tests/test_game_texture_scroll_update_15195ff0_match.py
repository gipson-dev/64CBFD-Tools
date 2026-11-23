"""Texture-scroll C, loop induction, guest aliases and strict full-image gates."""
import unittest
from tools.experiments import game_texture_scroll_update_15195ff0_match as p
class TextureScrollUpdate(unittest.TestCase):
 @classmethod
 def setUpClass(cls):p.inspect_source()
 def test_01_symbolic_loop_induction(self):
  from tools.tests.game_texture_scroll_update_15195ff0_symbolic import proof
  proof()
 def test_02_guards_and_GNU_rebases(self):
  from tools.experiments.game_texture_scroll_update_15195ff0_qualification import main
  main()
 def test_03_guest_callers_and_faults(self):
  from tools.tests import game_texture_scroll_update_15195ff0_guest as g
  g.main();g.aliases();g.callers();g.faults()
 def test_04_native_SDK32(self):
  from tools.tests.game_texture_scroll_update_15195ff0_native import main
  main()
 def test_05_actual_Make_and_complete_image(self):p.qualify()
if __name__=='__main__':unittest.main()
