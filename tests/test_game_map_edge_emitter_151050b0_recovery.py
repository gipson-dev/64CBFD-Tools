"""Private semantic recovery and explicit, uncredited retail-layout boundary."""
import hashlib,json,unittest
from tools.experiments import game_map_edge_emitter_151050b0_recovery as source
from tools.tests import game_map_edge_emitter_151050b0_oracle as guest
from tools.tests.game_map_edge_emitter_151050b0_native import native_checks
class MapEdgeRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p=source.prepare()
    def receipt(self,name,v):(self.p['out']/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def test_01_complete_owner_profile_pools_neighbors_and_inputs(self):
        r=self.p['report'];self.assertEqual((r['raw_words'],r['retail_words'],r['frame'],r['unchanged_owner_neighbors']),(275,279,208,10));self.assertEqual(r['unchanged_warnings'],5);self.assertTrue(r['pools_unchanged']);self.assertEqual(r['matching_credit'],0)
    def test_02_guest_public_state_packet_fields_and_ordered_FP(self):self.receipt('guest',guest.guest_checks(self.p['truth'],self.p['words']))
    def test_03_connected_original_callback_dispatcher(self):self.receipt('caller',guest.caller_checks(self.p['truth'],self.p['words'],source.ROOT))
    def test_04_fired_public_prefixes_and_effective_instruction_controls(self):
        self.receipt('prefix',guest.prefix_checks(self.p['truth'],self.p['words']));controls={
          'timer-branch':(0x48,1),'timer-field':(0x7C,2),'packet-duration':(0x17C,2),
          'conversion-control':(0x1E4,1<<16),'interpolation-component':(0x344,4),'channel-byte':(0x3E8,1)};tested=[]
        for name,(off,mask)in controls.items():
            wrong=self.p['truth'][:];wrong[off//4]^=mask;effective=False
            for c in(guest.Case(),guest.Case(timer=-1),guest.Case(timer=0),guest.Case(mutation=8)):
                try:
                    initial=guest.fixture(c);m=guest.Oracle(wrong,initial,c).run();assert(guest.public(m.memory),m.calls,m.packets)==guest.reference(initial,c);guest.preserved(m,c)
                except(AssertionError,ValueError,KeyError):effective=True;break
            self.assertTrue(effective,name);tested.append(name)
        self.receipt('instruction-controls',dict(effective_controls=tested))
    def test_05_actual_native_SDK32_and_exhaustive_RNG_index_domain(self):self.receipt('native',native_checks(self.p['out']))
    def test_06_installed_baseline_preserved_and_layout_still_open(self):
        r=source.ROOT;self.assertEqual((r/source.SOURCE).read_text(),source.SPEC['old_source']);self.assertIn('#pragma GLOBAL_ASM("asm/nonmatchings/game_131F30/func_151050B0.s")',(r/source.SOURCE).read_text())
        for n in('conker/build/conker.us.elf','conker/progress.csv','conker/retail_word_patches.us.csv',source.SPEC['object']):self.assertEqual(hashlib.sha256((r/n).read_bytes()).hexdigest(),source.SPEC['predecessor']['inputs'][n])
        self.assertNotEqual(self.p['words'],self.p['truth']);self.assertFalse(self.p['report']['source_installed']);self.assertTrue(self.p['report']['concrete_layout_GNU_Make_full_image_gates_pending'])
        self.receipt('boundary',dict(source_installed=False,matching_credit=0,raw_words=275,retail_words=279,frame=208,whole_installed_ELF_unchanged=True,padder_Make_rebases_full_image_and_guard_qualification_pending=True))
if __name__=='__main__':unittest.main()
