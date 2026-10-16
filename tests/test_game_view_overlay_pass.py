"""Unguarded semantic recovery; retail instruction matching remains open."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_view_overlay_pass as source
from tools.tests import game_view_overlay_oracle as model
from tools.tests import game_view_overlay_native as native
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object


class ViewOverlayPassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.raw,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>102I',cls.rom,source.ROM))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_raw_shape_and_all15_neighbors_without_new_guards(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['new_guards']),(98,64,94,0))
        self.assertFalse(self.row['byte_exact'])
        self.assertEqual(self.row['raw_sha256'],source.RAW_SHA256)
        old,new=parse_object(self.out/'neighbor-before.o'),parse_object(self.obj)
        binding=lambda p,f:{a-f['value']:v for a,v in p[2].items() if f['value']<=a<f['value']+f['size']}
        self.assertEqual(set(old[1]),set(new[1]));self.assertEqual(len(old[1])-1,15)
        for name,f in old[1].items():
            if name==source.FUNCTION:continue
            g=new[1][name]
            self.assertEqual(old[0][f['value']:f['value']+f['size']],new[0][g['value']:g['value']+g['size']],name)
            self.assertEqual(binding(old,f),binding(new,g),name)
        data,functions=source.build.link_owner(self.root,self.out,self.padded,source.OWNER)
        f=functions[source.FUNCTION]
        self.assertEqual(data[f['value']:f['value']+408],struct.pack('>98I',*self.raw)+bytes(16))
        self.assertEqual(f['size'],392)

    def compare(self,memory,view,pattern,mode,phase=0):
        expected,calls,observations,fired,result=model.reference(memory,view,pattern,mode)
        models=[]
        for words in (self.truth,self.raw):
            m=model.OverlayOracle(words,memory,view,pattern,mode,phase).run()
            self.assertEqual((model.public(m.memory),m.calls,m.observations,m.fired,m.r[2]),
                (model.public(expected),calls,observations,fired,result),(hex(view),pattern,mode,phase))
            models.append(m)
        return models

    def test_02_full_word_views_all256_pages_live_callbacks_and_instruction_coverage(self):
        visits=[set(),set()];fired=set();count=0
        for memory,view,pattern,mode in model.corpus():
            for phase in (0,8):
                models=self.compare(memory,view,pattern,mode,phase)
                for i,m in enumerate(models):visits[i].update(m.visits)
                fired.update(models[0].fired);count+=1
        for seen,size in zip(visits,(408,392)):
            self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+size,4)))
        self.assertEqual({x[2] for x in fired},set(range(1,6)))
        self.receipt('guest',retail_raw_C_cases=count,retail_words_visited=102,C_words_visited=98,
            fired_sites=len(fired),all256_page_encodings=True,full_word_view_and_signed_helper_arguments=True,
            callback_prefix_bytes=512,late_projection_page_reload=True,
            saved_register_stack_and_RA_checked=True,public_protocol_only_not_instruction_fault_equivalence=True)

    def test_03_native32_O2_O0_UBSan_and_eight_effective_controls(self):
        harness=self.out/'native.c';harness.write_text(native.program());exits={}
        for name,opt,body in [('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[
                (name,'-O2',body) for name,body in native.controls().items()]:
            unit=self.out/('native-'+name+'.c');unit.write_text(native.HEADER+body+'\n');exe=unit.with_suffix('.elf')
            result=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',
                str(unit.relative_to(self.root)),str(harness.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True);exits[name]=run.returncode
            if name in ('o2','o0'):self.assertEqual(run.returncode,0,run.stderr)
            else:self.assertIn(run.returncode,range(21,28),name)
        self.receipt('native',cases_each=len(list(native.corpus())),exits=exits,
            actual_C_O2_O0_UBSan=True,table_is_one_valid256_word_array=True,
            full_cursor_buffer_table_and_callback_prefix_checks=True,
            guest_only_between_packet_page_effect_not_claimed_as_native=True)

    def test_04_all98_raw_words_24_bindings_and_pools_fail_closed(self):
        text,functions,relocations=parse_object(self.obj);f=functions[source.FUNCTION]
        for i in range(98):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,relocations)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for offset in source.RELOCATIONS:
            bad=dict(relocations);bad[f['value']+offset]=[('R_MIPS_26','wrong')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        bad=dict(relocations);bad[f['value']]=[('R_MIPS_26','extra')]
        with patch.object(source,'parse_object',return_value=(text,functions,bad)):
            with self.assertRaises(ValueError):source.checked_object(self.obj)
        with patch.object(source,'sections',return_value={'.rodata':(0,b'bad')}):
            with self.assertRaises(ValueError):source.checked_object(self.obj)
        self.assertEqual(len(source.RELOCATIONS),24)

    def test_05_independent_HI_LO_carry_and_JAL_rebases(self):
        text,functions,relocations=parse_object(self.obj);f=functions[source.FUNCTION]
        raw=list(struct.unpack('>98I',text[f['value']:f['value']+392]))
        names=sorted({name for rows in source.RELOCATIONS.values() for _,name in rows})
        for index in range(3):
            entry=0x15407FFC+index*0x100000
            symbols={name:(entry+0x10000+n*0x100 if name.startswith('func_') else
                0x80100000+index*0x100000+n*0x10000+(0x7FFC if n%2 else 0x8004)) for n,name in enumerate(names)}
            emitted,unresolved=emit_function(text,f,relocations,source.FUNCTION,symbols);self.assertFalse(unresolved)
            path=self.out/('rebase-%d.s'%index);path.write_text(emitted);obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            script=path.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            elf=path.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
            expected=list(raw)
            for offset,((kind,name),) in source.RELOCATIONS.items():
                value=symbols[name];word=expected[offset//4]
                if kind=='R_MIPS_HI16':word=(word&0xFFFF0000)|(((value+0x8000)>>16)&65535)
                elif kind=='R_MIPS_LO16':word=(word&0xFFFF0000)|(value&65535)
                elif kind=='R_MIPS_26':word=(word&0xFC000000)|((value>>2)&0x3FFFFFF)
                else:self.fail(kind)
                expected[offset//4]=word
            self.assertEqual(sections(elf)['.text'][1][:392],struct.pack('>98I',*expected))
        self.receipt('rebases',independent_links=3,all_source_words=98,bindings=24,
            HI_LO_carry_and_JAL=True,retail_word_identity_not_claimed=True)

    def test_06_actual_frame_driver_call_and_cursor_publication(self):
        caller,join,global_cursor,count_address=0x15018B98,0x15018BA4,0x800BE9D0,0x80082FA4
        class Join(Exception):pass
        class CallerCode(faults.TrackedCode):
            def __getitem__(self,pc):
                if pc==join:raise Join
                return super().__getitem__(pc)
        class CallerOracle(model.OverlayOracle):
            def record_call(self,target):
                if target==source.ENTRY:
                    args=self.arguments(2);self.calls.append((target,args));self.events.append(('CALL',target,args))
                    self.observations.append((target,model.snapshot(self.memory)));self.counts[target]+=1
                else:super().record_call(target)
        data,functions=source.build.link_owner(self.root,self.out,self.padded,source.OWNER)
        f=functions['func_1501878C'];full=list(struct.unpack_from('>412I',data,f['value']))
        self.assertEqual(full,list(struct.unpack_from('>412I',self.rom,0x45C3C)))
        cut=full[(caller-0x1501878C)//4:(join-0x1501878C)//4];self.assertEqual(len(cut),3)
        count=0
        for view,category,mode in ((v,c,m) for v in (0,1,0x8001,0xA55A8001,0xFFFFFFFF)
                for c in (0,0x1D,0x1001D) for m in range(5)):
            memory=model.fixture(128,category,1)
            model.put(memory,count_address,view);model.put(memory,global_cursor,model.CURSOR)
            expected,calls,observations,fired,value=model.reference(memory,view,1,mode)
            model.put(expected,global_cursor,value)
            for words in (self.truth,self.raw):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                m=CallerOracle(cut,memory,view,1,mode,entry=caller,connected=connected)
                m.r[17]=m.before[17]=global_cursor;m.r[18]=m.before[18]=count_address
                m.code=CallerCode(m.code,m)
                with self.assertRaises(Join):m.run()
                self.assertEqual((model.public(m.memory),m.calls,m.observations,m.fired,m.r[2]),
                    (model.public(expected),[(source.ENTRY,(model.CURSOR,view))]+calls,
                        [(source.ENTRY,model.snapshot(memory))]+observations,fired,value))
                self.assertEqual(m.r[29],m.before[29])
            count+=1
        self.receipt('caller-cut',cases=count,fresh_full_C_driver_words=412,actual_cut_words=3,
            full_word_view_load_in_call_delay=True,returned_cursor_publication=True,
            complete_frame_pipeline_or_gameplay_not_claimed=True)


if __name__=='__main__':unittest.main()
