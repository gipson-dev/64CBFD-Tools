"""Focused semantic, native, caller, relocation and image gates."""
import unittest
from tools.experiments import game_resource_matrix_15157dec_match as source
from tools.tests import game_resource_matrix_15157dec_oracle as guest
from tools.tests import game_resource_matrix_15157dec_native as native
from tools.tests import game_resource_matrix_15157dec_caller as caller
from tools.tests import game_resource_matrix_15157dec_controls as controls
ROOT=source.ROOT
class ResourceMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=source.prepare(ROOT)
    def test_01_owner_and_strict_image(self):
        self.assertEqual((self.report['words'],self.report['raw_neighbors'],self.report['padded_neighbors'],self.report['strict_unexplained_bytes'],self.report['image_changed_bytes']),(101,25,25,0,319))
    def test_02_guest_and_fault_prefixes(self):guest.main()
    def test_03_native_and_defined_controls(self):native.main()
    def test_04_original_dispatcher(self):caller.main()
    def test_05_relocations_and_effective_controls(self):controls.main()
    def test_06_original_rotation_connection(self):caller.connection_checks()
if __name__=='__main__':unittest.main()
