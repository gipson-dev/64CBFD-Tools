"""Verify view scaling, existing jump-table reuse and the linked image."""
import csv,io,os,subprocess,sys,unittest
from tools.experiments import game_view_scale_1500e738_match as source

class ViewScaleTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.texts,cls.installed=source.prepare()
 def run_check(self,name,marker):
  result=subprocess.run([sys.executable,'-m','tools.tests.game_view_scale_1500e738_'+name],cwd=source.ROOT,capture_output=True,text=True,env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT)),timeout=240)
  self.assertEqual(result.returncode,0,(result.stdout,result.stderr));self.assertIn(marker,result.stdout)
 def test_01_source_and_guards(self):
  for name,spec in source.MANIFEST['paths'].items():
   before,after=self.texts[name];self.assertEqual(source.sha(before),spec['before_sha256']);self.assertEqual(source.sha(after),spec['after_sha256']);self.assertEqual(source.apply(after,spec['changes'],True),before)
  old=list(csv.DictReader(io.StringIO(self.texts['guards'][0])));new=list(csv.DictReader(io.StringIO(self.texts['guards'][1])))
  self.assertEqual(new[:len(old)],old);self.assertEqual(new[len(old):],source.MANIFEST['guard_rows']);self.assertEqual(len(new)-len(old),2)
  self.assertTrue(all(r['expected']==r['replacement'] for r in new[len(old):]))
 def test_02_guest(self):self.run_check('guest','2048 input pairs per retail and raw body; visited 86 of 86 words')
 def test_03_caller_prefix(self):self.run_check('caller','420 original caller prefixes per retail/padded body')
 def test_04_faults(self):self.run_check('faults','37 matched retail/padded guest access-fault prefixes')
 def test_05_native(self):self.run_check('native','five incorrect implementations rejected')
 def test_06_guards(self):self.run_check('guards','4 single-guard instruction and relocation corruptions rejected')
 def test_07_relocations(self):self.run_check('rebase','8 GNU links across four symbol layouts agree')
 def test_08_table(self):self.run_check('table','all 16 compiler table relocations resolve')
 def test_09_actual_make_and_linked_image(self):self.run_check('make','"strict_exclusions": 0')

if __name__=='__main__':unittest.main()
