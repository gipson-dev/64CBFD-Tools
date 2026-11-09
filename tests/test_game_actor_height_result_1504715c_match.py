"""Full actor/result body, ABI, alias and insertion qualification."""
import unittest
from tools.experiments import game_actor_height_result_1504715c_match as source
from tools.tests import game_actor_height_result_1504715c_oracle as guest
from tools.tests import game_actor_height_result_1504715c_native as native
from tools.tests import game_actor_height_result_1504715c_controls as controls
from tools.tests import game_actor_height_result_1504715c_caller as caller
ROOT=source.ROOT
class ActorHeightResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=source.prepare(ROOT)
    def test_01_owner_actual_Make_and_entire_image(self):
        self.assertEqual(tuple(self.report[n]for n in('words','raw_words','frame','guards','insertions','raw_neighbors','padded_neighbors','strict_unexplained_bytes','image_changed_bytes')),(89,87,24,54,2,42,42,0,232))
    def test_02_guest_aliases_raw_truth_and_original_helper(self):guest.main()
    def test_03_native_contract_and_effective_controls(self):native.main()
    def test_04_insertions_stale_guards_and_IDO_controls(self):controls.main()
    def test_05_retail_census_and_real_native_caller(self):caller.main()
    def test_06_corruption_and_scope_rejected(self):
        out=ROOT/source.BUILD;before=(out/'frozen'/source.ELF).read_bytes();actual=(out/'qualified-image/conker.us.elf').read_bytes();truth=(ROOT/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE]
        for at in(0,source.elf_slot_offset(actual,source.ENTRY,source.SIZE),source.elf_slot_offset(actual,0x150E75A0,304),len(actual)-1):
            bad=bytearray(actual);bad[at]^=1
            with self.assertRaises(AssertionError):source.strict_image(before,bytes(bad),truth)
        raw,refs=source.payload(out/'qualified-owner.o')
        with self.assertRaises(ValueError):source.checked(bytes([raw[0]^1])+raw[1:],refs)
        for owner,function in(('wrong_owner',source.FUNCTION),(source.OWNER,'wrong_function')):
            with self.assertRaises(ValueError):source.checked(raw,refs,owner,function)
        with self.assertRaises(ValueError):source.checked(raw,{})
if __name__=='__main__':unittest.main()
