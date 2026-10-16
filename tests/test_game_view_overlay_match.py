"""Qualify all 102 words, closed temporary roles and the restored S0 lifetime."""
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_view_overlay_match as source
from tools.experiments import game_view_overlay_uopt_trace as trace
from tools.tests import test_game_view_overlay_pass as contracts
from tools.tests import game_view_overlay_oracle as model
from tools.tests import game_view_overlay_native as native
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object


def controls():
    body=source.SELECTED
    return dict(narrow_address_view=body.replace('s32 view) {','s32 view) {\n    view = (s16)view;'),
        lost_helper_sign=body.replace('(s16)view','(s16)(view & 0x7FFF)'),
        low_half_category=body.replace('D_800BE9F0 == 0x1D','(u16)D_800BE9F0 == 0x1D'),
        wrong_view_argument=body.replace('commands, 5, 0,','commands, 5, (s16)view,'),
        wrong_matrix_mode=body.replace('G_MTX_PROJECTION | G_MTX_MUL','G_MTX_PROJECTION | G_MTX_LOAD'),
        wrong_table_page=body.replace('[D_800BE9C0]','[D_800BE9C0 ^ 1]'),
        cached_page=body.replace('s32 view) {','s32 view) {\n    u8 page = D_800BE9C0;').replace('D_800BE9C0 *','page *').replace('[D_800BE9C0]','[page]'),
        lost_return=body.replace('return (s32)commands;','return (s32)(commands - 1);'))


class ViewOverlayMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.raw,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>102I',cls.rom,source.ROM))
        data,functions=source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.words=list(struct.unpack_from('>102I',data,functions[source.FUNCTION]['value']))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_all102_words_frame_saved_homes_bindings_and_15_neighbors(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['new_guards']),(102,64,37,37))
        self.assertEqual(self.raw[:31],self.truth[:31]);self.assertEqual(self.raw[-4:],self.truth[-4:])
        self.assertEqual(self.raw[24],0xAFAC0028)
        text,functions,relocations=parse_object(self.padded);f=functions[source.FUNCTION]
        self.assertEqual({a-f['value']:v for a,v in relocations.items() if f['value']<=a<f['value']+f['size']},source.RELOCATIONS)
        original,changed=parse_object(self.out/'neighbor-before.o'),parse_object(self.obj)
        bindings=lambda p,f:{a-f['value']:v for a,v in p[2].items() if f['value']<=a<f['value']+f['size']}
        self.assertEqual(set(original[1]),set(changed[1]));self.assertEqual(len(original[1])-1,15)
        for name,f in original[1].items():
            if name==source.FUNCTION:continue
            g=changed[1][name]
            self.assertEqual(original[0][f['value']:f['value']+f['size']],changed[0][g['value']:g['value']+g['size']],name)
            self.assertEqual(bindings(original,f),bindings(changed,g),name)

    def test_02_three_way_semantics_all256_pages_full_view_and_all102_words(self):
        count=0;visits=set();fired=set()
        for memory,view,pattern,mode in model.corpus():
            expected,calls,observations,effects,result=model.reference(memory,view,pattern,mode)
            for phase in (0,8):
                models=[]
                for words in (self.truth,self.raw,self.words):
                    m=model.OverlayOracle(words,memory,view,pattern,mode,phase).run()
                    self.assertEqual((model.public(m.memory),m.calls,m.observations,m.fired,m.r[2]),
                        (model.public(expected),calls,observations,effects,result),(hex(view),pattern,mode,phase))
                    visits.update(m.visits);models.append(m)
                self.assertEqual(model.machine.state(models[0]),model.machine.state(models[2]))
                self.assertEqual(models[0].memory,models[1].memory)
                fired.update(models[0].fired);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+408,4)))
        self.assertEqual({x[2] for x in fired},set(range(1,6)))
        self.receipt('guest',three_way_cases=count,all102_words_visited=True,fired_sites=len(fired),
            all256_pages_full_word_views_signed_helpers=True,callback_prefix_bytes=512,
            raw_C_complete_memory_and_protocol=True,guarded_retail_complete_state=True)

    def test_03_every_memory_access_fault_prefix(self):
        count=0
        for view,category,mode in ((0,0,0),(0xA55A8001,0x1D,1),(0xFFFFFFFF,0x1D,2),
                (0x80000001,0x1001D,3),(0x8000,0x1D,4),(0xFFFF,0,5)):
            memory=model.fixture(128,category,1)
            complete=model.OverlayOracle(self.truth,memory,view,1,mode).run()
            for cut in range(complete.root_accesses):
                models=[]
                for words in (self.truth,self.raw,self.words):
                    m=model.OverlayOracle(words,memory,view,1,mode);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);models.append(m)
                self.assertEqual(model.machine.state(models[0]),model.machine.state(models[2]))
                self.assertEqual((models[0].memory,models[0].events,models[0].calls),
                    (models[1].memory,models[1].events,models[1].calls))
                count+=1
        self.receipt('faults',fired_access_prefixes=count,paths=6,
            raw_C_access_order_and_complete_memory=True,guarded_retail_complete_state=True,
            emitted_guest_only_not_portable_C_faults=True)

    def test_04_all102_raw_words_bindings_pools_and_every_guard_field(self):
        text,functions,relocations=parse_object(self.obj);f=functions[source.FUNCTION]
        for i in range(102):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,relocations)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for offset in source.RELOCATIONS:
            bad=dict(relocations);bad[f['value']+offset]=[('R_MIPS_26','wrong')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with patch.object(source.previous,'sections',return_value={'.rodata':(0,b'bad')}):
            with self.assertRaises(ValueError):source.checked_object(self.obj)
        before=(self.out/'before-guards').read_bytes();guards=source.guarded_manifest(self.out,self.obj)
        self.assertEqual(source.checked_manifest(guards,self.out,self.obj),guards)
        fields=csv.DictReader(io.StringIO(before.decode())).fieldnames
        rows=list(csv.DictReader(io.StringIO(guards[len(before):].decode()),fieldnames=fields))
        self.assertEqual(len(rows),37)
        def serialize(rows):
            stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
            writer.writerows(rows);return before+stream.getvalue().encode()
        self.assertEqual(serialize(rows),guards)
        with patch.object(source,'guarded_manifest',return_value=guards) as expected:
            for index in range(37):
                for field in fields:
                    changed=[dict(r) for r in rows];changed[index][field]+='corrupt'
                    with self.assertRaises(ValueError):source.checked_manifest(serialize(changed),self.out,self.obj)
            self.assertEqual(expected.call_count,37*len(fields))
        raw,_=source.checked_object(self.obj);normalized=source.normalized_instructions(self.obj)
        for i,word in enumerate(raw):
            replacement=normalized[i*4][0]
            self.assertEqual(word>>26,replacement>>26)
            if word>>26==0:mask=(31<<21)|(31<<16)|(31<<11)
            else:mask=(31<<21)|(31<<16)
            self.assertEqual(word&~mask,replacement&~mask)

    def test_05_independent_retail_and_padded_links_with_HI_LO_carries(self):
        text,functions,relocations=parse_object(self.padded);f=functions[source.FUNCTION]
        original='.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+(self.out/'before-view_overlay_assembly').read_text()
        path=self.out/'independent-retail.s';path.write_text(original);original_obj=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(original_obj),str(path)],capture_output=True,check=True)
        anchors={name:int(name.split('_',1)[1],16) for rows in source.RELOCATIONS.values() for _,name in rows}
        for index,entry in enumerate((source.ENTRY,0x15207FF0,0x15318004)):
            symbols={name:value+index*0x200000 for name,value in anchors.items()}
            if index:
                for n,name in enumerate(sorted(k for k in symbols if k.startswith('D_'))):
                    symbols[name]=0x80100000+index*0x100000+n*0x10000+(0x7FFC if n%2 else 0x8004)
            emitted,unresolved=emit_function(text,f,relocations,source.FUNCTION,symbols);self.assertFalse(unresolved)
            path=self.out/('rebase-%d-source.s'%index);path.write_text(emitted);obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            script=path.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            data=[]
            for name,input_obj in (('retail',original_obj),('source',obj)):
                elf=self.out/('rebase-%d-%s.elf'%(index,name))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(input_obj)],capture_output=True,check=True)
                data.append(sections(elf)['.text'][1][:408])
            self.assertEqual(data[0],data[1])
        self.receipt('rebases',independent_original_source_links=3,all102_words=True,unchanged24_bindings=True)

    def test_06_actual_C_native32_and_eight_effective_controls(self):
        with patch.object(contracts,'source',source),patch.object(native,'controls',controls):
            contracts.ViewOverlayPassTests.test_03_native32_O2_O0_UBSan_and_eight_effective_controls(self)

    def test_07_actual_frame_driver_full_word_call_and_cursor_store(self):
        with patch.object(contracts,'source',source):
            contracts.ViewOverlayPassTests.test_06_actual_frame_driver_call_and_cursor_publication(self)

    def test_08_fingerprint_locked_baseline_selected_UOPT_and_integer_view_colors(self):
        results={}
        for variant in ('baseline','selected'):
            for mode in (5,6):
                row=trace.trace_owner(self.root,mode,variant);results[variant,mode]=row
                self.assertTrue(row['code_unchanged']);self.assertFalse(row['installable'])
                self.assertEqual(row['baseline']['flags'],['-O2','-g3'])
                self.assertTrue(row['view_variable']['virtual_register'])
        colors=lambda row:[v['color'] for v in row['constraints'] if v['identity']==row['view_variable']['identity']]
        self.assertEqual(colors(results['baseline',5]),[-1,-1,-1])
        self.assertEqual(colors(results['selected',5]),[14])
        block=trace.procedure_block((self.root/trace.BUILD/'selected-mode-6/uoptlist').read_text())
        for value in (block.replace('IN LOCAL OPTIMIZATION OF '+source.FUNCTION,'missing'),block+block):
            with self.assertRaises(ValueError):trace.procedure_block(value)
        self.receipt('uopt',four_owned_normal_profile_compiles=True,complete_objects_bindings_pools_identical=True,
            baseline_view_colors=colors(results['baseline',5]),selected_view_colors=colors(results['selected',5]),
            frontend_vreg_marker_present_in_both=True,real_number_diagnostics_not_used=True)


if __name__=='__main__':unittest.main()
