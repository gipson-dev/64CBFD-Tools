import unittest
from tools.experiments import game_fade_update_151e4ee8_match as packet
from tools.tests import game_fade_update_151e4ee8_oracle as oracle
from tools.tests import game_fade_update_151e4ee8_connected as connected
from tools.tests import game_fade_update_151e4ee8_native as native
from tools.tests import game_fade_update_151e4ee8_rebase as rebase
class GameFadeUpdateMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_guest_model(self):oracle.run()
 def test_state_dispatch_and_fault_prefix(self):connected.run()
 def test_native_and_controls(self):native.run()
 def test_rebase(self):rebase.run()
