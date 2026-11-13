"""Qualify script-node acquisition against retail and its table caller."""
import csv
import io
import os
import subprocess
import sys
import unittest

from tools.experiments import game_script_node_acquire_1509b5ac_match as source


class ScriptNodeAcquireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts, cls.installed = source.prepare()

    def run_check(self, name, marker):
        result = subprocess.run([sys.executable, '-m', 'tools.tests.game_script_node_acquire_1509b5ac_' + name],
                                cwd=source.ROOT, capture_output=True, text=True,
                                env=dict(os.environ, CBFD_CONSUMER_ROOT=str(source.ROOT)), timeout=240)
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
        self.assertIn(marker, result.stdout)

    def test_01_source_and_guard_fingerprints(self):
        for name, spec in source.MANIFEST['paths'].items():
            before, after = self.texts[name]
            self.assertEqual(source.sha(before), spec['before_sha256'])
            self.assertEqual(source.sha(after), spec['after_sha256'])
            self.assertEqual(source.apply(after, spec['changes'], True), before)
        old = list(csv.DictReader(io.StringIO(self.texts['guards'][0])))
        new = list(csv.DictReader(io.StringIO(self.texts['guards'][1])))
        self.assertEqual(new[:len(old)], old)
        self.assertEqual(new[len(old):], source.MANIFEST['guard_rows'])
        self.assertEqual(len(new)-len(old), 6)
        self.assertTrue(all(row['expected_relocations'] == row['replacement_relocations'] for row in new[len(old):]))

    def test_02_guest_and_stack_aliases(self):
        self.run_check('guest', 'stack alias cases 128')

    def test_03_connected_original_caller(self):
        self.run_check('callers', '96 original table-caller cases per body')

    def test_04_guest_faults(self):
        self.run_check('faults', '88 matched retail and padded guest access-fault prefixes')

    def test_05_native32(self):
        self.run_check('native', 'six semantic controls rejected')

    def test_06_guard_controls(self):
        self.run_check('guards', '12 single-guard instruction and relocation corruptions rejected')

    def test_07_relocations(self):
        self.run_check('rebase', '8 GNU links across four symbol layouts')

    def test_08_actual_make_and_linked_image(self):
        self.run_check('make', '"strict_exclusions": 0')


if __name__ == '__main__':
    unittest.main()
