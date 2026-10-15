"""ROM-free bounded source and immutable manifest structure checks."""
import unittest

from tools.experiments import game_actor_world_matrix as source


class ActorWorldMatrixCandidateTests(unittest.TestCase):
    def test_only_target_and_private_declaration_are_changed(self):
        before = '#include <ultra64.h>\ns32 func_1511490C(){return 0;}\ns32 neighbor(){return 7;}\n'
        after = source.recover(before)
        self.assertEqual(after.count(source.SELECTED.rstrip()), 1)
        self.assertIn('s32 neighbor(){return 7;}', after)
        self.assertIn(source.DECLARATION, after)
        with self.assertRaisesRegex(ValueError, 'preamble'):
            source.recover(after)

    def test_semantic_matrix_no_fake_locals_or_guards(self):
        self.assertIn('f32 scale[4][4];', source.SELECTED)
        self.assertIn('*(f32 *)(actor + 0x18) + *(s16 *)(actor + 0x12)', source.SELECTED)
        self.assertIn('func_150A7A48(scale, matrix, matrix)', source.SELECTED)
        self.assertNotIn('volatile', source.SELECTED)
        self.assertNotIn('M2C_', source.SELECTED)
        self.assertNotIn('asm', source.SELECTED)
        self.assertEqual(len(list(source.variants())), 5)

    def test_all_manifest_keys_are_unique_and_digests_are_full_sha256(self):
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        self.assertEqual(len(source.PATHS), 34)
        self.assertEqual(len(set(source.PATHS.values())), 34)
        for digest in source.BASELINE.values():
            self.assertRegex(digest, '^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()
