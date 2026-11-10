"""Reproducible compiler/ABI investigation; deliberately no matching credit."""
import os
import unittest
from pathlib import Path
from tools.experiments import game_actor_audio_handle_15060778_audit as audit

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', '.')).resolve()


class ActorAudioAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit.prepare(ROOT)

    def test_game_spill_boundary(self):
        self.assertEqual(self.report['game']['differences'],
                         [38, 39, 43, 44, 93, 95, 96, 98])
        self.assertEqual(self.report['game_equal_neighbors'], 88)

    def test_consistent_api_and_dependency_boundary(self):
        self.assertTrue(self.report['consistent_source_proposal'])
        self.assertEqual(self.report['init_changed_functions'],
                         ['func_10010BE8', 'func_10010FFC'])
        self.assertEqual(self.report['init_equal_neighbors'], 52)
        self.assertEqual(self.report['stale_callee_guards'], 85)

    def test_five_original_call_sites(self):
        self.assertEqual(len(self.report['callers']['calls']), 5)
        self.assertEqual(self.report['callers']['jump'], [])
        self.assertEqual(self.report['callers']['aligned_pointer'], [])

    def test_no_installation_or_credit(self):
        self.assertFalse(self.report['installed'])
        self.assertFalse(self.report['credited'])
        self.assertFalse(self.report['functional_validation'])
        self.assertFalse(self.report['production_build_run'])
        self.assertTrue(self.report['source_inputs_unchanged'])
        self.assertEqual(self.report['guard_rows_written'], 0)


if __name__ == '__main__':
    unittest.main()
