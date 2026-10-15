"""ROM-free scope, width and frozen-input checks."""
import unittest

from tools.experiments import game_factory_preset_wrapper as source


class FactoryPresetWrapperCandidateTests(unittest.TestCase):
    def test_only_the_target_placeholder_is_replaced(self):
        before = 's32 func_1516F1C0() {\n    return 0;\n}\ns32 neighbor(){return 7;}\n'
        self.assertEqual(source.recovered_owner(before), source.SELECTED + 's32 neighbor(){return 7;}\n')
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            source.recovered_owner(source.SELECTED)

    def test_narrow_only_the_third_input_without_guards_or_invented_names(self):
        self.assertIn('0, 0, arg1,', source.SELECTED)
        self.assertIn('0xA, 0xA, arg0,', source.SELECTED)
        self.assertIn('2, (u8) arg2, arg3)', source.SELECTED)
        for forbidden in ('volatile', 'GLOBAL_ASM', '(u16)', '(u8) arg0'):
            self.assertNotIn(forbidden, source.SELECTED)

    def test_all_41_input_paths_and_full_digests_are_unique(self):
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        self.assertEqual(len(source.PATHS), 41)
        self.assertEqual(len(set(source.PATHS.values())), 41)
        for digest in source.BASELINE.values():
            self.assertRegex(digest, '^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()
