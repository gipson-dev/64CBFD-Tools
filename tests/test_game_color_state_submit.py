"""Direct match, complete ABI/state/fault qualification and both real caller owners."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_color_state_submit as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_color_state_submit_oracle as model
from tools.tests import game_color_state_submit_native as native
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import game_sequence_event_scan_oracle as scan


def controls(body):
    return dict(unsigned_mode=body.replace('s8 mode','u8 mode'),
        unsigned_state=body.replace('mode != D_800DDDAC[channel]','mode != (u8)D_800DDDAC[channel]'),
        inclusive=body.replace('D_800DDDB0[channel] < D_800DDE28[channel]','D_800DDDB0[channel] <= D_800DDE28[channel]'),
        unsigned_time=body.replace('D_800DDDB0[channel] < D_800DDE28[channel]','(u32)D_800DDDB0[channel] < (u32)D_800DDE28[channel]'),
        ignored_busy=body.replace('D_800DDDC0[channel] != 0','0'),
        wrong_stride=body.replace('channel * 3','channel * 4'),
        wrong_red=body.replace('color[0] = red','color[0] = blue'),
        wrong_alias_order=body.replace('        D_800DDDAC[channel] = mode;\n        D_800DDDC0[channel] = 0;',
            '        D_800DDDC0[channel] = 0;\n        D_800DDDAC[channel] = mode;'))


def state(m):return (m.memory,m.r,m.f,m.lo,m.calls,m.events,m.current_pc,m.delay_of,m.all_accesses)


class ScanReference(scan.Reference):
    def call(self,target,packet,ordinal=None):
        result=super().call(target,packet,ordinal)
        if target==source.ENTRY:model.apply(self.memory,packet,model.GLOBALS)
        return result


class ColorStateSubmitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-color-state',
            (cls.out/'before-color_provider_original').read_text(),source.FUNCTION)
        data,functions=source.build.link_owner(cls.root,cls.out,cls.original,source.OWNER)
        f=functions[source.FUNCTION];cls.truth=list(struct.unpack_from('>48I',data,f['value']))
        data,fs=source.build.link_owner(cls.root,cls.out,cls.out/'color_pair_caller_owner-after-padded.o','generated_1A0100')
        f=fs['func_15172CA8'];cls.caller=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_direct_all48_words_bindings_no_guards_and_89_unchanged_functions(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(self.truth,list(struct.unpack_from('>48I',(self.out/'before-retail_rom').read_bytes(),source.ROM)))
        self.assertEqual(source.parts(self.obj),source.parts(self.original));source.checked_parts(*source.parts(self.obj))
        self.assertEqual(self.row['unchanged_raw_neighbors'],27);self.assertEqual(self.row['unchanged_padded_neighbors'],27)
        self.assertEqual([r['unchanged_raw_functions'] for r in self.row['typed_callers']],[57,5])
        self.assertTrue((self.root/source.PATHS['guards']).read_bytes()==(self.out/'before-guards').read_bytes())
        self.receipt('direct-owner',all48_words_and_16_bindings=True,frame=8,direct=True,guards=0,
            unchanged_owner_neighbors=27,unchanged_scan_caller_functions=57,unchanged_pair_caller_functions=5,
            both_prototypes_use_signed_byte_mode=True,no_private_pools_or_diagnostics=True)

    def test_02_full_state_signed_byte_time_short_circuit_and_six_alias_maps(self):
        count=0;seen=set();changed=set()
        for memory,args,g in model.cases():
            wanted,updated=model.reference(memory,args,g)
            for phase in (0,8):
                machines=[]
                # Rebind aliased globals with the same independently emitted leaf.
                words=self.rebound(g)
                for body in (words[0],words[1]):
                    m=model.ColorOracle(body,memory,args,phase).run()
                    self.assertTrue(model.public(m.memory)==model.public(wanted),(args,g,phase))
                    self.assertEqual(m.calls,[]);seen.update(m.visits);machines.append(m)
                self.assertTrue(state(machines[0])==state(machines[1]),(args,g,phase))
                count+=1;changed.add(updated)
        self.assertEqual(changed,{False,True});self.assertTrue(set(range(source.ENTRY,source.ENTRY+192,4))<=seen)
        self.receipt('direct-guest',paired_cases=count,all48_words=True,full_literal_memory_register_events_PC_delay=True,
            four_fixture_channels=True,signed_byte_mode_and_signed_times=True,six_alias_maps=True,
            arbitrary_argument_padding_guest_only=True,not_hardware_or_rendering_acceptance=True)

    def rebound(self,g):
        key=tuple(g[name] for name in model.NAMES)
        if not hasattr(self.__class__,'rebindings'):self.__class__.rebindings={}
        if key not in self.rebindings:
            text,functions,relocations=source.parse_object(self.obj)
            symbols=dict(zip(model.SYMBOLS,key))
            asm,unresolved=emit_function(text,functions[source.FUNCTION],relocations,source.FUNCTION,symbols)
            self.assertFalse(unresolved);index=len(self.rebindings);path=self.out/('alias-%d.s'%index);path.write_text(asm)
            obj=path.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            images=[]
            for name,source_obj in (('original',self.original),('C',obj)):
                script=self.out/('alias-%d-%s.ld'%(index,name));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(source_obj)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>48I',source.sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[1]);self.rebindings[key]=images
        return self.rebindings[key]

    def test_03_original_C_three_independent_symbol_carry_rebases(self):
        for n in range(3):
            g={name:0x80100000+i*0x10000+(0x7FFC,0x8004,0x7FD0)[n] for i,name in enumerate(model.NAMES)}
            self.assertEqual(*self.rebound(g))
        self.receipt('direct-rebases',independent_original_links=3,independent_C_links=3,all48_words=True,HI_LO_carries=True)

    def test_04_each_original_C_access_fault_prefix_is_literal(self):
        count=0
        for fixture,phase in ((model.fixture(mode=1),0),(model.fixture(times=(0,1)),8),
                (model.fixture(busy=255),0),(model.fixture(),8)):
            memory,args,g=fixture;words=self.rebound(g);full=model.ColorOracle(words[0],memory,args,phase).run()
            for fault in range(full.all_accesses):
                machines=[]
                for body in words:
                    m=model.ColorOracle(body,memory,args,phase);m.access_fault=fault
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault);machines.append(m)
                self.assertTrue(state(machines[0])==state(machines[1]));count+=1
        self.receipt('direct-faults',positively_fired_original_C_prefixes=count,full_literal_state=True,
            emitted_instruction_order_not_portable_C_exception_or_CP0_acceptance=True)

    def test_05_actual32word_pair_caller_and_48word_helper(self):
        count=0;seen=set()
        for channel in range(4):
            for old in (-128,-1,0,1,127):
                for mode in (0,1):
                    memory,args,g=model.fixture(channel,mode,mode,(1,0),0,7,slot_state=old)
                    wanted,calls=model.pair_reference(memory,channel,g);words=self.rebound(g);machines=[]
                    for body in words:
                        helpers=dict(zip(range(source.ENTRY,source.ENTRY+192,4),body))
                        m=model.ColorOracle(self.caller,memory,(channel,),entry=0x15172CA8,helpers=helpers).run()
                        self.assertEqual(model.public(m.memory),model.public(wanted));self.assertEqual(m.calls,calls)
                        seen.update(m.visits);machines.append(m)
                    self.assertTrue(state(machines[0])==state(machines[1]));count+=1
        self.assertEqual(len(self.caller),32)
        self.assertTrue(set(range(0x15172CA8,0x15172D28,4))<=seen)
        self.receipt('direct-pair-caller',original_C_cases=count,actual_caller_words=32,actual_helper_words=48,
            all_caller_words_executed=True,both_signed_mode_packets_and_channel_preserved=True,
            slot_sentinel_gate_and_real_two_call_state_updates=True)

    def test_06_native32_leaf_real_caller_O2_O0_UBSan_and_eight_controls(self):
        before=(self.out/'before-color_pair_caller_owner').read_text();lo,hi=source.build.function_span(before,'func_15172CA8')
        caller_body=before[lo:hi];exits={}
        variants=[('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[(n,'-O2',b) for n,b in controls(source.SELECTED).items()]
        for label,opt,body in variants:
            mode_type='u8' if label=='unsigned_mode' else 's8';header=native.header(mode_type)
            unit=self.out/('native-'+label+'.c');unit.write_text(header+native.MACROS+body+'\n')
            pair=self.out/('native-pair-'+label+'.c');pair.write_text(header+native.MACROS+caller_body+'\n')
            driver=self.out/('native-driver-'+label+'.c');driver.write_text(native.program(mode_type));exe=unit.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double','-fno-strict-aliasing',
                str(unit.relative_to(self.root)),str(pair.relative_to(self.root)),str(driver.relative_to(self.root)),
                '-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120);exits[label]=ran.returncode
            if label in ('o2','o0'):self.assertEqual(ran.returncode,0,(label,ran.stderr))
            else:self.assertEqual(ran.returncode,22,(label,ran.stderr))
        self.receipt('direct-native',cases_each=sum(1 for _ in native.cases()),exits=exits,
            full_leaf_and_actual_pair_caller_separate_units=True,UBSan=True,no_fwrapv=True,
            byte_bank_padding_slot_payload_and_canaries=True,same_width_aliases=True,
            cross_endian_byte_word_aliases_are_guest_only=True,mode_control_prototypes_remain_compatible=True)

    def test_07_all48_words_16_bindings_and_144_production_inputs_fail_closed(self):
        data,bindings=source.parts(self.obj)
        for index in range(48):
            bad=bytearray(data);bad[index*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(bad),bindings)
        for at in (*bindings,-4):
            bad=dict(bindings);bad[at]=[('R_MIPS_HI16','wrong')]
            with self.assertRaises(ValueError):source.checked_parts(data,bad)
        read=Path.read_bytes
        for relative in source.PATHS.values():
            target=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==target else read(p)):
                with self.assertRaises(ValueError):source.freeze(self.root,self.out)
        source.freeze(self.root,self.out)
        self.receipt('direct-inputs',word_controls=48,binding_controls=17,protected_inputs=len(source.PATHS),
            all_inputs_unchanged=True,no_new_word_guards=True)

    def test_08_complete219word_scan_caller_with_actual_C_color_helper(self):
        obj=self.out/'view_list_caller_owner-after-padded.o'
        data,fs=source.build.link_owner(self.root,self.out,obj,'generated_49D30');function=fs['func_1501DAAC']
        words=list(struct.unpack_from('>219I',data,function['value']));count=0
        self.assertEqual(words,list(struct.unpack_from('>219I',(self.out/'before-retail_rom').read_bytes(),0x4AF5C)))
        for slot in (0,1):
            for pattern in (0,3,8):
                for mode in (0,1):
                    for busy in (0,255):
                        memory,args,config=scan.fixture(slot=slot,pattern=pattern)
                        color_memory,_,_=model.fixture(mode=mode,old=mode,times=(1,0),busy=busy)
                        memory.update({at:value for at,value in color_memory.items() if model.BASE<=at<model.BASE+model.LENGTH})
                        expected=ScanReference(memory,args,config).run();machines=[]
                        for body in (self.truth,self.words):
                            helper=dict(zip(range(source.ENTRY,source.ENTRY+192,4),body))
                            m=scan.EventOracle(words,memory,args,config,helpers=helper).run()
                            self.assertEqual(scan.public(m.memory),scan.public(expected.memory));self.assertEqual(m.calls,expected.calls)
                            machines.append(m)
                        self.assertTrue(state(machines[0])==state(machines[1]));count+=1
        self.receipt('direct-scan-caller',paired_cases=count,actual_scan_words=219,actual_C_helper_words=48,
            independent_color_and_scan_reference=True,query_provider_still_bounded=True,
            not_full_sequence_engine_or_rendering_acceptance=True)


if __name__=='__main__':unittest.main()
