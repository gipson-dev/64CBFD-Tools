"""Consumer-independent source, ownership, guards and provider boundaries."""
import unittest

from tools.experiments import game_view_matrix_pass as source
from tools.tests import game_view_matrix_pass_native as native


class ViewMatrixPassCandidateTests(unittest.TestCase):
    def test_recovery_guard_scope_and_single_progress_ownership_change(self):
        before='extern u8 D_800D9B90[], D_800D9BD0[], D_800D9C10[];\ns32 func_1510B690(){return 0;}\nvoid next(void){}\n'
        after=source.recover(before)
        self.assertIn(source.BODY.rstrip(),after)
        self.assertTrue(after.endswith('void next(void){}\n'))
        self.assertEqual(source.BODY,dict(source.variants())['typed-fixed-array-temporary-first-s16'])
        self.assertEqual(len(dict(source.variants())),25)
        self.assertEqual(source.guard_manifest(b'header\n'),b'header\n'+source.GUARD_ROWS.encode())
        with self.assertRaises(AssertionError):
            source.guard_manifest(source.guard_manifest(b'header\n'))
        before=b'version,section,filename,function,vram,size,language\r\nus,game,other,other,1,4,c\r\nus,game,generated_D4E10,func_150A7A48,353008200,312,c\r\n'
        expected=before.replace(b'353008200,312,c\r\n',b'353008200,312,asm\r\n')
        self.assertEqual(source.expected_progress(before),expected)
        with self.assertRaises(ValueError):
            source.expected_progress(expected)

    def test_original_assembly_extent_and_host_provider_boundary(self):
        original='glabel func_150A7A48\n    swc1 $f20,-0x20($sp)\nendlabel func_150A7A48\n    /* 00000000 */ nop\n    /* 00000000 */ nop\n'
        text=source.restored_multiply_assembly(original)
        self.assertTrue(text.endswith('    /* 00000000 */ nop\nendlabel func_150A7A48\n'))
        before='void older(void){}\ns32 func_150A7A48(){return 0;}\n'
        restored=source.restored_multiply_owner(before)
        self.assertTrue(restored.startswith('void older(void){}\n'))
        self.assertIn('#pragma GLOBAL_ASM(',restored)
        self.assertNotIn('return 0;',restored)
        self.assertIn(0x7F812345,native.trig_returns(False))
        self.assertNotIn(0x7F812345,native.trig_returns(True))
        self.assertIn(0x7FC12345,native.trig_returns(True))


if __name__=='__main__':
    unittest.main()
