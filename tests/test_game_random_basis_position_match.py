"""Random basis position: live sampling, affine outputs and complete-image closure."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_random_basis_position_match as source
from tools.tests import game_random_basis_position_oracle as oracle
from tools.tests import game_random_basis_position_integration as integration
from tools.tests import game_random_basis_position_native as native
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class RandomBasisPositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output)
        cls.installed=os.environ.get('CBFD_RANDOM_BASIS_INSTALLED')=='1'
        cls.values=source.check_inputs(ROOT,cls.output,cls.installed)

    def test_01_sequenced_payloads_guards_and_independent_links(self):
        for i,(function,owner,entry,rom)in enumerate(source.SPECS):
            obj,diag=source.compile_owner(ROOT,self.output,source.HEADERS+source.SELECTED.replace(source.SPECS[0][0],function),'public-fresh-'+function)
            self.assertFalse(diag);raw,refs=source.checked_payload(*source.payload(obj,function))
            original,bindings=source.payload(self.output/('original-'+function+'.o'),function)
            self.assertEqual(source.normalized(raw,refs),(original,bindings));role=source.prove_roles(raw,original);self.assertEqual(role['helper_call_offsets'],[24,32,76]);self.assertEqual(role['output_store_offsets'],[132,176,220]);self.assertEqual(struct.unpack_from('>I',raw)[0],0x27BDFFD0)
            before=self.values['conker/src/game/'+owner+'.c'].decode()
            self.assertEqual(source.recovered_owner(before,i),(self.output/('proposed-'+owner+'.c')).read_text())
            for at,_,_ in source.PATCHES:
                bad=bytearray(raw);bad[at]^=1
                with self.assertRaises(ValueError):source.checked_payload(bytes(bad),refs)
            with self.assertRaises(ValueError):source.checked_payload(raw,{})
        q=json.loads((self.output/'private-roles-v4.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['guards'],len(q['layouts'])),(60,48,17,3))
        self.assertTrue(q['non_FP_words_and_all_memory_addresses_identical']);self.assertTrue(q['all_observable_FP_expressions_equal'])

    def test_02_guest_aliases_access_prefixes_and_original_math(self):
        q=oracle.qualify(ROOT,self.output)
        self.assertEqual((q['cases'],q['executions'],q['covered_words'],q['access_prefix_triples']),(2520,7560,60,116))
        self.assertTrue(q['all_memory_and_GPR_and_saved_FP_and_access_trace_equal'])
        q=oracle.helpers(ROOT,self.output)
        self.assertEqual((q['cases'],q['executions'],q['original_helper_words']),(388,1164,95))
        self.assertTrue(q['all95_words_executed']);self.assertTrue(q['all256_lookup_angles'])

    def test_03_all_three_original_caller_windows_and_float_ABI(self):
        q=integration.qualify(ROOT,self.output,oracle)
        self.assertEqual((q['original_callers'],q['total_cases'],q['executions']),(3,432,1296))
        self.assertEqual([v['words']for v in q['windows']],[9,9,7]);self.assertTrue(q['original_stack_output_routes'])
        self.assertTrue(q['callee_saved_F20_F26_preserved']);self.assertFalse(q['whole_parents_executed'])

    def test_04_native_aliases_live_providers_fences_and_controls(self):
        q=native.qualify(ROOT,self.output,source.SELECTED,source.HEADERS,oracle)
        self.assertEqual((q['cases_per_profile'],q['effective_controls_each']),(362,9))
        self.assertEqual(q['profiles'],['O0','O2','O3']);self.assertTrue(q['UBSan']);self.assertTrue(q['sequential_output_basis_aliases'])

    def test_05_actual_owner_Make_neighbors_and_literal_whole_image(self):
        for function,owner,_,_ in source.SPECS:
            for before,after in (('before-'+owner+'.o','after-'+owner+'.o'),('before-padded-'+owner+'.o','qualified-'+owner+'.o')):
                self.assertEqual(source.same_functions(self.output/before,self.output/after,(function,)),40)
                self.assertEqual(source.normalized_pools(self.output/before),source.normalized_pools(self.output/after))
            self.assertEqual((self.output/('qualified-'+owner+'.o')).read_bytes(),(self.output/('make-shadow-'+owner+'/src/game/'+owner+'.c.o')).read_bytes())
            self.assertEqual(len(json.loads((self.output/('Make-commands-'+owner+'.json')).read_text())),5)
        q=source.audit(ROOT,self.output,self.installed)
        self.assertEqual((q['functions'],q['other_bodies_fixed'],q['strict_exclusions']),(6052,6051,0));self.assertTrue(q['all_function_addresses_fixed'])
        self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
        before=self.values['conker/build/conker.us.elf'];rom=self.values['conker/conker.us.bin'];actual=(self.output/'private-joint-linked.elf').read_bytes()
        for at in (0x100,len(actual)-1,source.elf_slot_offset(actual,source.SPECS[0][2],240)+24):
            bad=bytearray(actual);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),rom)
        with self.assertRaises(ValueError):source.predict(actual,rom)
        source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
