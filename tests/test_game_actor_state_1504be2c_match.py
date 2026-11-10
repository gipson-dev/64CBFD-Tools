"""Complete actor state update, ABI, real retail window and checked insertion."""
import unittest
from tools.experiments import game_actor_state_1504be2c_match as source
from tools.tests import game_actor_state_1504be2c_oracle as guest
from tools.tests import game_actor_state_1504be2c_native as native
from tools.tests import game_actor_state_1504be2c_controls as controls
from tools.tests import game_actor_state_1504be2c_caller as caller
ROOT=source.ROOT
class ActorStateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_owner_actual_Make_entire_image(self):
  self.assertEqual(tuple(self.report[n]for n in('words','raw_words','frame','guards','insertions','raw_neighbors','padded_neighbors','strict_unexplained_bytes','image_changed_bytes')),(147,146,40,101,1,57,57,0,480))
  self.assertEqual(self.report['actual_Make']['commands'],5)
 def test_02_guest_aliases_and_rebases(self):guest.main()
 def test_03_native_SDK32_effective_controls(self):native.main()
 def test_04_stale_guards_IDO_GNU_and_insertion(self):controls.main()
 def test_05_original_retail_caller_window(self):caller.main()
 def test_06_scope_and_guard_history(self):
  raw,refs=source.payload(ROOT/source.BUILD/'selected.o')
  for owner,function in(('wrong_owner',source.FUNCTION),(source.OWNER,'wrong_function')):
   with self.assertRaises(ValueError):source.checked(raw,refs,owner,function)
  with self.assertRaises(ValueError):source.checked(raw,{})
  old=(ROOT/source.BUILD/'frozen'/source.GUARDS).read_bytes();new=source.guards(ROOT/source.BUILD);self.assertTrue(new.startswith(old));self.assertIn((ROOT/source.GUARDS).read_bytes(),(old,new))
if __name__=='__main__':unittest.main()
