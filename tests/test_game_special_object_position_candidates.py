"""ROM-free source, frame encoding and fail-closed guard-manifest checks."""
import unittest

from tools.experiments import game_special_object_position as source


class SpecialObjectPositionCandidateTests(unittest.TestCase):
    def test_only_body_and_private_prototypes_are_replaced(self):
        before = '#include <ultra64.h>\ns32 func_1511F31C(){return 0;}\ns32 neighbor(){return 7;}\n'
        after = source.recover(before)
        self.assertEqual(after.count(source.SELECTED.rstrip()), 1)
        self.assertIn('s32 neighbor(){return 7;}', after)
        self.assertIn('f32 matrix[4][4];', after)
        self.assertIn('u16 selector = *(u16 *)(object + 0x3E);', after)
        self.assertNotIn('volatile', after)
        self.assertNotIn('M2C_', after)
        with self.assertRaisesRegex(ValueError, 'preamble'):
            source.recover(after)

    def test_both_guards_change_only_balanced_stack_adjustment_immediates(self):
        self.assertEqual([offset for offset, _, _ in source.GUARDS], [0, 0xC0])
        first, last = source.GUARDS
        self.assertEqual(first[1:] , (0x27BDFF78, 0x27BDFF70))
        self.assertEqual(last[1:], (0x27BD0088, 0x27BD0090))
        for _, expected, replacement in source.GUARDS:
            self.assertEqual(expected >> 16, 0x27BD)
            self.assertEqual(replacement >> 16, 0x27BD)
        self.assertEqual((first[1] + last[1]) & 65535, 0)
        self.assertEqual((first[2] + last[2]) & 65535, 0)

    def test_guard_append_keeps_raw_prefix_and_rejects_duplicates(self):
        before = b'owner,function,offset,expected,replacement\r\n'
        after = source.guard_manifest(before)
        self.assertTrue(after.startswith(before))
        self.assertEqual(after[len(before):].count(b'\n'), 2)
        with self.assertRaises(ValueError):
            source.guard_manifest(after)
        with self.assertRaises(ValueError):
            source.guard_manifest(before.rstrip())
        with self.assertRaises(ValueError):
            source.normalize(b'\0' * 204, source.RELOCATIONS)


if __name__ == '__main__':
    unittest.main()
