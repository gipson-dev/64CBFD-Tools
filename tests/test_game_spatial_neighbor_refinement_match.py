"""Spatial-refinement word provenance, private prefixes, actual callers and image gates."""
from collections import Counter
from copy import deepcopy
from dataclasses import replace
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_spatial_neighbor_refinement_fitting as source
from tools.experiments import game_spatial_neighbor_refinement_layout as layout
from tools.experiments import game_spatial_neighbor_refinement_integration as integration
from tools.experiments.game_route_projection_layout_normalizer import relocate
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_spatial_neighbor_refinement_oracle as oracle
from tools.tests import test_game_spatial_neighbor_refinement_recovery as recovery
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly


def state(model):
    return (model.r,model.f,model.lo,model.condition,model.memory,model.events,model.stores,
        model.reads,model.requested,model.visits,model.calls,model.raw_calls,model.accesses)


class SpatialNeighborRefinementMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.cases=list(oracle.cases())
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out)
        cls.raw,cls.bindings=source.payload(cls.obj);cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.anchors={name:int(name[2:],16) if name.startswith('D_') else int(name[5:],16)
            for entries in cls.moved.values() for _,name in entries}
        cls.normalized_words=relocate(cls.normalized,cls.moved,cls.anchors)
        cls.rom=cls.values['conker/conker.us.bin'];cls.retail=list(struct.unpack_from('>179I',cls.rom,source.ROM))

    def receipt(self,name,**row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_literal_words_origins_bindings_and_stale_controls(self):
        self.assertEqual(self.normalized_words,self.retail)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(176,120,139))
        self.assertFalse(self.row['diagnostics']);controls=0
        for at in range(0,704,4):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Unknown refinement'):layout.normalize(bytes(bad),self.bindings)
            controls+=1
        for at in self.bindings:
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_26',source.FUNCTION)]
            with self.assertRaisesRegex(ValueError,'Unknown refinement'):layout.normalize(self.raw,bad)
            controls+=1
        self.assertEqual({x for x in layout.origins() if isinstance(x,int)},set(range(0,704,4))-set(layout.OMITTED))
        self.assertEqual(Counter(x for entries in self.bindings.values() for x in entries),
            Counter(x for entries in self.moved.values() for x in entries))
        self.receipt('recipe',raw_source_controls=controls,source_words_retained=174,omitted_dead_words=2,
            inserted_minimum_copies_NEG_SLTI_and_hazard_words=5,all179_words_and11_bindings_exact=True,
            not_direct_compiler_identity=True)

    def test_02_public_reference_literal_private_states_and_fired_cuts(self):
        triples=cuts=0;visited=set()
        for case in self.cases:
            memory=oracle.fixture(case);wanted,expected,calls,stores,_,_=oracle.reference(memory,case)
            for phase in (0,8):
                models=[oracle.RefinementModel(w,memory,case,phase).run() for w in
                    (self.retail,self.normalized_words,self.words)]
                self.assertEqual(state(models[0]),state(models[1]),case);visited|=models[0].visits
                for model in models:
                    self.assertEqual(model.r[2],wanted,case);self.assertEqual(model.calls,calls,case)
                    self.assertEqual(oracle.public(model.memory),oracle.public(expected),case)
                    self.assertEqual(recovery.public_stores(model),stores,case)
                triples+=1
        chosen=[oracle.Case(count=0),oracle.Case(initial=255),oracle.Case(),
            oracle.Case(neighbors=(255,)*5),oracle.Case(object=oracle.OBJECT,inside=1,alias=1),
            oracle.Case(radius=255,threshold=100.,answer=256),oracle.Case(mutation=7,object=oracle.OBJECT),
            oracle.Case(point=(0.,0.,3.))]
        for case in chosen:
            memory=oracle.fixture(case)
            for phase in (0,8):
                complete=oracle.RefinementModel(self.retail,memory,case,phase).run()
                for cut in range(complete.accesses):
                    models=[]
                    for words in (self.retail,self.normalized_words):
                        model=oracle.RefinementModel(words,memory,case,phase);model.fault=cut
                        with self.assertRaises(oracle.core.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut);models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]),(case,phase,cut));cuts+=1
        unvisited=sorted(set(range(source.ENTRY,source.ENTRY+716,4))-visited)
        self.assertEqual(unvisited,[0x150861A0,0x150861A4,0x150861A8,0x150861F0])
        self.receipt('literal-private',fixtures=len(self.cases),completed_triples=triples,fired_access_cut_pairs=cuts,
            retail_words_visited=len(visited),preserved_unvisited_words=[hex(x) for x in unvisited],
            all_GP_FP_LO_conditions_bytes_accesses_calls_and_visits_equal=True,raw_only_public_equivalence=True)

    def test_03_native_profiles_and_effective_behavioral_negatives(self):
        with patch.object(recovery,'source',source):
            recovery.SpatialNeighborRefinementRecoveryTests.test_03_native_profiles_and_effective_behavioral_negatives(self)

    def test_04_loop_induction_local_coefficient_and_frame_only_negative(self):
        self.assertFalse(any(w>>26==3 for w in self.words[0x164//4:0x250//4]))
        for value in range(5):
            a=oracle.RefinementModel([],{},oracle.Case());a.r[7]=value
            a.execute(self.words[0x168//4]);a.execute(self.words[0x160//4])
            b=oracle.RefinementModel([],{},oracle.Case());b.r[6]=value
            b.execute(self.normalized_words[0x160//4]);b.execute(self.normalized_words[0x244//4])
            self.assertEqual(a.r[7],b.r[6]);self.assertEqual(a.r[7]!=a.r[10],b.r[1]!=0)
        self.assertEqual(self.words[0x130//4],self.normalized_words[0x194//4])
        for case in (oracle.Case(count=0),oracle.Case(object=oracle.OBJECT,inside=1)):
            memory=oracle.fixture(case);models=[oracle.RefinementModel(w,memory,case).run()
                for w in (self.retail,self.normalized_words)]
            self.assertEqual(state(models[0]),state(models[1]))
        case=oracle.Case(count=0);memory=oracle.fixture(case);frame_only=self.words.copy()
        frame_only[0]=frame_only[0]&0xFFFF0000|0xFF90;frame_only[-1]=frame_only[-1]&0xFFFF0000|0x70
        original=oracle.RefinementModel(self.retail,memory,case)
        self.assertEqual(oracle.read(original.memory,oracle.STACK+0x14,4),oracle.LIST)
        bad=oracle.RefinementModel(frame_only,memory,case).run()
        self.assertEqual(oracle.read(bad.memory,oracle.STACK+0x14,4),0)
        original.run()
        self.assertNotEqual(bad.memory,original.memory)
        self.assertEqual(oracle.read(original.memory,oracle.STACK+0x14,4),oracle.LIST)
        self.receipt('lifetime-controls',counter_values_checked=5,loop_has_no_helpers=True,
            coefficient_materialized_in_loop=True,all_six_saved_FP_pairs_and_S0_restored=True,
            frame_only_edit_overwrites_incoming_list_word=True,no_hardware_or_FCSR_execution_claim=True)

    def test_05_actual_helpers_caller_and_result_consumer(self):
        recovery.SpatialNeighborRefinementRecoveryTests.test_04_actual_height_record_wrapper_and_containment_packet(self)
        recovery.SpatialNeighborRefinementRecoveryTests.test_05_actual_seven_argument_caller_and_result_consumer(self)
        raw=self.words
        try:
            self.words=self.normalized_words
            recovery.SpatialNeighborRefinementRecoveryTests.test_04_actual_height_record_wrapper_and_containment_packet(self)
            recovery.SpatialNeighborRefinementRecoveryTests.test_05_actual_seven_argument_caller_and_result_consumer(self)
        finally:self.words=raw
        self.receipt('actual-windows',connected_helper_runs=24,actual_caller_runs=96,actual_helper_words=71,
            seven_argument_window_and_return_consumer=True,find_and_query_opaque=True,not_full_script_or_gameplay=True)

    def test_06_independent_GNU_maps_all_bindings_and_backing(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n')
        end=asm.index('endlabel '+source.FUNCTION,start);prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text()
        retail=self.out/'retail.s';retail.write_text(prelude+'\n.text\n'+asm[start:end])
        normalized=self.out/'normalized.s';lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>179I',self.normalized)):
            lines.append('.word 0x%08X'%word)
            if i*4 in self.moved:
                kind,name=self.moved[i*4][0];lines.append('.reloc .-4,%s,%s'%(kind,name))
        normalized.write_text('\n'.join(lines)+'\n')
        for path in (retail,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',
                str(self.root/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        pairs=0
        for n,(entry,delta) in enumerate(((source.ENTRY,0),(0x1621FFF4,0x115CAC),(0x18FFF000,0x235CB0))):
            anchors={name:value+delta for name,value in self.anchors.items()};images=[]
            for path in (retail,normalized):
                script=self.out/(path.stem+'-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in anchors.items()],'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:716])
            self.assertEqual(*images);self.assertEqual(list(struct.unpack('>179I',images[0])),relocate(self.normalized,self.moved,anchors))
            shift=0x40000*n;moved={name:getattr(oracle,name)+delta for name in
                ('NODES','LIMIT','HEIGHT','CLOSEST','LOOKUP','INSIDE','REFINE')}
            moved.update(BANKS=tuple(b+shift for b in oracle.BANKS),ACTOR=oracle.ACTOR+shift,
                OBJECT=oracle.OBJECT+shift,LIST=oracle.LIST+shift,STATE=oracle.STATE+shift)
            moved['SEGMENTS']=((moved['NODES'],4),(moved['LIMIT'],4),(oracle.CACHE,4),
                *((b,0x400) for b in moved['BANKS']),(moved['ACTOR'],0x400),(moved['OBJECT'],0x100))
            with patch.multiple(oracle,**moved):
                for case in self.cases[::11]:
                    case=replace(case,object=moved['OBJECT'] if case.object else 0)
                    memory=oracle.fixture(case);value,wanted,calls,stores,_,_=oracle.reference(memory,case)
                    for words in (list(struct.unpack('>179I',images[0])),relocate(self.raw,self.bindings,anchors)):
                        model=oracle.RefinementModel(words,memory,case,entry=entry).run()
                        self.assertEqual(model.r[2],value);self.assertEqual(model.calls,calls)
                        self.assertEqual(oracle.public(model.memory),oracle.public(wanted));self.assertEqual(recovery.public_stores(model),stores)
                    pairs+=1
        self.receipt('GNU-maps',independent_maps=3,rebased_raw_normalized_pairs=pairs,
            normalized_bytes_equal_independent_retail=True,all11_bindings_and_HI_LO_carries=True)

    def test_07_completed_publication_and_state_aliases(self):
        for alias in (1,2):
            case=oracle.Case(alias=alias,object=oracle.OBJECT,inside=1,answer=2);memory=oracle.fixture(case)
            value,wanted,calls,stores,_,_=oracle.reference(memory,case)
            models=[oracle.RefinementModel(w,memory,case).run() for w in (self.retail,self.normalized_words,self.words)]
            self.assertEqual(state(models[0]),state(models[1]))
            for model in models:
                self.assertEqual(model.r[2],value);self.assertEqual(model.calls,calls)
                self.assertEqual(oracle.public(model.memory),oracle.public(wanted));self.assertEqual(recovery.public_stores(model),stores)
        self.receipt('publication-alias',completed_triples=2,list_state_alias_and_global_pointer_byte_alias=True,
            helper_store_order_preserved=True,no_native_overlapping_region_claim=True)

    def test_08_real_padding_Make_and_strict_complete_image(self):
        out=self.root/integration.BUILD;integration.qualify(self.root,out);integration.make_shadow(self.root,out)
        self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        values=source.freeze(self.root,out);before=values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+716]
        expected=integration.predicted_image(before,truth);canonical=lambda data:Counter((n,*f[1:]) for _,n,f,_ in symbol_rows(data))
        rows=[r for r in symbol_rows(before) if r[1]==source.FUNCTION];_,name,fields,_=rows[0]
        old=canonical(before);old[(name,*fields[1:])]-=1;old[(name,fields[1],716,*fields[3:])]+=1
        self.assertEqual(canonical(expected),+old)
        for at in (64,elf_slot_offset(before,source.ENTRY,716)+112,len(before)-1,rows[0][0]+4):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'image differs'):integration.check_image(before,bytes(bad),truth)
        guards=(out/'qualified-guards.csv').read_bytes();reader=csv.DictReader(io.StringIO(guards.decode()));rows=list(reader)
        target=next(i for i,r in enumerate(rows) if r['filename']==source.OWNER and r['function']==source.FUNCTION)
        for field,value in (('expected','0xFFFFFFFF'),('expected_relocations','R_MIPS_HI16:D_800D2350')):
            corrupt=deepcopy(rows);corrupt[target][field]=value;stream=io.StringIO()
            writer=csv.DictWriter(stream,fieldnames=reader.fieldnames);writer.writeheader();writer.writerows(corrupt)
            path=out/('stale-'+field+'.csv');path.write_text(stream.getvalue())
            with self.assertRaises(ValueError):emit_padded_assembly(out/'after-primary.o',self.root/'conker/asm/B3020.s',
                function_objects={'func_150891E8':out/'after-normal.o'},word_patches_path=path,filename=source.OWNER)
        if (self.root/source.SOURCE).read_bytes()!=values[source.SOURCE]:integration.audit(self.root,out)
        self.receipt('image-controls',strict_image_controls=4,real_padder_stale_controls=2,
            only_target_size_changed=True,guard_prefix_and_all_other_inputs_preserved=True)


if __name__=='__main__':unittest.main()
