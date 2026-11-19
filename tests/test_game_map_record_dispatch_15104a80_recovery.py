"""Private semantic recovery; no normalization or adoption credit."""
import json,unittest
from tools.experiments import game_map_record_dispatch_15104a80_recovery as source
from tools.tests import game_map_record_dispatch_15104a80_oracle as guest
from tools.tests import game_map_record_dispatch_15104a80_native as native
class MapRecordRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.prepared=source.prepare()
    def receipt(self,name,value):(self.prepared['out']/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    def test_01_complete_owner_profile_fingerprint_and_warning_boundary(self):
        p=self.prepared;r=p['report'];self.assertEqual((r['body_words'],r['retail_words'],r['frame'],r['unchanged_owner_neighbors']),(110,113,104,10))
        self.assertEqual(r['new_diagnostics'],0);self.assertFalse(r['source_installed']);self.assertEqual(r['matching_credit'],0)
        for i in range(440):
            wrong=bytearray(p['raw']);wrong[i]^=1
            with self.assertRaises(ValueError):source.checked(bytes(wrong),p['refs'])
        for at in p['refs']:
            wrong=dict(p['refs']);wrong[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):source.checked(p['raw'],wrong)
    def test_02_original_and_raw_guest_contract_with_original_wrapper(self):self.receipt('guest-contract',guest.guest_checks(self.prepared))
    def test_03_actual_SDK32_native_source_and_effective_controls(self):self.receipt('native-contract',native.native_checks(self.prepared['out']))
    def test_04_ordered_memory_prefixes_and_private_bytes(self):self.receipt('memory-prefixes',guest.prefix_checks(self.prepared))
    def test_05_registered_original_JALR_window(self):self.receipt('original-callback-window',guest.caller_checks(self.prepared))
if __name__=='__main__':unittest.main()
