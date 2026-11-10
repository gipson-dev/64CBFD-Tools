"""Complete entity-height pair and its three unchanged retail callers."""
import unittest
from tools.experiments import game_context2_height_pair_match as source
from tools.tests import game_context2_height_pair_oracle as guest
from tools.tests import game_context2_height_pair_native as native
from tools.tests import game_context2_height_pair_controls as controls
from tools.tests import game_context2_height_pair_caller as caller
ROOT=source.ROOT
class Context2HeightPairTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_owner_actual_Make_and_entire_image(self):
  self.assertEqual(tuple(self.report[n]for n in('guards','insertions','raw_neighbors','padded_neighbors','diagnostics_before','diagnostics_after','new_diagnostics','image_changed_bytes','strict_unexplained_bytes')),(146,0,41,41,0,0,0,472,0))
  self.assertEqual(self.report['actual_Make']['commands'],5)
  for function,guards in zip(source.FUNCTIONS,(72,74)):
   v=self.report['targets'][function];self.assertEqual(tuple(v[n]for n in('words','raw_words','frame','guards')),(153,153,40,guards))
 def test_02_guest_aliases_and_rebases(self):guest.main()
 def test_03_native_SDK32_and_effective_controls(self):native.main()
 def test_04_stale_guards_IDO_controls_and_GNU(self):controls.main()
 def test_05_complete_retail_callers(self):caller.main()
 def test_06_scope_and_guard_prefix(self):
  for f in source.FUNCTIONS:
   raw,refs=source.payload(ROOT/source.BUILD/'selected.o',f)
   for owner,function in(('wrong_owner',f),(source.OWNER,'wrong_function')):
    with self.assertRaises(ValueError):source.checked(raw,refs,owner,function)
   with self.assertRaises(ValueError):source.normalize(bytes([raw[0]^1])+raw[1:],refs,f)
  old=(ROOT/source.BUILD/'frozen'/source.GUARDS).read_bytes();new=source.guards(ROOT/source.BUILD);self.assertTrue(new.startswith(old));self.assertIn((ROOT/source.GUARDS).read_bytes(),(old,new))
if __name__=='__main__':unittest.main()
