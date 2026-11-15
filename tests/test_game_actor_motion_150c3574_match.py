"""Matching callback, private-local proof, native API compatibility and padders."""
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_actor_motion_150c3574_match as s

class ActorMotion150C3574MatchTests(unittest.TestCase):
    def test_complete_matching_qualification(self):
        record=json.loads((s.OUT/'production-baseline/fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        installed=(s.ROOT/s.SOURCE).read_text()==s.proposed((s.OUT/'production-baseline'/s.SOURCE).read_text())
        plan=json.loads((s.OUT/'adoption-plan.json').read_text()) if (s.OUT/'adoption-plan.json').exists() else {}
        for n,h in record['inputs'].items():self.assertEqual(sha(s.ROOT/n),plan.get(n,h) if installed else h,n)
        before={n:sha(s.ROOT/n) for n in record['inputs']}
        for module in ('tools.experiments.game_actor_motion_150c3574_match','tools.tests.game_actor_motion_150c3574_qualification','tools.tests.game_actor_motion_150c3574_padder'):
            p=subprocess.run([sys.executable,'-m',module],cwd=s.ROOT,env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT)),capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{n:sha(s.ROOT/n) for n in record['inputs']})
        report=dict(installed=installed,body_words=264,frame=56,guards=11,frozen_inputs=len(before))
        (s.OUT/'match-suite.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

    def test_native_default_api_is_unchanged(self):
        from tools.tests import game_actor_motion_150c3574_native as native
        from tools.experiments import game_actor_motion_150c3574_recovery as old
        files={old.OUT/'native.c':'107f8feec5237e35506c84538266755a8cb0bac6e52a732e938a5a6adf9e4d93',
            old.OUT/'native-O0':'873fcceeffdbca8168fbf485e8b6840590e63402907900d8a738b6e820e8152b',
            old.OUT/'native-O2':'9e666c6d4095992dcf559eacd5e45c82194470766b3750862067519b13b45b81',
            old.OUT/'native-O3':'86562f800fe19b1483c9283872623ff91a6a6e0780e17712416c6cf442ae7e9a'}
        for p,want in files.items():self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),want,str(p))
        native.main()
        for p,want in files.items():self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),want,str(p))
        (s.OUT/'native-default-api.json').write_text(json.dumps(dict(files_unchanged=4,fresh_default_run=True),indent=2)+'\n')

if __name__=='__main__':unittest.main()
