"""Private semantic qualification with no installation and frozen production inputs."""
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_radial_effect_150c29f0_recovery as s

class RadialEffect150C29F0RecoveryTests(unittest.TestCase):
 def test_semantics_without_match_credit(self):
  record=json.loads((s.OUT/'production-baseline/fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  for name,want in record['inputs'].items():self.assertEqual(sha(s.ROOT/name),want,name)
  self.assertEqual((s.ROOT/s.SOURCE).read_bytes(),(s.OUT/'production-baseline'/s.SOURCE).read_bytes())
  modules=('tools.experiments.game_radial_effect_150c29f0_recovery','tools.tests.game_radial_effect_150c29f0_oracle','tools.tests.game_radial_effect_150c29f0_native','tools.tests.game_radial_effect_150c29f0_callers')
  for module in modules:
   q=subprocess.run([sys.executable,'-m',module],cwd=s.ROOT,env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT)),capture_output=True,text=True)
   self.assertEqual(q.returncode,0,module+'\n'+q.stdout+'\n'+q.stderr);print(module+': '+q.stdout.strip(),flush=True)
  for name,want in record['inputs'].items():self.assertEqual(sha(s.ROOT/name),want,name)
  result=json.loads((s.OUT/'recovery-report.json').read_text());self.assertEqual((result['body_words'],result['frame'],result['real_word_differences']),(129,152,126));self.assertEqual(result['c_match_credit'],0)
  report=dict(private=True,installed=False,frozen_inputs=len(record['inputs']),source_unchanged=True,c_match_credit=0,frame_still_different=True)
  (s.OUT/'recovery-suite.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':unittest.main()
