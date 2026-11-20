"""Private trail recovery; explicitly reject premature exact-match credit."""
import hashlib,json,subprocess,unittest
from tools.experiments import game_map_trail_emitter_151058b4_recovery as source
from tools.tests import game_map_trail_emitter_151058b4_oracle as guest
from tools.tests.game_map_trail_emitter_151058b4_native import native_checks

class MapTrailRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p=source.prepare()
    def receipt(self,name,value):(self.p['out']/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    def test_01_complete_owner_profile_neighbors_and_recovery_boundary(self):
        q=self.p['report'];self.assertEqual((q['raw_words'],q['retail_words'],q['raw_frame'],q['retail_frame'],q['aligned_word_differences']),(197,197,248,240,24))
        self.assertEqual((q['unchanged_owner_neighbors'],q['warnings_before'],q['warnings_after'],q['matching_credit']),(10,5,2,0));self.assertFalse(q['source_installed']);self.assertTrue(q['pools_unchanged'])
    def test_02_guest_defined_fields_helpers_and_signedness(self):
        result=guest.guest_checks(self.p['truth'],self.p['words']);self.assertEqual((result['cases'],result['visited_words']),(140,[196,196]))
        self.assertEqual(result['raw_padding_differences'],[[22,23],[34,35,51,58,59]]);self.assertEqual(result['public_read_order_difference_cases'],68);self.receipt('guest',result)
    def test_03_original_wrapper_and_commands(self):
        result=guest.caller_checks(self.p['truth'],self.p['words'],source.ROOT);self.assertEqual(result['cases'],40);self.receipt('caller',result)
    def test_04_actual_SDK32_native_and_effective_source_controls(self):
        result=native_checks(self.p['out']);self.assertEqual((result['cases_each_positive_profile'],result['actual_C_wrapper_cases_each_profile'],result['controls']),(68,54,8));self.receipt('native',result)
    def test_05_fired_remaining_frame_and_access_schedule_witness(self):
        result=guest.layout_witness(self.p['truth'],self.p['words']);self.assertEqual(result['raw_minus_retail_private_address'],-8);self.assertEqual(result['matching_credit'],0);self.receipt('layout-witness',result)
    def test_06_frozen_live_image_guards_conversion_and_fresh_recount(self):
        root=source.ROOT;base=source.PACKET/'baseline';elf='conker/build/conker.us.elf'
        for name in(elf,'conker/retail_word_patches.us.csv','conker/progress.csv',source.SOURCE):self.assertEqual((root/name).read_bytes(),(base/name).read_bytes())
        result=subprocess.run(['python3','tools/match_progress.py','conker/progress.csv',elf,'conker/conker.us.bin','--version','us'],cwd=root,capture_output=True,text=True,check=True)
        self.assertIn('4570 / 5521 (82.77%) | 0 | 951',result.stdout);self.assertIn('3897 / 4848 (80.38%) | 0 | 951',result.stdout)
        (self.p['out']/'live-recount.md').write_text(result.stdout)
        self.receipt('uninstalled-image',dict(ELF_unchanged=True,guards_unchanged=True,conversion_rows_unchanged=True,source_unchanged=True,matching_credit=0,sha256=hashlib.sha256((root/elf).read_bytes()).hexdigest()))
if __name__=='__main__':unittest.main()
