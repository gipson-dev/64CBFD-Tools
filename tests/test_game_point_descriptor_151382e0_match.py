"""Fingerprint and qualify the private point descriptor and trail ABI screen."""
import csv
import io
import os
import subprocess
import sys
import unittest

from tools.experiments import game_point_descriptor_151382e0_match as screen


class PointDescriptorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts, cls.installed = screen.prepare()

    def run_check(self, name, marker):
        command = [sys.executable, '-m', 'tools.tests.game_point_descriptor_151382e0_' + name]
        result = subprocess.run(command, cwd=screen.ROOT, capture_output=True, text=True,
                                env=dict(os.environ, CBFD_CONSUMER_ROOT=str(screen.ROOT)), timeout=180)
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
        self.assertIn(marker, result.stdout)

    def test_01_source_reconstruction_and_guard_scope(self):
        for name, spec in screen.MANIFEST['paths'].items():
            before, after = self.texts[name]
            self.assertEqual(screen.sha(before), spec['before_sha256'])
            self.assertEqual(screen.sha(after), spec['after_sha256'])
            self.assertEqual(screen.apply(after, spec['changes'], True), before)
            broken = list(spec['changes'])
            self.assertTrue(broken)
            index = next(i for i, item in enumerate(broken) if item['old'])
            item = dict(broken[index]); item['old'] = 'deliberately invalid context\n'; broken[index] = item
            with self.assertRaises(ValueError):
                screen.apply(before, broken)
        old = list(csv.DictReader(io.StringIO(self.texts['guards'][0])))
        new = list(csv.DictReader(io.StringIO(self.texts['guards'][1])))
        old_other = [r for r in old if r['function'] != screen.HELPER]
        new_other = [r for r in new if r['function'] not in (screen.HELPER, screen.NAME)]
        self.assertEqual(old_other, new_other)
        previous = [r for r in old if r['function'] == screen.HELPER]
        current = [r for r in new if r['function'] == screen.HELPER]
        changed = []
        for a, b in zip(previous, current):
            if a != b:
                self.assertEqual({k: v for k, v in a.items() if k != 'expected'},
                                 {k: v for k, v in b.items() if k != 'expected'})
                changed.append(int(a['offset'], 0))
        self.assertEqual(changed, [0, 0x44, 0x78, 0x22c, 0x29c])
        self.assertEqual([int(r['offset'], 0) for r in new if r['function'] == screen.NAME],
                         [0, 4, 0x124, 0x138])

    def test_02_guest_descriptor_and_frame_aliases(self):
        self.run_check('guest', 'guest nonoverlap cases 640')

    def test_03_original_caller(self):
        self.run_check('caller', '512 cases')

    def test_04_helper_guest(self):
        self.run_check('helper_guest', '256 guest cases')

    def test_05_point_native32(self):
        self.run_check('native', 'six effective semantic controls')

    def test_06_helper_native(self):
        self.run_check('helper_native', '256 cases each at O0/O2/O3')

    def test_06b_trail_native(self):
        self.run_check('trail_native', '"negative_controls": 16')

    def test_07_guard_controls(self):
        self.run_check('guard_controls', 'effective guard corruption controls: 36')

    def test_08_gnu_relocations(self):
        self.run_check('rebase', '15 GNU relocation links')

    def test_08b_fault_prefixes(self):
        self.run_check('faults', 'guest fault-prefix pairs matched')

    def test_09_actual_make_and_strict_image(self):
        self.run_check('make', '"strict_exclusions": 0')


if __name__ == '__main__':
    unittest.main()
