"""Fresh private recovery gates; passing never installs or assigns C credit."""
import hashlib,json,unittest
from tools.experiments import game_actor_motion_150c3574_recovery as source
from tools.tests import game_actor_motion_150c3574_oracle as guest
from tools.tests import game_actor_motion_150c3574_native as native
from tools.tests import game_actor_motion_150c3574_callers as callers

class ActorMotionRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source.main()
        report=json.loads((source.OUT/'recovery-report.json').read_text())
        assert report['raw_sha256']=='70dd14c2f17f6e24ed95e967bd815a49d49364c10d3dfafd5ce904114925a3a0'
        assert report['body_words']==264 and report['frame']==56 and report['bindings']==40
        assert report['real_word_differences']==81 and report['neighbors']==17
        assert report['prior_pool_guard'] and not report['installed'] and report['c_match_credit']==0

    def test_complete_finite_guest_behavior(self):guest.main()
    def test_native32_with_six_effective_controls(self):native.main()
    def test_original_dispatch_window(self):callers.main()
    def test_production_inputs_remain_frozen(self):
        record=json.loads((source.OUT/'production-baseline/fingerprints.json').read_text())
        for name,want in record['inputs'].items():
            self.assertEqual(hashlib.sha256((source.ROOT/name).read_bytes()).hexdigest(),want,name)
        self.assertIn('s32 func_150C3574() {\n    return 0;\n}',(source.ROOT/source.SOURCE).read_text())

if __name__=='__main__':unittest.main()
