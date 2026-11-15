"""Private semantic recovery gates; no source installation or matching credit."""
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_actor_effect_binding_150c4120_recovery as s

class ActorEffectBinding150C4120RecoveryTests(unittest.TestCase):
    def test_private_semantic_recovery(self):
        record=json.loads((s.OUT/'production-baseline/fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        for n,h in record['inputs'].items():self.assertEqual(sha(s.ROOT/n),h,n)
        self.assertIn('#pragma GLOBAL_ASM("asm/nonmatchings/generated_F15D0/func_150C4120.s")',(s.ROOT/s.SOURCE).read_text())
        for module in ('tools.experiments.game_actor_effect_binding_150c4120_recovery','tools.tests.game_actor_effect_binding_150c4120_oracle','tools.tests.game_actor_effect_binding_150c4120_native','tools.tests.game_actor_effect_binding_150c4120_callers'):
            p=subprocess.run([sys.executable,'-m',module],cwd=s.ROOT,env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT)),capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        report=json.loads((s.OUT/'recovery-report.json').read_text())
        self.assertEqual((report['body_words'],report['frame'],report['raw_word_differences'],report['neighbors']),(225,240,78,5))
        self.assertEqual(report['raw_body_sha256'],'9e5f094486ca28d5474da3caaf36efd497a0fc194379cc4cc9a6bf6ef3e0cda2')
        self.assertEqual(report['c_match_credit'],0);self.assertFalse(report['installed'])
        for n,h in record['inputs'].items():self.assertEqual(sha(s.ROOT/n),h,n)
        result=dict(frozen_inputs=len(record['inputs']),body_words=225,frame=240,raw_differences=78,padding_bytes_uncredited=7,installed=False,c_match_credit=0)
        (s.OUT/'recovery-suite.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':unittest.main()
