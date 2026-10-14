"""Standalone source-screen invariants; no consumer inputs or compiler needed."""
import unittest

from tools.experiments import game_view_projection_command_candidates as source


class ViewProjectionCommandCandidateTests(unittest.TestCase):
    def test_complete_unique_screens_and_real_selected_locals(self):
        rows = list(source.variants())
        self.assertEqual(len(rows), 130)
        self.assertEqual(len({label for label, _ in rows}), 130)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        body = dict(rows)[source.SELECTED_LABEL]
        self.assertIn('void func_1510B128(s32 index, f32 offsetX, f32 offsetY, f32 scale, f32 nearFallback)', body)
        for name in ('cosineX', 'cosineY', 'nearOverride', 'farOverride'):
            self.assertGreater(body.count(name), 1)
        self.assertEqual(body.count('cosf('), 2)
        self.assertEqual(body.count('sinf('), 2)
        self.assertEqual(body.count('func_1510B5F8('), 1)
        self.assertNotIn('return 0;', body)
        self.assertEqual(dict(rows)['nested-direct-product'].count('cosine'), 1)

    def test_typed_wrapper_and_parent_require_no_float_to_integer_conversion(self):
        before = ('extern u8 *D_800BE628;\n'
            's32 func_1510B128() { return 0; }\n'
            's32 func_1510B32C(s32 arg0, f32 arg1, f32 arg2, f32 arg3) {\n'
            '    func_1510B128(arg0, *(s32 *)&arg1, *(s32 *)&arg2, *(s32 *)&arg3, 0);\n}\n'
            's32 func_1510B5F8() { return 0; }\n')
        result = source.recover(before, dict(source.variants())[source.SELECTED_LABEL])
        self.assertIn('void func_1510B32C(', result)
        self.assertIn('func_1510B128(arg0, arg1, arg2, arg3, 0.0f);', result)
        self.assertNotIn('*(s32 *)&arg', result)
        self.assertIn('s32 func_1510B5F8(s32 index, u16 *normalization,', result)
        parent = 's32 func_1510B128(s32 index, f32 x, f32 y, f32 scale, f32 fallback);\n'
        self.assertEqual(source.recover_parent(parent), parent.replace('s32 func_', 'void func_', 1))


if __name__ == '__main__':
    unittest.main()
