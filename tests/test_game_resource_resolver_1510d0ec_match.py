"""Focused body, behavior, normalization and full-image gates."""
import unittest
from tools.experiments import game_resource_resolver_1510d0ec_match as source
from tools.tests import game_resource_resolver_1510d0ec_oracle as guest
from tools.tests import game_resource_resolver_1510d0ec_native as native
from tools.tests import game_resource_resolver_1510d0ec_controls as controls
from tools.tests import game_resource_resolver_1510d0ec_caller as caller
ROOT=source.ROOT
class ResourceResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=source.prepare(ROOT)
    def test_01_owner_and_strict_image(self):
        self.assertEqual(tuple(self.report[n]for n in('words','guards','raw_neighbors','padded_neighbors','strict_unexplained_bytes','image_changed_bytes')),(162,76,13,13,0,485))
    def test_02_guest_connected_helpers_and_faults(self):guest.main()
    def test_03_native_contract(self):native.main()
    def test_04_effective_controls_and_stale_guards(self):controls.main()
    def test_06_all_retail_caller_windows(self):caller.main()
    def test_05_image_corruption_rejected(self):
        out=ROOT/source.BUILD;before=(out/'frozen'/source.ELF).read_bytes();actual=(out/'qualified-image/conker.us.elf').read_bytes();truth=(out/'retail-slot.bin').read_bytes()
        for at in(0,source.elf_slot_offset(actual,source.ENTRY,648),source.elf_slot_offset(actual,0x150A32B4,124),len(actual)-1,0x2BC354,0x2FD6EB):
            bad=bytearray(actual);bad[at]^=1
            with self.assertRaises(AssertionError):source.strict_image(before,bytes(bad),truth)
if __name__=='__main__':unittest.main()
