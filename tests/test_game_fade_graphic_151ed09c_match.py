import unittest
from tools.experiments import game_fade_graphic_151ed09c_match as packet
from tools.tests import game_fade_graphic_151ed09c_oracle as oracle
from tools.tests import game_fade_graphic_151ed09c_faults as faults
from tools.tests import game_fade_graphic_151ed09c_connected as connected
from tools.tests import game_fade_graphic_151ed09c_native as native
from tools.tests import game_fade_graphic_151ed09c_rebase as rebase
class FadeGraphicMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_guest_model(self):oracle.run()
 def test_fault_prefix(self):faults.run()
 def test_indirect_caller(self):connected.run()
 def test_native_and_controls(self):native.run()
 def test_rebase(self):rebase.run()
