"""Owner, alias, caller, native and full-image qualification for the menu loader."""
import csv,io,os,subprocess,sys,unittest
from tools.experiments import game_menu_load_151e22bc_match as source

class MenuLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.texts,cls.installed=source.prepare()
    def check_module(self,name,marker):
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT),PYTHONDONTWRITEBYTECODE='1')
        p=subprocess.run([sys.executable,'-m','tools.tests.game_menu_load_151e22bc_'+name],
                         cwd=source.ROOT,env=env,capture_output=True,text=True,timeout=300)
        self.assertEqual(p.returncode,0,(name,p.stdout,p.stderr));self.assertIn(marker,p.stdout)
    def test_source_profile_and_guards(self):
        old=list(csv.DictReader(io.StringIO(self.texts['guards'][0])))
        new=list(csv.DictReader(io.StringIO(self.texts['guards'][1])))
        self.assertEqual(new[:len(old)],old);self.assertEqual(new[len(old):],source.MANIFEST['guard_rows'])
        self.assertEqual(len(new)-len(old),55)
    def test_guest(self):self.check_module('guest',"'reference_mismatches': [0, 0, 0, 0]")
    def test_alias_and_negative_control(self):self.check_module('alias',"'mismatches': [0, 16, 0, 0]")
    def test_native(self):self.check_module('native',"'cases_per_optimization': 1810")
    def test_caller(self):self.check_module('caller',"'cases': 36")
    def test_faults(self):self.check_module('fault',"'fault_prefixes': 83")
    def test_byte_load_register_flow(self):self.check_module('flow',"'stream_checks': 22")
    def test_relocations(self):self.check_module('rebase',"'gnu_links': 8")
    def test_pool_rebase(self):self.check_module('pool',"'changed_linked_neighbor_functions': []")
    def test_guard_rejections(self):self.check_module('guards',"'stale_word_or_relocation_rejections': 220")
    def test_actual_make_image(self):self.check_module('image','"strict_exclusions": 0')
if __name__=='__main__':unittest.main()
