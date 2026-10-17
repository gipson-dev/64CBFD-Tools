"""Full projection, literal bindings, actual tail/private ABI and native controls."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_overlay_projection as source
from tools.tests import game_overlay_projection_oracle as model
from tools.tests import game_overlay_projection_native as native
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_projected_packet_draw import native_command


def state(m):return model.point.state(m),m.packet_snapshots


class OverlayProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>120I',cls.rom,source.ROM))
        cls.helper=list(struct.unpack_from('>58I',cls.rom,0xD4E10))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-projection',
            (cls.out/'before-color_provider_original').read_text(),source.FUNCTION)
        data,functions=source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.emitted=list(struct.unpack_from('>120I',data,functions[source.FUNCTION]['value']))

    def receipt(self,name,**row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_direct120_pool_binding_frame_private_homes_and27_neighbors(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.emitted,self.truth)
        self.assertEqual((self.row['frame'],self.row['unchanged_raw_padded_neighbors'],self.row['guards']),(64,27,0))
        source.checked_parts(*source.parts(self.obj),source.sections(self.obj)['.rodata'][1])
        self.assertEqual(len(source.parts(self.obj)[1]),15)
        elf=(self.out/'before-elf').read_bytes();at=elf_slot_offset(elf,model.LIMITS,12)
        self.assertEqual(elf[at:at+12],source.POOL[:12])
        at=elf_slot_offset(elf,model.point.MATRIX,232)
        self.assertEqual(elf[at:at+232],self.rom[0xD4E10:0xD4EF8])
        self.receipt('direct',words=120,frame=64,new_instruction_guards=0,unchanged_raw_padded_neighbors=27,
            original_literal_bytes_bound=12,unused_alignment_padding_not_installed=4,helper_words=[40,5,13],
            raw_C_and_normal_padder_equal_after_existing_pool_binding=True)

    def test_02_complete_guest_reference_aliases_clamps_nonfinite_and_private_packets(self):
        count=0;seen=set();calls=0
        for memory,args in model.corpus():
            expected,packet,transformed=model.reference(memory,args)
            for phase in (0,8):
                models=[]
                for words in (self.truth,self.words,self.emitted):
                    m=model.ProjectionOracle(words,memory,args,self.helper,phase).run()
                    self.assertEqual(model.point.public(m.memory),model.point.public(expected),(args,phase))
                    self.assertEqual(len(m.calls),int(packet is not None))
                    if packet is not None:
                        sp=model.STACK+phase-64
                        wanted=(*packet,sp+60,sp+56,sp+52,sp+48)
                        self.assertEqual(m.calls,[(model.point.TAIL,wanted)])
                        self.assertEqual(m.packet_snapshots,[(sp,0xDEAD0000,wanted)])
                        self.assertEqual(model.read(m.memory,sp+52),transformed[2])
                        calls+=1
                    self.assertEqual(model.point.TAIL in m.visits,packet is not None)
                    seen.update(m.visits);models.append(m)
                self.assertTrue(state(models[0])==state(models[1])==state(models[2]));count+=1
        missing=set(range(source.ENTRY,source.ENTRY+480,4))-seen
        self.assertEqual(missing,{source.ENTRY+0x190})
        self.assertTrue(set(range(model.point.MATRIX,model.point.MATRIX+232,4))<=seen)
        self.receipt('guest',three_way_cases=count,actual_helper_runs=calls,natural_words=119,retained_dead_compare_offset=0x190,
            all58_matrix_tail_words=True,all_private_memory_register_events_and_call_homes=True,
            output_view_field_aliases_and_distinct_guest_only_pool_limits=True,not_hardware_FP_or_gameplay=True)

    def test_03_independent_original_C_literal_block_HI_LO_and_helper_rebases(self):
        for index,base in enumerate((0x80107FFC,0x80118004,0x80127FD0)):
            anchors={'D_800D9D10':base+0x1000,'D_800BE628':base+0x2000,'D_800DDDE8':base+0x3000,
                'D_800A7280':base,'D_800A7284':base+4,'D_800A7288':base+8,'func_150A7A00':0x15218000+index*0x1000}
            images=[]
            for label,obj in (('original',self.original),('C',self.out/'bound-raw.o')):
                path=self.out/('rebase-%d-%s.ld'%(index,label));elf=path.with_suffix('.elf')
                path.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(path),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
                images.append(source.sections(elf)['.text'][1][:480])
            self.assertEqual(*images)
        self.receipt('rebases',independent_original_links=3,independent_C_links=3,all120_words=True,
            shared_three_word_literal_block_carry_and_changed_R26_helper=True)

    def test_04_all_fired_fault_prefixes_preserve_literal_private_state(self):
        count=0
        for mode,pattern,alias,phase in ((0,0,0,0),(0,2,0,8),(1,0,1,0),(1,0,2,8),(0,4,1,8)):
            memory,args=model.fixture(1,mode,pattern=pattern,alias=alias)
            complete=model.ProjectionOracle(self.truth,memory,args,self.helper,phase).run()
            for fault in range(complete.all_accesses):
                models=[]
                for words in (self.truth,self.words,self.emitted):
                    m=model.ProjectionOracle(words,memory,args,self.helper,phase);m.access_fault=fault
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault);models.append(m)
                self.assertTrue(state(models[0])==state(models[1])==state(models[2]));count+=1
        self.receipt('faults',positively_fired_three_way_prefixes=count,private_point_tail_and_partial_publication=True,
            not_portable_C_fault_or_CP0_acceptance=True)

    def test_05_native32_complete_body_typed_caller_adapter_and_eight_controls(self):
        caller=self.out/'native-caller.c';caller.write_text(native.CALLER)
        helper=self.out/'native-helper.c';helper.write_text(native.HELPER)
        driver=self.out/'native-driver.c';driver.write_text(native.program());exits={}
        forms=[('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[(n,'-O2',b) for n,b in native.controls(source.SELECTED).items()]
        for label,opt,body in forms:
            unit=self.out/('native-'+label+'.c');unit.write_text(native.HEADER+body+'\n');exe=unit.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double','-fno-strict-aliasing',
                *[str(p.relative_to(self.root)) for p in (unit,caller,helper,driver)],'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120);exits[label]=ran.returncode
            self.assertEqual(ran.returncode,0 if label in ('o2','o0') else 22,(label,ran.stderr))
        self.receipt('native',cases_each=sum(1 for _ in native.cases()),exits=exits,UBSan=True,no_fwrapv_or_LTO=True,
            separate_complete_body_typed_caller_semantic_matrix_adapter=True,full_banks_matrices_outputs_canaries=True,
            NaN_class_only_for_changed_float_outputs=True,invalid_indices_private_aliases_and_mutable_literals_guest_only=True)

    def test_06_all120_words16_pool_bytes16_binding_controls_and156_inputs_fail_closed(self):
        raw,bindings=source.parts(self.obj);pool=source.sections(self.obj)['.rodata'][1]
        for i in range(120):
            bad=bytearray(raw);bad[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(bad),bindings,pool)
        for i in range(16):
            bad=bytearray(pool);bad[i]^=1
            with self.assertRaises(ValueError):source.checked_parts(raw,bindings,bytes(bad))
        for at in (*bindings,-4):
            bad=dict(bindings);bad[at]=[('R_MIPS_HI16','wrong')]
            with self.assertRaises(ValueError):source.checked_parts(raw,bad,pool)
        self.assertEqual(len(source.PATHS),156);read=Path.read_bytes
        for relative in source.PATHS.values():
            target=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==target else read(p)):
                with self.assertRaises(ValueError):source.freeze(self.root,self.out)
        source.freeze(self.root,self.out)
        self.receipt('inputs',word_controls=120,pool_byte_controls=16,binding_controls=16,
            protected_input_entries=156,distinct_paths=len(set(source.PATHS.values())),all_fail_closed=True)

    def test_07_actual_eleven_word_caller_packet_and_private_preservation(self):
        entry,join=0x15181914,0x15181940;words=list(struct.unpack_from('>11I',self.rom,entry-0x15000000+0x2D4B0))
        class Join(Exception):pass
        class Code(faults.TrackedCode):
            def __getitem__(self,pc):
                if pc==join:raise Join
                return super().__getitem__(pc)
        count=0
        for view in (0,1,3,-1,0x10001):
            for pattern in (0,1,2,4):
                for phase in (0,8):
                    memory,args=model.fixture(view,pattern=pattern);sp=model.STACK+phase;point=0x22000
                    for i,value in enumerate(args[1:4]):model.put(memory,sp+0xCC-i*4,value)
                    for i,value in enumerate((37.25,-5.5)):model.put(memory,point+i*4,model.bits(value))
                    expected,_,_=model.reference(memory,args);models=[]
                    for target in (self.truth,self.words,self.emitted):
                        code=dict(zip(range(source.ENTRY,source.ENTRY+480,4),target));code[join]=0
                        m=model.ProjectionOracle(words,memory,args,self.helper,phase,entry,code)
                        m.r[17]=point;m.r[18]=view&model.MASK;m.r[8]=0x12345678;m.code=Code(m.code,m)
                        with self.assertRaises(Join):m.run()
                        self.assertEqual(m.calls[0],(source.ENTRY,args));self.assertEqual(model.point.public(m.memory),model.point.public(expected))
                        self.assertEqual(model.read(m.memory,sp+0x74),0x12345678)
                        self.assertEqual([model.read(m.memory,sp+p) for p in (0xC0,0xBC)],[model.bits(37.25),model.bits(-5.5)])
                        models.append(m)
                    self.assertTrue(state(models[0])==state(models[1])==state(models[2]));count+=1
        self.receipt('caller',three_way_packet_cases=count,all11_original_packet_words=True,actual120word_callee_and58word_tail=True,
            caller_private_float_and_word_snapshots_preserved=True,not_full_parent_overlay_acceptance=True)

    def test_08_deferred_pulse_reset_and_indexed_guest_writer_boundary(self):
        from tools.tests import game_pulsed_overlay_oracle as pulse
        code=source.previous.images(self.root,self.out)
        reset=list(struct.unpack_from('>76I',self.rom,0x35F10))
        channel=list(struct.unpack_from('>20I',self.rom,0x1AC938))
        for phase in (0,8):
            for enabled in (0,1,255):
                memory,_=pulse.fixture((self.out/'before-elf').read_bytes(),pulse=enabled,seed=pulse.bits(.25),phase=phase)
                for i in range(0x120):memory.setdefault(0x800DDD40+i,0xA5)
                m=pulse.PulseOracle(reset,memory,(0,),phase,0x15008A60).run()
                self.assertEqual(pulse.read(m.memory,pulse.TIMER,2),0)
                self.assertEqual(pulse.read(m.memory,pulse.PULSE,1),enabled)
            memory,args=pulse.fixture((self.out/'before-elf').read_bytes(),pulse=1,seed=pulse.bits(.25),phase=phase)
            for i in range(0x120):memory.setdefault(0x800DDD40+i,0xA5)
            m=pulse.PulseOracle(channel,memory,(10,20,30,0,99,0xFFFFFFF0),phase,0x1517F488).run()
            self.assertEqual(pulse.read(m.memory,pulse.PULSE,1),0)
            self.assertEqual(pulse.read(m.memory,pulse.TIMER,2),1)
            helper=pulse.helpers(code);helper={pc:w for pc,w in helper.items() if not source.previous.ENTRY<=pc<source.previous.ENTRY+444}
            wrapped=pulse.PulseOracle(code['pulse'],m.memory,args,phase,connected=helper).run()
            self.assertEqual(wrapped.draw_packets[0][2:5],(60,65,100))
            self.assertFalse(wrapped.read_provenance[0][1])
        self.receipt('pulse-writer-boundary',actual_reset76_word_cases=6,actual_channel20_word_alias_cases=2,
            reset_clears_timer_not_pulse=True,index_minus16_aliases_alpha_store_to_pulse_byte=True,
            negative_index_is_guest_only_not_valid_native_or_natural_gameplay=True,
            no_global_pulse_one_precondition_or_defined_C_lifetime_established=True,pulse_source_not_adopted=True)


if __name__=='__main__':unittest.main()
