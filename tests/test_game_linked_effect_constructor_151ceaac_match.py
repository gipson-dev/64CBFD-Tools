"""Qualify the direct-C linked-effect constructor and both callers."""
import os,struct,subprocess,sys,unittest
from tools.experiments import game_linked_effect_constructor_151ceaac_match as source
class LinkedEffectTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.texts,cls.installed=source.prepare()
 def check_module(self,name,markers):
  env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT),PYTHONDONTWRITEBYTECODE='1')
  p=subprocess.run([sys.executable,'-m','tools.tests.game_linked_effect_constructor_151ceaac_'+name],cwd=source.ROOT,env=env,capture_output=True,text=True,timeout=300)
  self.assertEqual(p.returncode,0,(name,p.stdout,p.stderr))
  for marker in markers:self.assertIn(marker,p.stdout)
 def test_guest(self):self.check_module('guest',["'cases': 96", "'real_position_helper': True", "'null_helper_fault': True", "'untouched_request_and_payload_bytes': True"])
 def test_native(self):self.check_module('native',["'cases_per_configuration': 96", "'alias_modes': 2", "'ubsan': True"])
 def test_callers(self):self.check_module('caller',["'cases': 32",'0x1506ac74','0x151d0e88'])
 def test_faults(self):self.check_module('fault',["'fault_prefixes': 128"])
 def test_relocations(self):self.check_module('rebase',["'gnu_links': 8", "'candidate_equals_retail': True"])
 def test_actual_make_and_image(self):self.check_module('image',['"strict_exclusions": 0','"caller_functions_unchanged": 16'])
 def test_direct_call_census(self):
  rom=(source.ROOT/'conker/conker.us.bin').read_bytes();needle=struct.pack('>I',0x0d473aab)
  hits=[i for i in range(0x2d4b0,0x22d710,4) if rom[i:i+4]==needle]
  self.assertEqual(hits,[0x98124,0x1fe338])
if __name__=='__main__':unittest.main()
