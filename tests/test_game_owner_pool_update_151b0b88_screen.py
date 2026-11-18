"""A semantic screen is deliberately not a byte-exact adoption gate."""
import unittest
from tools.experiments import game_owner_pool_update_151b0b88_screen as m
from tools.tests import game_owner_pool_update_151b0b88_oracle as guest
from tools.tests import game_owner_pool_update_151b0b88_native as native
from tools.tests import game_owner_pool_update_151b0b88_callers as callers
class OwnerPoolUpdateScreen(unittest.TestCase):
 def test_01_source_and_neighbors(self):self.assertEqual(m.qualify_source()['c_match_credit'],0)
 def test_02_guest_semantics(self):self.assertTrue(guest.main()['passes'])
 def test_03_native_source_and_controls(self):self.assertTrue(native.main()['passes'])
 def test_04_original_dispatcher(self):self.assertTrue(callers.main()['passes'])
 @classmethod
 def tearDownClass(cls):m.check_inputs()
if __name__=='__main__':unittest.main()
