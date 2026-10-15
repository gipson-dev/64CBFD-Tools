"""ROM-free mask recovery, scoped recipes and the direct-match gate."""
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_packed_coordinate_expression_fit as source


class CoordinateMatchCandidateTests(unittest.TestCase):
    def test_masked_signed_coordinate_body_replaces_only_the_target(self):
        before = 's32 func_1516E778() {\n    return 0;\n}\nvoid other(void) { }\n'
        self.assertEqual(source.recovered_owner(before), source.SELECTED + 'void other(void) { }\n')
        self.assertIn('(s16)(arg0 & 0xFFFF)', source.SELECTED)
        self.assertIn('0x155, arg1,', source.SELECTED)
        self.assertIn('(u8)arg3, arg4', source.SELECTED)
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))

    def test_eight_complete_recipes_do_not_rewrite_identifiers(self):
        recipes = source.candidates()
        self.assertEqual(len(recipes), 8)
        self.assertEqual(recipes['mask-cast-low'], source.SELECTED)
        for body in recipes.values():
            self.assertEqual(source.source.build.body(body, source.FUNCTION), body[body.index('void func_'):].strip())
            self.assertNotIn('arg0U', body)
            self.assertNotIn('arg4U', body)
            self.assertNotIn('volatile', body)
        self.assertIn('0U,', recipes['unsigned-literals'])

    def test_all_50_unique_input_fingerprints_are_retained(self):
        self.assertEqual(len(source.PATHS), 50)
        self.assertEqual(len(set(source.PATHS.values())), 50)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        for value in source.BASELINE.values():
            self.assertRegex(value, '^[0-9a-f]{64}$')

    def test_gate_rejects_wrong_length_differences_or_warnings(self):
        for count, differences, diagnostics in ((84, 0, ''), (85, 1, ''), (85, 0, 'warning')):
            with patch.object(source.source, 'measure', return_value=(None, [], dict(
                    words=count, differences=differences, diagnostics=diagnostics))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))


if __name__ == '__main__':
    unittest.main()
