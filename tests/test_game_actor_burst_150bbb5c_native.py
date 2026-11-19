"""Native SDK32 gate for the uninstalled actor-burst recovery."""
import unittest
from tools.experiments import game_actor_burst_150bbb5c_recovery as source
from tools.tests import game_actor_burst_150bbb5c_native as native


class ActorBurstNativeTests(unittest.TestCase):
    def test_native_sdk32_and_effective_controls(self):
        row = native.run()
        self.assertEqual((row['cases_per_positive_run'], row['positive_runs'], row['effective_negatives']), (384,3,12))
        self.assertTrue(row['UBSan'] and row['strict_aliasing'])
        self.assertFalse(row['source_installed'])
        self.assertEqual(row['c_match_credit'], 0)

    @classmethod
    def tearDownClass(cls):
        source.check_inputs()


if __name__ == '__main__':
    unittest.main()
