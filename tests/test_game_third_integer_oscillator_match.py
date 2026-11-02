"""Qualified oscillator pair: full-width clocks, live providers and original dispatcher."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_third_integer_oscillator_match as source
from tools.tests import game_third_integer_oscillator_oracle as oracle
from tools.tests import game_third_integer_oscillator_integration as integration
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class ThirdIntegerOscillatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output)
        cls.installed=os.environ.get('CBFD_THIRD_OSCILLATOR_INSTALLED')=='1'
        cls.values=source.check_inputs(ROOT,cls.output,cls.installed)

    def test_01_sequenced_payloads_guards_and_independent_links(self):
        for i,(function,owner,entry,rom)in enumerate(source.SPECS):
            obj,diag=source.compile_owner(ROOT,self.output,source.HEADERS+source.SELECTED.replace(source.SPECS[0][0],function),'public-fresh-'+function)
            self.assertFalse(diag);raw,refs=source.checked_payload(*source.payload(obj,function))
            original,bindings=source.payload(self.output/('original-'+function+'.o'),function)
            self.assertEqual(source.normalized(raw,refs),(original,bindings));self.assertEqual(struct.unpack_from('>I',raw)[0],0x27BDFFD8)
            before=self.values['conker/src/game/'+owner+'.c'].decode()
            self.assertEqual(source.recovered_owner(before,i),(self.output/('proposed-'+owner+'.c')).read_text())
            for at,_,_ in source.PATCHES:
                bad=bytearray(raw);bad[at]^=1
                with self.assertRaises(ValueError):source.checked_payload(bytes(bad),refs)
            with self.assertRaises(ValueError):source.checked_payload(raw,{})
        q=json.loads((self.output/'layout-v1.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['guards'],len(q['layouts'])),(60,40,6,3))
        self.assertTrue(q['all_words_and_bindings_equal_qualified_family'])

    def test_02_guest_aliases_private_lifetimes_faults_and_real_RNG(self):
        q=oracle.qualify(ROOT,self.output)
        self.assertEqual((q['cases'],q['executions'],q['covered_words'],q['access_prefix_triples'],q['zero_divisor_preinstruction_triples']),(5214,15642,59,93,6))
        self.assertTrue(q['private_stack_projection_and_guest_aliases'])
        q=oracle.helpers(ROOT,self.output)
        self.assertEqual((q['cases'],q['executions'],q['original_integer_words'],q['original_float_words']),(216,648,18,25))
        self.assertTrue(q['all43_helper_words_executed']);self.assertTrue(q['retained_helpers_equal_original'])

    def test_03_original_callback_dispatch_cleanup_and_return_gate(self):
        q=integration.qualify(ROOT,self.output,oracle)
        self.assertEqual((q['cases'],q['executions'],q['parent_words'],q['visited_parent_words']),(1536,4608,188,89))
        self.assertEqual(q['callback_slots'],[9]);self.assertTrue(q['all17_cleanup_words_executed'])
        self.assertEqual(q['wrong_target_stub_return_rejected'],2);self.assertFalse(q['retained_parent_parity_claimed'])

    def test_04_native_full_width_state_live_providers_fences_and_controls(self):
        q=oracle.native_reuse(ROOT,self.output)
        self.assertFalse(q['fresh_native_execution']);self.assertTrue(q['explicit_fingerprinted_reuse'])
        self.assertEqual(q['effective_controls_each'],9);self.assertEqual(q['cases_each_target_profile'],818)
        self.assertTrue(q['UBSan']);self.assertTrue(q['only_C_function_identifier_changed'])

    def test_05_actual_owner_Make_neighbors_and_literal_whole_image(self):
        for function,owner,_,_ in source.SPECS:
            for before,after in (('before-'+owner+'.o','after-'+owner+'.o'),('before-padded-'+owner+'.o','qualified-'+owner+'.o')):
                self.assertEqual(source.same_functions(self.output/before,self.output/after,(function,)),9)
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
