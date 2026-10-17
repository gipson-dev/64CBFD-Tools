"""Direct aggregate, live callback/FP behavior, saved lifetime and real chains."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_color_channel_aggregate as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_color_channel_aggregate_oracle as model
from tools.tests import game_color_channel_aggregate_native as native
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset


def controls(body):
    return dict(exclusive_loop=body.replace('channel <= D_80082FA0','channel < D_80082FA0'),
        nonzero_progress=body.replace('func_1517EF00(channel) > 0','func_1517EF00(channel) != 0'),
        nonnegative_float=body.replace('D_800DDDC8[channel] > 0.0f','D_800DDDC8[channel] >= 0.0f'),
        negative_float=body.replace('D_800DDDC8[channel] > 0.0f','D_800DDDC8[channel] < 0.0f'),
        cached_limit=body.replace('s32 active = -1;','s32 active = -1;\n    s32 limit = D_80082FA0;').replace(
            'channel <= D_80082FA0','channel <= limit').replace('active == D_80082FA0','active == limit'),
        wrong_count_origin=body.replace('s32 active = -1;','s32 active = 0;'),
        reversed_result=body.replace('active == D_80082FA0','active != D_80082FA0'),
        missing_float=body.replace('D_800DDDC8[channel] > 0.0f','0'))


def state(m):
    return (m.memory,m.r,m.f,m.lo,m.hi,m.condition,m.calls,m.events,
        m.current_pc,m.delay_of,m.all_accesses,m.role_observations)


class ColorChannelAggregateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-aggregate',
            (cls.out/'before-color_provider_original').read_text(),source.FUNCTION)
        data,functions=source.build.link_owner(cls.root,cls.out,cls.original,source.OWNER)
        f=functions[source.FUNCTION];cls.truth=list(struct.unpack_from('>44I',data,f['value']))
        data,functions=source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        f=functions['func_1517EF00'];cls.helper=list(struct.unpack_from('>43I',data,f['value']))
        cls.helper_truth=list(struct.unpack_from('>43I',(cls.out/'before-retail_rom').read_bytes(),model.progress.source.ROM))
        elf=(cls.out/'before-elf').read_bytes();at=elf_slot_offset(elf,model.CALLER,164)
        cls.caller=list(struct.unpack_from('>41I',elf,at))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def rebound(self,g):
        key=tuple(g[name] for name in model.GLOBALS)
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
                images.append(list(struct.unpack_from('>44I',source.sections(elf)['.text'][1])))
            self.assertEqual(*images);self.rebindings[key]=images
        return self.rebindings[key]

    def helpers(self,body,aggregate=None):
        result=dict(zip(range(model.progress.source.ENTRY,model.progress.source.ENTRY+172,4),body))
        if aggregate is not None:result.update(zip(range(source.ENTRY,source.ENTRY+176,4),aggregate))
        return result

    def test_01_all44_words_five_bindings_frame30_and_27_neighbors(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(self.truth,list(struct.unpack_from('>44I',(self.out/'before-retail_rom').read_bytes(),source.ROM)))
        self.assertEqual(source.parts(self.obj),source.parts(self.original));source.checked_parts(*source.parts(self.obj))
        self.assertEqual(self.row['frame'],0x30);self.assertEqual(self.helper,self.helper_truth)
        self.assertEqual(self.row['unchanged_raw_neighbors'],27);self.assertEqual(self.row['unchanged_padded_neighbors'],27)
        self.assertEqual(self.caller,list(struct.unpack_from('>41I',(self.out/'before-retail_rom').read_bytes(),model.CALLER_ROM)))
        self.assertTrue((self.root/source.PATHS['guards']).read_bytes()==(self.out/'before-guards').read_bytes())
        self.receipt('direct-owner',all44_words_and_five_bindings=True,frame=48,direct=True,guards=0,
            unchanged_raw_padded_neighbors=27,actual_helper_words=43,actual_sequence_gate_words=41,
            no_new_profiles_pools_or_diagnostics=True)

    def test_02_live_limits_FP_aliases_private_lifetime_and_actual43word_helper(self):
        count=0;traps=0;seen=set();helper_seen=set();observations=0;actual_calls=0
        for memory,config,g in model.cases():
            reference=model.Reference(memory,config,g);trap=None;wanted=None
            try:wanted=reference.run()
            except model.progress.DivisionTrap as error:trap=error.code
            words=self.rebound(g)
            for phase in (0,8):
                machines=[]
                for index,body in enumerate(words):
                    helpers=self.helpers((self.helper_truth,self.helper)[index]) if config['actual'] else None
                    m=model.AggregateOracle(body,memory,config,g,phase,helpers=helpers)
                    if trap:
                        with self.assertRaises(model.progress.DivisionTrap) as error:m.run()
                        self.assertEqual(error.exception.code,6);self.assertEqual(m.current_pc,model.progress.source.ENTRY+0x70)
                    else:m.run();self.assertEqual(m.r[2],wanted,(config,g,phase))
                    self.assertEqual(model.public(m.memory),model.public(reference.memory));self.assertEqual(m.calls,reference.calls)
                    for row in m.role_observations:
                        self.assertEqual((row['limit'],row['states'],row['f20'],row['stack']),
                            (g['limit'],g['states'],0,model.STACK+phase-0x30))
                        self.assertEqual(row['saved_pair'],m.saved_f[1]<<32|m.saved_f[0])
                        self.assertEqual(row['saved_gprs'],tuple(m.before[r] for r in (16,17,18,19,31)))
                    if config['actual'] and reference.calls:
                        self.assertIn(g['progress'],m.visits);actual_calls+=1
                    observations+=len(m.role_observations);seen.update(m.visits);helper_seen.update(m.visits);machines.append(m)
                self.assertTrue(state(machines[0])==state(machines[1]));count+=1;traps+=bool(trap)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+176,4))<=seen)
        self.assertEqual(set(range(model.progress.source.ENTRY,model.progress.source.ENTRY+172,4))-helper_seen,
            {model.progress.source.ENTRY+0x58})
        self.assertGreater(actual_calls,0);self.assertGreater(traps,0)
        self.receipt('direct-guest',paired_cases=count,overflow_traps=traps,all44_aggregate_words=True,
            actual_progress_words_reached=42,helper_break7_still_unreachable=True,
            saved_S0_S1_S2_S3_RA_and_F20_F21_pair=True,role_observations=observations,
            live_signed_limit_and_strict_FP_comparison=True,three_alias_maps=True,
            literal_full_private_state_and_access_events=True,actual_helper_entry_fired=True,
            not_hardware_FCSR_CP0_or_portable_exception_acceptance=True)

    def test_03_original_C_three_independent_HI_LO_and_call_rebases(self):
        for n,low in enumerate((0x7FFC,0x8004,0x7FD0)):
            g=dict(limit=0x80100000+low,states=0x80110000+low,progress=0x15100000+n*0x10000+4)
            self.assertEqual(*self.rebound(g))
        self.receipt('direct-rebases',independent_original_links=3,independent_C_links=3,all44_words=True,
            HI_LO_carries_and_R26_calls=True)

    def test_04_every_fired_data_fault_prefix_in_real_aggregate_progress_chain(self):
        count=0
        fixtures=(model.fixture(-1,actual=True),model.fixture(0,2,1,actual=True),
            model.fixture(3,3,3,actual=True),model.fixture(0,6,0,actual=True))
        for phase,fixture in enumerate(fixtures):
            phase=(phase&1)*8;memory,config,g=fixture
            full=model.AggregateOracle(self.truth,memory,config,g,phase,helpers=self.helpers(self.helper_truth))
            try:full.run()
            except model.progress.DivisionTrap as error:self.assertEqual(error.code,6)
            for fault in range(full.all_accesses):
                machines=[]
                for body,helper in ((self.truth,self.helper_truth),(self.words,self.helper)):
                    m=model.AggregateOracle(body,memory,config,g,phase,helpers=self.helpers(helper));m.access_fault=fault
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault);machines.append(m)
                self.assertTrue(state(machines[0])==state(machines[1]));count+=1
        self.receipt('direct-faults',positively_fired_original_C_data_prefixes=count,
            actual_aggregate_and_progress_code=True,literal_full_private_state=True,
            emitted_order_not_portable_C_fault_or_CP0_acceptance=True)

    def test_05_complete41word_sequence_gate_44word_aggregate_43word_progress(self):
        count=0;traps=0;seen=set();calls=0
        for memory,config,g in model.script_cases():
            reference=model.ScriptReference(memory,config,g);trap=None
            try:reference.run()
            except model.progress.DivisionTrap as error:trap=error.code
            for phase in (0,8):
                machines=[]
                for aggregate,helper in ((self.truth,self.helper_truth),(self.words,self.helper)):
                    m=model.AggregateOracle(self.caller,memory,config,g,phase,entry=model.CALLER,
                        helpers=self.helpers(helper,aggregate))
                    if trap:
                        with self.assertRaises(model.progress.DivisionTrap) as error:m.run()
                        self.assertEqual(error.exception.code,6)
                    else:m.run()
                    self.assertEqual(model.public(m.memory),model.public(reference.memory));self.assertEqual(m.calls,reference.calls)
                    self.assertEqual(source.ENTRY in m.visits,model.read(memory,0x800E0B94,1)!=8)
                    self.assertEqual(model.progress.source.ENTRY in m.visits,any(target==g['progress'] for target,_ in reference.calls))
                    calls+=sum(target==g['progress'] for target,_ in reference.calls);seen.update(m.visits);machines.append(m)
                self.assertTrue(state(machines[0])==state(machines[1]));count+=1;traps+=bool(trap)
        self.assertTrue(set(range(model.CALLER,model.CALLER+164,4))<=seen)
        self.receipt('direct-sequence-gate',paired_cases=count,overflow_traps=traps,actual_caller_words=41,
            actual_aggregate_words=44,actual_progress_words=43,all_caller_words_executed=True,
            aggregate_and_helper_entries_checked_for_fired_and_skipped_paths=True,
            independent_phase_timer_transition_reference=True,no_opaque_provider_in_chain=True,
            helper_calls_observed=calls,not_full_gameplay_acceptance=True)

    def test_06_native32_full_aggregate_progress_and_sequence_gate_O2_O0_UBSan(self):
        text=(self.out/'before-aggregate_caller_owner').read_text();lo,hi=source.build.function_span(text,'func_151E8214')
        caller=self.out/'native-sequence.c';caller.write_text(native.HEADER+native.MACROS+text[lo:hi]+'\n')
        helper=self.out/'native-progress.c';helper.write_text(native.HEADER+native.MACROS+
            source.previous.SELECTED.replace('func_1517EF00(','actual_progress(',1)+'\n')
        driver=self.out/'native-driver.c';driver.write_text(native.program());exits={}
        variants=[('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[(n,'-O2',b) for n,b in controls(source.SELECTED).items()]
        for label,opt,body in variants:
            unit=self.out/('native-'+label+'.c');unit.write_text(native.HEADER+native.MACROS+body+'\n');exe=unit.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double','-fno-strict-aliasing',
                *[str(p.relative_to(self.root)) for p in (unit,helper,caller,driver)],'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120);exits[label]=ran.returncode
            self.assertEqual(ran.returncode,0 if label in ('o2','o0') else 22,(label,ran.stderr))
        self.receipt('direct-native',cases_each=sum(1 for _ in native.cases()),exits=exits,UBSan=True,no_fwrapv_or_LTO=True,
            full_aggregate_progress_and_sequence_caller_separate_units=True,
            dispatcher_selects_actual_compiled_progress_or_bounded_mutating_provider=True,
            complete_bank_limit_script_fields_padding_and_canaries=True,
            live_limits_FP_NaNs_subnormals_and_word_aliases=True,
            overflow_division_guest_only_not_hardware_FCSR_acceptance=True)

    def test_07_all44_words_five_bindings_and_148_inputs_fail_closed(self):
        data,bindings=source.parts(self.obj)
        for index in range(44):
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
        self.receipt('direct-inputs',word_controls=44,binding_controls=6,protected_inputs=len(source.PATHS),all_inputs_unchanged=True)


if __name__=='__main__':unittest.main()
