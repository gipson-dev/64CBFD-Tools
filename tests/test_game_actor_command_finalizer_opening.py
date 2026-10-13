"""Qualify the full opening fit, preserving caller homes and live stack slots."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_opening as opening
from tools.tests import test_game_actor_command_finalizer_roles as roles
from tools.tests import test_game_actor_command_finalizer_recovery as recovery
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout


class GameActorCommandFinalizerOpeningTests(unittest.TestCase):
    run_native=roles.GameActorCommandFinalizerRolesTests.run_native
    native_source=roles.GameActorCommandFinalizerRolesTests.native_source
    compare=roles.GameActorCommandFinalizerRolesTests.compare
    test_02_all_types_channels_field_boundaries_and_call_mutations=(
        roles.GameActorCommandFinalizerRolesTests.test_02_all_types_channels_field_boundaries_and_call_mutations)
    test_03_full_word_selectors_and_output_aliases=(
        roles.GameActorCommandFinalizerRolesTests.test_03_full_word_selectors_and_output_aliases)
    test_04_live_saves_and_private_provider_mutation_controls=(
        roles.GameActorCommandFinalizerRolesTests.test_04_live_saves_and_private_provider_mutation_controls)
    test_07_copied_owner_all_neighbors_pools_and_both_padders=(
        roles.GameActorCommandFinalizerRolesTests.test_07_copied_owner_all_neighbors_pools_and_both_padders)
    test_10_actual_parent_calls_complete_finalizer=(
        roles.GameActorCommandFinalizerRolesTests.test_10_actual_parent_calls_complete_finalizer)
    test_11_incoming_home_contract_retained=(
        roles.GameActorCommandFinalizerRolesTests.test_11_incoming_home_contract_retained)

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-command-finalizer-opening-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=recovery.screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            layout='conker/retail_layout.us.txt',makefile='conker/Makefile',
            caller='conker/src/game/generated_61490.c',rodata='conker/asm/data/23C630.rodata.s')
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads(manifest.read_text())
        assert cls.baseline['source']=='f4a7922c5317deaaec503865d0e0af59bfb29b6d31d1377c31b67b24e0d77024'
        assert cls.baseline['elf']=='6b3a795a43992b6ac9d8ffb736c8d80360a3416936d5ae7708db7c54aa3ecb86'
        cls.before=(cls.out/'before-elf').read_bytes()
        cls.owner_before=(cls.out/'before-source').read_text()
        cls.owner_after=opening.recovered_owner(cls.owner_before)
        cls.meta,cls.words=opening.flow.roles.fitting.compile_candidate(cls.root,cls.out,'selected',opening.SELECTED)
        _,cls.banked_words=opening.flow.roles.fitting.compile_candidate(cls.root,cls.out,'banked',opening.BASE)
        _,cls.old_words=opening.flow.roles.fitting.compile_candidate(cls.root,cls.out,'old-slot-control',opening.flow.roles.BASE)
        cls.retail=list(struct.unpack_from('>405I',(cls.root/'conker/conker.us.bin').read_bytes(),recovery.screen.ROM))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_original_extent_frame_selector_schedule_and_no_guards(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(405,72,299,0,''))
        self.assertEqual(self.words[:5],self.retail[:5])
        self.assertEqual(self.words[-4:],self.retail[-4:])
        self.assertEqual(self.words[9],self.retail[9])
        self.assertEqual(self.words[8]>>26,5)
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertFalse([r for r in csv.DictReader(stream) if r['function']==recovery.screen.FUNCTION])
        observations=[opening.opening(w,self.retail) for w in (self.banked_words,self.words)]
        self.assertEqual([r['retail_selector_load_indices'] for r in observations],[[27],[9]])
        self.assertEqual([r['cut5_GPRs'] for r in observations],[[1,3,6,7,9,10],[3,7]])
        for result in observations:
            self.assertEqual(result['equal_cuts'],[True]*5+[False])
            self.assertTrue(all(result[k] for k in ('memory_equal','events_equal','FPRs_equal','RA_equal')))
        self.receipt('shape',words=405,frame=72,differences=299,matching_credit=0,
            opening=observations,all_private_fault_equivalence=False)

    def test_05_native32_actual_source_and_fresh_effective_negatives(self):
        with patch.object(roles.roles,'SELECTED',opening.SELECTED):
            roles.GameActorCommandFinalizerRolesTests.test_05_native32_actual_source_and_fresh_effective_negatives(self)

    def test_06_owned_frame_and_temporary_records(self):
        results=[]
        for name,body in (('banked',opening.BASE),('selected',opening.SELECTED)):
            record=opening.flow.roles.fitting.trace(self.root,self.out,name,body)
            self.assertTrue(record['code_unchanged'])
            events=[e for e in record['events'] if e['event']=='frame-write']
            self.assertEqual([e['frame'] for e in events],[8,24,72])
            self.assertEqual((events[-1]['locals'],events[-1]['saved'],events[-1]['outgoing']),(48,8,16))
            definitions=[r['length'] for r in record['records']['optimizer'] if r['name']=='def' and r['storage']=='M']
            offsets=sorted({r['offset']-0x100000000 if r['offset']>=0x80000000 else r['offset']
                for r in record['records']['optimizer'] if r['storage']=='M' and r.get('offset') is not None})
            self.assertEqual(definitions,[48])
            self.assertEqual(offsets,[-48,-40,-36,-28,-24,-20])
            results.append(dict(name=name,M_definition=definitions[0],M_offsets=offsets,inputs=record['inputs']))
        self.receipt('allocation',frames_equal=True,objects_unchanged=True,records=results,
            all_six_role_offsets_preserved=True)

    def test_08_literal_image_and_all_protected_inputs(self):
        current=(self.root/self.paths['elf']).read_bytes()
        source=(self.root/self.paths['source']).read_text()
        expected=bytearray(self.before)
        installed=source==self.owner_after
        if installed:
            offset=elf_slot_offset(self.before,recovery.screen.ENTRY,1620)
            self.assertEqual(offset,elf_slot_offset(current,recovery.screen.ENTRY,1620))
            expected[offset:offset+1620]=struct.pack('>405I',*self.words)
        else:
            self.assertEqual(source,self.owner_before)
        self.assertEqual(current,bytes(expected))
        for name in set(self.paths)-{'source','elf'}:
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes(),name)
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('linked-audit',installed=installed,guard_rows_added=0,matching_credit=0,
            changed_bytes=sum(a!=b for a,b in zip(self.before,current)),data=data)

    def test_09_independent_original_links_and_carry_rebases(self):
        original_compile=recovery.screen.compile_candidate
        def compile_selected(root,out,name,body=None):
            return original_compile(root,out,name,opening.SELECTED if body is None else body)
        with patch.object(recovery.screen,'compile_candidate',compile_selected):
            recovery.GameActorCommandFinalizerRecoveryTests.test_08_independent_original_links_and_carry_sensitive_rebases(self)


    def test_12_all_sampled_fired_access_cuts_keep_the_open_boundary(self):
        domains=[(kind,pattern,1,2,phase) for kind,pattern,phase in
            itertools.product((0,0x42,0x69,0x70,0x7C,0x87),(0,1,3),(0,8))]
        domains += [(kind,0,first,second,phase) for kind,first,second,phase in
            itertools.product((0,0x70),(1,255),(2,255),(0,8))]
        cases=[]
        pairs=equal=0
        for kind,pattern,first,second,phase in domains:
            memory,args=recovery.fixture(kind,pattern,first,second)
            complete=[opening.faults.InstructionOracle(w,memory,args,phase,0xFFFFFFFF).run()
                for w in (self.retail,self.words)]
            self.assertEqual(complete[0].accesses,complete[1].accesses)
            first_difference=None
            for cut in range(complete[0].accesses):
                pair=[]
                for words in (self.retail,self.words):
                    model=opening.faults.InstructionOracle(words,memory,args,phase,0xFFFFFFFF)
                    model.fault=cut
                    with self.assertRaises(recovery.stream.AccessFault):model.run()
                    self.assertEqual(model.accesses,cut)
                    self.assertIn(model.dispatched_word>>26,(32,33,35,36,37,40,41,43,49,57))
                    pair.append(model)
                same=opening.faults.state(pair[0])==opening.faults.state(pair[1])
                equal+=same
                pairs+=1
                if not same and first_difference is None:
                    first_difference=cut
                    self.assertEqual([i for i in range(32) if pair[0].r[i]!=pair[1].r[i]],[3,7])
                    self.assertEqual((pair[0].memory,pair[0].events,pair[0].f,pair[0].r[31]),
                        (pair[1].memory,pair[1].events,pair[1].f,pair[1].r[31]))
                    self.assertEqual(pair[0].dispatched_word,pair[1].dispatched_word)
            self.assertEqual(first_difference,5)
            cases.append(dict(kind=kind,pattern=pattern,selectors=[first,second],phase=phase,
                accesses=complete[0].accesses,first_difference=first_difference))
        self.assertEqual((len(cases),pairs),(52,2938))
        self.receipt('fault-boundary',cases=cases,fired_pairs=pairs,equal_states=equal,
            first_cut_GPRs=[3,7],whole_private_fault_match=False,hardware_PC_BD_FCSR_not_claimed=True)


    def test_13_non_selector_fault_is_not_mislabeled_as_a_selector_load(self):
        body=dict(opening.candidates())['q0-w0-nvalue']
        _,words=opening.flow.roles.fitting.compile_candidate(self.root,self.out,'observation-control',body)
        observed=opening.opening(words,self.retail)
        self.assertEqual(observed['cut5_words'],['8FAE0050','C42A7D44'])
        self.assertEqual(observed['cut5_word_indices'],[43])
        self.assertNotEqual(observed['retail_selector_load_indices'],observed['cut5_word_indices'])
        self.assertTrue(all(words[i]==0x8FAE0050 for i in observed['retail_selector_load_indices']))
        self.receipt('observation-label',non_selector_control_effective=True,observation=observed)


if __name__=='__main__':
    unittest.main()
