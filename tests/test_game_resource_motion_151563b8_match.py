"""Focused semantic, native, caller, relocation and image gates."""
import unittest
from tools.experiments import game_resource_motion_151563b8_match as source
from tools.tests import game_resource_motion_151563b8_oracle as guest
from tools.tests import game_resource_motion_151563b8_native as native
from tools.tests import game_resource_motion_151563b8_caller as caller
from tools.tests import game_resource_motion_151563b8_controls as controls
ROOT=source.ROOT
class ResourceMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=source.prepare(ROOT)
    def test_01_owner_and_strict_image(self):
        self.assertEqual((self.report['words'],self.report['raw_neighbors'],self.report['padded_neighbors'],self.report['strict_unexplained_bytes'],self.report['image_changed_bytes']),(80,25,25,0,233))
    def test_02_guest_and_fault_prefixes(self):guest.main()
    def test_03_native_and_defined_controls(self):native.main()
    def test_04_original_dispatcher(self):caller.main()
    def test_05_relocations_and_effective_controls(self):controls.main()
if __name__=='__main__':unittest.main()
