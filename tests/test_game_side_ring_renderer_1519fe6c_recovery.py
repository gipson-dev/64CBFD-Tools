"""Private whole-renderer source/caller/native gates, with no installation credit."""
import unittest
from tools.experiments import game_side_ring_renderer_1519fe6c_recovery as s
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
class SideRingRendererRecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):s.main()
 def test_complete_private_source(self):
  from tools.tests import game_side_ring_renderer_1519fe6c_callers as callers
  from tools.tests import game_side_ring_renderer_1519fe6c_native as native
  count=s.immutable();g.main();callers.main();native.main();self.assertEqual(s.immutable(),count)
 def test_inactive_and_failed_allocation_pointer_reads_are_lazy(self):
  for c in (g.Case(count=1),g.Case(count=-128),g.Case(count=2,success=0)):
   m=g.fixture(c)
   for off in range(0x94,0x9C):del m[g.E+off]
   expected,result,calls,_=g.reference(m,c)
   for label,w in g.programs().items():
    q=g.Machine(w,m,c).run();self.assertEqual((g.public(q.memory),q.r[2],q.calls),(g.public(expected),result,calls),label)
if __name__=='__main__':unittest.main()
