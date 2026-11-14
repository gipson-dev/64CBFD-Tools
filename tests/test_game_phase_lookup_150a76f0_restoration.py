"""Genuine handwritten restoration, independent table model and immutable inputs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_phase_lookup_150a76f0_restoration as source
class PhaseLookup150A76F0RestorationTests(unittest.TestCase):
 def test_original_assembly(self):
  root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();protected=(source.SOURCE,source.ASSEMBLY,'conker/asm/D4450.s','conker/build/conker.us.elf','conker/progress.csv','conker/retail_word_patches.us.csv');before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in protected};env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
  for module in ('tools.experiments.game_phase_lookup_150a76f0_restoration','tools.tests.game_phase_lookup_150a76f0_object','tools.tests.game_phase_lookup_150a76f0_padder','tools.tests.game_phase_lookup_150a76f0_oracle'):
   q=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True);self.assertEqual(q.returncode,0,module+'\n'+q.stdout+'\n'+q.stderr);print(module+': '+q.stdout.strip(),flush=True)
  report=json.loads((root/source.BUILD/'raw-report.json').read_text());self.assertEqual((report['body_words'],report['alignment_words'],report['neighbors'],report['c_match_credit']),(29,3,18,0));self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in protected})
if __name__=='__main__':unittest.main()
