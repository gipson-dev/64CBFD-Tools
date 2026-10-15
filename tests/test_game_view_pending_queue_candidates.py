"""Consumer-independent recovery, guard scope and native carrier checks."""
import unittest

from tools.experiments import game_view_pending_queue as source
from tools.tests import game_view_pending_queue_native as native
from tools.tests import game_view_pending_queue_oracle as model


class ViewPendingQueueCandidateTests(unittest.TestCase):
    def test_complete_recovery_preserves_neighbors_and_guard_prefix(self):
        before = 'extern u8 *D_800BE628;\ns32 func_1510B3B0(){return 0;}\ns32 next(){return 7;}\n'
        recovered = source.recover(before)
        self.assertIn(source.BODY.rstrip(), recovered)
        self.assertTrue(recovered.endswith('s32 next(){return 7;}\n'))
        self.assertEqual(recovered.count('extern s32 D_80082FA0;'), 1)
        self.assertEqual(source.guard_manifest(b'header\n'), b'header\n'+source.GUARD_ROWS.encode())
        with self.assertRaises(AssertionError):
            source.guard_manifest(source.guard_manifest(b'header\n'))
        with self.assertRaises(AssertionError):
            source.guard_manifest(b'header')
        forms = dict(source.variants())
        self.assertEqual(len(forms), 24)
        self.assertTrue(all('D_800D9AF0 = 0;' in body and 'func_1510B128(' in body for body in forms.values()))

    def test_endian_alias_carrier_and_six_changed_semantic_controls(self):
        rows = native.vectors()
        self.assertEqual(len(rows), 2352)
        self.assertTrue(any(model.read(row['memory'], model.COUNT) == 5 for row in rows))
        text = native.program(rows[:1])
        self.assertIn(source.BODY, text)
        self.assertIn('0x40^3', text)
        self.assertEqual(len(native.negatives(rows)), 6)
        for label, body, _, status in native.negatives(rows):
            self.assertNotEqual(body, source.BODY, label)
            self.assertIn(status, (1, 2))


if __name__ == '__main__':
    unittest.main()
