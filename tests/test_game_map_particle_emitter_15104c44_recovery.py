"""Complete emitter semantics and ordered FP/call relation; no matching credit."""
import json,random,unittest
from tools.experiments import game_map_particle_emitter_15104c44_recovery as source
from tools.tests import game_map_particle_emitter_15104c44_oracle as guest
from tools.tests import game_map_particle_emitter_15104c44_native as native
from tools.tests import game_map_particle_emitter_15104c44_relation as proof
class MapParticleRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.prepared=source.prepare()
    def receipt(self,name,value):(self.prepared['out']/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    def test_01_owner_profile_homes_and_complete_fingerprints(self):
        p=self.prepared;r=p['report'];self.assertEqual((r['body_words'],r['frame'],r['word_differences'],r['unchanged_owner_neighbors']),(237,224,52,10))
        self.assertFalse(r['source_installed']);self.assertEqual(r['new_diagnostics'],0)
        for i in range(948):
            wrong=bytearray(p['raw']);wrong[i]^=1
            with self.assertRaises(ValueError):source.checked(bytes(wrong),p['refs'])
        for at in p['refs']:
            wrong=dict(p['refs']);wrong[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):source.checked(p['raw'],wrong)
    def test_02_independent_guest_contract_all_words_and_copied_bytes(self):
        p=self.prepared;r=guest.guest_checks(p['truth'],p['words']);r.update(guest.instruction_controls(p['truth']));self.receipt('guest-contract',r)
    def test_03_actual_SDK32_native_and_source_controls(self):self.receipt('native-contract',native.native_checks(self.prepared['out']))
    def test_04_original_registry_and_dispatcher_callback(self):
        p=self.prepared;self.receipt('original-dispatcher',guest.caller_checks(p['truth'],p['words'],source.ROOT))
    def test_05_complete_CFG_ordered_FP_private_data_and_ABI(self):
        p=self.prepared;report=proof.qualify(p['truth'],p['words']);self.assertEqual(len(report['effective_instruction_controls']),31)
        self.assertTrue(report['all_private_data_compared_before_helpers']);self.assertTrue(report['complete_loop_fixed_point'])
        self.assertFalse(report['physical_raw_fault_PC_private_prefix_identity']);self.receipt('ordered-CFG-relation',report)
    def test_06_affine_frame_domain_and_incoming_meets(self):
        rng=random.Random(0x15104C44);previous=None
        def value(x,env):
            if x[0]=='C':return x[1]
            if x[0]in('X','V'):return env[x]
            self.assertEqual(x[0],'add');return sum(value(a,env)for a in x[1:])&0xffffffff
        for _ in range(100):
            values=[proof.ex('add',('X',rng.randrange(12)),proof.C(rng.choice((0,224,-224,140,-84,4,-4,0x80000000))))if rng.randrange(4)else proof.C(rng.getrandbits(32))for _ in range(2*proof.N)]
            current=proof.abstract([values[:proof.N],values[proof.N:]])
            for inv in(current,current if previous is None else(current[0]&previous[0],current[1]&previous[1])):
                restored=proof.materialize(inv);facts=proof.abstract(restored);self.assertLessEqual(inv[0],facts[0]);self.assertLessEqual(inv[1],facts[1])
                env={('X',i):rng.getrandbits(32)for i in range(12)};env.update({('V',i):value(x,env)for i,x in enumerate(values)})
                self.assertEqual([value(x,env)for x in values],[value(x,env)for stream in restored for x in stream])
            previous=current
if __name__=='__main__':unittest.main()
