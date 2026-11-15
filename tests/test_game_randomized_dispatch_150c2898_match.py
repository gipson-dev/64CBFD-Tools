"""Frozen production inputs surround every fresh focused qualification suite."""
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_randomized_dispatch_150c2898_recovery as s

class RandomizedDispatch150C2898MatchTests(unittest.TestCase):
 def test_direct_body_and_qualification(self):
  record=json.loads((s.OUT/'production-baseline/fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  plan=json.loads((s.OUT/'adoption-plan.json').read_text()) if (s.OUT/'adoption-plan.json').exists() else {}
  installed=(s.ROOT/s.SOURCE).read_text()==s.proposed((s.OUT/'production-baseline'/s.SOURCE).read_text())
  for name,want in record['inputs'].items():self.assertEqual(sha(s.ROOT/name),plan.get(name,want) if installed else want,name)
  before={name:sha(s.ROOT/name) for name in record['inputs']}
  modules=('tools.experiments.game_randomized_dispatch_150c2898_recovery','tools.tests.game_randomized_dispatch_150c2898_oracle','tools.tests.game_randomized_dispatch_150c2898_native','tools.tests.game_randomized_dispatch_150c2898_callers','tools.tests.game_randomized_dispatch_150c2898_padder')
  for module in modules:
   q=subprocess.run([sys.executable,'-m',module],cwd=s.ROOT,env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT)),capture_output=True,text=True)
   self.assertEqual(q.returncode,0,module+'\n'+q.stdout+'\n'+q.stderr);print(module+': '+q.stdout.strip(),flush=True)
  self.assertEqual(before,{name:sha(s.ROOT/name) for name in record['inputs']})
  report=dict(installed=installed,body_words=86,frame=120,guards=0,frozen_inputs=len(before))
  (s.OUT/'match-suite.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':unittest.main()
