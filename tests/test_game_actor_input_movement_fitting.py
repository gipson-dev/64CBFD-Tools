"""Complete movement fit: real homes/extent, checked compiler traces and remaining private gap."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_frame as fitting
from tools.tests import test_game_actor_input_movement_recovery as previous
from tools.tests import game_actor_input_movement_oracle as model
from tools.tests import game_actor_input_movement_native as native

source=fitting.source


class MovementFittingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-input-movement-fitting-test'
        fitting.freeze(cls.root,cls.out);cls.body=fitting.fitted_body()
        cls.obj,cls.words,cls.row=source.measure(cls.root,cls.out,fitting.FITTED_NAME,cls.body)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>959I',cls.rom,source.ROM))
        cls.connected={0x150F34A0+i*4:w for i,w in enumerate(struct.unpack_from('>21I',cls.rom,0x120950))}
        cls.harness=previous.MovementRecoveryTests('test_02_all_three_paths_and_numeric_boundaries')
        for name in ('root','out','rom','obj','words','truth','connected'):setattr(cls.harness,name,getattr(cls,name))
        cls.harness.coverage=set();cls.harness.providers=set()

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_full_slot_real_homes_and_bounded_source_controls(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(959,128,744))
        self.assertEqual(self.row['raw_sha'],fitting.FITTED_SHA)
        self.assertEqual((self.row['raw_neighbors'],self.row['padded_neighbors']),(11,11))
        self.assertEqual((self.row['new_guards'],self.row['matching_credit'],self.row['extent_gap']),(0,0,0))
        self.assertEqual((self.words[0],self.words[1],self.words[4],self.words[5]),
                         (0x27BDFF80,0xAFB00028,0xAFBF002C,0xE7B00058))
        expected={
            'selected':(962,112,811),'ordered-homes':(962,112,811),
            'split-values':(962,112,811),'split-ordered-homes':(962,128,804),
            'fitted-layout':(962,128,804),'animation-cast':(960,128,804),
            'animation-implicit':(960,128,804),'heading-wide':(961,128,758),
            'heading-wide-cast':(959,128,744),'heading-wide-implicit':(959,128,744),
            'typed-link-addresses':(960,128,804)}
        rows=[];implicit=None
        for name,body in (*fitting.forms(),*fitting.fitting_forms()):
            obj,words,row=source.measure(self.root,self.out,name,body)
            self.assertEqual(tuple(row[k] for k in ('words','frame','differences')),expected[name],name)
            self.assertEqual(row['raw_neighbors'],11)
            if row['words']>959:self.assertTrue(row['padder_rejected'])
            if name in ('animation-cast','animation-implicit','typed-link-addresses'):
                if implicit is None:implicit=words
                else:self.assertEqual(words,implicit)
            if name=='heading-wide-implicit':self.assertEqual(words,self.words)
            rows.append(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'}))
        self.receipt('forms',rows=rows,complete_C_forms=len(rows),overflow_rejections=9,
            zero_executable_trimming=True,no_frame_address_or_new_word_guards=True)

    def test_02_fingerprint_locked_normal_identical_compiler_traces(self):
        forms=dict(fitting.forms());forms[fitting.FITTED_NAME]=self.body
        expected={
            'selected':(962,112,fitting.RAW_SHA),
            'split-values':(962,112,'b49516a6dd5dbff2f60cabc3766d49bc826f5fa084f0111f809a018bfab97b50'),
            'split-ordered-homes':(962,128,'36e000ec396e357d5a92fce7faac1f70fe0f584da5982b4f956d468b99004de7'),
            fitting.FITTED_NAME:(959,128,fitting.FITTED_SHA)}
        rows=[]
        for name,shape in expected.items():
            record=fitting.trace(self.root,self.out/'traces',name,forms[name],shape)
            self.assertTrue(record['code_unchanged']);self.assertTrue(record['whole_owner_target_identical'])
            self.assertEqual(record['layout']['frame'],shape[1])
            rows.append(dict(name=name,layout=record['layout']))
        self.receipt('traces',completed_owned_traces=len(rows),rows=rows,
            normal_code_functions_relocations_and_pools_identical=True)

    def test_03_effective_wire_frame_lifecycle_and_emission_controls(self):
        work=self.out/'traces'/fitting.FITTED_NAME
        record=json.loads((work/'movement-summary.json').read_text())
        words=list(struct.unpack_from('>959I',source.projection.sections(work/'baseline-linked.elf')['.text'][1]))
        expected=fitting.check_layout(record,words,fitting.FITTED_NAME);count=0
        for phase in ('frontend','optimizer'):
            bad=copy.deepcopy(record)
            next(r for r in bad['phases'][phase]['definitions'] if r['storage']=='M')['length']+=4
            with self.assertRaises(ValueError):fitting.check_layout(bad,words,fitting.FITTED_NAME)
            count+=1
        for name,rows in record['phases']['frontend']['markers'].items():
            stores=[i for i,r in enumerate(rows) if r['name']=='str' and r['storage']=='M']
            if not stores:continue
            bad=copy.deepcopy(record);bad['phases']['frontend']['markers'][name][stores[0]]['offset']-=4
            if name in expected['caller_relative']:
                with self.assertRaises(ValueError):fitting.check_layout(bad,words,fitting.FITTED_NAME)
                count+=1
                for key,value in (('length',8),('dtype','X')):
                    bad=copy.deepcopy(record);bad['phases']['frontend']['markers'][name][stores[0]][key]=value
                    with self.assertRaises(ValueError):fitting.check_layout(bad,words,fitting.FITTED_NAME)
                    count+=1
        for key in ('code_unchanged','whole_owner_target_identical'):
            bad=copy.deepcopy(record);bad[key]=False
            with self.assertRaises(ValueError):fitting.check_layout(bad,words,fitting.FITTED_NAME)
            count+=1
        for i in range(4):
            for key in ('frame','host_pc'):
                bad=copy.deepcopy(record);bad['events'][i][key]^=4
                with self.assertRaises(ValueError):fitting.check_layout(bad,words,fitting.FITTED_NAME)
                count+=1
        for key,value in (('locals',88),('saved',24),('outgoing',40),('temporary',4),('temp_base',4),('pool',[{}])):
            bad=copy.deepcopy(record);bad['events'][-1][key]=value
            with self.assertRaises(ValueError):fitting.check_layout(bad,words,fitting.FITTED_NAME)
            count+=1
        for offset in (0,5):
            bad=list(words);bad[offset]^=4
            with self.assertRaises(ValueError):fitting.check_layout(record,bad,fitting.FITTED_NAME)
            count+=1
        call=words.index(0x0D4169BE)
        for op in (43,57):
            index=next(i for i in range(call-5,call+2) if words[i]>>26==op)
            bad=list(words);bad[index]^=4
            with self.assertRaises(ValueError):fitting.check_layout(record,bad,fitting.FITTED_NAME)
            count+=1
        log=(work/'debugger.txt').read_text()
        for prefix in ('FRAME_INPUT ','TRACE_EXIT ','FRAME_TRACE '):
            bad='\n'.join(line for line in log.splitlines() if not line.startswith(prefix))
            with self.assertRaises(ValueError):fitting.shared.validate_observations(work,bad)
            count+=1
        self.receipt('trace-controls',effective_controls=count,raw_storage_and_actual_machine_homes_checked=True)

    def test_04_complete_public_packets_all_widths_mutations_and_FP_edges(self):
        for name in ('test_02_all_three_paths_and_numeric_boundaries','test_03_every_signed_stick_byte_and_cooldown',
                'test_04_record_filters_nearest_ties_and_mutating_providers','test_10_modeled_float_edges_not_hardware_FCSR'):
            getattr(self.harness,name)()
        self.assertEqual(len(self.harness.coverage&set(range(source.ENTRY,source.ENTRY+source.SIZE,4))),947)
        self.receipt('complete-public',core_cases=2496,additional_FP_cases=20,actual_curve_connected=True,
            raw_retail_words_exercised=947,remaining_original_duplicate_words=12,padding_not_masked=True,
            no_hardware_or_general_FCSR_claim=True)

    def test_05_two_text_rebases_and_native32_complete_fields(self):
        self.harness.test_05_two_independent_text_rebases()
        specs=[*list(previous.core_specs())[::7],*list(previous.mutation_specs())[::5],*previous.targeted_specs()]
        with patch.object(source,'SELECTED',self.body):row=native.qualify(self.root,self.out,self.rom,specs)
        self.assertEqual(row['cases_per_profile'],130);self.assertEqual(row['effective_controls'],8)

    def test_06_initial_full_private_fault_boundaries_restored_not_full_match(self):
        comparisons=0;failures=[]
        for phase,pattern,gate in itertools.product((0,8),(0,1),(0,1)):
            memory,case=model.fixture(self.rom,held=101,phase=phase,pattern=pattern,gate=gate)
            for cut in range(11):
                machines=[model.Oracle(w,memory,case,self.connected) for w in (self.truth,self.words)]
                for machine in machines:
                    machine.access_fault=cut
                    with self.assertRaises(model.point.faults.AccessBoundary):machine.run()
                equal=model.point.state(machines[0])==model.point.state(machines[1])
                self.assertEqual(equal,cut<10,(phase,pattern,gate,cut))
                if equal:comparisons+=1
                else:
                    self.assertEqual(machines[0].memory,machines[1].memory)
                    self.assertEqual(machines[0].f,machines[1].f)
                    self.assertEqual(machines[0].current_pc,0x150F3544)
                    differing=[i for i,(a,b) in enumerate(zip(machines[0].r,machines[1].r)) if a!=b]
                    self.assertEqual(differing,[3,10]);failures.append(dict(phase=phase,pattern=pattern,gate=gate))
        self.receipt('private',equal_complete_prefix_states=comparisons,first_remaining_cut=10,
            effective_rejections=len(failures),different_GPRs=[3,10],same_memory_FPR_and_PC=True,
            PC='0x150F3544',full_private_or_fault_matching_not_claimed=True)

    def test_07_entire_production_and_all_prior_checkpoints_unchanged(self):
        fitting.freeze(self.root,self.out)
        for key,path in fitting.PATHS.items():
            self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+key)).read_bytes())
        self.harness.test_07_production_baseline_and_callback_preserved()
        self.receipt('protected',entries=len(fitting.PATHS),distinct_paths=len(set(fitting.PATHS.values())),
            ELF_sha=hashlib.sha256((self.root/'conker/build/conker.us.elf').read_bytes()).hexdigest(),
            no_source_guard_profile_conversion_or_checkpoint_changes=True,installed=False,matching_credit=0)


    def test_08_global_controller_screen_and_guest_alias_boundaries(self):
        _,words,row=source.measure(self.root,self.out,'global-controller',fitting.global_controller_body())
        self.assertEqual((row['words'],row['frame'],row['differences']),(959,128,763))
        self.assertEqual(row['raw_sha'],'dbaf70063f8d6ce82a2b33781acd1722592f219030eb4cbb491ba451612fb053')
        count=0
        for alias,gate,mode in itertools.product((0x800CC284,0x800CC288,model.SLOT),(0,1),(0,1)):
            memory,case=model.fixture(self.rom,gate=gate,mode=mode,pattern=1,pressed=0x8000)
            model.put(memory,model.SLOT,alias)
            memory.update({0x800C0080+i:0xA5 for i in range(32)})
            expected=model.reference(memory,case)
            for image in (self.truth,self.words,words):
                actual=model.Oracle(image,memory,case,self.connected).run()
                self.assertEqual(model.public(actual.memory),model.public(expected[0]))
                self.assertEqual(actual.calls,expected[1]);self.assertEqual(actual.observations,expected[2])
            count+=1
        memory,case=model.fixture(self.rom,held=101,pattern=1)
        pair=[model.Oracle(image,memory,case,self.connected) for image in (self.truth,words)]
        for machine in pair:
            machine.access_fault=10
            with self.assertRaises(model.point.faults.AccessBoundary):machine.run()
        self.assertNotEqual(model.point.state(pair[0]),model.point.state(pair[1]))
        self.receipt('controller-control',complete_guest_alias_cases=count,ordinary_semantics_preserved=True,
            words=959,frame=128,overlapping_differences=763,first_cut10_still_rejected=True,
            adopted=False,no_native_pointer_alias_claim=True)


if __name__=='__main__':unittest.main()
