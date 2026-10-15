"""ROM-free packed argument widths, closed schedule cycles and source scope."""
import unittest

from tools.experiments import game_record_factory as source


class RecordFactoryCandidateTests(unittest.TestCase):
    def test_only_target_and_private_allocator_declaration_change(self):
        before = 'extern s32 D_800BE9E4;\ns32 func_1516D99C() {\n    return 0;\n}\ns32 other(){return 7;}\n'
        expected = before.replace('extern s32 D_800BE9E4;\n', 'extern s32 D_800BE9E4;\n\n' + source.DECLARATION).replace(
            's32 func_1516D99C() {\n    return 0;\n}', source.SELECTED.rstrip())
        self.assertEqual(source.recovered_owner(before), expected)
        with self.assertRaises(ValueError):
            source.recovered_owner(expected)

    def test_wire_flag_width_is_not_a_narrow_caller_prototype(self):
        self.assertEqual(len(source.SELECTED_TYPES), 49)
        self.assertEqual(source.SELECTED_TYPES[47], 's32')
        self.assertIn('((u8 *)&arg47)[3]', source.SELECTED)
        self.assertIn('record[0x42] = 0;', source.SELECTED)
        self.assertNotIn('GLOBAL_ASM', source.SELECTED)
        self.assertNotIn('volatile', source.SELECTED)

    def test_two_closed_schedule_cycles_and_43_unique_inputs(self):
        for group, order in ((source.GUARDS[:3], (2, 0, 1)), (source.GUARDS[3:], (1, 2, 0))):
            self.assertEqual([new for _, _, new in group], [group[i][1] for i in order])
            self.assertTrue(all(offset not in source.RELOCATIONS for offset, _, _ in group))
        self.assertEqual(len(source.PATHS), 43)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        self.assertEqual(len(set(source.PATHS.values())), 43)
        for value in source.BASELINE.values():
            self.assertRegex(value, '^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()
