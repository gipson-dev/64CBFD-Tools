"""Qualify texture tile C semantics, callers, padding and the linked image."""
import csv,io,os,subprocess,sys,unittest
from tools.experiments import game_texture_tile_151ed29c_match as source
class TextureTileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.texts,cls.installed=source.prepare()
    def check_module(self,name,markers,extra=None):
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT),PYTHONDONTWRITEBYTECODE='1')
        if extra:env.update(extra)
        p=subprocess.run([sys.executable,'-m','tools.tests.game_texture_tile_151ed29c_'+name],cwd=source.ROOT,env=env,capture_output=True,text=True,timeout=360)
        self.assertEqual(p.returncode,0,(name,p.stdout,p.stderr))
        for marker in markers:self.assertIn(marker,p.stdout)
    def test_source_and_guards(self):
        old=list(csv.DictReader(io.StringIO(self.texts['guards'][0])));new=list(csv.DictReader(io.StringIO(self.texts['guards'][1])))
        self.assertEqual(new[:len(old)],old);self.assertEqual(new[len(old):],source.MANIFEST['guard_rows']);self.assertEqual(len(new)-len(old),88)
    def test_guest(self):self.check_module('guest',["'cases': 7200"])
    def test_guest_size_values(self):self.check_module('size',["'cases': 10240", "'guest_size_values': 256"])
    def test_overlap(self):self.check_module('alias',['"checked": 3024','"first_counterexamples": []'])
    def test_caller(self):self.check_module('caller',["'cases': 288",'0x151ed478'])
    def test_native(self):self.check_module('native',["'cases_per_optimization': 4096", "'late-format'"])
    def test_native_strict(self):self.check_module('native',["'cases_per_optimization': 4096", "'strict_aliasing': True"],{'TILE_STRICT_ALIASING':'1'})
    def test_faults(self):self.check_module('fault',["'fault_prefixes': 96"])
    def test_dataflow(self):self.check_module('dataflow',['"completed_cases": 1620','"first_issue": []'])
    def test_derivation(self):self.check_module('derive',['"problems": []','"register_edits_involving_zero": []'])
    def test_relocations(self):self.check_module('rebase',["'gnu_links': 8", "'guarded_equals_retail': True"])
    def test_padders(self):self.check_module('padder',["'stale_preimage_rejections': 352"])
    def test_call_site_inventory(self):self.check_module('call_sites',['0x151ed478'])
    def test_actual_make_and_image(self):self.check_module('image',['"strict_exclusions": 0','"owner_neighbors_unchanged": 26'])
if __name__=='__main__':unittest.main()
