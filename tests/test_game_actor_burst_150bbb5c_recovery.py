"""Private source, guest semantics and effective negatives; no match credit."""
import unittest
from tools.experiments import game_actor_burst_150bbb5c_recovery as source
from tools.tests import game_actor_burst_150bbb5c_oracle as guest


class ActorBurstRecoveryTests(unittest.TestCase):
    def test_01_full_owner_and_original_census(self):
        row = source.qualify_source()
        self.assertEqual((row['raw_words'], row['retail_words'], row['raw_frame']), (589,587,624))
        self.assertEqual(row['overlapping_word_differences'], 539)
        self.assertFalse(row['source_installed'])
        self.assertEqual(row['c_match_credit'], 0)
        self.assertTrue(source.census()['passes'])

    def test_02_guest_reference_all_original_words(self):
        row = guest.run()
        self.assertEqual((row['cases'], row['executions'], row['retail_words_visited']), (274,548,587))

    def test_03_effective_semantic_negatives(self):
        self.assertEqual(source.controls()['effective_negatives'], 12)

    def test_04_early_type_read_fault_boundary(self):
        self.assertEqual(guest.faults()['programs'], 2)

    @classmethod
    def tearDownClass(cls):
        source.check_inputs()


if __name__ == '__main__':
    unittest.main()
