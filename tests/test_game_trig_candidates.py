"""Pure source screens; only full compiled retail comparisons prove matching."""
import unittest

from tools.experiments import game_trig_candidates as source


class GameTrigCandidateTests(unittest.TestCase):
    def test_selected_float_sine_has_all_retail_paths_and_pinned_inputs(self):
        text = source.body('sinf')
        self.assertIn('f32 sinf(f32 angle)', text)
        self.assertNotIn('f64', text)
        for token in ('0xE6', '0xFF', '0x136', 'D_80085EB0', 'D_80085EB4', 'D_80085EB8',
                      'D_80098D90', 'D_8002C920', 'D_80085EBC'):
            self.assertIn(token, text)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        self.assertEqual(source.TARGETS['sinf'], (0x15047D60, 0x75210, 104, 104))
        self.assertEqual(source.TARGETS['cosf'], (0x15047C00, 0x750B0, 88, 85))

    def test_operand_order_screens_retain_complete_functions(self):
        for name in source.TARGETS:
            for order in range(4):
                text = source.body(name, order)
                self.assertEqual(text.count('f32 ' + name + '('), 1)
                self.assertIn('return -result;', text)
                self.assertIn('if (angle != angle)', text)
                self.assertIn('raw = *(s32 *)&angle;', text)
        self.assertNotEqual(source.body('sinf'), source.body('sinf', 2))


if __name__ == '__main__':
    unittest.main()
