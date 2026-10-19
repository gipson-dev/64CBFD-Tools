"""Literal timer layout, raw private traces and actual indirect result consumer."""
from copy import deepcopy
from collections import Counter
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_target_timer_matching as source
from tools.experiments import game_actor_target_timer_layout as layout
from tools.experiments import game_actor_target_timer_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_actor_target_timer_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_target_timer_recovery as recovery
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly

class ResultStored(Exception):pass


class ScriptModel(oracle.TimerModel):
    def record_call(self,target):
        if target in (0x150AE12C,0x1509DFC4):
            self.events.append(('DISPATCH',target,tuple(self.r[4:7])));return
        super().record_call(target)

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and address==0x800D384C:raise ResultStored()


class ActorTargetTimerMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.cases=list(oracle.cases())
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out,'selected',source.RESEARCH_PARTIAL)
        cls.raw,cls.bindings=source.payload(cls.obj);cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.anchors={name:int(name[2:],16) if name.startswith('D_') else int(name[5:],16) for v in cls.bindings.values() for _,name in v}
        cls.normalized_words=layout.relocate(cls.normalized,cls.moved,cls.anchors)
        cls.rom=cls.values['conker/conker.us.bin'];cls.retail=list(struct.unpack_from('>115I',cls.rom,source.ROM))
        cls.random=list(struct.unpack_from('>25I',cls.rom,0xDAF18));cls.notify=list(struct.unpack_from('>26I',cls.rom,0xBC040))

    def receipt(self,name,**row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_exact_recipe_and_effective_corruption_controls(self):
        self.assertEqual(self.normalized_words,self.retail)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(115,80,60))
        count=0
        for offset in (0,40,72,252,272,316,344,459):
            bad=bytearray(self.raw);bad[offset]^=1
            with self.assertRaisesRegex(ValueError,'Unknown actor-target'):layout.normalize(bytes(bad),self.bindings)
            count+=1
        for offset in self.bindings:
            bad=deepcopy(self.bindings);bad[offset]=[('R_MIPS_26',source.FUNCTION)]
            with self.assertRaisesRegex(ValueError,'Unknown actor-target'):layout.normalize(self.raw,bad)
            count+=1
        with patch.object(layout,'OPEN',{**layout.OPEN,8:5}):
            with self.assertRaisesRegex(ValueError,'Changed timer lifetime'):layout.normalize(self.raw,self.bindings)
        self.assertEqual(layout.origins().count(86),2);self.assertNotIn(10,layout.origins())
        for new,old in enumerate(layout.origins()):
            a=struct.unpack_from('>I',self.raw,old*4)[0];b=struct.unpack_from('>I',self.normalized,new*4)[0]
            if a>>26==17:
                mask=~(31<<16) if a>>21&31 in (0,4) else -1
                self.assertEqual(a&mask,b&mask)
            if a>>26 in (49,57):self.assertEqual(a&0x1FFFFF,b&0x1FFFFF)
            if old not in (68,79):self.assertEqual(a>>26,b>>26)
        self.receipt('recipe',corruption_controls=count+1,all_FP_fields_unchanged=True,
            duplicate_slot_shift_omitted=True,timer_load_split_over_mutually_exclusive_edges=True)

    def test_02_literal_states_and_raw_entire_private_trace(self):
        pairs=cuts=0
        for case in self.cases:
            m=oracle.fixture(case)
            for phase in (0,8):
                models=[oracle.TimerModel(w,m,case,phase).run() for w in (self.retail,self.normalized_words,self.words)]
                a,b,c=models
                self.assertEqual((a.r,a.f,a.lo,a.condition,a.memory,a.events),(b.r,b.f,b.lo,b.condition,b.memory,b.events))
                self.assertEqual((a.memory,a.events,a.r[2]),(c.memory,c.events,c.r[2]),case);pairs+=1
        for case in (oracle.Case(target=-1),oracle.Case(timer=7,threshold=10),oracle.Case(timer=1,mask=0),
                     oracle.Case(timer=1,notify_change=1),oracle.Case(timer=1,random_change=1)):
            m=oracle.fixture(case);complete=oracle.TimerModel(self.retail,m,case).run()
            for cut in range(complete.accesses):
                models=[]
                for words in (self.retail,self.normalized_words,self.words):
                    model=oracle.TimerModel(words,m,case);model.fault=cut
                    with self.assertRaises(oracle.core.AccessFault):model.run()
                    self.assertEqual(model.accesses,cut);models.append(model)
                a,b,c=models
                self.assertEqual((a.requested,a.r,a.f,a.lo,a.memory,a.events),(b.requested,b.r,b.f,b.lo,b.memory,b.events))
                self.assertEqual((a.requested,a.memory,a.events),(c.requested,c.memory,c.events));cuts+=1
        self.receipt('literal',full_literal_pairs=pairs,raw_private_memory_entire_events_and_residual_V0_equal=True,
            fired_cut_triples=cuts,not_hardware_FCSR_or_fault_claims=True)

    def test_03_actual_indirect_script_return_is_stored(self):
        count=0;seeded=0;zero_control=None
        corpus=[(c,None) for c in [oracle.Case(target=-1),oracle.Case(target=-2147483648),
            oracle.Case(timer=7,threshold=10),oracle.Case(timer=1,notify_change=1),*self.cases[::9]]]
        corpus += [(oracle.Case(),seed) for seed in (0,89413)]
        for case,seed in corpus:
            memories=[];results=[]
            for words in (self.retail,self.normalized_words,self.words):
                m=oracle.fixture(case);packet=0x2C000
                m.update({packet+i:0xA5 for i in range(32)})
                m.update({0x800D3840+i:0xA5 for i in range(16)})
                for a,v in ((packet,0xF000),(packet+4,14),(packet+8,case.slot),
                    (0x800886BC,struct.unpack_from('>I',self.rom,0x22D17C)[0]),
                    (0x8008850C,struct.unpack_from('>I',self.rom,0x22CFCC)[0]),
                    (0x8009F33C,struct.unpack_from('>I',self.rom,0x243DFC)[0])):oracle.put(m,a,v,4)
                if seed is not None:
                    oracle.put(m,oracle.SEED,seed,8);oracle.put(m,oracle.SCALE,0x37800080,4)
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                if seed is not None:connected.update({oracle.RANDOM+i*4:w for i,w in enumerate(self.random)})
                for entry,rom,length in ((0x150AE12C,0xDB5DC,26),(0x1509DFC4,0xCB474,262)):
                    connected.update({entry+i*4:w for i,w in enumerate(struct.unpack_from('>%dI'%length,self.rom,rom))})
                model=ScriptModel(list(struct.unpack_from('>20I',self.rom,0xDB488)),m,case,connected=connected,entry=0x150ADFD8)
                model.r[21]=packet;model.r[10]=6
                with self.assertRaises(ResultStored):model.run()
                self.assertEqual(oracle.read(model.memory,0x800D384C,4),0x800D3848)
                self.assertIn(0x150AE00C,model.visits);self.assertEqual(model.caller_args,[(case.slot,)])
                if case.target<0:self.assertEqual(oracle.read(model.memory,0x800D3848,4),0)
                if seed is not None:
                    self.assertEqual(oracle.read(model.memory,0x800D3848,4),oracle.next_seed(seed)&65535)
                    self.assertEqual(oracle.read(model.memory,oracle.SEED,8),oracle.next_seed(seed))
                if seed==89413 and words is self.retail:
                    # Replacing the otherwise dead return-delay NOP preserves
                    # function effects but corrupts its actual interpreter result.
                    bad=words.copy();bad[-1]=0x00001025
                    altered=dict(connected);altered.update({source.ENTRY+i*4:w for i,w in enumerate(bad)})
                    negative=ScriptModel(list(struct.unpack_from('>20I',self.rom,0xDB488)),m,case,connected=altered,entry=0x150ADFD8)
                    negative.r[21]=packet;negative.r[10]=6
                    with self.assertRaises(ResultStored):negative.run()
                    zero_control=oracle.read(negative.memory,0x800D3848,4)
                    self.assertNotEqual(zero_control,oracle.next_seed(seed)&65535)
                results.append(oracle.read(model.memory,0x800D3848,4));memories.append(model.memory)
            self.assertEqual(results,[results[0]]*3);self.assertEqual(memories[0],memories[1]);self.assertEqual(memories[0],memories[2]);count+=1
            if seed is not None:seeded+=1
        self.assertEqual(zero_control,0)
        self.receipt('script-return-consumer',fixture_triples=count,actual_two_indirect_tables_and_switch_table=True,
            actual_dispatcher_prologue_target_epilogue_and_result_stores=True,
            actual_seeded_RNG_triples=seeded,effective_zero_result_control=True,
            fired_stop_after_D_800D384C_store=True,full_interpreter_or_general_C_result_not_claimed=True)

    def test_04_native_actual_partial_body_with_result_discarded(self):
        for label,opt,sanitize in (('O0','-O0',False),('O2','-O2',False),('UBSan','-O2',True)):
            program=self.out/('native-partial-'+label+'.c');exe=program.with_suffix('.exe')
            program.write_text(oracle.native_harness(source.RESEARCH_PARTIAL,self.cases))
            result=subprocess.run(native_command(opt,sanitize)+['-Wno-return-type','-mstackrealign','-fno-strict-aliasing',str(program),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(subprocess.run([str(exe)]).returncode,0)
        body=source.RESEARCH_PARTIAL
        negatives={
            'threshold-equality':body.replace('] < *timer','] <= *timer'),
            'probability-equality':body.replace('] < (s32)','] <= (s32)'),
            'unsigned-probability':body.replace('D_800872E8[D_800E0BD0]','(u8)D_800872E8[D_800E0BD0]'),
            'stale-timer':body.replace('    if (*timer == 0)','    timer = (s32 *)((u8 *)D_800D23B0 + 0x29C) + slot;\n    if (*timer == 0)'),
            'distance-equality':body.replace('distance > 2000.0f','distance >= 2000.0f')}
        for name,body in negatives.items():
            self.assertNotEqual(body,source.RESEARCH_PARTIAL)
            program=self.out/('negative-partial-'+name+'.c');exe=program.with_suffix('.exe')
            program.write_text(oracle.native_harness(body,self.cases))
            result=subprocess.run(native_command('-O2',False)+['-Wno-return-type','-mstackrealign','-fno-strict-aliasing',str(program),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertIn(subprocess.run([str(exe)]).returncode,(21,23))
        self.receipt('native-partial',profiles=3,fixtures_each=len(self.cases),effective_negatives=5,actual_partial_return_C_body=True,
            no_fallthrough_result_consumed=True,only_native_return_type_warning_disabled=True)

    def test_05_three_independent_GNU_maps(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n');end=asm.index('endlabel '+source.FUNCTION,start)
        prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text();retail=self.out/'retail.s'
        retail.write_text(prelude+'\n.text\n.type '+source.FUNCTION+', @function\n'+asm[start:end]+'\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>115I',self.normalized)):
            entries=self.moved.get(i*4,[])
            if entries:
                kind,name=entries[0];mask=0xFC000000 if kind=='R_MIPS_26' else 0xFFFF0000
                lines+=['.word 0x%08X'%(word&mask),'.reloc .-4,%s,%s'%(kind,name)]
            else:lines.append('.word 0x%08X'%word)
        normalized=self.out/'normalized.s';normalized.write_text('\n'.join(lines)+'\n')
        for path in (retail,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(self.root/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        executed=0
        for n,(entry,delta) in enumerate(((source.ENTRY,0),(0x1621FFF4,0x118004),(0x18FFF000,0x32FFFC))):
            anchors={k:v+delta for k,v in self.anchors.items()};images=[]
            for path in (retail,normalized):
                script=self.out/(path.stem+'-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in anchors.items()],'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:460])
            self.assertEqual(*images);self.assertEqual(list(struct.unpack('>115I',images[0])),layout.relocate(self.normalized,self.moved,anchors))
            moved={key:anchors[name] for key,name in (('ACTORS','D_800CC2D0'),('CONTEXT','D_800D23B0'),('MODE','D_800E0BD0'),
                ('THRESHOLDS','D_80087320'),('PROBABILITY','D_800872E8'),('LIMIT','D_8009DA8C'),
                ('NOTIFY','func_1508EB90'),('RANDOM','func_150ADA68'))}
            moved.update(BANKS=tuple(v+0x40000*(n+1) for v in oracle.BANKS),NESTED=oracle.NESTED+0x40000*(n+1))
            moved['SEGMENTS']=tuple((moved['BANKS'][i],0x1800) for i in range(2))+(
                (moved['ACTORS'],26*0x32C),(moved['NESTED'],27*0x130),(moved['THRESHOLDS']-768,1536),
                (moved['MODE'],1),(moved['CONTEXT'],4),(moved['LIMIT'],4))
            with patch.multiple(oracle,**moved):
                for case in self.cases[::11]:
                    memory=oracle.fixture(case);wanted,stores,calls,_=oracle.reference(memory,case)
                    models=[oracle.TimerModel(w,memory,case,entry=entry).run() for w in (
                        list(struct.unpack('>115I',images[0])),layout.relocate(self.raw,self.bindings,anchors))]
                    for model in models:
                        self.assertEqual(oracle.public(model.memory),oracle.public(wanted));self.assertEqual(oracle.writes(model),stores)
                        self.assertEqual(model.calls,calls)
                    self.assertEqual((models[0].memory,models[0].events,models[0].r[2]),(models[1].memory,models[1].events,models[1].r[2]));executed+=1
        self.receipt('GNU-maps',maps=3,all16_bindings_including_calls_independently_assembled=True,
            executed_rebased_pairs=executed,code_globals_heaps_and_providers_rebased=True)

    def test_06_real_padding_Make_image_and_stale_controls(self):
        out=self.root/integration.BUILD
        integration.qualify(self.root,out);integration.make_shadow(self.root,out)
        self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        values=source.freeze(self.root,out);before=values['conker/build/conker.us.elf']
        truth=values['conker/conker.us.bin'][source.ROM:source.ROM+460];expected=integration.predicted_image(before,truth)
        canonical=lambda data:Counter((n,*f[1:]) for _,n,f,_ in symbol_rows(data))
        old=canonical(before);rows=[r for r in symbol_rows(before) if r[1]==source.FUNCTION];_,name,fields,_=rows[0]
        old[(name,*fields[1:])]-=1;old[(name,fields[1],460,*fields[3:])]+=1
        self.assertEqual(canonical(expected),+old)
        row=next(r for r in symbol_rows(expected) if r[1]=='D_80090244')
        for at in (64,elf_slot_offset(before,source.ENTRY,460)+112,len(before)-1,row[0]+4,row[3]):
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
        self.receipt('image-controls',strict_image_controls=5,real_padder_stale_controls=2,
            canonical_symbols_only_target_size_changed=True,nine_symbol_four_run_serialization_predicted=True)

    test_07_independent_public_semantics=recovery.ActorTargetTimerRecoveryTests.test_02_complete_public_buffers_stores_callbacks_and_ABI
    test_08_actual_RNG=recovery.ActorTargetTimerRecoveryTests.test_04_real_64bit_float_RNG_and_incidental_integer_result
    test_09_actual_notification_wrapper=recovery.ActorTargetTimerRecoveryTests.test_05_real_notification_wrapper_and_fired_access_cuts
    test_10_publication_alias_and_returning_caller=recovery.ActorTargetTimerRecoveryTests.test_06_target_publication_alias_and_actual_returning_caller

    def test_11_backed_guest_target_width_and_shift_count(self):
        count=0
        for target in (32,33,63,255,256):
            case=oracle.Case(slot=7,target=target,timer=1,x=3000.,z=4000.)
            memory=oracle.fixture(case);wanted,stores,calls,_=oracle.reference(memory,case)
            models=[oracle.TimerModel(w,memory,case).run() for w in (self.retail,self.normalized_words,self.words)]
            for model in models:
                self.assertEqual(oracle.public(model.memory),oracle.public(wanted));self.assertEqual(oracle.writes(model),stores)
                self.assertEqual(model.calls,calls)
            a,b,c=models
            self.assertEqual((a.r,a.f,a.lo,a.memory,a.events),(b.r,b.f,b.lo,b.memory,b.events))
            self.assertEqual((a.memory,a.events,a.r[2]),(c.memory,c.events,c.r[2]));count+=1
        self.receipt('guest-targets',completed_triples=count,published_byte_not_used_as_signed_target=True,
            hardware_low5_shift_count_modeled=True,not_native_array_bounds_or_shift_validity_claim=True)


if __name__=='__main__':unittest.main()
