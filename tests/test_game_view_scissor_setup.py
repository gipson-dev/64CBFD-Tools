"""Direct SDK scissor match, real clamp, bounded conversions and cursor ABI."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_view_scissor_setup as source
from tools.tests import game_view_scissor_oracle as model
from tools.tests import game_view_scissor_native as native
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as tracking
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object


class ViewScissorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.raw,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>124I',cls.rom,source.ROM))
        cls.clamp=list(struct.unpack_from('>87I',cls.rom,0x483F4))
        data,functions=source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.emitted=list(struct.unpack_from('>124I',data,functions[source.FUNCTION]['value']))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_all124_direct_words_frame_homes_ten_neighbors_and_actual_clamp(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(124,72,0))
        self.assertEqual((self.row['unchanged_neighbors'],self.row['clamp_words'],self.row['clamp_exact']),(10,87,True))
        self.assertEqual(self.row['diagnostics'],'');self.assertFalse(self.row['pools'])
        self.assertEqual(self.raw,self.truth);self.assertEqual(self.emitted,self.truth)
        self.assertEqual(len(source.RELOCATIONS),7)
        for address in model.CLAMP_DEAD:
            index=(address-model.CLAMP)//4
            self.assertEqual(self.clamp[index-4:index+1],
                [0x45020004,0x46000306,0x10000002,0x46001306,0x46000306])
        for index,word in enumerate(self.clamp):
            if word>>26 in (4,5,20,21) or word>>26==17 and word>>21&31==8:
                offset=word&65535;offset=offset if offset<32768 else offset-65536
                self.assertNotIn(model.CLAMP+index*4+4+offset*4,model.CLAMP_DEAD)
        before=(self.out/'before-makefile').read_text();after=source.recovered_makefile(before)
        self.assertEqual(after.count('$(BUILD_DIR)/$(SRC_DIR)/game_476D0.c.o, '),1)
        self.assertTrue(after.replace(' $(BUILD_DIR)/$(SRC_DIR)/game_476D0.c.o, ', ', ')==before)
        self.receipt('emission',direct_words=124,frame=72,new_guards=0,no_profile_change=True,
            unchanged_neighbors=10,real_clamp_exact_words=87,no_padding_or_private_pools=True)

    def test_02_full_connected_guest_and_invalid_conversion_prefixes(self):
        completed=invalid=0;seen=[set(),set(),set()];helper=set()
        for memory,args,spec in model.corpus():
            expected,observations,writes,complete,result=model.reference(memory,args)
            for phase in (0,8):
                machines=[]
                for i,words in enumerate((self.truth,self.raw,self.emitted)):
                    m=model.ScissorOracle(words,memory,args,self.clamp,phase)
                    if complete:m.run();self.assertEqual(m.r[2],result)
                    else:
                        with self.assertRaises(model.ConversionBoundary):m.run()
                        self.assertEqual(m.code[m.current_pc]>>26,17)
                    self.assertEqual(model.public(m.memory),model.public(expected),(args,spec,phase))
                    self.assertEqual(m.observations,observations)
                    self.assertEqual(len(m.calls),0 if model.half(args[1])==255 else 1)
                    if m.calls:
                        sp=m.before[29]-0x48
                        self.assertEqual(m.calls[0],(model.CLAMP,(sp+0x3C,sp+0x34,sp+0x38,sp+0x30)))
                    seen[i].update(m.visits);helper.update(m.visits);machines.append(m)
                state=lambda m:(m.memory,m.r,m.f,m.events,m.calls,m.observations,m.current_pc,m.delay_of,m.all_accesses)
                for m in machines[1:]:self.assertEqual(state(m),state(machines[0]))
                if complete:completed+=1
                else:invalid+=1
        wanted=set(range(source.ENTRY,source.ENTRY+496,4))
        for visits in seen:self.assertEqual(visits&wanted,wanted)
        self.assertEqual(helper&set(range(model.CLAMP,model.CLAMP+348,4)),
            set(range(model.CLAMP,model.CLAMP+348,4))-model.CLAMP_DEAD)
        self.assertGreater(invalid,0)
        self.receipt('guest',completed_three_way_cases=completed,invalid_conversion_prefix_cases=invalid,
            all124_root_and83_reachable_clamp_words_visited=True,four_dead_clamp_words_statically_checked=True,actual_connected_helper=True,
            full_private_and_public_state=True,hardware_FCSR_or_invalid_cast_result_not_claimed=True)

    def test_03_all124_words_seven_bindings_pools_and_stale_predecessors_fail_closed(self):
        text,functions,relocations=parse_object(self.obj);f=functions[source.FUNCTION]
        for i in range(124):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,relocations)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for at in (*source.RELOCATIONS,0):
            bad=dict(relocations);bad[f['value']+at]=[('R_MIPS_26','wrong')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with patch.object(source.previous.previous,'sections',return_value={'.rodata':(0,b'bad')}):
            with self.assertRaises(ValueError):source.checked_object(self.obj)
        with self.assertRaises(ValueError):source.recovered_owner(source.recovered_owner((self.out/'before-frustum_owner').read_text()))
        with self.assertRaises(ValueError):source.recovered_makefile(source.recovered_makefile((self.out/'before-makefile').read_text()))
        self.receipt('fail-closed',raw_words=124,bindings=7,extra_binding=1,private_pool=1,stale_source_and_makefile=True)

    def test_04_independent_original_and_direct_C_rebases(self):
        original=assembly.ViewListSetupTests.original.__func__(type(self),'original-scissor',
            (self.out/'before-scissor_original').read_text(),source.FUNCTION)
        text,functions,relocations=parse_object(self.padded)
        names=sorted({name for rows in source.RELOCATIONS.values() for _,name in rows})
        for index in range(3):
            entry=0x15207FF0+index*0x100000
            symbols={name:(entry+0x10000 if name.startswith('func_') else
                0x80100000+n*0x10000+(0x7FFC,0x8004,0x7FD0)[index]) for n,name in enumerate(names)}
            emitted,unresolved=emit_function(text,functions[source.FUNCTION],relocations,source.FUNCTION,symbols)
            self.assertFalse(unresolved)
            asm=self.out/('direct-rebase-%d.s'%index);asm.write_text(emitted);obj=asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],capture_output=True,check=True)
            images=[]
            for label,path in (('original',original),('direct',obj)):
                script=self.out/('rebase-%s-%d.ld'%(label,index));script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(path)],capture_output=True,check=True)
                images.append(sections(elf)['.text'][1][:496])
            self.assertEqual(images[0],images[1])
        self.receipt('rebases',original_GNU_links=3,independent_C_links=3,all124_words_compared=True,HI_LO_carries_and_call_region=True)

    def test_05_actual_native32_SDK_and_real_clamp_O2_O0_UBSan_controls(self):
        harness=self.out/'native.c';harness.write_text(native.program())
        before=(self.out/'before-frustum_owner').read_text();lo,hi=source.build.function_span(before,'func_1501AF44')
        helper=self.out/'native-clamp.c';helper.write_text(native.HEADER+before[lo:hi]+'\n')
        exits={}
        for name,opt,body in [('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[
                (name,'-O2',body) for name,body in native.controls().items()]:
            if name not in ('o2','o0'):self.assertNotEqual(body,source.SELECTED)
            unit=self.out/('native-'+name+'.c');unit.write_text(native.HEADER+body+'\n');exe=unit.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',
                str(unit.relative_to(self.root)),str(helper.relative_to(self.root)),str(harness.relative_to(self.root)),
                '-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);exits[name]=ran.returncode
            self.assertEqual(ran.returncode,0 if name in ('o2','o0') else 22 if name=='missing_advance' else 21,(name,ran.stderr))
        self.receipt('native',cases_each=sum(1 for _ in native.cases()),exits=exits,
            real_SDK_and_clamp_in_separate_units=True,all864_public_words_and_canaries=True,
            no_translation_of_packed_GPU_data=True,UBSan=True,no_fwrapv=True,
            invalid_float_casts_not_executed=True,field_offsets_and_six_word_ABI_checked=True)

    def test_06_two_complete_original_callers_and_consumed_cursor_stores(self):
        callers=(('view_overlay_assembly','game_45B80','func_15019CC8',0x47178,102,0x15019D1C,15),
            ('builder_original','generated_13D350','func_1510FEA0',0x13D350,267,0x15110288,13))
        cases=0
        for key,owner,name,rom,count,entry,length in callers:
            obj=assembly.ViewListSetupTests.original.__func__(type(self),'original-'+name,(self.out/('before-'+key)).read_text(),name)
            data,functions=source.build.link_owner(self.root,self.out,obj,owner);f=functions[name]
            full=data[f['value']:f['value']+f['size']]
            self.assertEqual(len(full),count*4);self.assertEqual(full,self.rom[rom:rom+len(full)])
            va=0x15019CC8 if key=='view_overlay_assembly' else 0x1510FEA0
            cut=list(struct.unpack_from('>%dI'%length,full,entry-va));join=entry+length*4
            class Join(Exception):pass
            class Code(tracking.TrackedCode):
                def __getitem__(self,pc):
                    if pc==join:raise Join
                    return super().__getitem__(pc)
            for view in (-1,0,3,255,0x100FF,0x10001):
                for coords in ((4.25,5.5,200.75,180.25),(-4.,-5.,500.,300.)):
                    memory,args=model.fixture(view,coords=coords)
                    model.put(memory,0x80082FA6,view&65535,2)
                    call_args=(args[0],model.half(view)&0xFFFFFFFF,0,0,0,0)
                    expected,observations,_,complete,result=model.reference(memory,call_args);self.assertTrue(complete)
                    model.put(expected,result,0xDA380003 if key=='view_overlay_assembly' else 0xD9FFFFFF)
                    model.put(expected,result+4,0x80089470 if key=='view_overlay_assembly' else 0x400)
                    for phase in (0,8):
                        machines=[]
                        for words in (self.truth,self.raw,self.emitted):
                            connected={source.ENTRY+i*4:w for i,w in enumerate(words)};connected[join]=0
                            m=model.ScissorOracle(cut,memory,args,self.clamp,phase,entry,connected)
                            m.r[16]=m.before[16]=view&0xFFFFFFFF;m.code=Code(m.code,m)
                            with self.assertRaises(Join):m.run()
                            self.assertEqual(model.public(m.memory),model.public(expected))
                            self.assertEqual(m.calls[0],(source.ENTRY,call_args));self.assertEqual(m.observations,observations)
                            self.assertEqual(m.r[2],result if key=='view_overlay_assembly' else result+8)
                            for reg in (*range(16,24),28,29,30):self.assertEqual(m.r[reg],m.before[reg])
                            if key=='view_overlay_assembly':self.assertEqual(model.read(m.memory,m.r[29]+0x28),call_args[1])
                            machines.append(m)
                        for m in machines[1:]:self.assertEqual((m.memory,m.r,m.f,m.events),(machines[0].memory,machines[0].r,machines[0].f,machines[0].events))
                        cases+=1
        self.receipt('callers',original_words=[102,267],actual_cut_cases=cases,
            sign_extension_stack_delay_arguments_and_consumed_cursor=True,
            original_real_post_call_commands=True,full_renderer_or_gameplay_not_claimed=True)

    def test_07_all_connected_memory_fault_prefixes(self):
        cases=0
        fixtures=[model.fixture(),model.fixture(255),model.fixture(limit=-1),model.fixture(coords=(-4.,-5.,500.,300.)),
            model.fixture(output=model.WIDTH),model.fixture(output=model.VIEWS+0x24)]
        for memory,args in fixtures:
            for phase in (0,8):
                full=model.ScissorOracle(self.truth,memory,args,self.clamp,phase).run()
                for fault in range(full.all_accesses):
                    machines=[]
                    for words in (self.truth,self.raw,self.emitted):
                        m=model.ScissorOracle(words,memory,args,self.clamp,phase);m.access_fault=fault
                        with self.assertRaises(tracking.AccessBoundary):m.run()
                        self.assertEqual(m.all_accesses,fault);machines.append(m)
                    state=lambda m:(m.memory,m.r,m.f,m.events,m.calls,m.observations,m.current_pc,m.delay_of)
                    for m in machines[1:]:self.assertEqual(state(m),state(machines[0]))
                    cases+=1
        self.receipt('faults',fired_three_way_prefixes=cases,all_executed_root_and_connected_clamp_accesses=True,
            hardware_exceptions_not_emulated=True)


if __name__=='__main__':unittest.main()
