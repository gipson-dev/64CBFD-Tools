"""Qualify the configured effect factory and its linked production image."""
import os,struct,subprocess,sys,unittest
from tools.experiments import game_effect_config_1519c09c_match as source
class EffectConfigTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.texts,cls.installed=source.prepare()
 def check_module(self,name,markers):
  env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT),PYTHONDONTWRITEBYTECODE='1')
  p=subprocess.run([sys.executable,'-m','tools.tests.game_effect_config_1519c09c_'+name],cwd=source.ROOT,env=env,capture_output=True,text=True,timeout=300)
  self.assertEqual(p.returncode,0,(name,p.stdout,p.stderr))
  for marker in markers:self.assertIn(marker,p.stdout)
 def test_guest(self):self.check_module('guest',["'cases': 96", "'header_padding_preserved': True"])
 def test_native(self):self.check_module('native',["'cases_per_configuration': 96", "'alias_modes': 2", "'ubsan': True"])
 def test_caller(self):self.check_module('caller',["'cases': 96",'0x15199804'])
 def test_faults(self):self.check_module('fault',["'fault_prefixes': 137"])
 def test_relocations(self):self.check_module('rebase',["'gnu_links': 8", "'guarded_equals_retail': True"])
 def test_stale_guards(self):self.check_module('stale',["'stale_preimage_rejections': 40"])
 def test_actual_make_and_image(self):self.check_module('image',['"strict_exclusions": 0','"owner_neighbors_unchanged": 68'])
 def test_direct_call_census(self):
  rom=(source.ROOT/'conker/conker.us.bin').read_bytes();needle=struct.pack('>I',0x0d467027)
  hits=[i for i in range(0x2d4b0,0x22d710,4) if rom[i:i+4]==needle]
  self.assertEqual(hits,[0x1c6cb4])
if __name__=='__main__':unittest.main()
