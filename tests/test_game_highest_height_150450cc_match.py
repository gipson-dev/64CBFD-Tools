"""Complete highest-height query, original context/caller and protected image qualification."""
import unittest
from tools.experiments import game_highest_height_150450cc_match as source
from tools.tests import game_highest_height_150450cc_oracle as guest
from tools.tests import game_highest_height_150450cc_native as native
from tools.tests import game_highest_height_150450cc_controls as controls
from tools.tests import game_highest_height_150450cc_caller as caller
ROOT=source.ROOT
class HighestHeightTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_owner_actual_Make_and_entire_image(self):
  self.assertEqual(tuple(self.report[n]for n in('words','raw_words','frame','guards','insertions','raw_neighbors','padded_neighbors','diagnostics_before','diagnostics_after','new_diagnostics','image_changed_bytes','strict_unexplained_bytes')),(144,144,40,30,0,42,42,0,0,0,197,0))
  self.assertEqual(self.report['actual_Make']['commands'],5)
 def test_02_guest_heights_aliases_original_context_and_rebases(self):guest.main()
 def test_03_native_SDK32_contract_and_effective_controls(self):native.main()
 def test_04_stale_guards_payloads_IDO_controls_and_GNU(self):controls.main()
 def test_05_complete_retail_height_combiner(self):caller.main()
 def test_06_scope_and_guard_prefix(self):
  raw,refs=source.payload(ROOT/source.BUILD/'selected.o')
  for owner,function in(('wrong_owner',source.FUNCTION),(source.OWNER,'wrong_function')):
   with self.assertRaises(ValueError):source.checked(raw,refs,owner,function)
  with self.assertRaises(ValueError):source.normalize(bytes([raw[0]^1])+raw[1:],refs)
  old=(ROOT/source.BUILD/'frozen'/source.GUARDS).read_bytes();new=source.guards(ROOT/source.BUILD)
  self.assertTrue(new.startswith(old));self.assertIn((ROOT/source.GUARDS).read_bytes(),(old,new))
if __name__=='__main__':unittest.main()
