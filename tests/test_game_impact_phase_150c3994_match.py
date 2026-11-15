"""Source, connected constructor, native, guard and complete-owner gates."""
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_impact_phase_150c3994_match as s

class ImpactPhase150C3994MatchTests(unittest.TestCase):
    def test_complete_matching_qualification(self):
        record=json.loads((s.OUT/'production-baseline/fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        installed=(s.ROOT/s.SOURCE).read_text()==s.proposed((s.OUT/'production-baseline'/s.SOURCE).read_text())
        plan=json.loads((s.OUT/'adoption-plan.json').read_text()) if (s.OUT/'adoption-plan.json').exists() else {}
        for n,h in record['inputs'].items():self.assertEqual(sha(s.ROOT/n),plan.get(n,h) if installed else h,n)
        before={n:sha(s.ROOT/n) for n in record['inputs']}
        for module in ('tools.experiments.game_impact_phase_150c3994_match','tools.tests.game_impact_phase_150c3994_qualification','tools.tests.game_impact_phase_150c3994_padder'):
            p=subprocess.run([sys.executable,'-m',module],cwd=s.ROOT,env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT)),capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{n:sha(s.ROOT/n) for n in record['inputs']})
        report=dict(installed=installed,body_words=237,frame=80,guards=1,frozen_inputs=len(before))
        (s.OUT/'match-suite.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':unittest.main()
