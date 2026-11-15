"""Bank the private lifetime boundary, including effective false-fit rejection."""
import json,os,subprocess,sys,unittest
from tools.experiments import game_attachment_effect_150f97ec_lifetime as s
class AttachmentLifetimeTests(unittest.TestCase):
    def test_private_source_behavior_and_rejections(self):
        count=s.immutable();env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT),PYTHONDONTWRITEBYTECODE='1')
        for module in ('tools.experiments.game_attachment_effect_150f97ec_lifetime','tools.tests.game_attachment_effect_150f97ec_lifetime_guest','tools.tests.game_attachment_effect_150f97ec_lifetime_native','tools.tests.game_attachment_effect_150f97ec_lifetime_padder'):
            p=subprocess.run([sys.executable,'-m',module],cwd=s.ROOT,env=env,capture_output=True,text=True);self.assertEqual(p.returncode,0,module+'\n'+p.stdout+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(s.immutable(),count)
        report=json.loads((s.OUT/'lifetime-guest.json').read_text());self.assertTrue(report['null_path_false_fit_rejected']);self.assertEqual(report['false_fit_changed_private_bytes'],8);self.assertEqual(report['c_match_credit'],0)
if __name__=='__main__':unittest.main()
