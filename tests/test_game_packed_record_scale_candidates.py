"""ROM-free recovery scope, safe arithmetic and exact relocation guard contract."""
import unittest

from tools.experiments import game_packed_record_scale as source


class PackedRecordScaleCandidateTests(unittest.TestCase):
    def test_only_the_pinned_placeholder_changes(self):
        before = '#include <ultra64.h>\ns32 func_1516ECAC() {\n    return 0;\n}\ns32 other(){return 7;}\n'
        self.assertEqual(source.recovered_owner(before), '#include <ultra64.h>\n' + source.SELECTED + 's32 other(){return 7;}\n')
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))

    def test_word_accumulator_byte_fields_and_defined_wrap(self):
        self.assertIn('s32 value = record[0x1F]', source.SELECTED)
        self.assertIn('((u32)D_800BE9E4 << 7)', source.SELECTED)
        self.assertIn('(u32)value - (u32)D_800BE9E4 * record[0x26]', source.SELECTED)
        self.assertIn('record[0x24] == 0 && value == 0', source.SELECTED)
        self.assertIn('(u32)base * (u32)value', source.SELECTED)
        for bad in ('volatile', 'GLOBAL_ASM', 'u8 value', 'func_1516D738'):
            self.assertNotIn(bad, source.SELECTED)

    def test_three_closed_relocation_sites_and_49_unique_frozen_inputs(self):
        self.assertEqual([row[0] for row in source.GUARDS], [72, 76, 80])
        self.assertEqual(source.GUARDS[1][3:], ('-', 'R_MIPS_LO16:D_800BE9E4'))
        self.assertEqual(source.GUARDS[2][3:], ('R_MIPS_LO16:D_800BE9E4', '-'))
        self.assertEqual(len(source.PATHS), 49)
        self.assertEqual(len(set(source.PATHS.values())), 49)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        for digest in source.BASELINE.values():
            self.assertRegex(digest, '^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()
