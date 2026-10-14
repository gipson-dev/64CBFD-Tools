"""Pure cosine lifetime screens; compiled whole-slot gates decide matching."""
import unittest

from tools.experiments import game_cosine_candidates as source


class GameCosineCandidateTests(unittest.TestCase):
    def test_selected_copy_and_literal_types_remain_explicit(self):
        text = source.body()
        self.assertIn('absolute = angle > 0 ? angle : -angle;', text)
        self.assertIn('reduced = absolute;', text)
        self.assertIn('periods >= 0.0f', text)
        self.assertNotIn('f64', text)
        self.assertEqual((source.ENTRY, source.ROM, source.SLOT, source.CODE), (0x15047C00, 0x750B0, 88, 85))
        self.assertEqual(set(source.PATHS), set(source.BASELINE))

    def test_no_copy_and_merged_zero_controls_are_distinct_complete_sources(self):
        self.assertNotIn('reduced = absolute;', source.body(copy=False))
        for absolute in ('0', '0.0f', '0.0'):
            for rounding in ('0', '0.0f', '0.0'):
                text = source.body(absolute, rounding)
                self.assertEqual(text.count('f32 cosf('), 1)
                self.assertIn('return D_8002C920;', text)
                self.assertIn('return -result;', text)
        self.assertNotEqual(source.body(), source.body('0', '0'))


if __name__ == '__main__':
    unittest.main()
