"""Complete scan semantics, all word coverage, live provider state and raw neighbors."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_sequence_event_scan as source
from tools.experiments.game_sequence_state_reset_match import original
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests import game_sequence_event_scan_oracle as model
from tools.tests import game_sequence_event_scan_native as native
from tools.tests.test_game_projected_packet_draw import native_command


def controls(body):
    return dict(narrow_best=body.replace('    s32 best;','    s16 best;'),
        narrow_value=body.replace('    s32 value;','    s16 value;'),
        stale_count=body.replace('    s32 index;','    s32 index;\n    s32 cachedCount;').replace(
            '    index = 0;','    index = 0;\n    cachedCount = *count;').replace('index < *count','index < cachedCount'),
        stale_commands=body.replace('commands, 5, index, &event, 1, 0x0E','(u8 *)*record + 0x18, 5, index, &event, 1, 0x0E'),
        wrong_flag=body.replace('if (event != NULL) D_800C35AA = 1','if (event != NULL) D_800C35A9 = 1'),
        unsigned_index=body.replace('event->colorIndex','(u8)event->colorIndex'),
        signed_output=body.replace('(u16)D_800C3C8E','(s16)D_800C3C8E'),
        wrong_filter=body.replace('&event, 1, 1, 1, 0','&event, 1, 1, 0, 0'))


class SequenceEventScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]; cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.row=source.measure(cls.root,cls.out,'selected',source.SELECTED)
        cls.original=original(cls.root,cls.out,'original-event-scan',source.FUNCTION)
        data,functions=source.build.link_owner(cls.root,cls.out,cls.original,source.OWNER)
        f=functions[source.FUNCTION]; cls.truth=list(struct.unpack_from('>219I',data,f['value']))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_complete_original_ROM_and_56_raw_neighbors_frame_homes_and_no_pools(self):
        self.assertEqual(self.truth,list(struct.unpack_from('>219I',(self.out/'before-retail_rom').read_bytes(),source.ROM)))
        self.assertEqual(self.row['diagnostics'],''); self.assertFalse(self.row['pools'])
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(219,128,77))
        self.assertEqual(self.row['raw_sha256'],'887e373590a5a49348a3264073762e84372b897230e37fd67ca26f240683e8c0')
        old,diagnostics=source.compile_owner(self.root,self.out,(self.out/'before-view_list_caller_owner').read_text(),'neighbor-before',True)
        self.assertEqual(diagnostics,''); self.assertEqual(same_functions(old,self.obj,(source.FUNCTION,)),56)
        self.assertEqual(self.words[40],0x27B20074)
        self.assertIn(0xAFA20068,self.words)
        self.receipt('recovered-owner',raw_words=219,frame=128,event_home=116,count_home=104,
            linked_differences=77,unchanged_raw_neighbors=56,not_installed=True,no_matching_credit=True)

    def test_02_full_original_C_cases_all_words_outputs_calls_and_live_provider_gates(self):
        count=0; seen=[set(),set()]; fired=set()
        for memory,args,config in model.cases():
            reference=model.Reference(memory,args,config).run()
            for phase in (0,8):
                for i,words in enumerate((self.truth,self.words)):
                    m=model.EventOracle(words,memory,args,config,phase).run()
                    self.assertTrue(model.public(m.memory)==model.public(reference.memory),(args,config,phase,i))
                    self.assertEqual(m.calls,reference.calls); self.assertEqual(m.fired,reference.fired)
                    self.assertEqual(m.r[29],model.STACK+phase)
                    seen[i].update(m.visits); fired.update(m.fired)
                count+=1
        for i,words in enumerate((self.truth,self.words)):
            self.assertEqual(seen[i]&set(range(source.ENTRY,source.ENTRY+len(words)*4,4)),set(range(source.ENTRY,source.ENTRY+len(words)*4,4)))
        self.assertEqual(len(fired),5)
        self.receipt('recovered-guest',two_way_cases=count,all219_original_and_C_words=True,
            eleven_argument_query_packets_and_cleared_output_cells=True,all_five_positive_gates=sorted(fired),
            full_signed_query_values_signed_color_index_unsigned_final_halfword=True,
            bounded_query_and_color_providers_not_gameplay=True)

    def test_03_eight_compiled_semantic_controls_fail_public_state_call_or_required_memory(self):
        cases=[model.fixture(pattern=p,mode=mode) for p in range(len(model.VALUES)) for mode in (0,31)]
        cases += [model.fixture(present=4),model.fixture(color_index=-1)]
        rejected=[]
        for label,body in controls(source.SELECTED).items():
            self.assertNotEqual(body,source.SELECTED)
            _,words,row=source.measure(self.root,self.out,'control-'+label,body)
            self.assertEqual(row['diagnostics'],''); differences=0
            for memory,args,config in cases:
                reference=model.Reference(memory,args,config).run()
                try:
                    m=model.EventOracle(words,memory,args,config).run()
                    differences+=m.calls!=reference.calls or model.public(m.memory)!=model.public(reference.memory)
                except (KeyError,ValueError): differences+=1
                except AssertionError as error:
                    if not error.args or not isinstance(error.args[0],tuple) or error.args[0][0] != 'unmapped read': raise
                    differences+=1
            self.assertGreater(differences,0,label); rejected.append(label)
        self.receipt('recovered-controls',eight_compiled_controls_rejected=rejected,
            real_state_packet_or_memory_difference=True,not_compile_or_sanitizer_failures=True)

    def test_04_all141_production_inputs_unchanged_and_unknown_inputs_rejected(self):
        source.freeze(self.root,self.out); read=Path.read_bytes
        for relative in source.PATHS.values():
            target=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==target else read(p)):
                with self.assertRaises(ValueError): source.freeze(self.root,self.out)
        self.receipt('recovered-inputs',inputs=len(source.PATHS),all_unchanged=True,
            production_source_guards_ELF_and_CSV_unchanged=True)

    def test_05_full_native32_C_O2_O0_UBSan_and_seven_effective_controls(self):
        caller=self.out/'native-caller.c'; caller.write_text(native.program()); exits={}
        variants=[('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)] + [
            (label,'-O2',body) for label,body in controls(source.SELECTED).items() if label!='unsigned_index']
        for label,opt,body in variants:
            unit=self.out/('native-'+label+'.c'); unit.write_text(native.BODY_HEADER+body+'\n'); exe=unit.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double','-fno-strict-aliasing',
                str(unit.relative_to(self.root)),str(caller.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120); exits[label]=ran.returncode
            if label in ('o2','o0'): self.assertEqual(ran.returncode,0,(label,ran.stderr))
            else: self.assertIn(ran.returncode,(21,22),(label,ran.stderr))
        self.receipt('recovered-native',cases_each=sum(1 for _ in native.cases()),exits=exits,
            actual_full_C_body_separate_from_scripted_providers=True,UBSan=True,no_fwrapv=True,
            all_bank_fields_pointer_lanes_event_padding_canaries_and_payload=True,
            negative_color_indices_use_valid_biased_native_fixture_array=True,
            unsigned_index_control_is_guest_only_to_avoid_native_out_of_bounds=True)


if __name__=='__main__': unittest.main()
