"""Motion approach: complete source/ABI/execution/owner/caller/image qualification."""
import unittest
from tools.experiments import game_motion_approach_1505a3a8_match as source
from tools.tests import game_motion_approach_1505a3a8_oracle as guest
from tools.tests import game_motion_approach_1505a3a8_native as native
from tools.tests import game_motion_approach_1505a3a8_controls as controls
from tools.tests import game_motion_approach_1505a3a8_caller as caller
ROOT=source.ROOT
class MotionApproachTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_owner_actual_Make_entire_image(self):
  self.assertEqual(tuple(self.report[n]for n in('words','raw_words','frame','guards','insertions','omissions','raw_neighbors','padded_neighbors','strict_unexplained_bytes','image_changed_bytes')),(137,137,16,2,0,0,88,88,0,455))
  self.assertTrue(self.report['caller_declaration']['padded_object_identical'])
 def test_02_guest_flags_float_edges_aliases_rebases(self):guest.main()
 def test_03_native_SDK32_effective_controls(self):native.main()
 def test_04_fail_closed_controls_and_GNU_links(self):controls.main()
 def test_05_seven_callers_return_liveness_and_complete_parent(self):caller.main()
 def test_06_scope_and_guard_history(self):
  raw,refs=source.payload(ROOT/source.BUILD/'selected.o')
  for owner,function in(('wrong_owner',source.FUNCTION),(source.OWNER,'wrong_function')):
   with self.assertRaises(ValueError):source.checked(raw,refs,owner,function)
  with self.assertRaises(ValueError):source.checked(raw,{})
  old=(ROOT/source.BUILD/'frozen'/source.GUARDS).read_bytes();new=source.guards(ROOT/source.BUILD);self.assertTrue(new.startswith(old));self.assertIn((ROOT/source.GUARDS).read_bytes(),(old,new))
if __name__=='__main__':unittest.main()
