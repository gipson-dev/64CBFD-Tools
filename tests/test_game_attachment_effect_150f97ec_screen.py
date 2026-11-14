"""Bounded, explicitly uncredited screen for the 150F97EC placeholder."""
import os,struct,subprocess,sys,unittest
from tools.experiments import game_attachment_effect_150f97ec_screen as source
class AttachmentEffectScreenTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):source.prepare()
 def run_check(self,name,markers):
  env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT),PYTHONDONTWRITEBYTECODE='1')
  p=subprocess.run([sys.executable,'-m','tools.tests.game_attachment_effect_150f97ec_'+name],cwd=source.ROOT,env=env,capture_output=True,text=True,timeout=120)
  self.assertEqual(p.returncode,0,(name,p.stdout,p.stderr))
  for marker in markers:self.assertIn(marker,p.stdout)
 def test_guest(self):self.run_check('guest',['"cases_per_stream": 96','"effective_negative_controls": 3','"uncredited": true'])
 def test_original_caller_window(self):self.run_check('caller',['"cases_per_stream": 32','"caller": "func_150265CC"','"uncredited": true'])
 def test_census(self):
  rom=(source.ROOT/'conker/conker.us.bin').read_bytes();jal=struct.pack('>I',0x0d43e5fb);pointer=struct.pack('>I',0x150f97ec)
  self.assertEqual([i for i in range(0x2d4b0,0x22d710,4) if rom[i:i+4]==jal],[0x55dc0])
  self.assertEqual([i for i in range(0,len(rom)-3,4) if rom[i:i+4]==pointer],[])
 def test_line_endings(self):
  self.assertEqual(source.input_digest('conker/Makefile',b'a\r\nb\n'),source.input_digest('conker/Makefile',b'a\nb\n'))
  self.assertNotEqual(source.input_digest('conker/conker.us.bin',b'a\r\n'),source.input_digest('conker/conker.us.bin',b'a\n'))
if __name__=='__main__':unittest.main()
