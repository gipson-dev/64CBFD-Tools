"""Complete selector recovery; its saved frame/literal lifetimes still need matching."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_sine_selector_candidates as source
from tools.experiments import game_route_projection_integration as mixed
from tools.tests import game_actor_sine_selector_oracle as oracle
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_projected_packet_draw import native_command
from tools.pad_generated_object import emit_padded_assembly
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import load_section


class ActorSineSelectorRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.cases=list(oracle.cases())
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out)
        cls.retail=list(struct.unpack_from('>136I',cls.values['conker/conker.us.bin'],source.ROM))
        cls.sine=list(struct.unpack_from('>104I',cls.values['conker/conker.us.bin'],0x75210))
        cls.connected={oracle.SINE+i*4:w for i,w in enumerate(cls.sine)}

    def receipt(self,name,**row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_measured_matching_boundary_and_frozen_production(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(138,128,77))
        self.assertEqual(self.row['raw_SHA256'],'9b36dd52ce1411f49bae251814c8a252900c479b10c8c7e22e2eed05d14afbc3')
        self.assertFalse(self.row['diagnostics'])
        for name,digest in source.INPUTS.items():self.assertEqual(hashlib.sha256((self.root/name).read_bytes()).hexdigest(),digest,name)
        self.assertIn(source.ORIGINAL,(self.root/source.SOURCE).read_text())
        self.receipt('matching-boundary',raw_words=138,retail_words=136,raw_frame=128,retail_frame=112,
            word_differences=77,installed=False,matching_credit=0)

    def test_02_independent_return_buffers_and_ordered_sine_arguments(self):
        count=0;visits=set()
        for case in self.cases:
            memory=oracle.fixture(case);result,wanted,calls,stores=oracle.reference(memory,case)
            for phase in (0,8):
                for words in (self.retail,self.words):
                    model=oracle.SelectorModel(words,memory,case,phase).run()
                    self.assertEqual(oracle.signed(model.r[2]),result,case)
                    self.assertEqual(oracle.public(model.memory),oracle.public(wanted),case)
                    self.assertEqual(model.calls,[(target,angle) for target,angle,_ in calls],case)
                    writes=[(e[1],e[2],e[3]) for e in model.events if e[0]=='W' and not oracle.STACK-0x500<=e[1]<oracle.STACK+0x100]
                    self.assertEqual(writes,stores)
                    if words is self.retail:visits|=model.visits
                count+=1
        self.receipt('public-semantics',fixtures=len(self.cases),paired_phase_runs=count,
            ordered_helper_arguments_and_full_buffers=True,retail_words_visited=len(visits),
            no_private_stack_or_full_GP_identity_claim=True)

    def test_03_actual_sine_connection_and_leaf_identity(self):
        elf=self.values['conker/build/conker.us.elf'];offset=elf_slot_offset(elf,oracle.SINE,416)
        self.assertEqual(elf[offset:offset+416],self.values['conker/conker.us.bin'][0x75210:0x753B0])
        base,data=load_section(self.root/'conker/build/conker.us.elf','.game_data')
        checked=0
        for address,value in {**oracle.CONSTANTS,**oracle.trig.GLOBALS}.items():
            if base<=address<base+len(data):
                self.assertEqual(struct.unpack_from('>I',data,address-base)[0],value);checked+=1
        count=0;visits=set()
        for case in self.cases:
            if case.mutation or case.answers:continue
            memory=oracle.fixture(case);result,wanted,calls,_=oracle.reference(memory,case)
            for words in (self.retail,self.words):
                model=oracle.SelectorModel(words,memory,case,connected=self.connected).run()
                self.assertEqual(oracle.signed(model.r[2]),result,case)
                self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                self.assertEqual(model.calls,[(target,angle) for target,angle,_ in calls]);visits|=model.visits
            count+=1
        self.assertGreater(len(set(self.connected)&visits),60)
        self.receipt('actual-sine',fixture_pairs=count,original_helper_words=104,
            helper_words_visited=len(set(self.connected)&visits),unchanged_sine_source_SHA256=source.INPUTS['conker/src/libultra/gu/sinf.c'],
            production_sine_all104_words_exact=True,production_game_data_constant_words_checked=checked,
            bounded_clamped_angle_domain=True,not_full_trig_or_FCSR_requalification=True)

    def test_04_native_O0_O2_UBSan_and_effective_negatives(self):
        sine=self.values['conker/src/libultra/gu/sinf.c'].decode()
        def run(name,body,opt,sanitize):
            program=self.out/(name+'.c');exe=program.with_suffix('.exe')
            program.write_text(oracle.native_harness(body,self.cases,sine))
            built=subprocess.run(native_command(opt,sanitize)+['-mstackrealign','-fno-strict-aliasing',str(program),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            return subprocess.run([str(exe)]).returncode
        for name,opt,sanitize in (('native-O0','-O0',False),('native-O2','-O2',False),('native-UBSan','-O2',True)):
            self.assertEqual(run(name,source.SELECTED,opt,sanitize),0,name)
        negatives={
            'tie-last':source.SELECTED.replace('best < score','best <= score'),
            'wrong-state':source.SELECTED.replace('states[i] != 3','states[i] != 2'),
            'wrong-eligibility-bits':source.SELECTED.replace('(bit << 16)','bit'),
            'live-count':source.SELECTED.replace('++i < count','++i < *(s32 *)((u8 *)D_800D23B0 + 0x10)'),
            'live-state-base':source.SELECTED.replace('states[i]','((s32 *)((u8 *)D_800D23B0 + 0xE64))[i]').replace('    s32 *states = (s32 *)(state + 0xE64);\n',''),
            'live-phase':source.SELECTED.replace(' * factor + phase',' * factor + D_8009DA54').replace('    f32 phase;\n','').replace('    phase = D_8009DA54;\n','')}
        for name,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED,name)
            self.assertIn(run('negative-'+name,body,'-O2',False),(21,22,23,24,25,26),name)
        self.receipt('native',profiles=3,fixtures_each=len(self.cases),effective_negatives=len(negatives),
            actual_sine_C_used_for_normal_providers=True,complete_translated_buffers=True)

    def test_05_null_actor_guest_branch_and_nan_score(self):
        # Zero-linked actor storage is a backed guest case, not a native null array.
        anchors={name:int(name[2:],16) if name.startswith('D_') else oracle.SINE for values in self.row['bindings'].values() for _,name in values}
        anchors['D_800CC2D0']=0
        def relocate(words,bindings):
            result=words.copy()
            for offset,values in bindings.items():
                kind,name=values[0];value=anchors[name];i=int(offset)//4
                if kind=='R_MIPS_HI16':result[i]=result[i]&0xFFFF0000|((value+0x8000)>>16)&65535
                elif kind=='R_MIPS_LO16':result[i]=result[i]&0xFFFF0000|value&65535
                elif kind=='R_MIPS_26':result[i]=result[i]&0xFC000000|(value>>2)&0x3FFFFFF
                else:raise AssertionError(kind)
            return result
        raw,bindings=source.payload(self.obj);rebased=relocate(list(struct.unpack('>%dI'%(len(raw)//4),raw)),bindings)
        original=self.retail.copy()
        self.assertEqual(original.count(0x3C12800D),1);self.assertEqual(original.count(0x2652C2D0),1)
        # Both original actor HI/LO words are independently identified in assembly.
        for i,w in enumerate(original):
            if w==0x3C12800D:original[i]=0x3C120000
            elif w==0x2652C2D0:original[i]=0x26520000
        segments=tuple((0,n) if b==oracle.ACTORS else (b,n) for b,n in oracle.SEGMENTS)
        with patch.multiple(oracle,ACTORS=0,SEGMENTS=segments):
            case=oracle.Case(count=1);memory=oracle.fixture(case);result,wanted,calls,_=oracle.reference(memory,case)
            for words in (original,rebased):
                model=oracle.SelectorModel(words,memory,case).run()
                self.assertEqual(oracle.signed(model.r[2]),result);self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                self.assertEqual(model.calls,[(target,angle) for target,angle,_ in calls])
        case=oracle.Case(answers=(float('nan'),.5,.5,-1.));memory=oracle.fixture(case)
        result,wanted,calls,_=oracle.reference(memory,case)
        for words in (self.retail,self.words):
            model=oracle.SelectorModel(words,memory,case).run();self.assertEqual(oracle.signed(model.r[2]),result)
        self.receipt('guest-prefixes',completed_zero_actor_pairs=1,modeled_nan_return_pairs=1,not_native_null_or_FCSR_claim=True)

    def test_06_both_owner_profiles_padding_and_no_installation(self):
        same=mixed.candidate.source.neighbor.same_functions;profiles={}
        for label,normal in (('primary',False),('normal',True)):
            old,diag=source.compile_profile(self.root,self.out,self.values[source.SOURCE].decode(),'before-'+label,normal)
            new,words,row=source.compile_candidate(self.root,self.out,'after-'+label,normal=normal,whole=True)
            self.assertFalse(diag or row['diagnostics']);self.assertEqual(words,self.words)
            self.assertEqual(same(old,new,(source.FUNCTION,)),72);self.assertEqual(normalized_pools(old),normalized_pools(new));profiles[label]=new
        with self.assertRaisesRegex(ValueError,'retail span is only 0x220'):
            mixed.padded(self.root,self.out,profiles['primary'],'oversized-rejected',self.root/'conker/retail_word_patches.us.csv',profiles['normal'])
        assembly=emit_padded_assembly(profiles['primary'],self.root/'conker/asm/B3020.s',
            function_objects={mixed.FUNCTION:profiles['normal'],source.FUNCTION:self.out/'before-primary.o'},
            word_patches_path=self.root/'conker/retail_word_patches.us.csv',filename=source.OWNER)
        path=self.out/'retained-target.s';path.write_text(assembly);padded=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(self.root/'conker/include'),'-o',str(padded),str(path)],check=True,capture_output=True)
        baseline=self.root/'conker/build/src/game/generated_B3020.c.o'
        self.assertEqual(same(baseline,padded,()),73);self.assertEqual(normalized_pools(baseline),normalized_pools(padded))
        _,before=source.link_owner(self.root,self.out,baseline,source.OWNER);image,after=source.link_owner(self.root,self.out,padded,source.OWNER)
        self.assertEqual(before.keys(),after.keys())
        for name in after:self.assertEqual(before[name]['value'],after[name]['value'])
        for name,value in self.values.items():self.assertEqual((self.root/name).read_bytes(),value,name)
        self.receipt('owner-isolation',neighbors_each_profile=72,oversized_target_rejected=True,
            retaining_only_old_target_reproduces_all73_padded_bodies=True,pools_and_all73_addresses_fixed=True,
            production_source_guards_ELF_and_all_frozen_inputs_unchanged=True)

    def test_07_first_private_store_boundary_remains_unmatched(self):
        case=oracle.Case();memory=oracle.fixture(case);models=[]
        for words in (self.retail,self.words):
            model=oracle.SelectorModel(words,memory,case);model.fault=0
            with self.assertRaises(oracle.core.AccessFault):model.run()
            self.assertEqual(model.accesses,0);models.append(model)
        self.assertEqual(models[0].requested,('W',oracle.STACK-4,4))
        self.assertEqual(models[1].requested,('W',oracle.STACK-20,4))
        self.receipt('first-private-cut',fired=True,retail_RA_store=oracle.STACK-4,raw_RA_store=oracle.STACK-20,
            mismatched_by_16_bytes=True,not_patched_or_counted_as_literal_match=True)

    def test_08_actual_returning_caller_and_full_word_slot(self):
        rom=self.values['conker/conker.us.bin'];jal=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
        self.assertEqual([i for i in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==jal],[0xCB968])
        count=0
        for case in self.cases[::11]:
            for words in (self.retail,self.words):
                memory=oracle.fixture(case);packet=oracle.BANKS[1]+0x1700
                oracle.put(memory,packet+8,case.slot,4)
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                connected.update({0x1509E62C+i*4:w for i,w in enumerate(struct.unpack_from('>3I',rom,0xCBADC))})
                model=oracle.SelectorModel(list(struct.unpack_from('>4I',rom,0xCB968)),memory,case,connected=connected,entry=0x1509E4B8)
                model.r[29]=oracle.STACK-24;model.r[6]=packet;oracle.put(model.memory,oracle.STACK-4,0xDEAD0000,4)
                result,_,_,_=oracle.reference(memory,case);model.run()
                self.assertEqual(oracle.signed(model.r[2]),result);self.assertEqual(model.caller_args,[(case.slot,)]);count+=1
        self.receipt('returning-caller',actual_complete_window_runs=count,caller_frame_live_in=24,
            full_word_slot_delay_load=True,all_returns_restore_caller_SP_and_RA=True)

    def test_09_independent_GNU_rebases_and_executed_semantics(self):
        raw,bindings=source.payload(self.obj)
        anchors={name:int(name[2:],16) if name.startswith('D_') else oracle.SINE for values in bindings.values() for _,name in values}
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n');end=asm.index('endlabel '+source.FUNCTION,start)
        prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text();original=self.out/'retail.s'
        original.write_text(prelude+'\n.text\n.type '+source.FUNCTION+', @function\n'+asm[start:end]+'\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>%dI'%(len(raw)//4),raw)):
            if i*4 in bindings:
                kind,name=bindings[i*4][0];mask=0xFC000000 if kind=='R_MIPS_26' else 0xFFFF0000
                lines+=['.word 0x%08X'%(word&mask),'.reloc .-4,%s,%s'%(kind,name)]
            else:lines.append('.word 0x%08X'%word)
        candidate=self.out/'candidate.s';candidate.write_text('\n'.join(lines)+'\n')
        for path in (original,candidate):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(self.root/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        count=0
        for n,(entry,delta) in enumerate(((source.ENTRY,0),(0x1621FFF4,0x118004),(0x18FFF000,0x32FFFC))):
            moved={name:value+delta for name,value in anchors.items()};images=[]
            for path,length in ((original,136),(candidate,138)):
                script=self.out/(path.stem+'-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in moved.items()],'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(list(struct.unpack('>%dI'%length,sections(elf)['.text'][1][:length*4])))
            values=dict(ACTORS=oracle.ACTORS+delta,CONTEXT=oracle.CONTEXT+delta,SINE=oracle.SINE+delta,
                COEFFICIENT=oracle.COEFFICIENT+delta,CONSTANTS={a+delta:v for a,v in oracle.CONSTANTS.items()},
                BANKS=tuple(b+0x40000*(n+1) for b in oracle.BANKS))
            values['SEGMENTS']=tuple((a+(values['BANKS'][i]-a) if i<2 else a+delta if a in (oracle.ACTORS,oracle.CONTEXT,oracle.COEFFICIENT) else a,size)
                for i,(a,size) in enumerate(oracle.SEGMENTS))
            with patch.multiple(oracle,**values):
                for case in [*self.cases[::17],oracle.Case(mutation=2),oracle.Case(mutation=4)]:
                    memory=oracle.fixture(case);result,wanted,calls,_=oracle.reference(memory,case)
                    for words in images:
                        model=oracle.SelectorModel(words,memory,case,entry=entry).run()
                        self.assertEqual(oracle.signed(model.r[2]),result);self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                        self.assertEqual(model.calls,[(target,angle) for target,angle,_ in calls])
                    count+=1
        self.receipt('GNU-rebases',maps=3,executed_public_pairs=count,code_globals_contexts_actors_and_provider_rebased=True,
            code_bytes_and_private_frames_explicitly_still_different=True)


if __name__=='__main__':unittest.main()
