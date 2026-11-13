import unittest
from tools.experiments import game_camera_direction_15122980_match as packet
from tools.tests import game_camera_direction_15122980_oracle as oracle
from tools.tests import game_camera_direction_15122980_connected as connected
from tools.tests import game_camera_direction_15122980_native as native
from tools.tests import game_camera_direction_15122980_rebase as rebase
class GameCameraDirectionMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_guest_model(self):oracle.run()
 def test_caller_and_fault_prefix(self):connected.run()
 def test_native_and_controls(self):native.run()
 def test_rebase(self):rebase.run()
