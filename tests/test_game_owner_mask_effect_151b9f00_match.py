"""Focused source, guest, caller, rebasing and SDK32 checks."""
import unittest
from tools.experiments import game_owner_mask_effect_151b9f00_match as packet
from tools.tests import game_owner_mask_effect_151b9f00_guest as guest
from tools.tests import game_owner_mask_effect_151b9f00_native as native
from tools.tests import game_owner_mask_effect_151b9f00_callers_links as connected
class OwnerMaskEffect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=packet.qualify()
    def test_01_guarded_owner_Make_and_complete_image(self):
        self.assertTrue(self.report['strict_predicted_ELF_equal'])
        self.assertEqual((self.report['words'],self.report['guards'],self.report['exclusions']),(97,25,0))
    def test_02_guest_model_private_bytes_and_effective_controls(self):guest.run()
    def test_03_original_caller_and_delay_controls(self):connected.caller_checks()
    def test_04_independent_GNU_rebases(self):connected.links()
    def test_05_defined_SDK32_native_and_source_controls(self):native.run()
if __name__=='__main__':unittest.main(verbosity=2)
