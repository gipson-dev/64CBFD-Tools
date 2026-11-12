"""Qualification for the position interpolation callback's guarded match."""
import importlib
import json
import unittest
from tools.experiments import game_position_interpolation_match as match

class GamePositionInterpolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = match.prepare()

    def test_01_actual_make_and_full_image(self):
        self.assertEqual(self.report['guards'], 10)

    def test_02_padders_and_rebased_links(self):
        importlib.import_module('tools.tests.game_position_interpolation_dual').main()

    def test_03_guest_and_aliases(self):
        importlib.import_module('tools.tests.game_position_interpolation_guest').main()
        importlib.import_module('tools.tests.game_position_interpolation_broad').main()

    def test_04_caller_windows(self):
        importlib.import_module('tools.tests.game_position_interpolation_callers').main()

    def test_05_access_fault_prefixes(self):
        importlib.import_module('tools.tests.game_position_interpolation_faults').main()

    def test_06_native32_and_controls(self):
        importlib.import_module('tools.tests.game_position_interpolation_native').main()

    def test_07_no_target_override_warning(self):
        plan = json.loads((match.out / 'actual-Make.json').read_text())
        self.assertNotIn('generated_EB340.c.o', plan['warnings'])
        self.assertEqual(len(plan['commands']), 4)
        self.assertTrue(any('-Wo,-no_const_in_reg' in c for c in plan['commands']))
        self.assertTrue(any('--function-object func_150BE2E8=' in c for c in plan['commands']))

if __name__ == '__main__':
    unittest.main()
