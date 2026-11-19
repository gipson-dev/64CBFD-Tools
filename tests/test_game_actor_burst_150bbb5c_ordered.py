"""Strict opening relation, full guest/native values and original caller connection."""
import unittest
from unittest.mock import patch
from tools.experiments import game_actor_burst_150bbb5c_ordered as source
from tools.experiments import game_actor_burst_150bbb5c_recovery as previous
from tools.tests import game_actor_burst_150bbb5c_oracle as guest
from tools.tests import game_actor_burst_150bbb5c_native as native
from tools.tests import game_actor_burst_150bbb5c_caller as caller


class OrderedActorBurstTests(unittest.TestCase):
    def test_01_owner_and_strict_prefix(self):
        row=source.qualify_source()
        self.assertEqual((row['raw_words'],row['frame'],row['strict_prefix_paths']),(590,624,5))
        self.assertFalse(row['source_installed'])

    def test_02_guest_values_and_early_fault(self):
        with patch.object(previous,'state',source.state):
            self.assertEqual(guest.run()['cases'],274)
            self.assertEqual(guest.faults()['programs'],2)

    def test_03_native_sdk32_with_controls(self):
        # Only supply the ordered source spelling; preserve all frozen-input
        # metadata and the independently checked reference and native fixture.
        with patch.object(previous,'PIN',dict(previous.PIN,body=source.PIN['body'])):
            self.assertEqual(native.run()['cases_per_positive_run'],384)

    def test_04_original_caller_connection(self):
        row=caller.run()
        self.assertEqual((row['cases'],row['original_caller_words'],row['caller_words_visited']),(3072,252,42))
        self.assertEqual(caller.controls()['effective_controls'],6)

    def test_05_effective_prefix_controls(self):
        self.assertEqual(source.prefix_controls()['effective_controls'],5)

    @classmethod
    def tearDownClass(cls):
        source.check_inputs()


if __name__=='__main__':unittest.main()
