"""Qualification of the inline line-record initializer and its retail match."""
import csv, io, os, subprocess, sys, unittest
from tools.experiments import game_line_record_1512dd50_match as source

class LineRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts, cls.installed = source.prepare()

    def check_module(self, name, marker):
        env = dict(os.environ, CBFD_CONSUMER_ROOT=str(source.ROOT), PYTHONDONTWRITEBYTECODE='1')
        p = subprocess.run([sys.executable, '-m', 'tools.tests.game_line_record_1512dd50_'+name],
                           cwd=source.ROOT, env=env, capture_output=True, text=True, timeout=240)
        self.assertEqual(p.returncode, 0, (name,p.stdout,p.stderr))
        self.assertIn(marker, p.stdout)

    def test_source_and_guards(self):
        old=list(csv.DictReader(io.StringIO(self.texts['guards'][0])))
        new=list(csv.DictReader(io.StringIO(self.texts['guards'][1])))
        self.assertEqual(new[:len(old)],old)
        self.assertEqual(new[len(old):],source.MANIFEST['guard_rows'])
        self.assertEqual(len(new)-len(old),69)

    def test_guest(self):self.check_module('guest',"'cases': 240")
    def test_native(self):self.check_module('native',"'values_per_optimization': 1118")
    def test_caller(self):self.check_module('caller',"'cases': 24")
    def test_faults(self):self.check_module('fault',"'fault_prefixes': 76")
    def test_stack_overlap(self):self.check_module('overlap','"explicit_conversion_mismatches": 0')
    def test_stack_overlap_extended(self):self.check_module('overlap_extended',"'all_terminated': 447")
    def test_relocations(self):self.check_module('rebase',"'gnu_links': 8")
    def test_guard_rejections(self):self.check_module('guards',"'stale_word_or_relocation_rejections': 276")
    def test_actual_make_and_image(self):self.check_module('image','"strict_exclusions": 0')

if __name__=='__main__':unittest.main()
