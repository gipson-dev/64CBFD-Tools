"""Qualify the recovered stack/read lifetimes, explicit recipe and complete image."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch
import unittest

from tools.experiments import game_category_boundaries_lifetime_fit as source
from tools.experiments import game_category_boundaries_layout as layout
from tools.experiments import game_category_boundaries_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_category_boundaries_oracle as oracle
from tools.tests import test_game_category_boundaries_recovery as prior
from tools.tests.test_game_packed_peer_lookup_match import state
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows,canonical_symbols
from tools.pad_generated_object import emit_padded_assembly


class CategoryBoundaryMatchTests(prior.CategoryBoundaryRecoveryTests):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD/'tests'
        cls.values=source.freeze(cls.root,cls.out);cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out,'qualified')
        cls.raw,cls.bindings=source.payload(cls.obj);cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.normalized_words=layout.relocate(cls.normalized,cls.moved,oracle.DEFAULT)
        cls.retail=list(struct.unpack_from('>112I',cls.values['conker/conker.us.bin'],source.ROM));cls.cases=list(oracle.cases())

    def test_01_complete_source_and_unresolved_instruction_layout(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(112,96,35,''))
        self.assertEqual(self.normalized_words,self.retail);self.assertEqual(self.moved,self.bindings);self.assertEqual(len(self.bindings),20)
        self.assertEqual(sorted(layout.origins()),list(range(112)))
        guards=layout.private_guards(self.values['conker/retail_word_patches.us.csv'],self.raw,self.bindings)
        self.assertTrue(guards.startswith(self.values['conker/retail_word_patches.us.csv']))
        rows=[r for r in csv.DictReader(io.StringIO(guards.decode())) if r['function']==source.FUNCTION]
        self.assertEqual(len(rows),35);self.assertTrue(all(not r['insert_after'] and r['omit']=='false' for r in rows))
        self.assertIn('s32 func_15085BE8(void);',source.recovered_owner(self.values[source.SOURCE].decode()))
        self.receipt('layout-match',words=112,frame=96,guards=35,source_origins_retained=112,
            moved_binding_positions=0,inserted_or_omitted_words=0,swapped_independent_ADDU_origins=[89,90])

    def test_03_native32_full_buffers_and_effective_source_negatives(self):
        with patch.object(prior.source,'FITTED',source.SELECTED):
            super().test_03_native32_full_buffers_and_effective_source_negatives()

    def test_04_fired_retail_access_cuts_and_explicit_raw_order_boundary(self):
        count=0
        for case in (oracle.Case(),oracle.Case(((0,0),)),oracle.Case(((4,0),(1,1))),oracle.Case(((0,0),(0,1)))):
            for phase in (0,8):
                memory=oracle.fixture(case,phase);run=oracle.BoundaryModel(self.retail,memory,phase).run()
                for cut,event in enumerate(run.events):
                    models=[]
                    for words in (self.retail,self.normalized_words,self.words):
                        model=oracle.BoundaryModel(words,memory,phase);model.fault=cut
                        with self.assertRaises(oracle.core.AccessFault):model.run()
                        self.assertEqual((model.accesses,model.requested),(cut,event[:3]));models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(getattr(models[0],'condition',None),getattr(models[1],'condition',None))
                    self.assertEqual((models[0].memory,models[0].events),(models[2].memory,models[2].events));count+=1
        self.receipt('fired-cuts',literal_pairs=count,all_requested_cuts_fired=True,
            raw_private_memory_and_access_events_also_equal=True,first_read_order_recovered=True,hardware_faults_not_claimed=True)

    def test_07_both_owner_profiles_actual_padding_and_frozen_production(self):
        out=self.root/integration.BUILD;result=integration.qualify(self.root,out);self.assertEqual(result['word_differences'],0)
        reader=csv.DictReader(io.StringIO((out/'qualified-guards.csv').read_text()));rows=list(reader)
        for index in (len(rows)-35,len(rows)-17,len(rows)-1):
            for field in ('expected','expected_relocations'):
                bad=[dict(r) for r in rows];bad[index][field]='0xFFFFFFFF' if field=='expected' else 'R_MIPS_26:'+source.FUNCTION
                text=io.StringIO();writer=csv.DictWriter(text,fieldnames=reader.fieldnames);writer.writeheader();writer.writerows(bad)
                path=self.out/('bad-%d-%s.csv'%(index,field));path.write_text(text.getvalue())
                with self.assertRaisesRegex(ValueError,'stale word patch' if field=='expected' else 'stale relocations'):
                    emit_padded_assembly(out/'after-primary.o',self.root/'conker/asm/B3020.s',
                        function_objects={'func_150891E8':out/'after-normal.o'},word_patches_path=path,filename=source.OWNER)
        if (self.root/source.SOURCE).read_bytes()==self.values[source.SOURCE]:
            for name,value in self.values.items():self.assertEqual((self.root/name).read_bytes(),value,name)
        else:integration.audit(self.root,out)

    def test_08_full_literal_states_and_raw_private_trace_on_complete_corpus(self):
        count=0
        for case in self.cases:
            for phase in (0,8):
                memory=oracle.fixture(case,phase)
                models=[oracle.BoundaryModel(w,memory,phase).run() for w in (self.retail,self.normalized_words,self.words)]
                self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(models[0].condition,models[1].condition)
                self.assertEqual((models[0].memory,models[0].events),(models[2].memory,models[2].events));count+=1
        self.receipt('literal-states',pairs=count,complete_GP_FP_LO_memory_events_and_result=True,
            raw_private_memory_and_entire_access_trace_equal=True,not_FCSR_or_hardware_exception_model=True)

    def test_09_backed_guest_stack_aliases_and_out_of_range_categories(self):
        count=0
        for category in (6,7,8,31,255):
            for height in (-32768,0,32767):
                for phase in (0,8):
                    memory=oracle.fixture(oracle.Case(((height,category),)),phase)
                    stack=oracle.STACK+phase-96
                    oracle.put(memory,stack+24+category*4,oracle.bits(-10000.),4)
                    oracle.put(memory,stack+48+category*4,oracle.bits(10000.),4)
                    models=[oracle.BoundaryModel(w,memory,phase).run() for w in (self.retail,self.normalized_words,self.words)]
                    self.assertEqual(state(models[0]),state(models[1]))
                    self.assertEqual((models[0].memory,models[0].events),(models[2].memory,models[2].events));count+=1
        for phase in (0,8):
            for offset in (24,48):
                memory=oracle.fixture(oracle.Case(((0,0),)),phase);stack=oracle.STACK+phase-96
                oracle.put(memory,oracle.DEFAULT['D_800D2350'],stack+offset,4)
                oracle.put(memory,stack+24+64*4,oracle.bits(-10000.),4)
                oracle.put(memory,stack+48+64*4,oracle.bits(10000.),4)
                models=[oracle.BoundaryModel(w,memory,phase).run() for w in (self.retail,self.normalized_words,self.words)]
                self.assertEqual(state(models[0]),state(models[1]))
                self.assertEqual((models[0].memory,models[0].events),(models[2].memory,models[2].events));count+=1
        self.receipt('guest-aliases',completed_guest_cases=count,finite_explicitly_backed_extra_scratch=True,
            rows_alias_both_initialized_arrays=True,not_portable_C_or_native_out_of_bounds_claims=True)

    def test_10_GNU_normalized_code_identity_all20_bindings_and_rebased_execution(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n');end=asm.index('endlabel '+source.FUNCTION,start)
        prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text();original=self.out/'retail-normalization.s'
        original.write_text(prelude+'\n.text\n.type '+source.FUNCTION+', @function\n'+asm[start:end]+'\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>112I',self.normalized)):
            entries=self.moved.get(i*4,[])
            if entries:
                kind,name=entries[0];lines+=['.word 0x%08X'%(word&0xFFFF0000),'.reloc .-4,%s,%s'%(kind,name)]
            else:lines.append('.word 0x%08X'%word)
        normalized=self.out/'normalized.s';normalized.write_text('\n'.join(lines)+'\n')
        for path in (original,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
                '-I',str(self.root/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        count=0
        for n,(entry,delta,rows) in enumerate(((source.ENTRY,0,oracle.ROWS),(0x1621FFF4,0x118004,0x68000),(0x18FFF000,0x32FFFC,0x90000))):
            anchors={k:v+delta for k,v in oracle.DEFAULT.items()};images=[]
            for path in (original,normalized):
                script=self.out/(path.stem+'-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:448])
            self.assertEqual(*images);words=list(struct.unpack('>112I',images[0]));self.assertEqual(words,layout.relocate(self.normalized,self.moved,anchors))
            for case in self.cases[::29]:
                for phase in (0,8):
                    memory=oracle.fixture(case,phase,anchors,rows);wanted,after=oracle.reference(memory,anchors)
                    model=oracle.BoundaryModel(words,memory,phase,entry).run()
                    self.assertEqual((model.r[2],oracle.public(model.memory)),(wanted,oracle.public(after)));count+=1
        self.receipt('normalized-GNU-maps',maps=3,executed_cases=count,all20_bindings_independently_assembled=True)

    def test_11_raw_binding_and_recipe_corruptions_and_exact_origin_fields(self):
        count=0
        for at in (0,8,176,356,447):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Unknown category-boundary'):layout.normalize(bytes(bad),self.bindings)
            count+=1
        for at in self.bindings:
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_26',source.FUNCTION)]
            with self.assertRaisesRegex(ValueError,'Unknown category-boundary'):layout.normalize(self.raw,bad)
            count+=1
        with patch.object(layout,'FINAL_GP',{**layout.FINAL_GP,5:7}):
            with self.assertRaisesRegex(ValueError,'Changed category-boundary'):layout.normalize(self.raw,self.bindings)
        with patch.object(layout,'FP',{0:3,2:0}):
            with self.assertRaisesRegex(ValueError,'Changed category-boundary'):layout.normalize(self.raw,self.bindings)
        old=struct.unpack('>112I',self.raw);new=struct.unpack('>112I',self.normalized)
        for destination,origin in enumerate(layout.origins()):
            a,b=old[origin],new[destination];self.assertEqual(a>>26,b>>26)
            if a>>26 not in (0,17):self.assertEqual(a&65535,b&65535)
            if a>>26==17 and a&63==60:self.assertEqual(a&0x7C0,b&0x7C0)
        self.assertEqual(old[0],new[0]);self.assertEqual(old[-1],new[-1])
        self.receipt('corruption-controls',raw_binding_recipe_controls=count+2,
            opcodes_immediates_frame_and_compare_CC_fields_unchanged=True)

    def test_12_actual_Make_first_image_and_strict_image_negatives(self):
        out=self.root/integration.BUILD;integration.make_shadow(self.root,out);self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        values=source.freeze(self.root,out);before=values['conker/build/conker.us.elf'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+448]
        expected=integration.predicted_image(before,truth)
        rows=[r for r in symbol_rows(expected) if r[1]=='D_8009D9C0'];self.assertEqual(len(rows),1)
        old_target=[r for r in symbol_rows(before) if r[1]==source.FUNCTION];self.assertEqual(len(old_target),1)
        _,name,fields,_=old_target[0];symbols=canonical_symbols(before)
        symbols[(name,*fields[1:])]-=1;symbols[(name,fields[1],448,*fields[3:])]+=1
        self.assertEqual(canonical_symbols(expected),+symbols)
        for at in (64,elf_slot_offset(before,source.ENTRY,448)+132,len(before)-1,rows[0][0]+4,rows[0][3]):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'image differs'):integration.check_image(before,bytes(bad),truth)
        if (self.root/source.SOURCE).read_bytes()!=values[source.SOURCE]:integration.audit(self.root,out)


if __name__=='__main__':unittest.main()
