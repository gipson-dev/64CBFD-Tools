"""Pure transfer-source and closed guard description checks."""
from collections import Counter
import unittest

from tools.experiments import game_view_fov_transfer_candidates as source


class ViewFovTransferCandidateTests(unittest.TestCase):
    def test_typed_body_keeps_all_seven_calls_and_live_reference_lookups(self):
        self.assertIn('void func_1501B0A0(s32 index, s32 reference)', source.BODY)
        self.assertEqual(source.BODY.count('sinf('), 2)
        self.assertEqual(source.BODY.count('cosf('), 2)
        self.assertEqual(source.BODY.count('func_150484A0('), 2)
        self.assertEqual(source.BODY.count('func_1510B128('), 1)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))

    def test_guard_word_and_relocation_atoms_are_one_closed_permutation(self):
        self.assertEqual(len(source.GUARDS), 13)
        self.assertEqual([row[0] for row in source.GUARDS], list(range(4, 56, 4)))
        before = Counter((word, relocation) for _, word, _, relocation, _ in source.GUARDS)
        after = Counter((word, relocation) for _, _, word, _, relocation in source.GUARDS)
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
