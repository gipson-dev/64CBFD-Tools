"""Qualify the guarded timed-motion callback and its indirect caller."""
import json,os,struct,subprocess,sys,unittest
from tools.experiments import game_timed_motion_150f48d0_match as source
class TimedMotionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.installed=source.prepare()
 def check(self,name,markers):
  env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT),PYTHONDONTWRITEBYTECODE='1')
  p=subprocess.run([sys.executable,'-m','tools.tests.game_timed_motion_150f48d0_'+name],cwd=source.ROOT,env=env,capture_output=True,text=True,timeout=300)
  self.assertEqual(p.returncode,0,(name,p.stdout,p.stderr))
  for marker in markers:self.assertIn(marker,p.stdout)
 def test_guards(self):
  r=json.loads((source.OUT/'guard-screen.json').read_text());self.assertEqual((r['guard_rows'],r['register_role_rows'],r['schedule_rows']),(22,16,6))
 def test_guest(self):self.check('guest',['"cases_per_stream": 96','"streams": 3','"tick_alias_modes": 3','"effective_negative_controls": 3'])
 def test_caller(self):self.check('caller',['"cases_per_stream": 24','"streams": 3','"caller": "func_151321D0"'])
 def test_connected_helper(self):self.check('connected',['"cases_per_stream": 24','"retail_helper_words": 22','"trigonometric_returns_modeled": true'])
 def test_faults(self):self.check('fault',['"fault_prefixes": 159','"retail_equals_guarded": true'])
 def test_stack_overlap(self):self.check('stack_alias',['"cases_per_stream": 123','"different": 0','"modeled_exceptions": 2'])
 def test_native(self):self.check('native',['"cases_per_configuration": 24','"alias_modes": 2','"ubsan": true'])
 def test_padders_and_rebases(self):self.check('padders',['"padders": 2','"gnu_links": 12'])
 def test_actual_make_image(self):self.check('image',['"strict_exclusions": 0','"owner_neighbors": 5'])
 def test_caller_census(self):
  rom=(source.ROOT/'conker/conker.us.bin').read_bytes();jal=struct.pack('>I',0x0c000000|((0x150f48d0>>2)&0x3ffffff));pointer=struct.pack('>I',0x150f48d0)
  self.assertEqual([i for i in range(0x2d4b0,0x22d710,4) if rom[i:i+4]==jal],[])
  self.assertEqual([i for i in range(0,len(rom)-3,4) if rom[i:i+4]==pointer],[0x22e3c8])
 def test_line_endings(self):
  self.assertEqual(source.input_digest('conker/Makefile',b'a\r\nb\n'),source.input_digest('conker/Makefile',b'a\nb\n'))
  self.assertNotEqual(source.input_digest('conker/conker.us.bin',b'a\r\n'),source.input_digest('conker/conker.us.bin',b'a\n'))
if __name__=='__main__':unittest.main()
