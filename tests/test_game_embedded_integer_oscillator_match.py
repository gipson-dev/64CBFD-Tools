"""Qualified oscillator pair: full-width clocks, live providers and original dispatcher."""
from pathlib import Path
import json,os,struct,unittest
from tools.experiments import game_embedded_integer_oscillator_match as source
from tools.tests import game_embedded_integer_oscillator_oracle as oracle
from tools.tests import game_embedded_integer_oscillator_native as native
from tools.tests import game_embedded_integer_oscillator_integration as integration
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))

class EmbeddedIntegerOscillatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD;source.verify_prepared(cls.output)
        cls.installed=os.environ.get('CBFD_OSCILLATOR_INSTALLED')=='1'
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
        q=json.loads((self.output/'private-sequenced-layout-v15.json').read_text())
        self.assertEqual([(v['words'],v['frame'],v['guards'],v['layouts'])for v in q['targets']],[(60,40,6,3)]*2)
        self.assertTrue(all(v['frame_address_not_escaped']for v in q['targets']))

    def test_02_guest_aliases_private_lifetimes_faults_and_real_RNG(self):
        q=oracle.qualify(ROOT,self.output)
        self.assertEqual((q['cases'],q['executions'],q['covered_words_each'],q['access_prefix_triples'],q['zero_divisor_preinstruction_triples']),(10428,31284,59,186,12))
        self.assertEqual(q['excluded_float_cast_cases'],0);self.assertTrue(q['full_modeled_state_after_private_byte_home_mapping'])
        q=oracle.helpers(ROOT,self.output)
        self.assertEqual((q['cases'],q['executions'],q['integer_words'],q['float_words']),(432,1296,18,25))
        self.assertTrue(q['all43_helper_words_executed']);self.assertTrue(q['retained_helpers_equal_original'])

    def test_03_original_callback_dispatch_cleanup_and_return_gate(self):
        q=integration.qualify(ROOT,self.output,oracle)
        self.assertEqual((q['cases'],q['executions'],q['parent_words'],q['visited_parent_words']),(3072,9216,188,89))
        self.assertEqual(q['callback_slots'],[7,8]);self.assertTrue(q['all34_cleanup_words_executed'])
        self.assertEqual(q['wrong_target_stub_return_rejected'],4);self.assertFalse(q['retained_parent_parity_claimed'])

    def test_04_native_full_width_state_live_providers_fences_and_controls(self):
        q=native.qualify(ROOT,self.output,source.SELECTED,source.HEADERS,oracle)
        self.assertEqual(q['effective_controls_each'],9);self.assertEqual(q['targets'],2)
        self.assertEqual(q['profiles'],['O0','O2','O3']);self.assertTrue(q['UBSan']);self.assertTrue(q['all_untouched_bytes_and_fences'])

    def test_05_actual_owner_Make_neighbors_and_literal_whole_image(self):
        for function,owner,_,_ in source.SPECS:
            for before,after in (('before-'+owner+'.o','after-'+owner+'.o'),('before-padded-'+owner+'.o','qualified-'+owner+'.o')):
                self.assertEqual(source.same_functions(self.output/before,self.output/after,(function,)),9 if owner=='generated_F3270'else 40)
                self.assertEqual(source.normalized_pools(self.output/before),source.normalized_pools(self.output/after))
            self.assertEqual((self.output/('qualified-'+owner+'.o')).read_bytes(),(self.output/('make-shadow-'+owner+'/src/game/'+owner+'.c.o')).read_bytes())
            self.assertEqual(len(json.loads((self.output/('Make-commands-'+owner+'.json')).read_text())),5)
        q=source.audit(ROOT,self.output,self.installed)
        self.assertEqual((q['functions'],q['other_bodies_fixed'],q['strict_exclusions']),(6052,6050,0));self.assertTrue(q['all_function_addresses_fixed'])
        self.assertEqual(source.expected_map(self.output),self.values['conker/build/conker.us.map'])
        before=self.values['conker/build/conker.us.elf'];rom=self.values['conker/conker.us.bin'];actual=(self.output/'private-joint-linked.elf').read_bytes()
        for at in (0x100,len(actual)-1,source.elf_slot_offset(actual,source.SPECS[0][2],240)+24):
            bad=bytearray(actual);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),rom)
        with self.assertRaises(ValueError):source.predict(actual,rom)
        source.verify_prepared(self.output);source.check_inputs(ROOT,self.output,self.installed)
