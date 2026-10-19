"""Qualify the complete selector and its closed saved-lifetime normalization."""
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

from tools.experiments import game_actor_sine_selector_candidates as source
from tools.experiments import game_actor_sine_selector_layout as layout
from tools.experiments import game_actor_sine_selector_integration as integration
from tools.experiments.game_route_projection_layout_normalizer import relocate
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_actor_sine_selector_oracle as oracle
from tools.tests import test_game_actor_sine_selector_recovery as recovery
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly


def state(model):
    return (model.requested,model.r,model.f,model.lo,model.condition,
            model.memory,model.events,model.calls)


class ActorSineSelectorMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD/'matching'
        cls.values=source.freeze(cls.root,cls.out);cls.cases=list(oracle.cases())
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out)
        cls.raw,cls.bindings=source.payload(cls.obj)
        cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.anchors={name:int(name[2:],16) if name.startswith('D_') else oracle.SINE
                     for entries in cls.bindings.values() for _,name in entries}
        cls.normalized_words=relocate(cls.normalized,cls.moved,cls.anchors)
        cls.rom=cls.values['conker/conker.us.bin']
        cls.retail=list(struct.unpack_from('>136I',cls.rom,source.ROM))
        cls.sine=list(struct.unpack_from('>104I',cls.rom,0x75210))
        cls.connected={oracle.SINE+i*4:w for i,w in enumerate(cls.sine)}

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_exact_recipe_and_complete_stale_controls(self):
        self.assertEqual(self.normalized_words,self.retail)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(138,128,77))
        controls=0
        for at in range(0,len(self.raw),4):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Unknown selector'):layout.normalize(bytes(bad),self.bindings)
            controls+=1
        for at in self.bindings:
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_26',source.FUNCTION)]
            with self.assertRaisesRegex(ValueError,'Unknown selector'):layout.normalize(self.raw,bad)
            controls+=1
        self.assertEqual(set(range(0,552,4))-(set(layout.origins())-{None}),set(layout.OMITTED))
        self.assertEqual(layout.origins().count(None),1)
        for new,old in enumerate(layout.origins()):
            if old is None:continue
            a=struct.unpack_from('>I',self.raw,old)[0];b=struct.unpack_from('>I',self.normalized,new*4)[0]
            if a>>26==17:
                self.assertEqual(a&0xFFFF0000,b&0xFFFF0000) if a>>21&31==8 else self.assertEqual(a,b)
            if a>>26 in (49,53,57,61):self.assertEqual(a&0x1FFFFF,b&0x1FFFFF)
        self.receipt('recipe',corruption_controls=controls,normalized_words=136,frame=112,
            all19_bindings_retained=True,all_FP_operations_and_fields_unchanged=True,
            source_words_retained=135,omitted_dead_words=3,inserted_state_cursor_move=1)

    def test_02_complete_private_states_and_fired_access_cuts(self):
        pairs=cuts=0
        for case in self.cases:
            memory=oracle.fixture(case);result,wanted,calls,_=oracle.reference(memory,case)
            for phase in (0,8):
                models=[oracle.SelectorModel(w,memory,case,phase).run()
                        for w in (self.retail,self.normalized_words,self.words)]
                a,b,c=models;self.assertEqual(state(a),state(b),case)
                for model in models:
                    self.assertEqual(oracle.signed(model.r[2]),result)
                    self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                    self.assertEqual(model.calls,[(target,angle) for target,angle,_ in calls])
                pairs+=1
        selected=[oracle.Case(count=0),oracle.Case(count=1),oracle.Case(count=2,wide=1),
            oracle.Case(active=0),oracle.Case(eligible=0),oracle.Case(states=(3,0,3,0)),
            *[oracle.Case(mutation=n) for n in range(1,5)]]
        for case in selected:
            memory=oracle.fixture(case)
            for phase in (0,8):
                complete=oracle.SelectorModel(self.retail,memory,case,phase).run()
                for cut in range(complete.accesses):
                    models=[]
                    for words in (self.retail,self.normalized_words):
                        model=oracle.SelectorModel(words,memory,case,phase);model.fault=cut
                        with self.assertRaises(oracle.core.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut);models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]));cuts+=1
        self.receipt('literal-private',completed_triples=pairs,fired_access_cut_pairs=cuts,
            entire_private_memory_GP_FP_LO_conditions_and_ordered_events=True,
            raw_compiler_private_frame_intentionally_different=True,not_hardware_FCSR_claim=True)

    def test_03_frame_only_patch_is_an_effective_negative(self):
        case=oracle.Case();memory=oracle.fixture(case)
        bad=self.words.copy();bad[0]=0x27BDFF90;bad[-1]=0x27BD0070
        model=oracle.SelectorModel(bad,memory,case).run()
        good=oracle.SelectorModel(self.normalized_words,memory,case).run()
        self.assertEqual(model.r[2],good.r[2])
        self.assertNotEqual(oracle.read(model.memory,oracle.STACK+4,4),oracle.read(good.memory,oracle.STACK+4,4))
        self.assertEqual(oracle.read(good.memory,oracle.STACK+4,4),0xA5A5A5A5)
        self.assertNotEqual(state(model),state(good))
        self.receipt('frame-negative',same_result_but_caller_word_corrupted=True,
            frame_only_patch_rejected=True,mask_spill_must_actually_disappear=True)

    def test_04_connected_actual_sine_private_identity(self):
        pairs=0
        for case in self.cases:
            if case.mutation or case.answers:continue
            memory=oracle.fixture(case);result,wanted,calls,_=oracle.reference(memory,case)
            a,b=[oracle.SelectorModel(w,memory,case,connected=self.connected).run()
                 for w in (self.retail,self.normalized_words)]
            self.assertEqual(state(a),state(b));self.assertEqual(oracle.signed(b.r[2]),result)
            self.assertEqual(oracle.public(b.memory),oracle.public(wanted))
            self.assertEqual(b.calls,[(target,angle) for target,angle,_ in calls]);pairs+=1
        self.receipt('actual-sine-private',paired_runs=pairs,actual104_word_sine=True,
            full_private_state_and_argument_bits_equal=True)

    test_05_native_semantics_and_six_effective_negatives=recovery.ActorSineSelectorRecoveryTests.test_04_native_O0_O2_UBSan_and_effective_negatives

    def test_06_actual_returning_caller_private_identity(self):
        runs=0
        for case in self.cases[::11]:
            models=[]
            for words in (self.retail,self.normalized_words,self.words):
                memory=oracle.fixture(case);packet=oracle.BANKS[1]+0x1700
                oracle.put(memory,packet+8,case.slot,4)
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                connected.update({0x1509E62C+i*4:w for i,w in enumerate(struct.unpack_from('>3I',self.rom,0xCBADC))})
                model=oracle.SelectorModel(list(struct.unpack_from('>4I',self.rom,0xCB968)),memory,case,
                    connected=connected,entry=0x1509E4B8)
                model.r[29]=oracle.STACK-24;model.r[6]=packet
                oracle.put(model.memory,oracle.STACK-4,0xDEAD0000,4);model.run();models.append(model)
                self.assertEqual(model.caller_args,[(case.slot,)]);runs+=1
            self.assertEqual(state(models[0]),state(models[1]))
            self.assertEqual(models[0].r[2],models[2].r[2])
        self.receipt('caller-private',actual_returning_window_runs=runs,
            caller_frame_live_in=24,normalized_caller_private_memory_and_registers_equal=True)

    def test_07_independent_GNU_maps_and_zero_actor_base(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n')
        end=asm.index('endlabel '+source.FUNCTION,start)
        prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text()
        retail=self.out/'retail.s';retail.write_text(prelude+'\n.text\n'+asm[start:end])
        normalized=self.out/'normalized.s';lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>136I',self.normalized)):
            lines.append('.word 0x%08X'%word)
            if i*4 in self.moved:
                kind,name=self.moved[i*4][0];lines.append('.reloc .-4,%s,%s'%(kind,name))
        normalized.write_text('\n'.join(lines)+'\n')
        for path in (retail,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
                '-I',str(self.root/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        pairs=0
        for n,(entry,delta) in enumerate(((source.ENTRY,0),(0x1621FFF4,0x118004),(0x18FFF000,0x32FFFC),(0x1921FFF4,0x518004))):
            anchors={k:v+delta for k,v in self.anchors.items()}
            if n==3:anchors['D_800CC2D0']=0
            images=[]
            for path in (retail,normalized):
                script=self.out/(path.stem+'-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in anchors.items()],'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:544])
            self.assertEqual(*images)
            self.assertEqual(list(struct.unpack('>136I',images[0])),relocate(self.normalized,self.moved,anchors))
            moved=dict(ACTORS=anchors['D_800CC2D0'],CONTEXT=anchors['D_800D23B0'],SINE=anchors['sinf'],
                COEFFICIENT=oracle.COEFFICIENT+delta,CONSTANTS={a+delta:v for a,v in oracle.CONSTANTS.items()},
                BANKS=tuple(b+0x40000*(n+1) for b in oracle.BANKS))
            moved['SEGMENTS']=tuple((moved['BANKS'][i] if i<2 else moved['ACTORS'] if a==oracle.ACTORS else
                a+delta if a in (oracle.CONTEXT,oracle.COEFFICIENT) else a,size) for i,(a,size) in enumerate(oracle.SEGMENTS))
            with patch.multiple(oracle,**moved):
                for case in [*self.cases[::17],oracle.Case(mutation=2),oracle.Case(mutation=4)]:
                    memory=oracle.fixture(case);result,wanted,calls,_=oracle.reference(memory,case)
                    models=[oracle.SelectorModel(w,memory,case,entry=entry).run() for w in
                        (list(struct.unpack('>136I',images[0])),relocate(self.raw,self.bindings,anchors))]
                    for model in models:
                        self.assertEqual(oracle.signed(model.r[2]),result)
                        self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                        self.assertEqual(model.calls,[(target,angle) for target,angle,_ in calls])
                    pairs+=1
        self.receipt('GNU-maps',independent_maps=4,rebased_raw_normalized_pairs=pairs,
            every_code_global_context_actor_and_provider_anchor_rebased=True,backed_zero_actor_map=True)

    def test_08_real_padding_first_image_and_effective_stale_controls(self):
        out=self.root/integration.BUILD
        integration.qualify(self.root,out);integration.make_shadow(self.root,out)
        self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        values=source.freeze(self.root,out);before=values['conker/build/conker.us.elf']
        truth=self.rom[source.ROM:source.ROM+544];expected=integration.predicted_image(before,truth)
        canonical=lambda data:Counter((n,*f[1:]) for _,n,f,_ in symbol_rows(data))
        rows=[r for r in symbol_rows(before) if r[1]==source.FUNCTION];_,name,fields,_=rows[0]
        old=canonical(before);old[(name,*fields[1:])]-=1;old[(name,fields[1],544,*fields[3:])]+=1
        self.assertEqual(canonical(expected),+old)
        for at in (64,elf_slot_offset(before,source.ENTRY,544)+112,len(before)-1,rows[0][0]+4):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'image differs'):integration.check_image(before,bytes(bad),truth)
        guards=(out/'qualified-guards.csv').read_bytes();reader=csv.DictReader(io.StringIO(guards.decode()));rows=list(reader)
        target=next(i for i,r in enumerate(rows) if r['filename']==source.OWNER and r['function']==source.FUNCTION)
        for field,value in (('expected','0xFFFFFFFF'),('expected_relocations','R_MIPS_HI16:D_800D23B0')):
            corrupt=deepcopy(rows);corrupt[target][field]=value;stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=reader.fieldnames)
            writer.writeheader();writer.writerows(corrupt);path=out/('stale-'+field+'.csv');path.write_text(stream.getvalue())
            with self.assertRaises(ValueError):emit_padded_assembly(out/'after-primary.o',self.root/'conker/asm/B3020.s',
                function_objects={source.FUNCTION:out/'after-normal.o'},word_patches_path=path,filename=source.OWNER)
        if (self.root/source.SOURCE).read_bytes()!=values[source.SOURCE]:integration.audit(self.root,out)
        self.receipt('image-controls',strict_image_controls=4,real_padder_stale_controls=2,
            canonical_symbols_only_target_size_changed=True)


if __name__=='__main__':unittest.main()
