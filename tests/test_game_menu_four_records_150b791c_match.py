"""Full candidate, object, semantic and linked-image qualification."""
import json,unittest
from tools.experiments import game_menu_four_records_150b791c_match as source
from tools.tests import game_menu_four_records_150b791c_oracle as guest
from tools.tests import game_menu_four_records_150b791c_native as native
from tools.tests import game_menu_four_records_150b791c_callers as callers
class MenuFourRecordsMatch(unittest.TestCase):
 def test_01_source_and_proof(self):source.qualify_source()
 def test_02_padders_and_controls(self):
  source.padders();self.assertEqual(source.guard_controls(),116)
 def test_03_guest_effects(self):self.assertTrue(guest.main()['passes'])
 def test_04_native_and_controls(self):self.assertTrue(native.main()['passes'])
 def test_05_original_menu_dispatcher(self):self.assertTrue(callers.main()['passes'])
 def test_06_actual_Make_and_image(self):source.qualify_image()
 @classmethod
 def tearDownClass(cls):source.check_inputs()
if __name__=='__main__':unittest.main()
