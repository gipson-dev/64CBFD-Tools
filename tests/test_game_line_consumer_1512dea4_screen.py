"""Fail-closed evidence for a private, explicitly uncredited camera screen."""
import hashlib,json,os,subprocess,sys,unittest
from pathlib import Path

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-line-consumer-1512dea4-screen'
MANIFEST=json.loads((Path(__file__).resolve().parents[1]/'experiments/game_line_consumer_1512dea4_manifest.json').read_text())

def run(name):
    env=dict(os.environ,CBFD_CONSUMER_ROOT=str(ROOT),PYTHONDONTWRITEBYTECODE='1')
    p=subprocess.run([sys.executable,'-m','tools.experiments.game_line_consumer_1512dea4_'+name],
                     cwd=ROOT,env=env,capture_output=True,text=True,timeout=240)
    if p.returncode:raise AssertionError((name,p.stdout,p.stderr))

class LineConsumerScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for path,expected in MANIFEST['inputs'].items():
            actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
            if actual!=expected:raise ValueError('Private screen input changed: '+path)
        run('shapes')

    def test_private_owner_shapes(self):
        rows=json.loads((OUT/'shape-screen.json').read_text())
        self.assertEqual([r['words'] for r in rows],[171,175,171,175,171,175])
        self.assertTrue(all(r['uninitialized_default_unqualified'] for r in rows))
        self.assertTrue(all(r['first_word']=='0x27BDFFA0' for r in rows))
        self.assertTrue(all(not r['diagnostics'] for r in rows))

    def test_retail_incoming_stack_dependency(self):
        run('retail');report=json.loads((OUT/'retail-kind-screen.json').read_text())
        self.assertEqual(report['cases'],48)
        self.assertEqual(report['invalid_kind_output_variants'],{'4':4,'255':4})
        self.assertTrue(report['immediate_branch_only'])

    def test_shapes_do_not_handle_invalid_kind(self):
        run('guest');report=json.loads((OUT/'guest-shape-screen.json').read_text())
        self.assertEqual(report['valid_mismatches'],[0]*6)
        self.assertEqual(report['invalid_mismatches'],[16]*6)
        self.assertEqual(report['errors'],0)

    def test_local_order_does_not_recover_retail_frame(self):
        run('local_order');rows=json.loads((OUT/'local-order-screen.json').read_text())
        self.assertEqual(len(rows),6)
        self.assertTrue(all(r['frame']==0x60 and r['words']==171 for r in rows))
        self.assertTrue(all(r['uncredited'] and not r['diagnostics'] for r in rows))

    def test_connected_retail_smoothing_helper(self):
        run('connected');report=json.loads((OUT/'connected-helper-screen.json').read_text())
        self.assertEqual(report['connected_retail_helper_words'],54)
        self.assertEqual(report['valid_mismatches'],[0]*6)
        self.assertEqual(report['invalid_mismatches'],[4]*6)
        self.assertEqual(report['retail_call_counts'],[5]*12)
        self.assertEqual(report['retail_errors'],[])

if __name__=='__main__':unittest.main()
