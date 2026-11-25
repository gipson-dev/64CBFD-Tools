import unittest
from tools.experiments import game_sibling_preset_150b5c38_match as packet,game_sibling_preset_150b5c38_make as make,game_sibling_preset_150b5c38_image as image
from tools.tests import game_sibling_preset_150b5c38_guest as guest,game_sibling_preset_150b5c38_boundaries as boundaries,game_sibling_preset_150b5c38_callers as callers,game_sibling_preset_150b5c38_helpers as helpers,game_sibling_preset_150b5c38_native as native
class SiblingPresetTests(unittest.TestCase):
 def test_01_both_owners_Make_and_strict_image(self):
  q=packet.objects();self.assertEqual((q['words'],q['guards'],q['neighbors']),(127,51,11));self.assertTrue(q['producer_whole_object_identical_to_frozen_baseline']);self.assertTrue(make.main()['both_changed_owners_replayed']);self.assertTrue(image.main()['strict_predicted_ELF_equal'])
 def test_02_guest_and_fault_prefixes(self):self.assertEqual(guest.main()['access_fault_quads'],225)
 def test_03_slot_limits_and_GNU(self):self.assertEqual(boundaries.main()['binding_pins'],11)
 def test_04_both_original_callers_and_helpers(self):
  self.assertEqual(callers.main()['cases_per_parent'],{'0x15071690':512,'0x15081e78':6144});self.assertEqual(helpers.main()['particle_cases'],64)
 def test_05_native_cross_owner_ABI_and_controls(self):self.assertEqual(len(native.main()['effective_controls']),13)
if __name__=='__main__':unittest.main()
