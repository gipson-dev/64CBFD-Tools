"""ROM-free adapter, formula and immutable-input structure checks."""
import unittest

from tools.experiments import game_rotation_matrix_leaf as source


class RotationMatrixLeafCandidateTests(unittest.TestCase):
    def test_restore_is_original_assembly_not_a_fake_C_definition(self):
        before = '#include <ultra64.h>\nvoid func_150A8050(f32 mtx[4][4], f32 arg1, f32 arg2, f32 arg3) {\n}\n'
        after = source.original_owner(before)
        self.assertIn('#pragma GLOBAL_ASM("asm/nonmatchings/game_D5500/func_150A8050.s")', after)
        self.assertNotIn('void func_150A8050(', after)
        self.assertNotIn('handwritten??', after)
        with self.assertRaises(ValueError):
            source.original_owner(after)

    def test_semantic_reference_has_six_calls_but_is_not_the_installed_adapter(self):
        self.assertEqual(source.SEMANTIC_C.count('func_150AD780('), 3)
        self.assertEqual(source.SEMANTIC_C.count('func_150AD78C('), 3)
        self.assertIn('matrix[0][2] = -sinP;', source.SEMANTIC_C)
        self.assertIn('matrix[3][3] = 1.0f;', source.SEMANTIC_C)
        with self.assertRaisesRegex(ValueError, 'progress predecessor'):
            source.restored_progress(b'us,game,game_D5500,func_150A8050,353009744,336,c\n')

    def test_all_inputs_and_complete_sha256_digests_are_named_once(self):
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        self.assertEqual(len(source.PATHS), 38)
        self.assertEqual(len(set(source.PATHS.values())), 38)
        for digest in source.BASELINE.values():
            self.assertRegex(digest, '^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()
