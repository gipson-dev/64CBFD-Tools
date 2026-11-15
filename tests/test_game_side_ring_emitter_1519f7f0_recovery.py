"""Complete literal-source qualification, preserving historical recovery fixtures."""
import hashlib,unittest
from tools.experiments import game_side_ring_emitter_1519f7f0_match as s
class SideRingEmitterRecoveryTests(unittest.TestCase):
 def test_undefined_private_inverse_is_excluded(self):
  from tools.tests import game_side_ring_emitter_1519f7f0_oracle as g
  c=g.Case(motion=1,progress=g.bits(2.))
  with self.assertRaisesRegex(AssertionError,'undefined private input'):
   g.reference(g.fixture(c),c)
 def test_complete_literal_source(self):
  from tools.tests import game_side_ring_emitter_1519f7f0_oracle as g
  from tools.tests import game_side_ring_emitter_1519f7f0_callers as callers
  from tools.tests import game_side_ring_emitter_1519f7f0_native as native
  paths=(s.SOURCE,'conker/retail_word_patches.us.csv','conker/build/conker.us.elf','conker/progress.csv')
  hashes=lambda:{p:hashlib.sha256((s.ROOT/p).read_bytes()).hexdigest() for p in paths}
  before=hashes();s.main();streams=s.programs();g.qualify_match(streams,s.OUT)
  callers.main(streams,s.OUT);native.main(s.PIN,s.OUT)
  self.assertEqual(before,hashes())
if __name__=='__main__':unittest.main()
