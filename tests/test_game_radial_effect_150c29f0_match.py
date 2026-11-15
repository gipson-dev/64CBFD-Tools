"""Guarded source qualification surrounded by immutable production fingerprints."""
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_radial_effect_150c29f0_match as s

class RadialEffect150C29F0MatchTests(unittest.TestCase):
 def test_source_guards_behavior_and_padders(self):
  record=json.loads((s.OUT/'production-baseline/fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  installed=(s.ROOT/s.SOURCE).read_text()==s.proposed((s.OUT/'production-baseline'/s.SOURCE).read_text());plan=json.loads((s.OUT/'adoption-plan.json').read_text()) if (s.OUT/'adoption-plan.json').exists() else {}
  for name,want in record['inputs'].items():self.assertEqual(sha(s.ROOT/name),plan.get(name,want) if installed else want,name)
  before={name:sha(s.ROOT/name) for name in record['inputs']}
  for module in ('tools.experiments.game_radial_effect_150c29f0_match','tools.tests.game_radial_effect_150c29f0_guards','tools.tests.game_radial_effect_150c29f0_qualification','tools.tests.game_radial_effect_150c29f0_padder'):
   q=subprocess.run([sys.executable,'-m',module],cwd=s.ROOT,env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT)),capture_output=True,text=True)
   self.assertEqual(q.returncode,0,module+'\n'+q.stdout+'\n'+q.stderr);print(module+': '+q.stdout.strip(),flush=True)
  self.assertEqual(before,{name:sha(s.ROOT/name) for name in record['inputs']})
  report=dict(installed=installed,body_words=132,frame=136,guards=11,frozen_inputs=len(before))
  (s.OUT/'match-suite.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':unittest.main()
