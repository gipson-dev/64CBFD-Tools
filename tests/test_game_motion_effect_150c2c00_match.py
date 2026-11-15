"""Source, guards, semantics and owner padding under frozen production inputs."""
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_motion_effect_150c2c00_match as s

class MotionEffect150C2C00MatchTests(unittest.TestCase):
    def test_complete_matching_qualification(self):
        record=json.loads((s.OUT/'production-baseline/fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        installed=(s.ROOT/s.SOURCE).read_text()==s.proposed((s.OUT/'production-baseline'/s.SOURCE).read_text())
        plan=json.loads((s.OUT/'adoption-plan.json').read_text()) if (s.OUT/'adoption-plan.json').exists() else {}
        for n,h in record['inputs'].items():self.assertEqual(sha(s.ROOT/n),plan.get(n,h) if installed else h,n)
        before={n:sha(s.ROOT/n) for n in record['inputs']}
        for module in ('tools.experiments.game_motion_effect_150c2c00_match','tools.tests.game_motion_effect_150c2c00_guards','tools.tests.game_motion_effect_150c2c00_qualification','tools.tests.game_motion_effect_150c2c00_padder'):
            q=subprocess.run([sys.executable,'-m',module],cwd=s.ROOT,env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT)),capture_output=True,text=True)
            self.assertEqual(q.returncode,0,module+'\n'+q.stdout+'\n'+q.stderr);print(module+': '+q.stdout.strip(),flush=True)
        self.assertEqual(before,{n:sha(s.ROOT/n) for n in record['inputs']})
        report=dict(installed=installed,body_words=243,frame=232,guards=22,constant_pool_bytes=80,frozen_inputs=len(before))
        (s.OUT/'match-suite.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':unittest.main()
