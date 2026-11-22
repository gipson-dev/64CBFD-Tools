"""All seven adoption gates for the script-driven view callback."""
import unittest
from tools.experiments import game_view_light_script_150ecc70_match as packet
from tools.tests import game_view_light_script_150ecc70_guest as guest
from tools.tests import game_view_light_script_150ecc70_faults as faults
from tools.tests import game_view_light_script_150ecc70_callers as callers
from tools.tests import game_view_light_script_150ecc70_connected as connected
from tools.tests import game_view_light_script_150ecc70_native as native
class ViewLightScript(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=packet.qualify()
 def test_01_owner_and_whole_image(self):
  self.assertTrue(self.report['strict_predicted_ELF_equal']);self.assertEqual(self.report['exclusions'],0)
  self.assertEqual((self.report['raw_words'],self.report['normalized_words'],self.report['guards']),(341,341,28))
 def test_02_ordered_guest(self):self.assertEqual(guest.main()['cases_per_stream'],664)
 def test_03_both_padders_and_full_signed_clamps(self):
  report=packet.normalize();self.assertTrue(report['both_padders_equal']);self.assertEqual(report['GNU_links'],8)
 def test_04_fault_prefixes(self):self.assertEqual(faults.main()['access_fault_pairs'],158)
 def test_05_original_callback_ABI(self):self.assertEqual(callers.main()['cases_per_stream'],80)
 def test_06_original_providers(self):self.assertEqual(connected.main()['target_cases_per_stream'],960)
 def test_07_SDK32_source_and_negative_controls(self):self.assertEqual(len(native.main()['effective_source_controls']),9)
if __name__=='__main__':unittest.main(verbosity=2)
