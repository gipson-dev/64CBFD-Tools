"""Private C qualification guarded by immutable production inputs."""
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_motion_effect_150c2c00_recovery as s

class MotionEffect150C2C00RecoveryTests(unittest.TestCase):
    def test_private_source_guest_native_and_caller(self):
        record=json.loads((s.OUT/'production-baseline/fingerprints.json').read_text())
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        for name,want in record['inputs'].items():self.assertEqual(sha(s.ROOT/name),want,name)
        self.assertEqual((s.ROOT/s.SOURCE).read_bytes(),(s.OUT/'production-baseline'/s.SOURCE).read_bytes())
        for module in ('tools.experiments.game_motion_effect_150c2c00_recovery','tools.tests.game_motion_effect_150c2c00_oracle','tools.tests.game_motion_effect_150c2c00_native','tools.tests.game_motion_effect_150c2c00_callers'):
            q=subprocess.run([sys.executable,'-m',module],cwd=s.ROOT,env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT)),capture_output=True,text=True)
            self.assertEqual(q.returncode,0,module+'\n'+q.stdout+'\n'+q.stderr)
            print(module+': '+q.stdout.strip(),flush=True)
        for name,want in record['inputs'].items():self.assertEqual(sha(s.ROOT/name),want,name)
        result=json.loads((s.OUT/'recovery-report.json').read_text())
        self.assertEqual((result['body_words'],result['frame'],result['real_word_differences']),(242,256,210))
        self.assertEqual(result['c_match_credit'],0)
        report=dict(private=True,installed=False,frozen_inputs=len(record['inputs']),source_unchanged=True,c_match_credit=0,frame_still_different=True)
        (s.OUT/'recovery-suite.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':unittest.main()
