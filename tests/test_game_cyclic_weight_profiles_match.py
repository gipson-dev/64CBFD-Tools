"""Cyclic-weight ABI, scratch endpoint, native contracts and strict installation proof."""
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

from tools.experiments import game_cyclic_weight_profiles_candidates as source
from tools.experiments import game_cyclic_weight_profiles_layout as layout
from tools.experiments import game_cyclic_weight_profiles_integration as integration
from tools.experiments.game_route_projection_layout_normalizer import relocate
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_cyclic_weight_profiles_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly

MODE=0x800E0BD0


def state(model):
    return (model.r,model.f,model.lo,model.condition,model.memory,model.events,model.stores,
        model.reads,model.requested,model.visits,model.calls,model.requests,model.accesses)


class WindowStop(Exception):pass


class CallerModel(oracle.WeightModel):
    def get(self,address,size):
        if address==MODE and size==1:
            self.stopped=True;self.requested=('R',address,size);raise WindowStop()
        return super().get(address,size)


class CyclicWeightProfilesMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD/'matching'
        cls.values=source.freeze(cls.root,cls.out);cls.cases=list(oracle.cases())
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out)
        cls.raw,cls.bindings=source.payload(cls.obj);cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.anchors={name:int(name[2:],16) if name.startswith('D_') else int(name[5:],16)
            for entries in cls.moved.values() for _,name in entries}
        cls.normalized_words=relocate(cls.normalized,cls.moved,cls.anchors)
        cls.rom=cls.values['conker/conker.us.bin'];cls.retail=list(struct.unpack_from('>189I',cls.rom,source.ROM))

    def receipt(self,name,**row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_words_origins_profiles_and_stale_controls(self):
        self.assertEqual(self.normalized_words,self.retail)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(188,136,167))
        self.assertFalse(self.row['diagnostics']);self.assertIn('void func_1508BC20(void)',source.SELECTED)
        controls=0
        for at in range(0,752,4):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Unknown cyclic-weight'):layout.normalize(bytes(bad),self.bindings)
            controls+=1
        for at in self.bindings:
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_26',source.FUNCTION)]
            with self.assertRaisesRegex(ValueError,'Unknown cyclic-weight'):layout.normalize(self.raw,bad)
            controls+=1
        self.assertEqual({x for x in layout.origins() if isinstance(x,int)},set(range(0,752,4)))
        self.assertEqual(Counter(x for entries in self.bindings.values() for x in entries),
            Counter(x for entries in self.moved.values() for x in entries))
        self.receipt('recipe',all189_words_and6_bindings_exact=True,source_words_retained=188,omitted=0,
            inserted_early_RA_copy=1,stale_controls=controls,normal_profile_required=True,not_direct_compiler_identity=True)

    def test_02_reference_private_states_and_fired_cuts(self):
        triples=cuts=0;visited=set()
        for case in self.cases:
            memory=oracle.fixture(case);wanted,calls,stores=oracle.reference(memory,case)
            for phase in (0,8):
                models=[oracle.WeightModel(w,memory,case,phase,used_offset=off).run() for w,off in
                    ((self.retail,0x50),(self.normalized_words,0x50),(self.words,0x68))]
                self.assertEqual(state(models[0]),state(models[1]),case);visited|=models[0].visits
                for model in models:
                    self.assertEqual(model.calls,calls,case);self.assertEqual(oracle.public(model.memory),oracle.public(wanted),case)
                    self.assertEqual(oracle.public_stores(model),stores,case)
                triples+=1
        chosen=[oracle.Case(count=0),oracle.Case(count=1),oracle.Case(count=3),oracle.Case(count=4),
            oracle.Case(count=4,used_mask=1,samples=(0.,0.5)),oracle.Case(count=8,mutation=4)]
        for case in chosen:
            memory=oracle.fixture(case)
            for phase in (0,8):
                complete=oracle.WeightModel(self.retail,memory,case,phase).run()
                for cut in range(complete.accesses):
                    models=[]
                    for words in (self.retail,self.normalized_words):
                        model=oracle.WeightModel(words,memory,case,phase);model.fault=cut
                        with self.assertRaises(oracle.core.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut);models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]));cuts+=1
        unvisited=sorted(set(range(source.ENTRY,source.ENTRY+756,4))-visited)
        self.assertEqual(unvisited,[0x1508BC8C,0x1508BC9C,0x1508BCA0,0x1508BCA4,
            0x1508BDA4,0x1508BE70,0x1508BEB0])
        self.receipt('literal-private',fixtures=len(self.cases),completed_triples=triples,fired_access_cut_pairs=cuts,
            retail_words_visited=len(visited),preserved_unvisited_words=[hex(x) for x in unvisited],
            complete_GP_FP_LO_condition_memory_requests_events_calls_and_PC_set_equal=True,
            raw_only_public_equivalence=True,private_callback_writes_are_guest_only_controls=True)

    def test_03_native_profiles_and_effective_negatives(self):
        unsafe=oracle.Case(count=16,samples=(1.,0.25))
        self.assertFalse(oracle.native_safe(unsafe))
        self.assertFalse(oracle.native_safe(oracle.Case(count=16,samples=(0.,1.,0.))))
        self.assertTrue(oracle.native_safe(oracle.Case(count=15,samples=(1.,0.25))))
        with self.assertRaisesRegex(ValueError,'Guest-only native'):
            oracle.native_harness(source.SELECTED,[unsafe])
        corpus=oracle.native_cases()
        def run(name,body,opt='-O2',sanitize=False):
            program=self.out/(name+'.c');exe=program.with_suffix('.exe');program.write_text(oracle.native_harness(body,corpus))
            built=subprocess.run(native_command(opt,sanitize)+['-mstackrealign','-fno-strict-aliasing',str(program),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            result=subprocess.run([str(exe)],capture_output=True,text=True);self.assertFalse(result.stderr,result.stderr)
            return result.returncode
        for name,opt,san in (('native-O0','-O0',False),('native-O2','-O2',False),('native-UBSan','-O2',True)):
            self.assertEqual(run(name,source.SELECTED,opt,san),0,name)
        reset=source.SELECTED.replace('        delta = step;\n','').replace('    step = 170 / divisor;',
            '    step = 170 / divisor;\n    delta = step;')
        late=source.SELECTED.replace('    u8 *weights = (u8 *)D_800D23B0 + 0x15B4;','    u8 *weights;').replace(
            '        used[position] = 1;', '        used[position] = 1;\n        weights = (u8 *)D_800D23B0 + 0x15B4 + row * 16;')
        negatives={'unsigned-count':source.SELECTED.replace('count = D_8008FD8C','count = (u8)D_8008FD8C'),
            'wrong-half':source.SELECTED.replace('count >> 1','count >> 2'),
            'wrong-budget':source.SELECTED.replace('170 / divisor','169 / divisor'),
            'wrong-initial-weight':source.SELECTED.replace('value = 85','value = 84'),
            'no-saturation':source.SELECTED.replace('value < 256 ? value : 255','value'),
            'early-bounce':source.SELECTED.replace('value >= 256','value >= 255'),
            'late-bounce':source.SELECTED.replace('value >= 256','value > 256'),
            'missing-second-random':source.SELECTED.replace('func_150ADA68() > 0.5f','0'),
            'rounded-origin':source.SELECTED.replace('func_150ADA68() * (f32)count)', 'func_150ADA68() * (f32)count + 0.5f)'),
            'delta-not-reset':reset,'late-context-base':late,
            'reloaded-count':source.SELECTED.replace('row < count','row < D_8008FD8C').replace('i < count','i < D_8008FD8C'),
            'wrong-row-stride':source.SELECTED.replace('weights += 16','weights += count'),
            'clamped-random-endpoint':source.SELECTED.replace('        if (func_150ADA68()',
                '        if (position >= count) { position = count - 1; }\n        if (func_150ADA68()')}
        exits={}
        for name,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED);exits[name]=run('negative-'+name,body)
            self.assertIn(exits[name],(21,22,23),name)
        self.receipt('native',profiles=3,fixtures_each=len(corpus),effective_negatives=exits,
            explicit_endpoint_and_odd_stream_backing_gate_fired=True,
            includes_large_count_zero_origin_cases=True,used_mask_and_count16_endpoint_excluded=True,
            no_uninitialized_or_out_of_array_native_access_claim=True)

    def test_04_division_domain_scratch_search_and_empty_private_negative(self):
        for value in range(256):
            count=oracle.signed(value,8);divisor=max(2,count>>1)
            self.assertTrue(2<=divisor<=63)
            model=oracle.WeightModel([],{},oracle.Case());model.r[14]=170;model.r[3]=divisor
            model.execute(self.normalized_words[0x58//4]);self.assertEqual(model.lo,170//divisor)
        case=oracle.Case(count=0);memory=oracle.fixture(case);models=[]
        for words in (self.retail,self.words):
            model=oracle.WeightModel(words,memory,case);model.fault=12
            with self.assertRaises(oracle.core.AccessFault):model.run()
            self.assertEqual(model.accesses,12);models.append(model)
        self.assertEqual(models[0].requested,('W',oracle.STACK-0x88+0x6C,4))
        self.assertEqual(models[1].requested,('R',oracle.STACK-0x88+0x3C,4))
        controls={
            'non-strict-direction':(source.SELECTED.replace('> 0.5f','>= 0.5f'),oracle.Case(used_mask=1,samples=(0.,0.5))),
            'missing-lower-wrap':(source.SELECTED.replace('''            if (position < 0) {
                position = count - 1;
            }
''',''),oracle.Case(used_mask=1,samples=(0.,0.25))),
            'missing-upper-search-wrap':(source.SELECTED.replace('''            if (position >= count) {
                position = 0;
            }
''','',1),oracle.Case(used_mask=8,samples=(0.9,0.75))),
            'inverted-mark-test':(source.SELECTED.replace('while (used[position] != 0)','while (used[position] == 0)'),
                oracle.Case(used_mask=1,samples=(0.,0.25)))}
        for name,(body,case) in controls.items():
            _,words,row=source.compile_candidate(self.root,self.out,'guest-negative-'+name,body)
            self.assertFalse(row['diagnostics']);self.assertEqual(row['frame'],136)
            wanted,_,_=oracle.reference(oracle.fixture(case),case)
            model=oracle.WeightModel(words,oracle.fixture(case),case,used_offset=0x68).run()
            self.assertNotEqual(oracle.public(model.memory),oracle.public(wanted),name)
        self.receipt('lifetime-controls',all256_signed_byte_divisors_safe=True,unconditional_DIV_store_preserved=True,
            fired_empty_count_access12_mismatch=True,effective_guest_only_search_negatives=len(controls),
            no_claim_real_RNG_writes_caller_scratch=True)

    def test_05_actual_RNG_and_legacy_endpoint_poison(self):
        connected={oracle.RANDOM+i*4:w for i,w in enumerate(struct.unpack_from('>25I',self.rom,0xDAF18))}
        elf=self.values['conker/build/conker.us.elf'];at=elf_slot_offset(elf,oracle.RANDOM,100)
        self.assertEqual(elf[at:at+100],self.rom[0xDAF18:0xDAF7C])
        self.assertEqual(oracle.f32(65535*oracle.floating(oracle.SCALE_BITS)),1.)
        self.assertEqual(oracle.previous.next_seed(0x15D45)&65535,65535)
        runs=endpoint_cuts=0
        for count in (1,4,16):
            for seed in (0,1,0x15D45,0xFFFFFFFF,0x100000000):
                case=oracle.Case(count=count,seed=seed)
                for poison in (0,0xA5):
                    memory=oracle.fixture(case,poison);wanted,calls,stores=oracle.reference(memory,case,poison)
                    models=[]
                    for words,off in ((self.retail,0x50),(self.normalized_words,0x50),(self.words,0x68)):
                        model=oracle.WeightModel(words,memory,case,connected=connected,used_offset=off).run()
                        self.assertEqual(model.calls,calls);self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                        self.assertEqual(oracle.public_stores(model),stores);models.append(model);runs+=1
                    self.assertEqual(state(models[0]),state(models[1]))
        for poison in (0,0xA5):
            case=oracle.Case(count=16,samples=(1.,0.25));memory=oracle.fixture(case,poison)
            wanted,calls,stores=oracle.reference(memory,case,poison);complete=oracle.WeightModel(self.retail,memory,case).run()
            self.assertEqual(oracle.public(complete.memory),oracle.public(wanted))
            cuts=[i for i,q in enumerate(complete.requests) if q==('R',oracle.STACK-0x88+0x60,1)]
            self.assertEqual(len(cuts),16)
            for cut in cuts:
                models=[]
                for words in (self.retail,self.normalized_words):
                    model=oracle.WeightModel(words,memory,case);model.fault=cut
                    with self.assertRaises(oracle.core.AccessFault):model.run()
                    self.assertEqual(model.accesses,cut);models.append(model)
                self.assertEqual(state(models[0]),state(models[1]));endpoint_cuts+=1
        self.receipt('actual-RNG',actual_helper_words=25,completed_runs=runs,endpoint_fired_cut_pairs=endpoint_cuts,
            frozen_scale_bits=hex(oracle.SCALE_BITS),actual_seed_reaches_inclusive_one='0x15D45',
            count16_uncleared_byte_at_SP60_preserved_with_two_poisons=True,not_portable_C_endpoint_safety=True)

    def test_06_actual_caller_and_fired_post_call_boundary(self):
        jal=0x0C000000|(source.ENTRY>>2)&0x3FFFFFF
        self.assertEqual([i for i in range(0,len(self.rom)-3,4) if struct.unpack_from('>I',self.rom,i)[0]==jal],[0xB7124])
        window=list(struct.unpack_from('>24I',self.rom,0xB7124));runs=0
        for count in (0,1,4,8):
            for mutation in (0,1,4):
                case=oracle.Case(count=count,mutation=mutation);memory=oracle.fixture(case)
                wanted,calls,_=oracle.reference(memory,case);base=oracle.read(wanted,oracle.CONTEXT,4)
                for offset in range(5):oracle.put(wanted,base+0x1700+offset,0,1)
                oracle.put(wanted,base+0x16BC,0x5678,2)
                for words,off in ((self.retail,0x50),(self.normalized_words,0x50),(self.words,0x68)):
                    mapping={source.ENTRY+i*4:w for i,w in enumerate(words)}
                    model=CallerModel(window,memory,case,connected=mapping,entry=0x15089C74,used_offset=off)
                    model.r[29]=oracle.STACK-40;model.r[4]=0x12345678;model.stopped=False
                    with self.assertRaises(WindowStop):model.run()
                    self.assertTrue(model.stopped);self.assertEqual(model.requested,('R',MODE,1))
                    self.assertEqual(model.calls,calls);self.assertEqual(model.caller_args,[()])
                    self.assertEqual(oracle.public(model.memory),oracle.public(wanted));runs+=1
        self.receipt('caller',actual_prefix_runs=runs,ROM_JAL='0xB7124',caller_frame_live_in=40,
            fired_stop_before_actual_MODE_read=True,five_fresh_context_byte_clears_and_halfword_publication=True,
            actual_caller_ignores_return_register=True,not_full_caller_return_or_gameplay=True)

    def test_07_independent_GNU_maps_and_completed_global_aliases(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n')
        end=asm.index('endlabel '+source.FUNCTION,start);prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text()
        retail=self.out/'retail.s';retail.write_text(prelude+'\n.text\n'+asm[start:end])
        normalized=self.out/'normalized.s';lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>189I',self.normalized)):
            lines.append('.word 0x%08X'%word)
            if i*4 in self.moved:
                kind,name=self.moved[i*4][0];lines.append('.reloc .-4,%s,%s'%(kind,name))
        normalized.write_text('\n'.join(lines)+'\n')
        for path in (retail,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',
                str(self.root/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        pairs=aliases=0
        for n,(entry,count,context,random) in enumerate(((source.ENTRY,oracle.COUNT,oracle.CONTEXT,oracle.RANDOM),
                (0x1621FFF4,0x80107FFC,0x80208000,0x16218000),(0x18FFF000,0x80308000,0x80407FFC,0x18012000))):
            anchors={'D_8008FD8C':count,'D_800D23B0':context,'func_150ADA68':random};images=[]
            for path in (retail,normalized):
                script=self.out/(path.stem+'-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in anchors.items()],'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:756])
            self.assertEqual(*images);self.assertEqual(list(struct.unpack('>189I',images[0])),relocate(self.normalized,self.moved,anchors))
            banks=tuple(b+n*0x40000 for b in oracle.BANKS)
            with patch.multiple(oracle,COUNT=count,CONTEXT=context,RANDOM=random,BANKS=banks,
                    SEGMENTS=((count,1),(context,4),(oracle.SEED,8),(oracle.SCALE,4),*((b,0x3000) for b in banks))):
                for case in self.cases[::13]:
                    memory=oracle.fixture(case);wanted,calls,stores=oracle.reference(memory,case)
                    for words,off in ((list(struct.unpack('>189I',images[0])),0x50),(relocate(self.raw,self.bindings,anchors),0x68)):
                        model=oracle.WeightModel(words,memory,case,entry=entry,used_offset=off).run()
                        self.assertEqual(model.calls,calls);self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                        self.assertEqual(oracle.public_stores(model),stores)
                    pairs+=1
        for global_address in (oracle.COUNT,oracle.CONTEXT):
            banks=(global_address-0x15B4,global_address-0x15B4+0x4000)
            with patch.multiple(oracle,BANKS=banks,SEGMENTS=((oracle.COUNT,1),(oracle.CONTEXT,4),
                    (oracle.SEED,8),(oracle.SCALE,4),*((b,0x3000) for b in banks))):
                case=oracle.Case(samples=(0.,0.25));memory=oracle.fixture(case);wanted,calls,stores=oracle.reference(memory,case)
                models=[oracle.WeightModel(w,memory,case,used_offset=off).run() for w,off in
                    ((self.retail,0x50),(self.normalized_words,0x50),(self.words,0x68))]
                self.assertEqual(state(models[0]),state(models[1]));self.assertNotEqual(memory[global_address],wanted[global_address])
                for model in models:
                    self.assertEqual(model.calls,calls);self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                    self.assertEqual(oracle.public_stores(model),stores)
                aliases+=1
        self.receipt('GNU-and-alias',independent_maps=3,rebased_raw_normalized_pairs=pairs,all6_bindings_and_HI_LO_carries=True,
            independently_assembled_retail_bytes_equal=True,completed_global_count_and_pointer_alias_triples=aliases,
            cached_count_and_base_survive_publication=True,aliases_not_native_overlapping_region_claims=True)

    def test_08_real_two_profile_padding_Make_and_complete_image(self):
        out=self.root/integration.BUILD;row=integration.qualify(self.root,out)
        self.assertEqual((row['words'],row['frame']),(189,136))
        integration.make_shadow(self.root,out);self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        values=source.freeze(self.root,out);before=values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+756]
        expected=integration.predicted_image(before,truth);canonical=lambda data:Counter((n,*f[1:]) for _,n,f,_ in symbol_rows(data))
        rows=[r for r in symbol_rows(before) if r[1]==source.FUNCTION];_,name,fields,_=rows[0]
        old=canonical(before);old[(name,*fields[1:])]-=1;old[(name,fields[1],756,*fields[3:])]+=1
        self.assertEqual(canonical(expected),+old)
        for at in (64,elf_slot_offset(before,source.ENTRY,756)+112,len(before)-1,rows[0][0]+4):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'image differs'):integration.check_image(before,bytes(bad),truth)
        guards=(out/'qualified-guards.csv').read_bytes();reader=csv.DictReader(io.StringIO(guards.decode()));rows=list(reader)
        target=next(i for i,r in enumerate(rows) if r['filename']==source.OWNER and r['function']==source.FUNCTION)
        for field,value in (('expected','0xFFFFFFFF'),('expected_relocations','R_MIPS_HI16:D_800D23B0')):
            corrupt=deepcopy(rows);corrupt[target][field]=value;stream=io.StringIO()
            writer=csv.DictWriter(stream,fieldnames=reader.fieldnames);writer.writeheader();writer.writerows(corrupt)
            path=out/('stale-'+field+'.csv');path.write_text(stream.getvalue())
            with self.assertRaises(ValueError):emit_padded_assembly(out/'after-primary.o',self.root/'conker/asm/B3020.s',
                function_objects={'func_150891E8':out/'after-normal.o',source.FUNCTION:out/'after-normal.o'},
                word_patches_path=path,filename=source.OWNER)
        if (self.root/source.SOURCE).read_bytes()!=values[source.SOURCE]:integration.audit(self.root,out)
        self.receipt('image-controls',strict_image_controls=4,real_padder_stale_controls=2,
            only_target_size_changes=True,two_selected_normal_functions_and_all_other_inputs_preserved=True)


if __name__=='__main__':unittest.main()
