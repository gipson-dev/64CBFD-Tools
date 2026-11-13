"""Qualify the slot event callback against retail and connected callers."""
import csv
import io
import os
import subprocess
import sys
import unittest

from tools.experiments import game_slot_notification_15156028_match as screen


class SlotNotificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts, cls.installed = screen.prepare()

    def run_check(self, name, marker):
        result = subprocess.run([sys.executable, '-m', 'tools.tests.game_slot_notification_15156028_' + name],
                                cwd=screen.ROOT, capture_output=True, text=True,
                                env=dict(os.environ, CBFD_CONSUMER_ROOT=str(screen.ROOT)), timeout=240)
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
        self.assertIn(marker, result.stdout)

    def test_01_source_and_guard_fingerprints(self):
        for name, spec in screen.MANIFEST['paths'].items():
            before, after = self.texts[name]
            self.assertEqual(screen.sha(before), spec['before_sha256'])
            self.assertEqual(screen.sha(after), spec['after_sha256'])
            self.assertEqual(screen.apply(after, spec['changes'], True), before)
            corrupt = [dict(item) for item in spec['changes']]
            index = next(i for i, item in enumerate(corrupt) if item['old']) if name == 'source' else None
            if index is not None:
                corrupt[index]['old'] = 'invalid expected context\n'
                with self.assertRaises(ValueError):
                    screen.apply(before, corrupt)
        old = list(csv.DictReader(io.StringIO(self.texts['guards'][0])))
        new = list(csv.DictReader(io.StringIO(self.texts['guards'][1])))
        self.assertEqual(new[:len(old)], old)
        added = new[len(old):]
        self.assertEqual(len(added), 51)
        self.assertTrue(all(r['function'] == screen.NAME and r['omit'] == 'false' for r in added))
        self.assertEqual(sum(r['expected_relocations'] != r['replacement_relocations'] for r in added), 7)

    def test_02_guest(self):
        self.run_check('guest', '192 signed-boundary cases plus all 256 opcode bytes per body')

    def test_03_connected_callers(self):
        self.run_check('connected', '108 original list/direct dispatch cases per body')

    def test_04_guest_faults(self):
        self.run_check('faults', '1416 matched retail and padded guest access-fault prefixes')

    def test_05_native32(self):
        self.run_check('native', '2048 cases each, 8 effective semantic controls')

    def test_06_guard_controls(self):
        self.run_check('guard_controls', '102 single-guard corruptions rejected')

    def test_07_relocations(self):
        self.run_check('rebase', '12 GNU links across four high/low symbol layouts')

    def test_08_actual_make_and_linked_image(self):
        self.run_check('make', '"strict_exclusions": 0')


if __name__ == '__main__':
    unittest.main()
