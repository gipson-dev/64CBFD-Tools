"""Complete direct clipping, private homes, original packets and native controls."""
import json
from pathlib import Path
import re
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_clipped_rectangle as source
from tools.tests import game_clipped_rectangle_oracle as model
from tools.tests import game_clipped_rectangle_native as native
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command


class ClippedRectangleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes();cls.truth=list(struct.unpack_from('>106I',cls.rom,source.ROM))
        data,functions=source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.emitted=list(struct.unpack_from('>106I',data,functions[source.FUNCTION]['value']))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-rectangle',
            (cls.out/'before-color_provider_original').read_text(),source.FUNCTION)

    def receipt(self,name,**row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_all106_direct_words_two_bindings_frame_pool_and27_neighbors(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.emitted,self.truth)
        self.assertEqual((self.row['frame'],self.row['new_guards'],self.row['unchanged_raw_padded_neighbors']),(0,0,27))
        source.checked_parts(*source.parts(self.obj),source.previous.sections(self.obj)['.rodata'][1])
        self.receipt('direct',words=106,frame=0,new_guards=0,bindings=2,unchanged_raw_padded_neighbors=27,
            inherited_pool_unchanged=True,no_new_makefile_or_profile=True)

    def test_02_independent_guest_reference_signed_clips_aliases_wrap_and_full_state(self):
        count=0;seen=set();emitted=0;rejected=0;home_returns=set()
        for memory,args,phase in model.corpus():
            expected,result,draw=model.reference(memory,args,phase);models=[]
            for words in (self.truth,self.words,self.emitted):
                m=model.RectangleOracle(words,memory,args,phase).run()
                self.assertEqual(m.memory,expected,(args,phase));self.assertEqual(m.r[2],result)
                self.assertFalse(m.calls);seen.update(m.visits);models.append(m)
            self.assertTrue(model.point.state(models[0])==model.point.state(models[1])==model.point.state(models[2]))
            if draw:emitted+=1
            else:rejected+=1
            if draw and args[0] in (model.STACK+phase,model.STACK+phase-4):home_returns.add(result)
            count+=1
        missing=set(range(source.ENTRY,source.ENTRY+424,4))-seen
        self.assertEqual(missing,{source.ENTRY+at for at in (0xA8,0xBC,0xC8,0xCC,0xF4,0xF8,0x10C,0x110,0x138,0x13C)})
        self.assertTrue(home_returns);self.assertTrue(emitted and rejected)
        self.receipt('guest',three_way_cases=count,emitted=emitted,rejected=rejected,natural_words=106-len(missing),
            retained_dead_compare_offsets=sorted(pc-source.ENTRY for pc in missing),home_alias_returns=sorted(home_returns),
            all_memory_register_events_identical=True,invalid_conversion_is_bounded_nontrapping_not_hardware_FCSR=True)

    def test_03_native32_full_body_typed_caller_all_canaries_and_eight_controls(self):
        caller=self.out/'native-caller.c';caller.write_text(native.CALLER)
        driver=self.out/'native-driver.c';driver.write_text(native.program());exits={}
        forms=[('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[(n,'-O2',b) for n,b in native.controls(source.SELECTED).items()]
        for label,opt,body in forms:
            unit=self.out/('native-'+label+'.c');unit.write_text(native.HEADER+body+'\n');exe=unit.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double','-fno-strict-aliasing',
                *[str(p.relative_to(self.root)) for p in (unit,caller,driver)],'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120);exits[label]=ran.returncode
            self.assertEqual(ran.returncode,0 if label in ('o2','o0') else 22,(label,ran.stderr))
        self.receipt('native',cases_each=sum(1 for _ in native.cases()),exits=exits,UBSan=True,no_LTO_or_fwrapv=True,
            separate_full_body_typed_caller_and_full_canaries=True,aligned_float_backed_viewport_output_aliases=True,
            invalid_indices_nonfinite_out_of_range_conversions_and_stack_home_aliases_guest_only=True)

    def test_04_three_independent_original_C_global_HI_LO_rebases(self):
        for index,base in enumerate((0x80107FFC,0x80118004,0x80127FD0)):
            images=[]
            for label,obj in (('original',self.original),('C',self.obj)):
                if label=='C':
                    raw,bindings=source.parts(obj)
                    from tools.experiments.alternative_source_draft_word_screen import emit_function
                    text,unresolved=emit_function(raw,dict(value=0,size=424),bindings,source.FUNCTION,{'D_800BE628':base})
                    self.assertFalse(unresolved);path=self.out/('rebase-C-%d.s'%index);path.write_text(text);obj=path.with_suffix('.o')
                    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
                path=self.out/('rebase-%d-%s.ld'%(index,label));elf=path.with_suffix('.elf')
                path.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(path),'-e',source.FUNCTION,
                    '--defsym=D_800BE628=0x%X'%base,'-o',str(elf),str(obj)],capture_output=True,check=True)
                images.append(source.previous.sections(elf)['.text'][1][:424])
            self.assertEqual(*images)
        self.receipt('rebases',original_links=3,C_links=3,all106_words=True,signed_low_carry_cases=True)

    def test_05_all_access_fault_prefixes_include_home_and_partial_command_stores(self):
        count=0
        for alias,endpoint,bounds,phase in ((0,0,0,0),(0,9,0,8),(1,0,0,0),(2,3,0,8),(3,0,0,0),(4,0,0,8),(5,0,0,0),(6,0,0,8),(7,12,2,0),(8,0,0,8)):
            memory,args=model.fixture(1,endpoint,bounds,alias,phase)
            completed=model.RectangleOracle(self.truth,memory,args,phase).run()
            for fault in range(completed.all_accesses):
                models=[]
                for words in (self.truth,self.words,self.emitted):
                    m=model.RectangleOracle(words,memory,args,phase);m.access_fault=fault
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault);models.append(m)
                self.assertTrue(model.point.state(models[0])==model.point.state(models[1])==model.point.state(models[2]));count+=1
        self.receipt('faults',positively_fired_three_way_prefixes=count,incoming_cursor_home_and_partial_command=True,
            not_portable_C_fault_or_CP0_acceptance=True)

    def test_06_all106_words_two_bindings_pool_and156_input_corruptions_reject(self):
        raw,bindings=source.parts(self.obj);pool=source.previous.sections(self.obj)['.rodata'][1]
        for i in range(106):
            bad=bytearray(raw);bad[4*i]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(bad),bindings,pool)
        for i in range(len(pool)):
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
        self.receipt('inputs',word_controls=106,binding_controls=3,inherited_pool_byte_controls=len(pool),
            protected_input_entries=156,distinct_paths=len(set(source.PATHS.values())),all_fail_closed=True)

    def test_07_all16_actual_caller_packets_delays_private_homes_and_real_callee(self):
        text=(self.out/'before-color_provider_original').read_text()
        sites=tuple(int(m,16) for m in re.findall(r'/\* [0-9A-F]+ ([0-9A-F]+) [0-9A-F]+ \*/  jal        func_1517F9F4',text))
        self.assertEqual(sites,model.SITES);count=0;seen=set()
        class Join(Exception):pass
        class Code(faults.TrackedCode):
            def __getitem__(self,pc):
                if pc==self.owner.join:raise Join
                return super().__getitem__(pc)
        for index,site in enumerate(sites):
            entry,join=site-16,site+8;packet=list(struct.unpack_from('>6I',self.rom,entry-0x15000000+0x2D4B0))
            for view in (0,1,3):
                for phase in (0,8):
                    memory,args=model.fixture(view,0,1,phase=phase);models=[]
                    for target in (self.truth,self.words,self.emitted):
                        code=dict(zip(range(source.ENTRY,source.ENTRY+424,4),target));code[join]=0
                        m=model.RectangleOracle(packet,memory,args,phase,entry,code);m.join=join
                        for r in range(8,26):m.r[r]=r+5
                        m.r[16]=2;m.r[23]=view;m.r[8]=(17<<16)|15;m.r[2]=0xAABBCCDD
                        m.f[10]=12;m.f[4]=(-7)&model.MASK;m.f[6]=15 if index==2 else model.bits(13.75)
                        expected,passed=model.packet_reference(index,m.r,m.f,m.memory,phase)
                        expected,result,_=model.reference(expected,passed,phase)
                        m.code=Code(m.code,m)
                        with self.assertRaises(Join):m.run()
                        self.assertEqual(m.calls,[(source.ENTRY,passed)],(index,phase))
                        self.assertEqual(m.memory,expected,(index,phase));self.assertEqual(m.r[2],result)
                        seen.update(m.visits);models.append(m)
                    self.assertTrue(model.point.state(models[0])==model.point.state(models[1])==model.point.state(models[2]));count+=1
        self.assertTrue(all(set(range(pc-16,pc+8,4))<=seen for pc in sites))
        self.receipt('callers',original_packet_sites=16,original_words_each=6,three_way_cases=count,
            real106word_callee=True,delay_argument_and_private_DC_EC_E8_40_3C_stores_preserved=True,
            bounded_packet_windows_not_complete_unrecovered_parents=True)


if __name__=='__main__':unittest.main()
