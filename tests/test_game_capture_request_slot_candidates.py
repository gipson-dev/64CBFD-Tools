"""ROM-free source-shape and bounded control inventory checks."""
import unittest

from tools.experiments import game_capture_request_slot as source


class CaptureRequestSlotCandidateTests(unittest.TestCase):
    def test_signed_byte_model_boundary(self):
        from tools.tests.test_game_capture_request_slot import RequestOracle,STACK,put
        for value in (0,1,127,128,255):
            memory={STACK+i:0 for i in range(32)}
            put(memory,STACK+16,value,1)
            instance=RequestOracle((0x83A20010,0x03E00008,0),memory,(0,0,0),0).run()
            self.assertEqual(instance.r[2],(value-256 if value&128 else value)&0xFFFFFFFF)

    def test_complete_inline_copy_not_pseudo_call(self):
        self.assertIn('request->payload = *payload;',source.SELECTED)
        self.assertIn('request->state == 0',source.SELECTED)
        self.assertIn('s8 callback, s32 value',source.SELECTED)
        self.assertNotIn('M2C_',source.SELECTED)
        self.assertNotIn('memcpy',source.SELECTED)
        self.assertNotIn('volatile',source.SELECTED)
        self.assertIn('u32 words[9];',source.TYPES)
        self.assertIn('u8 pad0D[3];',source.TYPES)
        self.assertIn('u8 pad35[3];',source.TYPES)

    def test_bounded_groups_and_only_target_replacement(self):
        self.assertEqual([len(list(fn())) for fn in (source.variants,source.schedule_variants,
            source.address_variants,source.interface_variants,source.return_variants)],[7,10,8,9,5])
        before='#include <ultra64.h>\ns32 func_151745F0(){return 0;}\ns32 neighbor(){return 7;}\n'
        after=source.recover(before,source.SELECTED)
        self.assertEqual(after.count(source.SELECTED.rstrip()),1)
        self.assertIn('s32 neighbor(){return 7;}',after)
        with self.assertRaisesRegex(ValueError,'preamble'):
            source.recover(after,source.SELECTED)


if __name__=='__main__':
    unittest.main()
