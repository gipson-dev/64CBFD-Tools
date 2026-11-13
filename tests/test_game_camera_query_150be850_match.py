"""Script-query and camera-condition qualification with modeled providers."""
import runpy,unittest
from tools.experiments import game_camera_query_150be850_match as packet
from tools.tests import game_camera_query_150be850_rebase as rebase
from tools.tests import game_camera_query_150be850_guards as guards
from tools.tests import game_camera_query_150be850_table as table

class CameraQueryMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.proposals=packet.prepare()
 def test_helper_guest(self):runpy.run_path(str(packet.OUT/'query-guest.py'))
 def test_camera_guest(self):runpy.run_path(str(packet.OUT/'guest.py'))
 def test_connected_query(self):runpy.run_path(str(packet.OUT/'camera-connected.py'))
 def test_original_dispatcher(self):runpy.run_path(str(packet.OUT/'camera-dispatcher.py'))
 def test_fault_prefixes(self):runpy.run_path(str(packet.OUT/'faults.py'))
 def test_helper_native(self):runpy.run_path(str(packet.OUT/'query-native.py'))
 def test_camera_native(self):runpy.run_path(str(packet.OUT/'camera-native.py'))
 def test_relocations(self):rebase.run()
 def test_guard_preimages(self):guards.run()
 def test_query_table_abi(self):table.run(self.proposals)

if __name__=='__main__':unittest.main(verbosity=2)
