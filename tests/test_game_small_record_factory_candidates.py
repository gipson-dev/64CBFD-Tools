"""ROM-free packed ABI, declaration ownership and direct-match source scope."""
import unittest

from tools.experiments import game_small_record_factory as source


class SmallRecordFactoryCandidateTests(unittest.TestCase):
    def test_only_target_and_typed_private_secondary_declaration_change(self):
        before = source.previous.DECLARATION + 's32 func_1516D4E8() {\n    return 0;\n}\ns32 other(){return 7;}\n'
        after = source.recovered_owner(before)
        self.assertEqual(after, source.previous.DECLARATION + source.DECLARATION + source.SELECTED + 's32 other(){return 7;}\n')
        with self.assertRaises(ValueError):
            source.recovered_owner(after)

    def test_real_local_lifetime_and_typed_position_scale_pointers(self):
        self.assertEqual(len(source.PARAM_TYPES), 31)
        self.assertLess(source.SELECTED.index('u8 *record;'), source.SELECTED.index('s32 kind;'))
        self.assertIn('(s16 *)(record + 0xE), (s16 *)(record + 0x14)', source.SELECTED)
        self.assertIn('*(struct PositionScaleRecord71820 **)(record + 0x30)', source.SELECTED)
        for bad in ('volatile', 'GLOBAL_ASM', 'sp34', 'savedRecord'):
            self.assertNotIn(bad, source.SELECTED)

    def test_all_45_input_paths_and_full_hashes_are_unique(self):
        self.assertEqual(len(source.PATHS), 45)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        self.assertEqual(len(set(source.PATHS.values())), 45)
        for value in source.BASELINE.values():
            self.assertRegex(value, '^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()
