"""Canonical owner-link event gate qualification, including actual dispatcher and ABI."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_owner_link_event_gate_match as source
from tools.tests import game_owner_link_event_gate_oracle as oracle
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

class OwnerLinkEventGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=ROOT;cls.prepared=ROOT/source.BUILD;cls.out=cls.prepared/('canonical-run-'+str(os.getpid()))
        cls.out.mkdir();cls.receipt={}
        proposed=(cls.prepared/'proposed-owner.c').read_bytes()
        cls.installed=(ROOT/source.SOURCE).read_bytes()==proposed
        cls.inputs=source.check_inputs(ROOT,cls.prepared,cls.installed);source.verify_prepared(cls.prepared)

    def test_01_owner_actual_Make_guards_and_full_literal_slot(self):
        p=self.prepared;values=source.check_inputs(self.root,p,self.installed)
        self.assertEqual(source.recovered_owner(values[source.SOURCE].decode()).encode(),(p/'proposed-owner.c').read_bytes())
        self.assertEqual(source.normalized_payload(*source.payload(p/'selected.o')),source.payload(p/('original-'+source.FUNCTION+'.o')))
        self.assertEqual(len(source.NEW_GUARDS),4)
        self.assertEqual((p/'proposed-word-patches.csv').read_bytes(),source.guard_manifest(values['conker/retail_word_patches.us.csv']))
        for old,new in(('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):
            self.assertEqual(source.same_functions(p/old,p/new,(source.FUNCTION,)),16)
            self.assertEqual(normalized_pools(p/old),normalized_pools(p/new))
        self.assertEqual((p/'before-padded.o').read_bytes(),values[source.OBJECT])
        self.assertEqual((p/'make-shadow/src/game/generated_1028F0.c.o').read_bytes(),(p/'qualified-padded.o').read_bytes())
        commands=json.loads((p/'Make-commands.json').read_text());self.assertEqual(len(commands),5)
        compiler=[cmd for cmd in commands if cmd[0]=='../ido/ido5.3_recomp/cc'];self.assertEqual(len(compiler),1)
        self.assertIn('-O2',compiler[0]);self.assertIn('-g3',compiler[0]);self.assertFalse(any('-loopunroll'in x for x in compiler[0]))
        self.assertEqual((p/'proposed-owner.c').read_text().count('#pragma GLOBAL_ASM'),6)
        self.assertIn('void func_150D596C(struct260 *owner, s32 eventAddress, u8 command)',(p/'proposed-owner.c').read_text())
        for name in('before-owner','after-owner','selected','actual-Make'):self.assertEqual((p/(name+'-diagnostics.txt')).read_bytes(),b'')
        self.receipt['owner']=dict(words=48,frame=24,bindings=1,guards=4,neighbors=16,compact_functions=17,Make_commands=5,retained_GLOBAL_ASM=6,diagnostics=0)

    def test_02_command_byte_pointer_priority_identity_alias_and_home_semantics(self):
        q=oracle.guest_checks(self.root,self.out)
        self.assertEqual((q['cases'],q['reachable_words'],q['unreachable_offsets']),(12288,46,[104,152]));self.receipt['guest']=q

    def test_03_native32_canonical_ABI_actual_dispatcher_release_and_controls(self):
        q=oracle.native_checks(self.root,self.out)
        self.assertEqual([(x['profile'],x['target_cases'],x['dispatcher_cases'],x['effective_controls'],x['exit'])for x in q['profiles']],[(x,786434,131072,12,0)for x in('O0','O2','O3')]);self.receipt['native']=q

    def test_04_complete_original_current_dispatcher_actual_registration(self):
        q=oracle.caller_checks(self.root,self.out)
        self.assertEqual((q['cases'],q['registry_entries'],q['registry_index']),(13568,74,40));self.receipt['caller']=q

    def test_05_retained_release_helper_kind_reload_and_bounded_callbacks(self):
        q=oracle.release_checks(self.root,self.out)
        self.assertEqual((q['cases'],q['retained_helper_words']),(96,28));self.receipt['release']=q

    def test_06_actual_padder_three_GNU_maps_IDO_negatives_and_corruptions(self):
        q=oracle.rebase_checks(self.root,self.out)
        self.assertEqual((q['layouts'],q['GNU_links'],q['rebased_cases'],q['rejection_controls'],len(q['actual_IDO_effective_controls'])),(3,9,18,52,4));self.receipt['rebases']=q

    def test_07_fired_guest_fault_prefixes_and_ignored_unmapped_arguments(self):
        q=oracle.fault_checks(self.root,self.out)
        self.assertGreater(q['fired_prefix_pairs'],0);self.receipt['faults']=q

    def test_08_strict_complete_image_unchanged_inputs_and_effective_corruptions(self):
        p=self.prepared;values=source.check_inputs(self.root,p,self.installed)
        before=values['conker/build/conker.us.elf'];actual=(p/'first-linked.elf').read_bytes();truth=values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE]
        source.check_image(before,actual,truth)
        at=source.elf_slot_offset(before,source.ENTRY,source.SIZE)
        self.assertEqual(sum(a!=b for a,b in zip(before,actual)),134)
        self.assertEqual(sum(a!=b for a,b in zip(before[at:at+192],truth)),133)
        for location in(0,20,at,at+4,at+191,len(actual)-1):
            wrong=bytearray(actual);wrong[location]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        protected=source.audit_layout(p/'first-linked.elf',self.root/'conker')
        self.assertEqual((protected['exact'],protected['owner_count'],protected['bytes'],protected['different_bytes']),(True,720,189088,0))
        if self.installed:source.audit(self.root,p)
        source.verify_prepared(p)
        self.receipt['image']=dict(changed_bytes=134,code_bytes=133,size_bytes=1,exclusions=0,effective_corruptions=6,protected_owners=720,protected_bytes=189088,other6055_bodies_and6056_addresses_preserved=True)

if __name__=='__main__':unittest.main()
