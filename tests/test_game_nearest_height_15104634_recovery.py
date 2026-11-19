"""Uninstalled full-function semantics; no guard, private or adoption credit."""
import json,unittest
from tools.experiments import game_nearest_height_15104634_recovery as source
from tools.tests import game_nearest_height_15104634_oracle as guest
from tools.tests import game_nearest_height_15104634_native as native
class NearestHeightRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.prepared=source.prepare()
    def receipt(self,name,value):(self.prepared['out']/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    def test_01_complete_owner_profile_frozen_inputs_and_corruption_gates(self):
        p=self.prepared;r=p['report'];self.assertEqual((r['body_words'],r['frame'],r['real_word_differences'],r['unchanged_raw_neighbors']),(272,224,137,4))
        self.assertFalse(r['source_installed']);self.assertEqual(r['matching_credit'],0)
        for i in range(1088):
            wrong=bytearray(p['raw']);wrong[i]^=1
            with self.assertRaises(ValueError):source.checked(bytes(wrong),p['refs'])
        for at in p['refs']:
            wrong=dict(p['refs']);wrong[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):source.checked(p['raw'],wrong)
    def test_02_complete_independent_guest_contract_and_effective_controls(self):self.receipt('guest-contract',guest.guest_checks(self.prepared))
    def test_03_actual_native32_private_C_and_effective_controls(self):self.receipt('native-contract',native.native_checks(self.prepared['out']))
    def test_04_original_caller_float_ABI_and_height_clamp(self):self.receipt('original-caller',guest.caller_checks(self.prepared))
if __name__=='__main__':unittest.main()
