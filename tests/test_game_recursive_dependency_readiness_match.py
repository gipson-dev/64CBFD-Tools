"""Canonical recursive dependency qualification, including its actual owner profile."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_recursive_dependency_readiness_match as source
from tools.tests import game_recursive_dependency_readiness_oracle as oracle
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

class RecursiveDependencyReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=ROOT;cls.prepared=ROOT/source.BUILD;cls.out=cls.prepared/('canonical-run-'+str(os.getpid()))
        cls.out.mkdir();cls.receipt={}
        proposed=(cls.prepared/'proposed-owner.c').read_bytes()
        cls.installed=(ROOT/source.SOURCE).read_bytes()==proposed
        cls.inputs=source.check_inputs(ROOT,cls.prepared,cls.installed);source.verify_prepared(cls.prepared)

    def test_01_owner_actual_no_unroll_profile_guards_and_literal_slot(self):
        p=self.prepared;values=source.check_inputs(self.root,p,self.installed)
        self.assertEqual(source.recovered_owner(values[source.SOURCE].decode()).encode(),(p/'proposed-owner.c').read_bytes())
        self.assertEqual(source.normalized_payload(*source.payload(p/'selected.o')),source.payload(p/('original-'+source.FUNCTION+'.o')))
        self.assertEqual(len(source.NEW_GUARDS),12)
        self.assertEqual((p/'proposed-word-patches.csv').read_bytes(),source.guard_manifest(values['conker/retail_word_patches.us.csv']))
        for old,new in(('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):
            self.assertEqual(source.same_functions(p/old,p/new,(source.FUNCTION,)),18)
            self.assertEqual(normalized_pools(p/old),normalized_pools(p/new))
        self.assertEqual((p/'before-padded.o').read_bytes(),values[source.OBJECT])
        self.assertEqual((p/'make-shadow/src/game/generated_C9EC0.c.o').read_bytes(),(p/'qualified-padded.o').read_bytes())
        commands=json.loads((p/'Make-commands.json').read_text());self.assertEqual(len(commands),3)
        self.assertEqual(commands[0].count('-Wo,-loopunroll,0'),1)
        self.assertIn('-O2',commands[0]);self.assertIn('-g3',commands[0])
        for name in('before-owner','after-owner','selected','actual-Make'):self.assertEqual((p/(name+'-diagnostics.txt')).read_bytes(),b'')
        self.receipt['owner']=dict(words=48,frame=40,bindings=5,guards=12,neighbors=18,compact_functions=19,Make_commands=3,retail_no_unroll=True,diagnostics=0)

    def test_02_actual_recursion_raw_C_live_bitmap_and_finite_graph_reference(self):
        q=oracle.recursive_checks(self.root,self.out)
        self.assertEqual((q['cases'],q['visited_body_words'],q['unreachable_word_offset']),(5380,47,144))
        self.assertTrue(q['child_stack_overwrites_live_bitmap_pointer']);self.receipt['guest']=q

    def test_03_native32_all_child_values_bitmap_bytes_chains_and_controls(self):
        q=oracle.native_checks(self.root,self.out)
        self.assertEqual([(x['profile'],x['positive_cases'],x['effective_controls'],x['exit'])for x in q['profiles']],[(x,268284,7,0)for x in('O0','O2','O3')])
        self.receipt['native']=dict(q,positive_cases_each_profile=268284,effective_controls=7)

    def test_04_complete_original_current_caller_and_bounded_outer_helpers(self):
        q=oracle.caller_checks(self.root,self.out)
        self.assertEqual(q['connected_cases'],576);self.assertTrue(q['current_caller_equals_original_208bytes'])
        self.assertTrue(q['all52_caller_words_visited']);self.receipt['caller']=q

    def test_05_all_halfword_entry_branch_delay_and_common_join_values(self):
        q=oracle.opening_checks(self.root,self.out)
        self.assertEqual(q['actual_join_pairs'],65536);self.receipt['opening']=q

    def test_06_actual_padder_three_GNU_maps_IDO_negatives_and_rejections(self):
        q=oracle.rebase_control_checks(self.root,self.out)
        self.assertEqual((q['GNU_layouts'],q['rebased_recursive_cases'],len(q['actual_IDO_effective_controls']),q['rejection_controls']),(3,18,2,10))
        self.receipt['rebases']=q

    def test_07_fired_private_fault_prefixes_and_unbounded_cycle_prefixes(self):
        q=oracle.fault_checks(self.root,self.out)
        self.assertEqual(q['fired_prefix_pairs'],283);self.receipt['faults']=q

    def test_08_strict_complete_image_unchanged_inputs_and_effective_corruptions(self):
        p=self.prepared;values=source.check_inputs(self.root,p,self.installed)
        before=values['conker/build/conker.us.elf'];actual=(p/'first-linked.elf').read_bytes();truth=values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE]
        source.check_image(before,actual,truth)
        at=source.elf_slot_offset(before,source.ENTRY,source.SIZE)
        self.assertEqual(sum(a!=b for a,b in zip(before,actual)),146)
        self.assertEqual(sum(a!=b for a,b in zip(before[at:at+192],truth)),145)
        for location in(0,20,at,at+4,at+191,len(actual)-1):
            wrong=bytearray(actual);wrong[location]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        protected=source.audit_layout(p/'first-linked.elf',self.root/'conker')
        self.assertEqual((protected['exact'],protected['owner_count'],protected['bytes'],protected['different_bytes']),(True,720,189088,0))
        if self.installed:source.audit(self.root,p)
        source.verify_prepared(p)
        self.receipt['image']=dict(changed_bytes=146,code_bytes=145,size_bytes=1,exclusions=0,effective_corruptions=6,protected_owners=720,protected_bytes=189088,other6055_bodies_and6056_addresses_preserved=True)

if __name__=='__main__':unittest.main()
