"""Layout-slot C, ABI home, normalization and strict production-image gates."""
import unittest
from tools.experiments import game_layout_slot_registration_15195aa8_match as p
class LayoutSlotRegistration(unittest.TestCase):
 @classmethod
 def setUpClass(cls):p.inspect_source()
 def test_01_symbolic_induction_and_ABI_home(self):
  from tools.tests.game_layout_slot_registration_15195aa8_symbolic import proof
  proof()
 def test_02_guards_and_GNU_rebases(self):
  from tools.experiments.game_layout_slot_registration_15195aa8_qualification import main
  main()
 def test_03_guest_callers_and_faults(self):
  from tools.tests import game_layout_slot_registration_15195aa8_guest as g
  g.main();g.callers();g.faults()
 def test_04_native_SDK32(self):
  from tools.tests.game_layout_slot_registration_15195aa8_native import main
  main()
 def test_05_actual_Make_and_complete_image(self):p.qualify()
if __name__=='__main__':unittest.main()
