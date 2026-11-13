"""Settings validator source, semantics, caller and production-image checks."""
import csv,io,os,subprocess,sys,unittest
from tools.experiments import game_settings_validator_151dd9e4_match as source

class SettingsValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.texts,cls.installed=source.prepare()
    def check_module(self,name,markers):
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT),PYTHONDONTWRITEBYTECODE='1')
        p=subprocess.run([sys.executable,'-m','tools.tests.game_settings_validator_151dd9e4_'+name],cwd=source.ROOT,env=env,capture_output=True,text=True,timeout=300)
        self.assertEqual(p.returncode,0,(name,p.stdout,p.stderr))
        for marker in markers:self.assertIn(marker,p.stdout)
    def test_source_and_guards(self):
        old=list(csv.DictReader(io.StringIO(self.texts['guards'][0])));new=list(csv.DictReader(io.StringIO(self.texts['guards'][1])))
        self.assertEqual(new[:len(old)],old);self.assertEqual(new[len(old):],source.MANIFEST['guard_rows']);self.assertEqual(len(new)-len(old),3)
    def test_guest(self):self.check_module('guest',["'cases': 11776", "'return_value': 23"])
    def test_native(self):self.check_module('native',["'cases_per_optimization': 11776", "'missing_last'"])
    def test_caller(self):self.check_module('caller',["'cases': 512",'0x1500752c','0x151e23ec'])
    def test_faults(self):self.check_module('fault',["'fault_prefixes': 389"])
    def test_relocations(self):self.check_module('rebase',["'gnu_links': 8", "'guarded_equals_retail': True"])
    def test_guard_rejections(self):self.check_module('stale',["'stale_preimage_rejections': 12"])
    def test_call_site_inventory(self):self.check_module('call_sites',['0x1500752c','0x151e23ec'])
    def test_actual_make_and_image(self):self.check_module('image',['"strict_exclusions": 0','"owner_neighbors_unchanged": 59'])

if __name__=='__main__':unittest.main()
