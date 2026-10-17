"""Direct signed-progress recovery, fault/trap boundaries and real caller chains."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_color_progress as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_color_progress_oracle as model
from tools.tests import game_color_progress_native as native
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset


def controls(body):
    return dict(ignored_busy=body.replace('D_800DDDC0[channel] != 0','0'),
        boolean_busy=body.replace('progress = D_800DDDC0[channel];','progress = D_800DDDC0[channel] != 0;'),
        unsigned_division=body.replace('(s32)((u32)D_800DDDB0[channel] * 255U) / D_800DDE28[channel]',
            '(s32)(((u32)D_800DDDB0[channel] * 255U) / (u32)D_800DDE28[channel])'),
        wrong_scale=body.replace('* 255U','* 254U'),
        missing_upper_clamp=body.replace('if (progress > 255)','if (0)'),
        invented_lower_clamp=body.replace('if (progress > 255)', 'if (progress < 0) { progress = 0; }\n            if (progress > 255)'),
        reversed_mode=body.replace('D_800DDDAC[channel] == 0','D_800DDDAC[channel] != 0'),
        narrowed_return=body.replace('return progress;','return (u8)progress;'))


def state(m):
    return (m.memory,m.r,m.f,m.lo,m.hi,m.calls,m.events,m.current_pc,m.delay_of,m.all_accesses)


class ColorProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-progress',
            (cls.out/'before-color_provider_original').read_text(),source.FUNCTION)
        data,functions=source.build.link_owner(cls.root,cls.out,cls.original,source.OWNER)
        f=functions[source.FUNCTION];cls.truth=list(struct.unpack_from('>43I',data,f['value']))
        data,functions=source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.callers={}
        for name in ('func_1517EFAC','func_1517F3A0'):
            f=functions[name];cls.callers[name]=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def rebound(self,g):
        key=tuple(g[name] for name in model.NAMES)
        if not hasattr(self.__class__,'rebindings'):self.__class__.rebindings={}
        if key not in self.rebindings:
            text,functions,relocations=source.parse_object(self.obj);symbols=dict(zip(model.SYMBOLS,key))
            asm,unresolved=emit_function(text,functions[source.FUNCTION],relocations,source.FUNCTION,symbols)
            self.assertFalse(unresolved);index=len(self.rebindings);path=self.out/('alias-%d.s'%index);path.write_text(asm)
            obj=path.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            images=[]
            for name,source_obj in (('original',self.original),('C',obj)):
                script=self.out/('alias-%d-%s.ld'%(index,name));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(source_obj)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>43I',source.sections(elf)['.text'][1])))
            self.assertEqual(*images);self.rebindings[key]=images
        return self.rebindings[key]

    def test_01_all43_words_eight_bindings_and_27_raw_padded_neighbors(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(self.truth,list(struct.unpack_from('>43I',(self.out/'before-retail_rom').read_bytes(),source.ROM)))
        self.assertEqual(source.parts(self.obj),source.parts(self.original));source.checked_parts(*source.parts(self.obj))
        self.assertEqual(self.row['unchanged_raw_neighbors'],27);self.assertEqual(self.row['unchanged_padded_neighbors'],27)
        self.assertEqual([len(w) for w in self.callers.values()],[12,27])
        self.assertTrue((self.root/source.PATHS['guards']).read_bytes()==(self.out/'before-guards').read_bytes())
        self.receipt('direct-owner',all43_words_and_eight_bindings=True,frame=0,direct=True,guards=0,
            unchanged_raw_padded_neighbors=27,actual_local_callers_words=[12,27],no_new_profiles_pools_or_diagnostics=True)

    def test_02_signed_wrapped_division_mode_busy_and_five_alias_maps(self):
        count=0;traps=0;seen=set();returns=set()
        for memory,args,g in model.cases():
            wanted,trap=model.reference(memory,args[0],g);words=self.rebound(g)
            for phase in (0,8):
                machines=[]
                for body in words:
                    m=model.ProgressOracle(body,memory,args,phase)
                    if trap:
                        with self.assertRaises(model.DivisionTrap) as failure:m.run()
                        self.assertEqual(failure.exception.code,6);self.assertEqual(m.current_pc,source.ENTRY+0x70)
                    else:
                        m.run();self.assertEqual(m.r[2],wanted,(args,g));returns.add(model.signed(wanted))
                    self.assertEqual(m.memory,memory);self.assertEqual(m.calls,[]);seen.update(m.visits);machines.append(m)
                self.assertTrue(state(machines[0])==state(machines[1]));count+=1;traps+=bool(trap)
        all_words=set(range(source.ENTRY,source.ENTRY+172,4))
        self.assertEqual(all_words-seen,{source.ENTRY+0x58})
        self.assertTrue(any(x<0 for x in returns));self.assertTrue(any(x>255 for x in returns));self.assertGreater(traps,0)
        self.receipt('direct-guest',paired_cases=count,overflow_traps=traps,natural_words_reached=42,
            all43_words_exact=True,break7_unreachable_due_to_duration_gate=True,
            full_literal_memory_GPR_FPR_HI_LO_calls_PC_delay_access_state=True,
            five_global_alias_maps=True,sparse_wrapped_indices_guest_only=True,
            emitted_division_trap_not_CP0_or_portable_C_exception_acceptance=True)

    def test_03_original_C_three_independent_symbol_carry_rebases(self):
        for n in range(3):
            g={name:0x80100000+i*0x10000+(0x7FFC,0x8004,0x7FD0)[n] for i,name in enumerate(model.NAMES)}
            self.assertEqual(*self.rebound(g))
        self.receipt('direct-rebases',independent_original_links=3,independent_C_links=3,all43_words=True,HI_LO_carries=True)

    def test_04_each_access_fault_prefix_and_signed_overflow_prefix_is_literal(self):
        count=0
        for fixture,phase in ((model.fixture(busy=255),0),(model.fixture(),8),
                (model.fixture(ticks=-1,duration=1),0),(model.fixture(ticks=-0x80000000,duration=-1),8)):
            memory,args,g=fixture;words=self.rebound(g);full=model.ProgressOracle(words[0],memory,args,phase)
            try:full.run()
            except model.DivisionTrap as error:self.assertEqual(error.code,6)
            for fault in range(full.all_accesses):
                machines=[]
                for body in words:
                    m=model.ProgressOracle(body,memory,args,phase);m.access_fault=fault
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault);machines.append(m)
                self.assertTrue(state(machines[0])==state(machines[1]));count+=1
        self.receipt('direct-faults',positively_fired_original_C_prefixes=count,full_literal_state=True,
            emitted_instruction_order_not_portable_C_exception_or_CP0_acceptance=True)

    def test_05_both_complete_local_callers_and_actual_progress_helper(self):
        count=0;seen=set()
        for channel in range(4):
            for ticks,duration in native.PAIRS:
                for mode in (0,1,127):
                    for busy in (0,255):
                        memory,args,g=model.fixture(channel,ticks,duration,mode,busy);wanted,trap=model.reference(memory,channel)
                        self.assertIsNone(trap)
                        for name,caller in self.callers.items():
                            entry=int(name[5:],16);machines=[]
                            for body in (self.truth,self.words):
                                helper=dict(zip(range(source.ENTRY,source.ENTRY+172,4),body))
                                arguments=(channel,) if entry==0x1517EFAC else (0x12345678,channel)
                                m=model.ProgressOracle(caller,memory,arguments,entry=entry,helpers=helper).run()
                                self.assertIn(source.ENTRY,m.visits)
                                result=int(wanted==255) if entry==0x1517EFAC else 0x13579BDF if wanted else 0x12345678
                                calls=[(source.ENTRY,(channel,))]
                                if entry==0x1517F3A0 and wanted:
                                    rgb=tuple(memory[model.previous.GLOBALS['colors']+channel*3+i] for i in range(3))
                                    calls.append((model.RENDER,(0x12345678,wanted,*rgb,channel)))
                                self.assertEqual(m.r[2],result);self.assertEqual(m.calls,calls)
                                self.assertEqual(model.public(m.memory),model.public(memory));seen.update(m.visits);machines.append(m)
                            self.assertTrue(state(machines[0])==state(machines[1]));count+=1
        for name,words in self.callers.items():
            entry=int(name[5:],16);self.assertTrue(set(range(entry,entry+len(words)*4,4))<=seen)
        self.receipt('direct-local-callers',paired_cases=count,caller_words=[12,27],all_local_caller_words_executed=True,
            actual43word_helper=True,helper_entry_fired_each_case=True,
            signed_return_and_RGB_packets=True,renderer_provider_still_bounded=True)

    def test_06_native32_leaf_two_real_wrappers_O2_O0_UBSan_and_eight_controls(self):
        before=(self.out/'before-color_owner').read_text();bodies=[];exits={}
        for name in self.callers:
            lo,hi=source.build.function_span(before,name);bodies.append(before[lo:hi])
        variants=[('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[(n,'-O2',b) for n,b in controls(source.SELECTED).items()]
        for label,opt,body in variants:
            unit=self.out/('native-'+label+'.c');unit.write_text(native.HEADER+native.MACROS+body+'\n')
            callers=self.out/('native-callers-'+label+'.c');callers.write_text(native.HEADER+native.MACROS+'\n'.join(bodies)+'\n')
            driver=self.out/('native-driver-'+label+'.c');driver.write_text(native.program());exe=unit.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double','-fno-strict-aliasing',
                str(unit.relative_to(self.root)),str(callers.relative_to(self.root)),str(driver.relative_to(self.root)),
                '-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120);exits[label]=ran.returncode
            self.assertEqual(ran.returncode,0 if label in ('o2','o0') else 22,(label,ran.stderr))
        self.receipt('direct-native',cases_each=sum(1 for _ in native.cases()),calls_each_case=3,exits=exits,
            full_leaf_and_two_actual_callers_separate_units=True,UBSan=True,no_fwrapv=True,
            native_division_overflow_excluded_and_guest_trap_tested=True,
            full_byte_bank_canaries_and_render_packets=True,same_width_aliases=True,
            cross_endian_aliases_and_sparse_indices_guest_only=True)

    def test_07_all43_words_eight_bindings_and_146_inputs_fail_closed(self):
        data,bindings=source.parts(self.obj)
        for index in range(43):
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
        self.receipt('direct-inputs',word_controls=43,binding_controls=9,protected_inputs=len(source.PATHS),all_inputs_unchanged=True)

    def test_08_complete111word_registration_caller_with_actual_C_progress(self):
        count=0;caller_entry=0x151D8868;elf=(self.out/'before-elf').read_bytes()
        at=elf_slot_offset(elf,caller_entry,444);caller=list(struct.unpack_from('>111I',elf,at))
        self.assertEqual(caller,list(struct.unpack_from('>111I',(self.out/'before-retail_rom').read_bytes(),0x205D18)))
        registration=model.registration
        for channel in range(4):
            for ticks,duration,mode,busy in ((0,0,0,0),(0,0,1,0),(-1,1,1,0),(1,1,1,0),(0,1,1,0),(0,0,0,255)):
                memory=registration.fixture(mask=1<<channel);color,args,g=model.fixture(channel,ticks,duration,mode,busy)
                memory.update({at:value for at,value in color.items() if model.BASE<=at<model.BASE+model.LENGTH})
                arguments=(registration.OWNER,16,128,0x11223344);config=registration.settings()
                for phase in (0,8):
                    reference=model.RegistrationReference(memory,arguments,config,phase);wanted=reference.run();machines=[]
                    for body in (self.truth,self.words):
                        helper=dict(zip(range(source.ENTRY,source.ENTRY+172,4),body))
                        m=model.RegistrationOracle(caller,memory,arguments,config,phase,connected=helper).run()
                        self.assertIn(source.ENTRY,m.visits)
                        self.assertEqual(m.r[2],wanted);self.assertEqual(m.calls,reference.calls)
                        self.assertEqual(registration.public(m.memory),registration.public(reference.memory));machines.append(m)
                    self.assertEqual((machines[0].memory,machines[0].r,machines[0].f,machines[0].hi,machines[0].lo,machines[0].events),
                        (machines[1].memory,machines[1].r,machines[1].f,machines[1].hi,machines[1].lo,machines[1].events));count+=1
        self.receipt('direct-registration-caller',paired_cases=count,actual_caller_words=111,actual_helper_words=43,
            helper_entry_fired_each_case=True,independent_composed_reference=True,
            other_providers_still_bounded=True,not_full_gameplay_acceptance=True)


if __name__=='__main__':unittest.main()
