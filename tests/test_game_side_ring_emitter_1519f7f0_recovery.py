"""Focused private screen only. This deliberately does not award a C match."""
import json,os,subprocess,sys,unittest
from tools.experiments import game_side_ring_emitter_1519f7f0_recovery as s
class SideRingEmitterRecoveryTests(unittest.TestCase):
 def test_private_screen(self):
  s.main();env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT))
  for module in ('game_side_ring_emitter_1519f7f0_oracle','game_side_ring_emitter_1519f7f0_callers'):
   subprocess.run([sys.executable,'-m','tools.tests.'+module],cwd=s.ROOT,env=env,check=True)
  self.assertEqual(s.immutable(),len(json.loads((s.OUT/'production-baseline/fingerprints.json').read_text())['inputs']))
if __name__=='__main__':unittest.main()
