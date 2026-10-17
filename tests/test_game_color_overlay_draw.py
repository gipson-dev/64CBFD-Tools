"""Direct SDK match, complete conversion paths, alias ordering and five callers."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_color_overlay_draw as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_color_overlay_draw_oracle as model
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import game_color_overlay_draw_native as native
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments import game_color_progress as progress_source


def state(m):
    return m.memory,m.r,m.f,m.lo,m.hi,m.fcsr,m.condition,m.calls,m.events,m.current_pc,m.delay_of,m.all_accesses,m.conversions,m.call_controls


class ColorOverlayDrawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-overlay',
            (cls.out/'before-color_provider_original').read_text(),source.FUNCTION)
        data,functions=source.build.link_owner(cls.root,cls.out,cls.original,source.OWNER)
        cls.truth=list(struct.unpack_from('>197I',data,functions[source.FUNCTION]['value']))
        cls.callers={};cls.caller_sources={}
        for obj,owner,key in ((cls.padded,source.OWNER,'color_owner'),
                *[(cls.out/(key+'-after-padded.o'),owner,key) for key,owner,_ in source.CALLERS]):
            data,functions=source.build.link_owner(cls.root,cls.out,obj,owner)
            for name,entry,words in model.CALLERS:
                if name in functions:
                    cls.callers[name]=list(struct.unpack_from('>%dI'%words,data,functions[name]['value']))
                    cls.caller_sources[name]=key
            if owner==source.OWNER:
                cls.progress=list(struct.unpack_from('>43I',data,functions['func_1517EF00']['value']))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_direct197_words_two_bindings_typed_ABI_and_38_unchanged_functions(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(self.truth,list(struct.unpack_from('>197I',(self.out/'before-retail_rom').read_bytes(),source.ROM)))
        self.assertEqual(source.parts(self.obj),source.parts(self.original));source.checked_parts(*source.parts(self.obj))
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],27)
        self.assertEqual([r['unchanged_raw_padded_functions'] for r in self.row['typed_callers']],[4,7])
        self.assertEqual(len(self.callers),5)
        for name,entry,words in model.CALLERS:
            self.assertEqual(self.callers[name],list(struct.unpack_from('>%dI'%words,(self.out/'before-retail_rom').read_bytes(),entry-0x15000000+0x2D4B0)),name)
        self.receipt('direct-owner',all197_words_and_two_bindings=True,direct=True,frame=0,guards=0,
            unchanged_raw_padded_functions=38,five_typed_callers_byte_identical=True)

    def test_02_full_packets_unsigned_paths_live_aliases_homes_and_FCSR_restore(self):
        seen=set();count=0;paths=set()
        for memory,args,phase in model.cases():
            wanted,result,valid,coords=model.reference(memory,args,phase)
            for fcsr in model.FCSRS:
                machines=[]
                for body in (self.truth,self.words):
                    m=model.OverlayOracle(body,memory,args,phase,fcsr).run()
                    self.assertEqual(model.public(m.memory),model.public(wanted),(args,phase))
                    self.assertEqual(m.r[2],result);self.assertEqual(m.fcsr,fcsr);self.assertEqual(m.calls,[])
                    seen.update(m.visits);paths.add(len(m.conversions));machines.append(m)
                self.assertTrue(state(machines[0])==state(machines[1]));count+=1
        missing=set(range(source.ENTRY,source.ENTRY+788,4))-seen
        self.assertEqual(missing,{source.ENTRY+offset for offset in (0x12C,0x1C0,0x25C,0x2E8)})
        self.assertTrue({4,8}<=paths)
        self.receipt('direct-guest',paired_cases=count,natural_words=193,unreachable_duplicate_MFC1_words=4,
            entire197_word_object_gate=True,all40_packet_bytes_cursor_and_memory=True,
            unsigned_fallback_and_negative_fraction_paths=True,live_pointer_and_coordinate_aliases=True,
            incoming_stack_home_overwrites_guest_only=True,all_four_initial_control_seeds_restored=True,
            scoped_invalid_flag_model_not_hardware_FCSR_trap_or_MMIO_acceptance=True)

    def test_03_three_independent_original_C_symbol_carry_rebases(self):
        text,functions,relocations=source.parse_object(self.obj)
        for index,address in enumerate((0x80107FFC,0x80118004,0x80127FD0)):
            asm,unresolved=emit_function(text,functions[source.FUNCTION],relocations,source.FUNCTION,{'D_800BE628':address})
            self.assertFalse(unresolved);path=self.out/('rebase-%d.s'%index);path.write_text(asm);obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            images=[]
            for label,input_obj in (('original',self.original),('C',obj)):
                script=self.out/('rebase-%d-%s.ld'%(index,label));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=D_800BE628=0x%X'%address,'-o',str(elf),str(input_obj)],capture_output=True,check=True)
                images.append(source.sections(elf)['.text'][1][:788])
            self.assertEqual(*images)
        self.receipt('direct-rebases',original_links=3,C_links=3,all197_words=True,HI_LO_carry_boundaries=True)

    def test_04_literal_fault_prefixes_include_partial_packets_and_control_state(self):
        count=0
        for alias,coords,phase in ((0,0,0),(0,5,8),(5,0,0),(6,0,8),(10,0,0)):
            memory,args=model.fixture(1,coords,3,alias,phase)
            full=model.OverlayOracle(self.truth,memory,args,phase,0x800003).run()
            for fault in range(full.all_accesses):
                machines=[]
                for body in (self.truth,self.words):
                    m=model.OverlayOracle(body,memory,args,phase,0x800003);m.access_fault=fault
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault);machines.append(m)
                self.assertTrue(state(machines[0])==state(machines[1]));count+=1
        self.receipt('direct-faults',positively_fired_pairs=count,literal_private_and_control_state=True,
            partial_packets_and_temporary_conversion_controls=True,not_CP0_or_portable_C_faults=True)

    def test_05_all_five_complete_callers_and_actual43word_progress_chain(self):
        count=0;seen=set();zero_alpha_calls=0
        for kind,(name,entry,words) in enumerate(model.CALLERS):
            for channel in range(4):
                for variant in range(6):
                    for coords in (0,2,4):
                        memory,args=model.caller_fixture(kind,channel,variant,coords)
                        wanted,result,calls,packet=model.caller_reference(memory,args,kind)
                        for phase in (0,8):
                            machines=[]
                            for body in (self.truth,self.words):
                                helpers=dict(zip(range(source.ENTRY,source.ENTRY+788,4),body))
                                helpers.update(zip(range(model.progress.source.ENTRY,model.progress.source.ENTRY+172,4),self.progress))
                                m=model.OverlayOracle(self.callers[name],memory,args,phase,3,entry=entry,helpers=helpers).run()
                                self.assertEqual(m.r[2],result);self.assertEqual(m.calls,calls,(name,args))
                                self.assertEqual(model.public(m.memory),model.public(wanted))
                                self.assertEqual(source.ENTRY in m.visits,packet is not None)
                                if kind==0:self.assertIn(model.progress.source.ENTRY,m.visits)
                                seen.update(m.visits);machines.append(m)
                            self.assertTrue(state(machines[0])==state(machines[1]));count+=1
                            if packet is not None and packet[1]==0:zero_alpha_calls+=1
        for name,entry,words in model.CALLERS:self.assertTrue(set(range(entry,entry+words*4,4))<=seen,name)
        self.assertGreater(zero_alpha_calls,0)
        self.receipt('direct-callers',paired_cases=count,caller_words=[r[2] for r in model.CALLERS],
            all_caller_words_executed=True,actual197_word_leaf_and_43_word_progress=True,
            zero_alpha_emission_pairs=zero_alpha_calls,helper_entries_fired_or_skipped_as_expected=True,
            complete_packets_and_returned_cursor=True,not_full_renderer_or_gameplay_acceptance=True)


    def test_06_actual_native32_SDK_leaf_five_callers_progress_O2_O0_and_eight_controls(self):
        header=native.HEADER;caller_text=[]
        for name,_,_ in model.CALLERS:
            key=self.caller_sources[name];before=(self.out/('before-'+key)).read_text()
            after=source.recovered_owner(before) if key=='color_owner' else source.recovered_caller(before)
            lo,hi=source.build.function_span(after,name);caller_text.append(after[lo:hi])
        callers=self.out/'native-callers.c';callers.write_text(header+'\n'.join(caller_text)+'\n')
        helper=self.out/'native-progress.c';helper.write_text(header+progress_source.SELECTED+'\n')
        driver=self.out/'native-driver.c';driver.write_text(native.program());exits={}
        variants=[('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[(n,'-O2',b) for n,b in native.controls(source.SELECTED).items()]
        for label,opt,body in variants:
            unit=self.out/('native-'+label+'.c');unit.write_text(header+source.DECLARATIONS+body+'\n');exe=unit.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double','-fno-strict-aliasing',
                *[str(p.relative_to(self.root)) for p in (unit,callers,helper,driver)],'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120);exits[label]=ran.returncode
            self.assertEqual(ran.returncode,0 if label in ('o2','o0') else 22,(label,ran.stderr))
        self.receipt('direct-native',cases_each=sum(1 for _ in native.cases()),exits=exits,UBSan=True,no_fwrapv_or_LTO=True,
            actual_SDK_typed_leaf_all_five_callers_and_progress_body=True,separate_units=True,
            entire_output_views_colors_packet_padding_and_canaries=True,
            finite_defined_unsigned_casts_and_aligned_output_only=True,
            pointer_redirections_private_homes_and_invalid_float_aliases_guest_only=True)

    def test_07_all197_words_two_bindings_and_152_inputs_fail_closed(self):
        data,bindings=source.parts(self.obj)
        for index in range(197):
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
        self.receipt('direct-inputs',word_controls=197,binding_controls=3,protected_inputs=len(source.PATHS),all_inputs_unchanged=True)

    def test_08_missing_final_control_restore_is_an_effective_emitted_negative(self):
        memory,args=model.fixture();bad=list(self.words);self.assertEqual(bad[0x300//4],0x44CDF800);bad[0x300//4]=0
        with self.assertRaisesRegex(AssertionError,'control state leaked'):
            model.OverlayOracle(bad,memory,args,fcsr=3).run()
        self.receipt('direct-control-negative',missing_final_CTC1_positive=True,nondefault_initial_control=3,
            bounded_control_model_not_hardware_traps=True)


if __name__=='__main__':unittest.main()
