import unittest
from tools.experiments import game_draw_list_15188d00_match as packet
from tools.tests import game_draw_list_15188d00_oracle as oracle
from tools.tests import game_draw_list_15188d00_connected as connected
from tools.tests import game_draw_list_15188d00_native as native
from tools.tests import game_draw_list_15188d00_rebase as rebase
class GameDrawListMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_guest_model(self):oracle.run()
 def test_caller_and_fault_prefix(self):connected.run()
 def test_native_and_controls(self):native.run()
 def test_rebase(self):rebase.run()
