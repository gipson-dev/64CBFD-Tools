"""Literal assignment layout, poisoned miss byte, real caller and strict image proof."""
from collections import Counter
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_balanced_target_assignment_candidates as source
from tools.experiments import game_balanced_target_assignment_layout as layout
from tools.experiments import game_balanced_target_assignment_integration as integration
from tools.experiments.game_route_projection_layout_normalizer import relocate
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_balanced_target_assignment_oracle as oracle
from tools.tests import test_game_balanced_target_assignment_recovery as recovery
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly


def state(model):
    return (model.r,model.f,model.lo,model.condition,model.memory,model.events,
        model.stores,model.reads,model.requested,model.visits,model.calls)


class BalancedTargetAssignmentMatchTests(unittest.TestCase):
    test_03_native_profiles_and_effective_semantic_negatives=(
        recovery.BalancedTargetAssignmentRecoveryTests.test_03_native_profiles_and_effective_semantic_negatives)

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD/'matching'
        cls.values=source.freeze(cls.root,cls.out);cls.cases=list(oracle.cases())
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out)
        cls.raw,cls.bindings=source.payload(cls.obj);cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.normalized_words=relocate(cls.normalized,cls.moved,{'D_800D23B0':oracle.CONTEXT})
        cls.rom=cls.values['conker/conker.us.bin'];cls.retail=list(struct.unpack_from('>160I',cls.rom,source.ROM))

    def receipt(self,name,**row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_all_words_origins_bindings_and_stale_controls(self):
        self.assertEqual(self.normalized_words,self.retail)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(160,224,123))
        self.assertFalse(self.row['diagnostics']);controls=0
        for at in range(0,640,4):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Unknown balanced-assignment'):layout.normalize(bytes(bad),self.bindings)
            controls+=1
        for at in self.bindings:
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_26',source.FUNCTION)]
            with self.assertRaisesRegex(ValueError,'Unknown balanced-assignment'):layout.normalize(self.raw,bad)
            controls+=1
        self.assertEqual({x for x in layout.origins() if isinstance(x,int)},set(range(0,640,4))-set(layout.OMITTED))
        self.assertEqual(self.moved,self.bindings)
        self.receipt('recipe',raw_source_controls=controls,source_words_retained=158,
            omitted_native_only_initializer_and_mask=2,inserted_clear_copies=2,
            all160_words_and_two_bindings_exact=True,not_direct_compiler_identity=True)

    def test_02_reference_full_private_states_and_fired_cuts(self):
        triples=cuts=0;visited=set()
        for case in self.cases:
            memory=oracle.fixture(case);wanted,stores=oracle.reference(memory)
            for phase in (0,8):
                models=[oracle.AssignmentModel(w,memory,phase).run() for w in (self.retail,self.normalized_words,self.words)]
                self.assertEqual(state(models[0]),state(models[1]),case);visited|=models[0].visits
                for model in models:
                    self.assertEqual(model.r[2],0);self.assertFalse(model.calls)
                    self.assertEqual(oracle.public(model.memory),oracle.public(wanted),case)
                    self.assertEqual(recovery.external_stores(model),stores,case)
                triples+=1
        chosen=[oracle.Case(count=0),oracle.Case(count=1),oracle.Case(count=3),
            oracle.Case(count=5,sentinel=0),oracle.Case(count=4,position=15),
            oracle.Case(count=4,scores=(0x40000001,))]
        for case in chosen:
            memory=oracle.fixture(case)
            for phase in (0,8):
                complete=oracle.AssignmentModel(self.retail,memory,phase).run()
                for cut in range(complete.accesses):
                    models=[]
                    for words in (self.retail,self.normalized_words):
                        model=oracle.AssignmentModel(words,memory,phase);model.fault=cut
                        with self.assertRaises(oracle.core.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut);models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]));cuts+=1
        self.assertEqual(len(visited),160)
        self.receipt('literal-private',fixtures=len(self.cases),completed_triples=triples,fired_access_cut_pairs=cuts,
            retail_words_visited=len(visited),all_GP_FP_LO_conditions_memory_ordered_accesses_and_visits_equal=True,
            raw_only_public_equivalence=True,no_helper_or_hardware_claim=True)

    def test_04_signed_byte_low_five_bits_and_original_private_poison(self):
        recovery.BalancedTargetAssignmentRecoveryTests.test_04_private_miss_cell_and_frame_only_negative(self)
        tuples=0
        for byte in range(256):
            for score in (0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x40000001):
                value=(byte if byte<128 else byte-256)&0xFFFFFFFF
                a=oracle.AssignmentModel([],{});a.r[24]=value;a.r[6]=score
                a.execute(self.words[0x1EC//4]);a.execute(self.words[0x1F0//4])
                b=oracle.AssignmentModel([],{});b.r[14]=value;b.r[6]=score
                b.execute(self.normalized_words[0x1F0//4])
                wanted=score<<(byte&31)&0xFFFFFFFF
                self.assertEqual(a.r[6],wanted);self.assertEqual(b.r[6],wanted);tuples+=1
        for poison in (0,0x7F,0xA5,0xFF):
            case=oracle.Case(count=5,active=(0,),flags=(2,));memory=oracle.fixture(case,poison)
            models=[oracle.AssignmentModel(w,memory).run() for w in (self.retail,self.normalized_words)]
            self.assertEqual(state(models[0]),state(models[1]))
            self.assertEqual(models[1].memory[oracle.STACK-176+0x7B],(poison+3)&255)
        self.receipt('mask-and-poison',signed_byte_score_tuples=tuples,retail_private_poisons=4,
            normalized_miss_byte_not_initialized=True,raw_backing_initializer_not_original_source_fact=True,
            complete_poisoned_private_states_equal=True,not_hardware_shift_execution=True)

    def test_05_actual_returning_caller_and_effective_frame_only_negative(self):
        recovery.BalancedTargetAssignmentRecoveryTests.test_05_actual_no_argument_returning_caller(self)
        runs=0
        for case in self.cases[::11]:
            models=[];memory=oracle.fixture(case);wanted,stores=oracle.reference(memory)
            for words in (self.retail,self.normalized_words,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                connected.update({0x1509E3CC+i*4:w for i,w in enumerate(struct.unpack_from('>4I',self.rom,0xCB87C))})
                model=oracle.AssignmentModel(list(struct.unpack_from('>4I',self.rom,0xCB564)),memory,
                    connected=connected,entry=0x1509E0B4)
                model.r[29]=oracle.STACK-72
                oracle.put(model.memory,oracle.STACK-36,0xDEAD0000,4)
                oracle.put(model.memory,oracle.STACK-40,model.before[16],4)
                model.run();self.assertEqual(model.caller_args,[()]);self.assertEqual(model.r[2],0)
                self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                self.assertEqual(recovery.external_stores(model),stores);models.append(model);runs+=1
            self.assertEqual(state(models[0]),state(models[1]))
        self.receipt('returning-caller',actual_window_runs=runs,ROM_JAL='0xCB564',caller_frame_live_in=72,
            frame_only_real_caller_RA_corruption_rejected=True,not_full_switch_execution=True)

    def test_06_independent_GNU_maps(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n')
        end=asm.index('endlabel '+source.FUNCTION,start);prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text()
        retail=self.out/'retail.s';retail.write_text(prelude+'\n.text\n'+asm[start:end])
        normalized=self.out/'normalized.s';lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>160I',self.normalized)):
            lines.append('.word 0x%08X'%word)
            if i*4 in self.moved:
                kind,name=self.moved[i*4][0];lines.append('.reloc .-4,%s,%s'%(kind,name))
        normalized.write_text('\n'.join(lines)+'\n')
        for path in (retail,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',
                str(self.root/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        pairs=0
        for n,(entry,global_at,bank) in enumerate(((source.ENTRY,oracle.CONTEXT,oracle.BANK),
                (0x1621FFF4,0x80207FFC,0x28000),(0x18FFF000,0x80308000,0x32000))):
            images=[]
            for path in (retail,normalized):
                script=self.out/(path.stem+'-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=D_800D23B0=0x%X'%global_at,'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:640])
            self.assertEqual(*images)
            self.assertEqual(list(struct.unpack('>160I',images[0])),relocate(self.normalized,self.moved,{'D_800D23B0':global_at}))
            with patch.multiple(oracle,CONTEXT=global_at,BANK=bank,SEGMENTS=((global_at,4),(bank,0x2000))):
                for case in self.cases[::9]:
                    memory=oracle.fixture(case);wanted,stores=oracle.reference(memory)
                    for w in (list(struct.unpack('>160I',images[0])),relocate(self.raw,self.bindings,{'D_800D23B0':global_at})):
                        model=oracle.AssignmentModel(w,memory,entry=entry).run()
                        self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                        self.assertEqual(recovery.external_stores(model),stores)
                    pairs+=1
        self.receipt('GNU-maps',independent_maps=3,rebased_raw_normalized_pairs=pairs,
            normalized_bytes_equal_independently_assembled_retail=True,both_global_bindings_and_HI_LO_carry=True)

    def test_07_completed_guest_publication_global_alias_keeps_cached_bases(self):
        bank=oracle.CONTEXT-0x45C
        with patch.multiple(oracle,BANK=bank,SEGMENTS=((oracle.CONTEXT,4),(bank,0x2000))):
            case=oracle.Case(count=4);memory=oracle.fixture(case);wanted,stores=oracle.reference(memory)
            models=[oracle.AssignmentModel(w,memory).run() for w in (self.retail,self.normalized_words,self.words)]
            self.assertEqual(state(models[0]),state(models[1]))
            self.assertNotEqual(oracle.read(wanted,oracle.CONTEXT,4),bank)
            for model in models:
                self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                self.assertEqual(recovery.external_stores(model),stores)
        self.receipt('global-alias',completed_guest_triple=True,first_cost_overwrites_global_context=True,
            later_receivers_keep_original_cached_bases=True,not_native_overlapping_region_claim=True)

    def test_08_real_padding_Make_and_strict_complete_image(self):
        out=self.root/integration.BUILD;integration.qualify(self.root,out);integration.make_shadow(self.root,out)
        self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        values=source.freeze(self.root,out);before=values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+640]
        expected=integration.predicted_image(before,truth)
        canonical=lambda data:Counter((n,*f[1:]) for _,n,f,_ in symbol_rows(data))
        rows=[r for r in symbol_rows(before) if r[1]==source.FUNCTION];_,name,fields,_=rows[0]
        old=canonical(before);old[(name,*fields[1:])]-=1;old[(name,fields[1],640,*fields[3:])]+=1
        self.assertEqual(canonical(expected),+old)
        for at in (64,elf_slot_offset(before,source.ENTRY,640)+112,len(before)-1,rows[0][0]+4):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'image differs'):integration.check_image(before,bytes(bad),truth)
        guards=(out/'qualified-guards.csv').read_bytes();reader=csv.DictReader(io.StringIO(guards.decode()));rows=list(reader)
        target=next(i for i,r in enumerate(rows) if r['filename']==source.OWNER and r['function']==source.FUNCTION)
        for field,value in (('expected','0xFFFFFFFF'),('expected_relocations','R_MIPS_HI16:D_800D23B0')):
            corrupt=deepcopy(rows);corrupt[target][field]=value;stream=io.StringIO()
            writer=csv.DictWriter(stream,fieldnames=reader.fieldnames);writer.writeheader();writer.writerows(corrupt)
            path=out/('stale-'+field+'.csv');path.write_text(stream.getvalue())
            with self.assertRaises(ValueError):emit_padded_assembly(out/'after-primary.o',self.root/'conker/asm/B3020.s',
                function_objects={'func_150891E8':out/'after-normal.o'},word_patches_path=path,filename=source.OWNER)
        if (self.root/source.SOURCE).read_bytes()!=values[source.SOURCE]:integration.audit(self.root,out)
        self.receipt('image-controls',strict_image_controls=4,real_padder_stale_controls=2,
            canonical_symbols_only_target_size_changed=True,guard_prefix_and_all_non_target_inputs_preserved=True)


if __name__=='__main__':unittest.main()
