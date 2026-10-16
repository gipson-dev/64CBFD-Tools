"""Shared overlay semantics and nontrivial guarded capture-address scheduling."""
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_shared_overlay_pass as source
from tools.tests import game_shared_overlay_oracle as model
from tools.tests import game_shared_overlay_native as native
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_projected_packet_draw import native_command


class SharedOverlayPassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.raw,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>175I',cls.rom,source.ROM))
        data,functions=source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.words=list(struct.unpack_from('>175I',data,functions[source.FUNCTION]['value']))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_full175_frame_fold_scale_and_all15_neighbors(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['new_guards']),(175,40,79,79))
        before=(self.out/'before-dispatch_owner').read_text()
        old,new=parse_object(self.out/'neighbor-before.o'),parse_object(self.obj)
        bindings=lambda parsed,f:{a-f['value']:v for a,v in parsed[2].items() if f['value']<=a<f['value']+f['size']}
        self.assertEqual(set(old[1]),set(new[1]))
        for name,f in old[1].items():
            if name==source.FUNCTION:continue
            g=new[1][name]
            self.assertEqual(old[0][f['value']:f['value']+f['size']],new[0][g['value']:g['value']+g['size']],name)
            self.assertEqual(bindings(old,f),bindings(new,g),name)
        self.assertEqual(len(old[1])-1,15)
        self.assertEqual(source.previous.previous.warning_sites(before,(self.out/'neighbor-before-diagnostics.txt').read_text()),
            source.previous.previous.warning_sites(source.recovered_owner(before),self.row['diagnostics']))
        planned=source.normalized_instructions(self.obj)
        self.assertEqual(planned[0xE4],(0x80630000,[('R_MIPS_LO16','D_80082F90')]))
        self.assertEqual(planned[0x1DC],(0x3C010000,[('R_MIPS_HI16','D_80082F90')]))
        self.assertEqual(planned[0x1E0],(0xA02B0000,[('R_MIPS_LO16','D_80082F90')]))
        self.assertEqual(planned[0x1AC][1],[('R_MIPS_26','func_151D5E90')])
        for page in range(256):self.assertEqual(((-page)<<2)&0xFFFFFFFF,(-(page<<2))&0xFFFFFFFF)
        self.assertEqual(self.words[:4],self.truth[:4])
        self.assertEqual(self.words[-5:],self.truth[-5:])

    def compare(self,memory,pattern,mode,phase=0):
        expected,calls,observations,_,fired,value=model.reference(memory,pattern,mode)
        models=[]
        for words in (self.truth,self.raw,self.words):
            m=model.OverlayOracle(words,memory,pattern,mode,phase).run()
            self.assertEqual((model.public(m.memory),m.calls,m.observations,m.fired,m.r[2]),
                (model.public(expected),calls,observations,fired,value),(pattern,mode,phase))
            models.append(m)
        self.assertEqual(model.state(models[0]),model.state(models[2]))
        return models[0]

    def test_02_complete_semantics_all_byte_domains_live_callbacks_and_175_words(self):
        count,visits,fired=0,set(),set()
        for views,counter,pattern,disabled,mode,phase in itertools.product((-1,0,1),(0,1,4,5,255),range(4),(0,255),range(10),(0,8)):
            m=self.compare(model.fixture(views,counter,pattern,disabled),pattern,mode,phase)
            visits.update(m.visits);fired.update(m.fired);count+=1
        for byte in range(256):
            for field,initial,mode in ((model.PHASE,model.fixture(1,byte,byte%4,1),4),
                    (model.PAGE,model.fixture(1,0,byte%4,1),3),(model.DISABLED,model.fixture(1,0,byte%4,byte),0)):
                initial[field]=byte
                m=self.compare(initial,byte%4,mode);visits.update(m.visits);count+=1
        for disabled,next_,pattern in itertools.product((0,1,128,255),(0,1,128,255),range(4)):
            m=self.compare(model.fixture(0,1,pattern,disabled,next_),pattern,0);visits.update(m.visits);count+=1
        for memory,pattern,mode in list(native.corpus())[-8:]:
            self.compare(memory,pattern,mode);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+700,4)))
        self.assertEqual({mode for _,_,mode in fired},set(range(1,10)))
        self.receipt('guest',three_way_cases=count,root_words_visited=len(visits),fired_effect_sites=len(fired),
            all256_counter_page_disabled_encodings=True,callback_prefix_hash_bytes=512,
            full_final_public_memory_and_raw_C_protocol=True,guarded_original_complete_state=True,
            hardware_FCSR_rendering_or_gameplay_not_claimed=True)

    def test_03_all_access_fault_prefixes_and_repeated_counter_transitions(self):
        count=0
        for views,counter,pattern,disabled,mode in ((1,0,1,1,3),(0,128,0,1,4),(-1,5,2,1,0),
                (1,0,1,0,2),(0,255,3,0,8),(0,1,0,0,6)):
            memory=model.fixture(views,counter,pattern,disabled)
            complete=model.OverlayOracle(self.words,memory,pattern,mode).run()
            for cut in range(complete.root_accesses):
                models=[model.OverlayOracle(words,memory,pattern,mode,fault=cut) for words in (self.truth,self.words)]
                for m in models:
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut)
                self.assertEqual(model.state(models[0]),model.state(models[1]));count+=1
        transitions=0
        for pattern in range(4):
            memory=model.fixture(1,0,pattern,1)
            for disabled in (1,1,1,1,1,1,0,1):
                memory[model.DISABLED]=disabled
                memory=self.compare(memory,pattern,0).memory;transitions+=1
        self.receipt('faults',fired_memory_access_prefix_pairs=count,paths=6,repeated_state_transitions=transitions,
            emitted_guest_order_only_not_portable_C_faults=True)

    def test_04_all175_words_53_bindings_pools_and_every_guard_field_fail_closed(self):
        text,functions,relocations=parse_object(self.obj);f=functions[source.FUNCTION]
        for index in range(175):
            bad=bytearray(text);bad[f['value']+index*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,relocations)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for offset in source.RELOCATIONS:
            bad=dict(relocations);bad[f['value']+offset]=[('R_MIPS_26','wrong')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        bad=dict(relocations);bad[f['value']+4]=[('R_MIPS_26','extra')]
        with patch.object(source,'parse_object',return_value=(text,functions,bad)):
            with self.assertRaises(ValueError):source.checked_object(self.obj)
        with patch.object(source,'sections',return_value={'.rodata':(0,b'x')}):
            with self.assertRaises(ValueError):source.checked_object(self.obj)
        before=(self.out/'before-guards').read_bytes();guards=source.guarded_manifest(self.out,self.obj)
        self.assertTrue(guards.startswith(before))
        names=csv.DictReader(io.StringIO(before.decode())).fieldnames
        rows=list(csv.DictReader(io.StringIO(guards[len(before):].decode()),fieldnames=names))
        self.assertEqual(len(rows),79)
        def serialized(changed):
            stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=names,lineterminator='\n')
            writer.writerows(changed)
            return before+stream.getvalue().encode()
        self.assertEqual(serialized(rows),guards)
        self.assertEqual(source.checked_manifest(guards,self.out,self.obj),guards)
        # Only manifest bytes change here; the object and complete expected
        # manifest were qualified above, including an unmocked positive gate.
        with patch.object(source,'guarded_manifest',return_value=guards) as expected:
            for index in range(len(rows)):
                for field in names:
                    changed=[dict(row) for row in rows];changed[index][field]+='corrupt'
                    with self.assertRaises(ValueError):source.checked_manifest(serialized(changed),self.out,self.obj)
            self.assertEqual(expected.call_count,len(rows)*len(names))

    def test_05_independent_original_and_padded_three_HI_LO_carry_links(self):
        text,functions,relocations=parse_object(self.padded);f=functions[source.FUNCTION]
        anchors={name:int(name.split('_',1)[1],16) for rows in source.RELOCATIONS.values() for _,name in rows}
        original='.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+(self.out/'before-overlay_assembly').read_text()
        path=self.out/'independent-retail.s';path.write_text(original);original_obj=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(original_obj),str(path)],capture_output=True,check=True)
        for index,entry in enumerate((source.ENTRY,0x15207FF0,0x15318004)):
            symbols={name:(value if not index else (value+index*0x200000)&0xFFFFFFFF) for name,value in anchors.items()}
            if index:
                for n,name in enumerate(sorted(k for k in symbols if k.startswith('D_'))):
                    symbols[name]=0x80100000+index*0x100000+n*0x10000+(0x7FFC if n%2 else 0x8004)
            emitted,unresolved=emit_function(text,f,relocations,source.FUNCTION,symbols);self.assertFalse(unresolved)
            path=self.out/('rebase-%d-source.s'%index);path.write_text(emitted);obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            script=path.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            results=[]
            for label,input_obj in (('retail',original_obj),('source',obj)):
                elf=self.out/('rebase-%d-%s.elf'%(index,label))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(input_obj)],capture_output=True,check=True)
                results.append(sections(elf)['.text'][1][:700])
            self.assertEqual(results[0],results[1])
        self.receipt('rebases',independent_original_source_links=3,complete_words=175,
            counter_fold_and_rematerialized_HI_LO_carries=True,moved_JAL_bindings=True)

    def test_06_native32_actual_C_O2_O0_UBSan_and_eight_effective_controls(self):
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
            actual_C_O2_O0_UBSan=True,all256_signed_counter_and_page_encodings=True,
            table_is_one_valid256_word_array_with_label_at_last_element=True,
            full_final_cursor_buffer_and_table_canaries=True,callback_buffer_prefix_hash_bytes=512)

    def test_07_actual_frame_driver_call_cut_reload_and_cursor_publication(self):
        caller,join,global_cursor=0x15018B68,0x15018B78,0x800BE9D0
        class CallerJoin(Exception):pass
        class CallerCode(faults.TrackedCode):
            def __getitem__(self,pc):
                if pc==join:
                    self.owner.current_pc,self.owner.delay_of=pc,None
                    raise CallerJoin
                return super().__getitem__(pc)
        class CallerOracle(model.OverlayOracle):
            def record_call(self,target):
                if target==source.ENTRY:
                    args=self.arguments(1)
                    self.calls.append((target,args));self.events.append(('CALL',target,args))
                    self.observations.append((target,model.snapshot(self.memory)));self.counts[target]+=1
                else:super().record_call(target)
        data,functions=source.build.link_owner(self.root,self.out,self.padded,source.OWNER)
        f=functions['func_1501878C']
        full=list(struct.unpack_from('>412I',data,f['value']))
        self.assertEqual(full,list(struct.unpack_from('>412I',self.rom,0x45C3C)))
        cut=full[(caller-0x1501878C)//4:(join-0x1501878C)//4]
        self.assertEqual(len(cut),4)
        count=0
        for views,counter,pattern,disabled,mode in itertools.product((-1,0,1),(0,1,5,128),range(4),(0,1),(0,1,3,4)):
            memory=model.fixture(views,counter,pattern,disabled)
            memory.update({global_cursor+i:0xA5 for i in range(-4,8)})
            model.put(memory,global_cursor,model.CURSOR)
            expected,calls,observations,_,fired,value=model.reference(memory,pattern,mode)
            model.put(expected,global_cursor,value)
            models=[]
            for words in (self.truth,self.words):
                connected={source.ENTRY+i*4:word for i,word in enumerate(words)}
                m=CallerOracle(cut,memory,pattern,mode,entry=caller,connected=connected)
                m.r[17]=m.before[17]=global_cursor;m.r[19]=m.before[19]=model.COUNT
                m.code=CallerCode(m.code,m)
                with self.assertRaises(CallerJoin):m.run()
                self.assertEqual((model.public(m.memory),m.calls,m.observations,m.fired,m.r[2]),
                    (model.public(expected),[(source.ENTRY,(model.CURSOR,))]+calls,
                        [(source.ENTRY,model.snapshot(memory))]+observations,fired,value))
                self.assertEqual((m.r[15],m.r[17],m.r[19]),(model.read(expected,model.COUNT),global_cursor,model.COUNT))
                models.append(m)
            self.assertEqual(model.state(models[0]),model.state(models[1]));count+=1
        self.receipt('caller-cut',cases=count,fresh_full_C_driver_words=412,actual_cut_words=4,
            connected_provider_words=175,live_count_reload_and_cursor_store=True,
            complete_frame_pipeline_or_gameplay_not_claimed=True)


if __name__=='__main__':unittest.main()
