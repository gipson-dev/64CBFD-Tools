"""Qualify the coordinate packet, caller ABI and linked production image."""
import csv,io,os,subprocess,sys,unittest
from tools.experiments import game_actor_coordinate_packet_150f1b48_match as source
class CoordinatePacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.texts,cls.installed=source.prepare()
    def check_module(self,name,markers):
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT),PYTHONDONTWRITEBYTECODE='1')
        p=subprocess.run([sys.executable,'-m','tools.tests.game_actor_coordinate_packet_150f1b48_'+name],cwd=source.ROOT,env=env,capture_output=True,text=True,timeout=300)
        self.assertEqual(p.returncode,0,(name,p.stdout,p.stderr))
        for marker in markers:self.assertIn(marker,p.stdout)
    def test_source_and_guards(self):
        old=list(csv.DictReader(io.StringIO(self.texts['guards'][0])));new=list(csv.DictReader(io.StringIO(self.texts['guards'][1])))
        self.assertEqual(new[:len(old)],old);self.assertEqual(new[len(old):],source.MANIFEST['guard_rows']);self.assertEqual(len(new)-len(old),23)
    def test_guest(self):self.check_module('guest',["'cases': 2304", "'overlap_tested': True"])
    def test_native(self):self.check_module('native',["'cases_per_optimization': 2304", "'early-snapshot'"])
    def test_caller(self):self.check_module('caller',["'cases': 216",'0x15034114'])
    def test_faults(self):self.check_module('fault',["'fault_prefixes': 92"])
    def test_derivation(self):self.check_module('derive',["'inserted_instructions': 3", "'folded_x_values': [190, 196, 202, 208]"])
    def test_relocations(self):self.check_module('rebase',["'gnu_links': 8", "'guarded_equals_retail': True"])
    def test_guard_rejections(self):self.check_module('stale',["'stale_preimage_rejections': 92"])
    def test_call_site_inventory(self):self.check_module('call_sites',['0x15034114'])
    def test_actual_make_and_image(self):self.check_module('image',['"strict_exclusions": 0','"caller_sections_changed": []'])
if __name__=='__main__':unittest.main()
