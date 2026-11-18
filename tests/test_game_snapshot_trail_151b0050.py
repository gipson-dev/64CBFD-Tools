"""Snapshot trail: complete capture proof, live emitted execution and image audit."""
import json
import unittest
from tools.experiments import game_snapshot_trail_151b0050_match as source
from tools.tests import game_snapshot_trail_151b0050_oracle as guest
from tools.tests import game_snapshot_trail_151b0050_proof as proof
from tools.tests import game_snapshot_trail_151b0050_native as native
from tools.tests import game_snapshot_trail_151b0050_caller as caller


class SnapshotTrailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = source.prepare()

    def record(self, name, report):
        (source.OUT / name).write_text(json.dumps(report, indent=2) + '\n')

    def test_01_owner_padders_and_guard_controls(self):
        self.assertEqual(source.guard_controls(), 48)
        self.assertEqual(len(source.PIN['guard_rows']), 8)

    def test_02_complete_capture_and_FP_relation(self):
        report = proof.main(self.state['raw_words'], self.state['retail_words'])
        self.assertEqual(report['raw_capture_relation']['private_bytes'], 188)
        self.assertEqual(report['derived_relation']['coverage'], [90, 90])
        self.assertEqual(len(report['controls']['effective_negatives']), 5)

    def test_03_guest_snapshots_and_zero_multiply(self):
        raw, retail = self.state['raw_words'], self.state['retail_words']
        report = guest.main(retail, raw, guest.derive(raw))
        self.assertEqual((report['cases'], report['ordered_FP_observations']), (2432, 14592))
        self.assertEqual(report['coverage'], [90, 90, 90])

    def test_04_fresh_native32_and_controls(self):
        report = native.main()
        self.assertEqual(report['cases'], 640)
        self.assertEqual(len(report['runs']), 10)
        self.assertTrue(report['passes'])
        self.record('native-report.json', report)

    def test_05_original_caller_window(self):
        raw, retail = self.state['raw_words'], self.state['retail_words']
        report = caller.run([retail, raw, guest.derive(raw)])
        self.assertEqual(report['cases_per_stream'], 80)
        self.assertTrue(report['return_zero_control_stops_loop'])
        self.record('caller-report.json', report)

    def test_06_actual_Make_and_strict_image(self):
        report = source.qualify_image()
        self.assertEqual(report['image']['strict_exclusions'], 0)
        self.assertEqual(report['neighbors_unchanged'], 15)
        self.assertTrue(report['all_other_6050_bodies_and_all_addresses_unchanged'])


if __name__ == '__main__':
    unittest.main()
