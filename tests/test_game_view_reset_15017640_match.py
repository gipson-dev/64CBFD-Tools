"""Full match qualification with immutable production-input accounting."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_view_reset_15017640_match as s
from tools.tests import game_view_reset_15017640_oracle as g

class ViewReset15017640MatchTests(unittest.TestCase):
 def test_qualification_and_immutable_inputs(self):
  record=json.loads((s.OUT/'production-baseline/fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  extras=json.loads((s.OUT/'qualification-inputs/fingerprints.json').read_text())
  for name,want in extras.items():self.assertEqual(sha(s.ROOT/name),want,name)
  plan=json.loads((s.OUT/'adoption-plan.json').read_text()) if (s.OUT/'adoption-plan.json').exists() else {}
  candidate=s.draft.recover((s.OUT/'production-baseline'/s.SOURCE).read_text(),s.draft.pointer_body())
  installed=(s.ROOT/s.SOURCE).read_text()==candidate
  for name,want in record['inputs'].items():self.assertEqual(sha(s.ROOT/name),plan.get(name,want) if installed else want,name)
  before={name:sha(s.ROOT/name) for name in record['inputs']}
  for module in ('tools.experiments.game_view_reset_15017640_match','tools.tests.game_view_reset_15017640_native','tools.tests.game_view_reset_15017640_callers','tools.tests.game_view_reset_15017640_padder'):
   q=subprocess.run([sys.executable,'-m',module],cwd=s.ROOT,env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT)),capture_output=True,text=True)
   self.assertEqual(q.returncode,0,module+'\n'+q.stdout+'\n'+q.stderr);print(module+': '+q.stdout.strip(),flush=True)
  programs=s.programs();seen=[set() for _ in programs];cases=0
  for c in g.corpus():
   initial=g.fixture(c);expected=g.reference(initial,c)
   for i,(words,entry) in enumerate(programs):
    m=g.Oracle(words,initial,c,entry);m.run();g.compare(m,expected);seen[i].update(m.visits)
   cases+=1
  self.assertEqual((cases,[len(v) for v in seen]),(3456,[82,82,82]));self.assertEqual(before,{name:sha(s.ROOT/name) for name in record['inputs']})
  for name,want in extras.items():self.assertEqual(sha(s.ROOT/name),want,name)
  report=dict(cases=cases,streams=3,all_words_visited=82,installed=installed,frozen_inputs=len(before),guards=13)
  (s.OUT/'match-suite.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':unittest.main()
