import unittest
from tools.experiments import game_hud_state_15178eb0_match as packet
from tools.tests import game_hud_state_15178eb0_oracle as oracle
from tools.tests import game_hud_state_15178eb0_connected as connected
from tools.tests import game_hud_state_15178eb0_native as native
from tools.tests import game_hud_state_15178eb0_rebase as rebase
from tools.tests import game_hud_state_15178eb0_splat as splat
class GameHudStateMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_guest_model(self):oracle.run()
 def test_caller_and_fault_prefix(self):connected.run()
 def test_native_and_controls(self):native.run()
 def test_rebase(self):rebase.run()
 def test_splat_inventory(self):splat.run()
