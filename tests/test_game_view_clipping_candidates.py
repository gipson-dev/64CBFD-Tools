"""Consumer-independent clipping source, field layout and guard-scope checks."""
import unittest

from tools.experiments import game_view_clipping_commands as source
from tools.tests import game_view_clipping_native as native


class ViewClippingCandidateTests(unittest.TestCase):
    def test_complete_recovery_preserves_neighbor_and_private_view_extent(self):
        before='extern u8 D_800D9AF0;\n    u8 padding84[0xFC];\ns32 func_1510B458(){return 0;}\ns32 func_1510B51C(){return 0;}\nvoid next(void){}\n'
        after=source.recover(before)
        self.assertIn(source.COMMAND_BODY.rstrip(),after)
        self.assertIn(source.QUEUE_BODY.rstrip(),after)
        self.assertTrue(after.endswith('void next(void){}\n'))
        self.assertIn('f32 matrixScale;\n    u8 padding88[0xF8];',after)
        self.assertEqual(4+0xF8,0xFC)
        self.assertEqual(len(dict(source.variants())),12)

    def test_guard_scope_and_actual_native_bodies(self):
        self.assertEqual(source.guard_manifest(b'header\n'),b'header\n'+source.GUARD_ROWS.encode())
        with self.assertRaises(AssertionError):
            source.guard_manifest(source.guard_manifest(b'header\n'))
        with self.assertRaises(AssertionError):
            source.guard_manifest(b'header')
        rows=native.vectors()
        self.assertEqual(len(rows),180)
        self.assertEqual(len(native.negatives(rows)),9)
        owner=source.recover('extern u8 D_800D9AF0;\ntypedef struct {u8 padding84[0xFC];} ViewProjection138520;\n#define PROJECTION_VIEWS_138520 ((ViewProjection138520*)D_800BE628)\nextern f32 D_800A2C24;\ns32 func_1510B458(){return 0;}\ns32 func_1510B51C(){return 0;}\n')
        text=native.program(owner,rows[:1])
        self.assertIn(source.COMMAND_BODY,text)
        self.assertIn(source.QUEUE_BODY,text)
        self.assertIn('0xD8^3',text)


if __name__ == '__main__':
    unittest.main()
