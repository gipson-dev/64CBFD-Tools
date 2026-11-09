"""Full owner, independent guest/native contract and fail-closed image checks."""
import unittest
from tools.experiments import game_positioned_emitter_150e75a0_match as source
from tools.tests import game_positioned_emitter_150e75a0_oracle as guest
from tools.tests import game_positioned_emitter_150e75a0_native as native
from tools.tests import game_positioned_emitter_150e75a0_controls as controls
from tools.tests import game_positioned_emitter_150e75a0_caller as caller
ROOT=source.ROOT
class PositionedEmitterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=source.prepare(ROOT)
    def test_01_owner_actual_Make_and_entire_image(self):
        self.assertEqual(tuple(self.report[n]for n in('words','frame','guards','raw_neighbors','padded_neighbors','strict_unexplained_bytes','image_changed_bytes')),(76,136,43,28,28,0,199))
    def test_02_guest_initialized_bytes_and_ABI(self):guest.main()
    def test_03_native_contract_and_connected_dispatcher(self):native.main()
    def test_04_effective_controls_and_stale_guards(self):controls.main()
    def test_05_all_retail_and_linked_callers(self):caller.main()
    def test_06_corruption_and_scope_rejected(self):
        out=ROOT/source.BUILD;before=(out/'frozen'/source.ELF).read_bytes();actual=(out/'qualified-image/conker.us.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE]
        for at in(0,source.elf_slot_offset(actual,source.ENTRY,source.SIZE),source.elf_slot_offset(actual,0x1510D404,516),len(actual)-1):
            bad=bytearray(actual);bad[at]^=1
            with self.assertRaises(AssertionError):source.strict_image(before,bytes(bad),truth)
        raw,refs=source.payload(out/'qualified-owner.o')
        with self.assertRaises(ValueError):source.checked(bytes([raw[0]^1])+raw[1:],refs)
        for owner,function in(('wrong_owner',source.FUNCTION),(source.OWNER,'wrong_function')):
            with self.assertRaises(ValueError):source.checked(raw,refs,owner,function)
        with self.assertRaises(ValueError):source.checked(raw,{})
if __name__=='__main__':unittest.main()
