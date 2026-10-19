"""Complete weighted selection, explicit helper contracts and private layout proof."""
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

from tools.experiments import game_weighted_target_selection_candidates as source
from tools.experiments import game_weighted_target_selection_layout as layout
from tools.experiments import game_weighted_target_selection_integration as integration
from tools.experiments.game_route_projection_layout_normalizer import relocate
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_weighted_target_selection_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly


def state(model):
    return (model.requested,model.r,model.f,model.lo,model.condition,model.memory,model.events,model.calls)


class WeightedTargetSelectionMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD/'matching'
        cls.values=source.freeze(cls.root,cls.out);cls.cases=list(oracle.cases())
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out)
        cls.raw,cls.bindings=source.payload(cls.obj)
        cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.anchors={name:int(name[2:],16) if name.startswith('D_') else int(name[5:],16)
            for entries in cls.bindings.values() for _,name in entries}
        cls.normalized_words=relocate(cls.normalized,cls.moved,cls.anchors)
        cls.rom=cls.values['conker/conker.us.bin'];cls.retail=list(struct.unpack_from('>153I',cls.rom,source.ROM))

    def receipt(self,name,**row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_recipe_and_complete_word_binding_controls(self):
        self.assertEqual(self.normalized_words,self.retail)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(151,64,36))
        self.assertFalse(self.row['diagnostics']);controls=0
        for at in range(0,604,4):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Unknown weighted-selector'):layout.normalize(bytes(bad),self.bindings)
            controls+=1
        for at in self.bindings:
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_26',source.FUNCTION)]
            with self.assertRaisesRegex(ValueError,'Unknown weighted-selector'):layout.normalize(self.raw,bad)
            controls+=1
        self.assertEqual({i for i in layout.origins() if isinstance(i,int)},set(range(0,604,4)))
        for new,old in enumerate(layout.origins()):
            if not isinstance(old,int):continue
            a=struct.unpack_from('>I',self.raw,old)[0];b=struct.unpack_from('>I',self.normalized,new*4)[0]
            if a>>26==17 and old not in (0x168,0x174):self.assertEqual(a,b)
            if old in (0x168,0x174):self.assertEqual(a&~(31<<16),b&~(31<<16))
        self.receipt('recipe',controls=controls,all151_source_origins_retained=True,
            all16_bindings_retained=True,FP_changes_only_closed_scale_colors=True,
            inserted_MFC_delay_NOP_and_mutually_exclusive_result_zero=True)

    def test_02_public_reference_private_states_and_all_selected_cuts(self):
        pairs=cuts=0;visited=set()
        for case in self.cases:
            memory=oracle.fixture(case);wanted,calls,stores,_,_=oracle.reference(memory,case)
            for phase in (0,8):
                models=[oracle.WeightedModel(w,memory,case,phase).run() for w in
                    (self.retail,self.normalized_words,self.words)]
                self.assertEqual(state(models[0]),state(models[1]),case);visited|=models[0].visits
                for model in models:
                    self.assertEqual(model.r[2],0);self.assertEqual(model.calls,calls)
                    self.assertEqual(oracle.public(model.memory),oracle.public(wanted),case)
                    writes=[(e[1],e[2],e[3]) for e in model.events if e[0]=='W' and not
                            oracle.STACK-0x500<=e[1]<oracle.STACK+0x100]
                    self.assertEqual(writes,stores)
                pairs+=1
        chosen=[oracle.Case(count=0),oracle.Case(count=1),oracle.Case(count=9),
            oracle.Case(positions=(-1,),sentinel=4),oracle.Case(positions=(15,)),
            oracle.Case(weights=(128,),preferred=1),*[oracle.Case(mutation=n) for n in range(1,5)]]
        for case in chosen:
            memory=oracle.fixture(case)
            for phase in (0,8):
                complete=oracle.WeightedModel(self.retail,memory,case,phase).run()
                for cut in range(complete.accesses):
                    models=[]
                    for words in (self.retail,self.normalized_words):
                        model=oracle.WeightedModel(words,memory,case,phase);model.fault=cut
                        with self.assertRaises(oracle.previous.core.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut);models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]));cuts+=1
        self.receipt('literal-private',fixtures=len(self.cases),completed_triples=pairs,fired_access_cut_pairs=cuts,
            retail_words_visited=len(visited),entire_GP_FP_LO_conditions_memory_and_events_equal=True,
            modeled_helpers_and_O32_argument_area_overwrites=True,not_helper_internal_or_hardware_FCSR_claim=True)

    def test_03_frame_only_edit_still_fails_private_homes(self):
        case=oracle.Case();memory=oracle.fixture(case)
        bad=self.words.copy();bad[0]=0x27BDFFA0;bad[-1]=0x27BD0060
        a=oracle.WeightedModel(self.normalized_words,memory,case).run()
        b=oracle.WeightedModel(bad,memory,case).run()
        self.assertEqual(oracle.public(a.memory),oracle.public(b.memory));self.assertNotEqual(a.memory,b.memory)
        mismatch=None
        for cut in range(a.accesses):
            models=[]
            for w in (self.normalized_words,bad):
                model=oracle.WeightedModel(w,memory,case);model.fault=cut
                with self.assertRaises(oracle.previous.core.AccessFault):model.run()
                models.append(model)
            if models[0].requested!=models[1].requested:
                mismatch=dict(cut=cut,retail=models[0].requested,frame_only=models[1].requested);break
        self.assertIsNotNone(mismatch)
        self.receipt('frame-only-negative',same_public_result_but_wrong_private_homes=True,first_fired_mismatch=mismatch)

    def test_04_native_profiles_and_effective_semantic_negatives(self):
        def run(name,body,opt='-O2',sanitize=False):
            program=self.out/(name+'.c');exe=program.with_suffix('.exe');program.write_text(oracle.native_harness(body,self.cases))
            built=subprocess.run(native_command(opt,sanitize)+['-mstackrealign','-fno-strict-aliasing',str(program),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            result=subprocess.run([str(exe)],capture_output=True,text=True)
            if sanitize:self.assertFalse(result.stderr,result.stderr)
            return result.returncode
        for name,opt,sanitize in (('native-O0','-O0',False),('native-O2','-O2',False),('native-UBSan','-O2',True)):
            self.assertEqual(run(name,source.SELECTED,opt,sanitize),0)
        negatives={
            'last-tie':source.SELECTED.replace('score < best','score <= best'),
            'signed-weight':source.SELECTED.replace('(f32)(u32)weights[i]','(f32)(s8)weights[i]'),
            'wrong-budget-boundary':source.SELECTED.replace('count >= 9','count >= 8'),
            'live-count':source.SELECTED.replace('++i < count','++i < *(s32 *)((u8 *)D_800D23B0 + 0x10)'),
            'live-current':source.SELECTED.replace('    weights =','    current = *(s32 *)((u8 *)D_800D23B0 + 4);\n    weights =',1),
            'live-active-base':source.SELECTED.replace('active[i]','((s32 *)((u8 *)D_800D23B0 + 0x39C))[i]').replace(
                '    s32 *active = (s32 *)((u8 *)D_800D23B0 + 0x39C);\n',''),
            'live-neighbor-base':source.SELECTED.replace('neighbors[scan]','((s32 *)((u8 *)D_800D23B0 + 0x5DC))[scan]').replace(
                '    s32 *neighbors = (s32 *)((u8 *)D_800D23B0 + 0x5DC);\n',''),
            'ignore-sentinel':source.SELECTED.replace('neighbors[scan] != -1','1')}
        for name,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED);self.assertIn(run('negative-'+name,body),(21,22,23,24,25),name)
        self.receipt('native',profiles=3,fixtures_each=len(self.cases),effective_negatives=len(negatives),
            complete_translated_buffers_and_ordered_two_helper_ABI=True,helper_results_intentionally_ignored=True)

    def test_05_target_publication_alias_requires_fresh_distance_context(self):
        case=oracle.Case(scores=(10,1000,300,400));memory=oracle.fixture(case)
        alias=oracle.CONTEXT-case.current*4-0x49C
        for base,size in ((alias,0x1800),(0x400,0x200)):
            for a in range(base,base+size):memory.setdefault(a,0xA5)
        for i in range(16):oracle.put(memory,alias+case.current*16+0x15B4+i,255,1)
        def alias_provider(case,ordinal):return [(oracle.CONTEXT,alias,4)] if ordinal==1 else []
        with patch.object(oracle,'changes',side_effect=alias_provider):
            wanted,calls,_,selected,distance=oracle.reference(memory,case)
            self.assertEqual(selected,0);self.assertEqual(oracle.read(wanted,oracle.CONTEXT,4),0)
            models=[oracle.WeightedModel(w,memory,case).run() for w in (self.retail,self.normalized_words,self.words)]
            self.assertEqual(state(models[0]),state(models[1]))
            for model in models:
                self.assertEqual(oracle.public(model.memory),oracle.public(wanted));self.assertEqual(model.calls,calls)
            bad=self.normalized_words.copy();self.assertEqual(bad[0x1E8//4],0x8DCE23B0)
            bad[0x1E8//4]=0x02607025
            negative=oracle.WeightedModel(bad,memory,case).run()
            self.assertNotEqual(oracle.public(negative.memory),oracle.public(wanted))
        self.receipt('publication-alias',completed_guest_triple=True,selected_zero_overwrites_context_pointer=True,
            fresh_zero_context_distance=distance,effective_cached_context_negative=True,not_native_null_pointer_claim=True)

    def test_06_actual_no_argument_returning_caller(self):
        jal=0x0C000000|(source.ENTRY>>2)&0x3FFFFFF
        self.assertEqual([i for i in range(0,len(self.rom)-3,4) if struct.unpack_from('>I',self.rom,i)[0]==jal],[0xCB5DC])
        count=0
        for case in self.cases[::13]:
            models=[]
            for words in (self.retail,self.normalized_words,self.words):
                memory=oracle.fixture(case);connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                connected.update({0x1509E3CC+i*4:w for i,w in enumerate(struct.unpack_from('>4I',self.rom,0xCB87C))})
                model=oracle.WeightedModel(list(struct.unpack_from('>4I',self.rom,0xCB5DC)),memory,case,
                    connected=connected,entry=0x1509E12C)
                model.r[29]=oracle.STACK-72
                oracle.put(model.memory,oracle.STACK-36,0xDEAD0000,4)
                oracle.put(model.memory,oracle.STACK-40,model.before[16],4)
                model.run();self.assertEqual(model.caller_args,[()]);self.assertEqual(model.r[2],0)
                models.append(model);count+=1
            self.assertEqual(state(models[0]),state(models[1]))
            self.assertEqual(oracle.public(models[0].memory),oracle.public(models[2].memory))
        self.receipt('returning-caller',actual_window_runs=count,caller_frame_live_in=72,
            full_JAL_NOP_branch_RA_S0_SP_JR_window=True,no_function_arguments=True,not_full_switch_execution=True)

    def test_07_independent_GNU_maps_with_both_providers(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n')
        end=asm.index('endlabel '+source.FUNCTION,start);prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text()
        retail=self.out/'retail.s';retail.write_text(prelude+'\n.text\n'+asm[start:end])
        normalized=self.out/'normalized.s';lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>153I',self.normalized)):
            lines.append('.word 0x%08X'%word)
            if i*4 in self.moved:
                kind,name=self.moved[i*4][0];lines.append('.reloc .-4,%s,%s'%(kind,name))
        normalized.write_text('\n'.join(lines)+'\n')
        for path in (retail,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
                '-I',str(self.root/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        pairs=0
        for n,(entry,delta) in enumerate(((source.ENTRY,0),(0x1621FFF4,0x118004),(0x18FFF000,0x32FFFC))):
            anchors={k:v+delta for k,v in self.anchors.items()};images=[]
            for path in (retail,normalized):
                script=self.out/(path.stem+'-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in anchors.items()],'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:612])
            self.assertEqual(*images);self.assertEqual(list(struct.unpack('>153I',images[0])),relocate(self.normalized,self.moved,anchors))
            moved=dict(ACTORS=anchors['D_800CC2D0'],CONTEXT=anchors['D_800D23B0'],PREPARE=anchors['func_1508C5B8'],
                SCAN=anchors['func_1508A1BC'],FAVOR=anchors['D_8009DA60'],UNIT=anchors['D_8009DA64'],
                SCALES={a+delta:v for a,v in oracle.SCALES.items()},BANKS=tuple(b+0x40000*(n+1) for b in oracle.BANKS))
            moved['SEGMENTS']=tuple((moved['BANKS'][i] if i<3 else a+delta,size) for i,(a,size) in enumerate(oracle.SEGMENTS))
            with patch.multiple(oracle,**moved):
                for case in [*self.cases[::19],*[oracle.Case(mutation=i) for i in range(1,5)]]:
                    memory=oracle.fixture(case);wanted,calls,_,_,_=oracle.reference(memory,case)
                    for w in (list(struct.unpack('>153I',images[0])),relocate(self.raw,self.bindings,anchors)):
                        model=oracle.WeightedModel(w,memory,case,entry=entry).run()
                        self.assertEqual(oracle.public(model.memory),oracle.public(wanted));self.assertEqual(model.calls,calls)
                    pairs+=1
        self.receipt('GNU-maps',independent_maps=3,rebased_raw_normalized_pairs=pairs,all16_bindings_including_two_providers=True)

    def test_08_real_padding_Make_and_strict_whole_image(self):
        out=self.root/integration.BUILD;integration.qualify(self.root,out);integration.make_shadow(self.root,out)
        self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        values=source.freeze(self.root,out);before=values['conker/build/conker.us.elf']
        truth=self.rom[source.ROM:source.ROM+612];expected=integration.predicted_image(before,truth)
        canonical=lambda data:Counter((n,*f[1:]) for _,n,f,_ in symbol_rows(data))
        rows=[r for r in symbol_rows(before) if r[1]==source.FUNCTION];_,name,fields,_=rows[0]
        old=canonical(before);old[(name,*fields[1:])]-=1;old[(name,fields[1],612,*fields[3:])]+=1
        self.assertEqual(canonical(expected),+old)
        for at in (64,elf_slot_offset(before,source.ENTRY,612)+112,len(before)-1,rows[0][0]+4):
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
            canonical_symbols_only_target_size_changed=True,eight_names_three_bounded_serialization_runs=True)


if __name__=='__main__':unittest.main()
