"""ROM-free callback ABI, safe wrapping arithmetic and register-only guards."""
import unittest

from tools.experiments import game_packed_record_updater as source


class PackedRecordUpdaterCandidateTests(unittest.TestCase):
    def test_only_target_and_actual_common_type_declarations_change(self):
        before = '#include <ultra64.h>\ns32 func_1516D678() {\n    return 0;\n}\ns32 other(){return 7;}\n'
        expected = '#include <ultra64.h>\n#include "structs.h"\n\n' + source.DECLARATIONS + source.SELECTED + 's32 other(){return 7;}\n'
        self.assertEqual(source.recovered_owner(before), expected)
        with self.assertRaises(ValueError):
            source.recovered_owner(expected)

    def test_callback_indirection_exact_one_and_defined_word_wrap(self):
        self.assertIn('D_8008CBA0[record[0x23]](record) == 1', source.SELECTED)
        self.assertIn('value = (s32)((u32)value - (u32)D_800BE9E4)', source.SELECTED)
        self.assertIn('value = value * 256;', source.SELECTED)
        self.assertIn('(u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4', source.SELECTED)
        self.assertNotIn('<<', source.SELECTED)
        for bad in ('volatile', 'GLOBAL_ASM', 'func_15044660'):
            self.assertNotIn(bad, source.SELECTED)

    def test_three_non_relocation_sites_and_46_unique_frozen_inputs(self):
        self.assertEqual([offset for offset, _, _ in source.GUARDS], [160, 164, 172])
        self.assertTrue(all(offset not in source.RELOCATIONS for offset, _, _ in source.GUARDS))
        self.assertEqual(len(source.PATHS), 46)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        self.assertEqual(len(set(source.PATHS.values())), 46)
        for value in source.BASELINE.values():
            self.assertRegex(value, '^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()
