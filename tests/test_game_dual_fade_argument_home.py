"""Real parameter home, unchanged public semantics and owned allocation witnesses."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_dual_fade_argument_home as source
from tools.tests import test_game_dual_buffer_fade as prior
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_point_transform_match import put,read


class ArgumentHomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>69I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-fade',
            (cls.out/'before-tile_original').read_text(),source.FUNCTION)

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def run_prior(self,name):
        with patch.object(prior,'source',source):getattr(prior.DualBufferFadeTests,name)(self)

    @classmethod
    @lru_cache(None)
    def captures(cls):
        return {label:source.capture(cls.root,cls.out,label,body) for label,body in
            (('normal',source.previous.SELECTED),('branch',source.BRANCH),('home',source.SELECTED))}

    def test_01_real_argument_home_and_still_unresolved_saved_role(self):
        self.assertEqual((self.row['words'],self.row['retail_words'],self.row['frame']),(68,69,48))
        self.assertEqual((self.row['record_home'],self.row['previous_weight_home'],self.row['state_home']),(48,36,28))
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],24);self.assertFalse(self.row['saves_s0'])
        self.assertNotIn(0xAFB00018,self.images[0]);self.assertEqual(self.images[0],self.images[1])
        for words in (self.images[0],self.truth):
            with self.assertRaisesRegex(ValueError,'unresolved|unqualified'):source.require_installable(words)
        raw,bindings=source.parts(self.obj)
        for i in range(68):
            wrong=bytearray(raw);wrong[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[(bindings[at][0][0],'D_800BE9E8')]
            with self.assertRaises(ValueError):source.checked_parts(raw,wrong)
        self.receipt('emission',**self.row,raw_word_controls=68,binding_controls=6,no_artificial_objects_or_guards=True)

    def test_02_full_public_corpus_aliases_and_mutation_boundaries(self):
        self.run_prior('test_02_ordered_public_reference_aliases_and_callback_mutations')

    def test_03_complete_native_body_caller_and_negative_controls(self):
        self.run_prior('test_05_native_complete_body_separate_typed_caller_and_controls')

    def test_04_independent_original_raw_padded_rebases(self):
        self.run_prior('test_04_independent_original_raw_padded_relocations')

    def test_05_full_actual_dispatcher_success_contract(self):
        self.run_prior('test_08_full_actual_callback_caller_uses_success_return')

    def test_06_actual_wrapper_closes_record_word_only_and_adversarial_reload(self):
        connected={}
        for entry,words in ((prior.COLOR,22),(prior.TEXT,42)):
            at=entry-0x15000000+0x2D4B0
            connected.update({entry+i*4:w for i,w in enumerate(struct.unpack_from('>%dI'%words,self.rom,at))})
        differences=[]
        for byte,phase in ((0,0),(1,0),(8,0),(33,0),(127,0),(128,0),(255,0),(8,8)):
            memory,args=prior.fixture(byte)
            machines=[prior.Oracle(words,memory,args,phase=phase,connected=connected).run() for words in (self.truth,*self.images)]
            for m in machines:self.assertEqual(m.calls,machines[0].calls);self.assertEqual(m.r[2],1)
            self.assertEqual(machines[1].payloads,machines[2].payloads)
            self.assertEqual(len(machines[0].payloads),len(machines[1].payloads))
            changed=[]
            for call,(a,b) in enumerate(zip(machines[0].payloads,machines[1].payloads)):
                self.assertEqual((a[8],b[8]),(prior.RECORD,prior.RECORD))
                changed.extend((call,i,x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y)
            self.assertTrue(changed,'Other private ABI gaps must remain visible')
            self.assertNotIn(8,[i for _,i,_,_ in changed]);differences.append(dict(countdown=byte,phase=phase,remaining_words=changed))
        before=(self.out/'before-tile_owner').read_text()
        normal,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,source.previous.SELECTED),'normal-control')
        self.assertFalse(diag);source.previous.checked_parts(*source.parts(normal))
        data,fs=source.build.link_owner(self.root,self.out,normal,source.OWNER);f=fs[source.FUNCTION]
        normal_words=list(struct.unpack_from('>65I',data,f['value']))
        alternate=0x40000
        class MutatingOracle(prior.Oracle):
            def hook(self,target):
                super().hook(target)
                if target==prior.COLOR and self.ordinal[prior.COLOR]==1:
                    self.put(self.r[29]+48,alternate,4)
        for phase in (0,8):
            memory,args=prior.fixture(8)
            for offset in range(0x460):memory[alternate+offset]=memory[prior.RECORD+offset]
            put(memory,alternate+0x3D,1,1);put(memory,alternate+0x40,0x44550000);put(memory,alternate+0x44,0x44550001)
            machines=[MutatingOracle(words,memory,args,phase=phase).run() for words in (self.truth,*self.images,normal_words)]
            self.assertEqual(machines[0].calls,machines[1].calls);self.assertEqual(machines[1].calls,machines[2].calls)
            self.assertNotEqual(machines[0].calls,machines[3].calls)
            self.assertEqual([c[1][3] for c in machines[0].calls if c[0]==prior.TEXT],[0x44550001,0x44550000])
        self.receipt('argument-home',actual_color_words=22,actual_text_words=42,actual_wrapper_cases=8,
            record_payload_word8_closed=True,other_private_differences=differences,
            positively_fired_adversarial_home_mutations=2,not_real_helper_mutation_or_complete_private_parity=True)

    def test_07_every_live_and_frozen_input_control(self):
        self.run_prior('test_06_every_protected_live_and_frozen_input')

    def test_08_owned_frontend_optimizer_ugen_captures_and_hash_controls(self):
        captures=self.captures();rows={label:summary for label,(_,summary) in captures.items()}
        self.assertEqual({label:row['baseline']['words'] for label,row in rows.items()},{'normal':65,'branch':64,'home':68})
        self.assertEqual({label:row['baseline']['target_sha256'] for label,row in rows.items()},
            {'normal':source.previous.RAW_SHA,'branch':'9bfe170e80d953dc7fcc19462aa813d48b5dc83f8576f4d6935ee23fe56b723a','home':source.RAW_SHA})
        self.assertEqual({label:row['cfe_formal_lda'] for label,row in rows.items()},{'normal':0,'branch':0,'home':5})
        self.assertEqual({label:row['optimized_formal_loads'] for label,row in rows.items()},{'normal':0,'branch':0,'home':5})
        self.assertEqual({label:row['optimized_automatic_bytes'] for label,row in rows.items()},{'normal':[12],'branch':[12],'home':[20]})
        original=Path.read_bytes;controls=0
        for label,(record,row) in captures.items():
            self.assertTrue(row['code_unchanged']);self.assertEqual(row['frontend_exits'],[0]);self.assertEqual(row['optimizer_exits'],[0])
            work=self.out/('capture-'+label);log=(work/'debugger.txt').read_text()
            for name in ('frontend.ucode','optimizer.ucode','ucode-table.json','ucode-types.json'):
                target=work/name;wrong=bytearray(target.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else original(path)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaises(ValueError):source.front.validate_capture(self.root,work,log,record['complete'])
                self.assertTrue(source.front.validate_capture(self.root,work,log,record['complete'])['code_unchanged']);controls+=1
        self.receipt('compiler-homes',captures=rows,positively_fired_capture_hash_controls=controls,
            complete_driver_objects_and_pools_unchanged=True,not_original_source_qualifier_recovery=True)

    def test_09_procedure_scoped_allocation_constraints_not_printed_costs(self):
        captures=self.captures();results={}
        for label,body in (('normal',source.previous.SELECTED),('home',source.SELECTED)):
            results[label]=source.allocation(self.root,self.out,label,body,captures[label][1]['procedure'])
        normal,home=results['normal']['final'],results['home']['final']
        self.assertEqual([(r['variable']['storage'],r['variable']['offset']) for r in normal],[('P',0),('M',-12)])
        self.assertEqual((normal[0]['variable']['virtual_register'],normal[0]['constraint']['color']),(True,14))
        self.assertEqual((home[0]['variable']['virtual_register'],home[0]['constraint']['color']),(False,-1))
        self.assertEqual((normal[1]['constraint']['color'],home[1]['constraint']['color']),(8,8))
        self.assertIn(14,normal[1]['constraint']['forbidden']);self.assertNotIn(14,home[1]['constraint']['forbidden'])
        poison='>>>active<<<{373|0} 0 14\nforbidden: [1]\n:::interfere with::: 0\n'
        for label in results:
            full=(self.out/('allocation-'+label)/'uoptlist').read_text();scoped=source.allocation_procedure(full)
            self.assertEqual(source.allocation_procedure(poison+full+poison),scoped)
            with self.assertRaises(ValueError):source.allocation_procedure(full+scoped)
            with self.assertRaises(ValueError):source.allocation_procedure(full.replace(' IN REEMISSION OF '+source.FUNCTION,' IN REEMISSION OF unknown'))
            self.assertTrue(results[label]['code_unchanged'])
        self.receipt('allocation',final={label:r['final'] for label,r in results.items()},
            scoped_boundary_controls=6,owned_mode5_drivers=2,real_numeric_costs_or_timings_not_interpreted=True)

    def test_10_negative_source_forms_do_not_bypass_lifetime_gates(self):
        rows=source.profiles(self.root,self.out)
        self.assertEqual({r['label']:(r['words'],r['frame'],r['saves_s0']) for r in rows},
            {'array-parameter':(65,48,True),'home-register':(68,48,False),'home-half':(69,48,False),'home-branch':(67,48,False)})
        self.assertEqual(rows[0]['sha256'],source.previous.RAW_SHA);self.assertEqual(rows[1]['sha256'],source.RAW_SHA)
        for row in rows:self.assertFalse(row['installable'])
        self.receipt('source-controls',forms=rows,retail_extent_alone_rejected=True)


if __name__=='__main__':unittest.main()
