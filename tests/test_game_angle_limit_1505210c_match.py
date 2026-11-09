"""Direct C, original caller windows and complete overflow image proof."""
import unittest
from tools.experiments import game_angle_limit_1505210c_match as source
from tools.tests import game_angle_limit_1505210c_oracle as guest
from tools.tests import game_angle_limit_1505210c_native as native
from tools.tests import game_angle_limit_1505210c_controls as controls
from tools.tests import game_angle_limit_1505210c_caller as caller
ROOT=source.ROOT
class AngleLimitTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_direct_owner_actual_Make_and_entire_image(self):
  self.assertEqual(tuple(self.report[n]for n in('words','raw_words','frame','guards','raw_neighbors','padded_neighbors','diagnostics')),(85,85,56,0,57,57,0));self.assertTrue(self.report['direct_C']);self.assertEqual(self.report['image_prediction']['removed_file_bytes'],420)
 def test_02_guest_float_contract_and_rebases(self):guest.main()
 def test_03_native_contract_and_effective_controls(self):native.main()
 def test_04_IDO_controls_GNU_links_and_image_corruptions(self):controls.main()
 def test_05_original_callers_and_remaining_trampoline(self):caller.main()
 def test_06_scope_and_unchanged_manifest(self):
  raw,refs=source.payload(ROOT/source.BUILD/'qualified-owner.o')
  for owner,function in(('wrong_owner',source.FUNCTION),(source.OWNER,'wrong_function')):
   with self.assertRaises(ValueError):source.checked(raw,refs,owner,function)
  self.assertEqual((ROOT/source.GUARDS).read_bytes(),(ROOT/source.BUILD/'frozen'/source.GUARDS).read_bytes())
if __name__=='__main__':unittest.main()
