"""Fire real compiler watches and reject shape-only trail matching."""
import json,hashlib,subprocess,unittest
from tools.experiments import game_map_trail_emitter_151058b4_frame as source
from tools.tests import game_map_trail_emitter_151058b4_oracle as guest
from tools.tests.game_map_trail_emitter_151058b4_frame_native import native_checks

class TrailFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p=source.prepare()
    def test_01_refined_owner_guest_caller_and_native_defined_behavior(self):
        self.assertEqual(self.p['report']['differences'],12)
        result=guest.guest_checks(self.p['truth'],self.p['words'])
        self.assertEqual((result['cases'],result['visited_words']),(140,[196,196]))
        self.assertEqual(result['raw_padding_differences'],[[22,23],[34,35,51,58,59]])
        self.assertEqual(result['public_read_order_difference_cases'],68)
        caller=guest.caller_checks(self.p['truth'],self.p['words'],source.ROOT);self.assertEqual(caller['cases'],40)
        native=native_checks(self.p['out']);self.assertEqual((native['cases_each_positive_profile'],native['actual_C_wrapper_cases_each_profile'],native['controls']),(68,54,8))
        witness=guest.layout_witness(self.p['truth'],self.p['words']);self.assertEqual(witness['raw_minus_retail_private_address'],-8)
        for name,value in(('guest',result),('caller',caller),('layout-witness',witness)):(self.p['out']/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    def test_02_owned_compiler_frames_extent_watches_and_effective_control(self):
        records={kind:source.trace(kind)for kind in('canonical','refined','anonymous-control')}
        self.assertEqual(records['canonical']['local_definitions'],{'frontend':[124],'optimizer':[128]})
        self.assertEqual(records['refined']['local_definitions'],{'frontend':[120],'optimizer':[124]})
        self.assertEqual(records['anonymous-control']['events'][-1]['frame'],240)
        listing=source.allocation_listing();self.assertTrue(listing['code_unchanged'])
    def test_03_actual_direction_definition_and_incompatible_pitch_control(self):
        report=source.direction_contract();self.assertTrue(report['wide_pitch_contract_rejected'])
    def test_04_live_image_and_fresh_actual_ELF_recount_unchanged(self):
        root=source.ROOT;base=source.prior.PACKET/'baseline';elf='conker/build/conker.us.elf'
        for n in(elf,'conker/progress.csv','conker/retail_word_patches.us.csv',source.prior.SOURCE):self.assertEqual((root/n).read_bytes(),(base/n).read_bytes())
        self.assertEqual(hashlib.sha256((root/elf).read_bytes()).hexdigest(),source.ELF_SHA)
        result=subprocess.run(['python3','tools/match_progress.py','conker/progress.csv',elf,'conker/conker.us.bin','--version','us'],cwd=root,capture_output=True,text=True,check=True)
        self.assertIn('4570 / 5521 (82.77%) | 0 | 951',result.stdout);self.assertIn('3897 / 4848 (80.38%) | 0 | 951',result.stdout)
        (self.p['out']/'live-recount.md').write_text(result.stdout)
if __name__=='__main__':unittest.main()
