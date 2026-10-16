"""Complete view startup, closed prologue, rebases and real caller boundary."""
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_view_initialization as source
from tools.tests import game_view_initialization_oracle as model
from tools.tests import game_view_initialization_native as native
from tools.tests import test_game_actor_burst_consumer_match as tracking
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object


class ViewInitializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.raw,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>95I',cls.rom,source.ROM))
        data,functions=source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.normalized=list(struct.unpack_from('>95I',data,functions[source.FUNCTION]['value']))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    @classmethod
    def original(cls,label,text):
        names=[line.split()[1] for line in text.splitlines() if line.startswith('glabel ')]
        if len(names)!=1:raise ValueError('Expected one original function')
        path=cls.out/(label+'.s')
        path.write_text('.include "'+str(cls.root/'conker/include/asm_processor_prelude.inc')+'"\n'+text+
            '\n.type '+names[0]+', @function\n.size '+names[0]+', .-'+names[0]+'\n')
        obj=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
        return obj

    def test_01_95_words_frame_homes_ten_neighbors_and_exact_guarded_slot(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(95,40,8))
        self.assertEqual(self.row['unchanged_neighbors'],10)
        self.assertEqual(self.row['diagnostics'],'');self.assertFalse(self.row['pools'])
        self.assertEqual(self.normalized,self.truth)
        self.assertEqual(set(i*4 for i,(a,b) in enumerate(zip(self.raw,self.truth)) if a!=b),set(range(0xC,0x2C,4)))
        self.assertEqual(len(source.RELOCATIONS),26)
        normalized=source.normalized_instructions(self.obj)
        self.assertEqual(normalized[0xC][1],[('R_MIPS_LO16','D_80082FA0')])
        self.assertEqual(normalized[0x14][1],[])
        for i in (*range(3),*range(11,95)):
            self.assertEqual(normalized[i*4],(source.checked_object(self.obj)[0][i],source.RELOCATIONS.get(i*4,[])))
        source.checked_manifest((self.out/'normalized-guards.csv').read_bytes(),self.out,self.obj)
        self.receipt('emission',body_words=95,slot_words=95,frame=40,new_guards=8,closed_prologue_only=True,
            unchanged_neighbors=10,no_padding_or_private_pools=True,unchanged_other_87_words=True)

    def test_02_full_guest_outputs_callbacks_private_state_and_all95_words(self):
        count=0;seen=[set(),set(),set()];nan=negative_zero=False
        for memory,request,projection,mode in model.corpus():
            expected,calls,observations,complete=model.reference(memory,request,projection,mode)
            self.assertTrue(complete)
            for phase in (0,8):
                machines=[]
                for i,words in enumerate((self.truth,self.raw,self.normalized)):
                    m=model.InitializationOracle(words,memory,request,projection,mode,phase).run()
                    self.assertEqual((model.public(m.memory),m.calls,m.observations),
                        (model.public(expected),calls,observations),(request,projection,mode,phase))
                    seen[i].update(m.visits);machines.append(m)
                for m in machines[1:]:
                    self.assertEqual((m.memory,m.r,m.f),(machines[0].memory,machines[0].r,machines[0].f))
                count+=1
            bias=model.read(expected,model.BIAS)
            nan|=model.canonical(bias)==0x7FC00000;negative_zero|=bias==0x80000000
        wanted=set(range(source.ENTRY,source.ENTRY+380,4))
        for visits in seen:self.assertEqual(visits,wanted)
        self.assertEqual(count,1704);self.assertTrue(nan);self.assertTrue(negative_zero)
        self.receipt('guest',three_way_cases=count,fixtures=len(list(model.corpus())),all95_words_visited_each=True,
            terminal_private_state_agrees=True,callback_arguments_order_and_264byte_hash_checked=True,
            null_and_high_allocations_no_failure_shortcut=True,negative_zero=True,NaN_class_only=True,
            opaque_providers_not_real_allocator_or_renderer=True)

    def test_03_closed_prologue_join_for_full_word_inputs_and_old_S1_values(self):
        class Join(Exception):pass
        class Code(tracking.TrackedCode):
            def __getitem__(self,pc):
                if pc==self.owner.join:raise Join
                return super().__getitem__(pc)
        values=[0,1,2,0x7FFFFFFF,0x80000000,0xFFFFFFFF]+[(i*1664525+1013904223)&0xFFFFFFFF for i in range(64)]
        count=0
        for request in values:
            for phase in (0,8):
                for old_s1 in (0,0x13579BDF,0xFFFFFFFF):
                    machines=[]
                    for words in (self.raw,self.normalized):
                        m=model.InitializationOracle(words,model.fixture(),request,0x87654321,phase=phase)
                        m.r[17]=old_s1;m.before[17]=old_s1
                        m.join=source.ENTRY+(0x2C if request==0 else 0x34)
                        m.code=Code(m.code,m)
                        with self.assertRaises(Join):m.run()
                        self.assertEqual(m.r[17],request)
                        self.assertEqual(model.read(m.memory,m.r[29]+0x1C),old_s1)
                        machines.append(m)
                    self.assertEqual((machines[0].memory,machines[0].r,machines[0].f),
                        (machines[1].memory,machines[1].r,machines[1].f))
                    count+=1
        self.assertEqual(count,420)
        self.receipt('prologue-join',cases=count,old_S1_saved_before_copy=True,all_registers_FPRs_and_memory_agree=True,
            actual_taken_and_fallthrough_delay_slots=True,raw_fault_prefix_equivalence_not_claimed=True)

    def test_04_actual_native32_O2_O0_UBSan_and_seven_effective_controls(self):
        harness=self.out/'native.c';harness.write_text(native.program());exits={}
        for name,opt,body in [('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[
                (name,'-O2',body) for name,body in native.controls().items()]:
            if name not in ('o2','o0'):self.assertNotEqual(body,source.SELECTED)
            unit=self.out/('native-'+name+'.c');unit.write_text(native.HEADER+body+'\n')
            exe=unit.with_suffix('.elf')
            build=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',
                str(unit.relative_to(self.root)),str(harness.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);exits[name]=result.returncode
            if name in ('o2','o0'):self.assertEqual(result.returncode,0,result.stderr)
            else:self.assertIn(result.returncode,(21,22,23,24),(name,result.stderr))
        self.receipt('native',cases_each=len(list(model.corpus())),exits=exits,separate_actual_C_units=True,
            UBSan=True,no_fwrapv=True,full_public_canaries_and_callback_snapshots=True,
            NaN_payloads_canonicalized_not_hardware_FCSR=True)

    def test_05_all_words_bindings_guards_and_actual_padder_fail_closed(self):
        text,functions,relocations=parse_object(self.obj);f=functions[source.FUNCTION]
        for i in range(95):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,relocations)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for offset in (*source.RELOCATIONS,0):
            bad=dict(relocations);bad[f['value']+offset]=[('R_MIPS_26','wrong')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with patch.object(source,'sections',return_value={'.rodata':(0,b'bad')}):
            with self.assertRaises(ValueError):source.checked_object(self.obj)
        before=(self.out/'before-guards').read_bytes();good=(self.out/'normalized-guards.csv').read_bytes()
        fields=next(csv.reader(io.StringIO(before.decode())))
        rows=list(csv.DictReader(io.StringIO(good[len(before):].decode()),fieldnames=fields));self.assertEqual(len(rows),8)
        def manifest(rows):
            out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=fields,lineterminator='\n')
            writer.writerows(rows);return before+out.getvalue().encode()
        keys=('filename','function','offset','expected','replacement','expected_relocations','replacement_relocations','insert_after','omit')
        for i in range(8):
            for key in keys:
                bad=[dict(row) for row in rows];bad[i][key]='bad'
                with self.assertRaises(ValueError):source.checked_manifest(manifest(bad),self.out,self.obj)
        for key,value in (('expected','0x00000000'),('expected_relocations','R_MIPS_HI16:wrong')):
            bad=[dict(row) for row in rows];bad[2][key]=value
            path=self.out/('bad-'+key+'.csv');path.write_bytes(manifest(bad))
            with self.assertRaises((ValueError,AssertionError)):
                source.pad_c_object.emit_padded_assembly(self.obj,self.root/source.PATHS['layout'],source.OWNER,word_patches_path=path)
        self.receipt('fail-closed',raw_words=95,bindings=26,extra_binding=1,private_pool=1,
            guard_field_mutations=72,actual_padder_expected_word_and_binding_rejections=2)

    def test_06_independent_original_and_normalized_rebases(self):
        original=self.original('retail-original',(self.out/'before-view_init_original').read_text())
        ptext,pfunctions,prel=parse_object(self.padded)
        names=sorted({name for rows in source.RELOCATIONS.values() for _,name in rows})
        for index in range(3):
            entry=0x15207FF0+index*0x100000
            symbols={name:(entry+0x10000+n*0x100 if name.startswith('func_') or name=='allocate_memory' else
                0x80100000+n*0x10000+(0x7FFC,0x8004,0x7FD0)[index]) for n,name in enumerate(names)}
            emitted,unresolved=emit_function(ptext,pfunctions[source.FUNCTION],prel,source.FUNCTION,symbols)
            self.assertFalse(unresolved)
            asm=self.out/('normalized-rebase-%d.s'%index);asm.write_text(emitted);obj=asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],capture_output=True,check=True)
            images=[]
            for label,object_path in (('original',original),('normalized',obj)):
                script=self.out/('rebase-%s-%d.ld'%(label,index))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(object_path)],capture_output=True,check=True)
                images.append(sections(elf)['.text'][1][:380])
            self.assertEqual(images[0],images[1])
        self.receipt('rebases',original_GNU_links=3,normalized_independent_links=3,all95_words_compared=True,
            moved_count_LO16_and_HI16_carries=True)

    def test_07_original_caller_boundary_and_high_count_prefixes(self):
        caller=self.original('retail-caller',(self.out/'before-view_init_caller').read_text())
        data,functions=source.build.link_owner(self.root,self.out,caller,'game_34F20')
        f=functions['func_15007B3C'];full=data[f['value']:f['value']+f['size']]
        self.assertEqual(full,self.rom[0x34FEC:0x34FEC+f['size']])
        cut=list(struct.unpack_from('>4I',full,0x15007D90-0x15007B3C))
        self.assertEqual(cut,[0x3C04800C,0x8C84E9E8,0x0D406888,0x24050001])
        self.assertEqual(struct.unpack_from('>I',full,0x15007DA0-0x15007B3C)[0],0x0D404BE4)
        class Join(Exception):pass
        class Code(tracking.TrackedCode):
            def __getitem__(self,pc):
                if pc==0x15007DA0:raise Join
                return super().__getitem__(pc)
        class Caller(model.InitializationOracle):
            def record_call(self,target):
                if target==source.ENTRY:
                    args=self.arguments(2);self.calls.append((target,args));self.observations.append(model.digest(self.memory))
                else:super().record_call(target)
        count=0
        for request in (-1,0,1,4):
            for mode in range(10):
                memory=model.fixture(request,-1);model.put(memory,0x800BE9E8,request&0xFFFFFFFF)
                expected,calls,observations,_=model.reference(memory,request,1,mode)
                for words in (self.truth,self.raw,self.normalized):
                    connected={source.ENTRY+i*4:w for i,w in enumerate(words)};connected[0x15007DA0]=0
                    m=Caller(cut,memory,request,1,mode,entry=0x15007D90,connected=connected);m.code=Code(m.code,m)
                    with self.assertRaises(Join):m.run()
                    self.assertEqual((model.public(m.memory),m.calls,m.observations),
                        (model.public(expected),[(source.ENTRY,(request&0xFFFFFFFF,1))]+calls,[model.digest(memory)]+observations))
                    for r in (*range(16,24),28,29,30):self.assertEqual(m.r[r],m.before[r])
                count+=1
        for request in (0x7FFFFFFF,0x40000000):
            memory=model.fixture(request,240)
            expected,calls,observations,complete=model.reference(memory,request,0,limit=3)
            self.assertFalse(complete)
            for words in (self.truth,self.raw,self.normalized):
                m=model.InitializationOracle(words,memory,request,0,limit=3)
                with self.assertRaises(model.CallLimit):m.run()
                self.assertEqual((model.public(m.memory),m.calls,m.observations),(model.public(expected),calls,observations))
        self.receipt('caller',full_original_caller_words=len(full)//4,boundary_cases=count,actual_call_cut_words=4,
            source_caller_still_stub=True,linked_caller_or_full_startup_not_claimed=True,high_count_prefixes=2,
            billions_of_iterations_and_loop_wrap_not_dynamically_run=True)

    def test_08_normalized_fault_prefixes_are_literal_retail(self):
        count=0
        for request,height,mode in ((0,2,0),(1,-1,0),(1,2,6),(4,7,4),(-1,240,5),(1,240,2)):
            memory=model.fixture(request,height)
            full=model.InitializationOracle(self.truth,memory,request,0x87654321,mode).run()
            for fault in range(full.root_accesses):
                machines=[]
                for words in (self.truth,self.normalized):
                    m=model.InitializationOracle(words,memory,request,0x87654321,mode)
                    m.root_fault=fault
                    with self.assertRaises(tracking.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,fault);machines.append(m)
                state=lambda m:(m.memory,m.r,m.f,m.events,m.calls,m.current_pc,m.delay_of,m.observations,m.provider_counts)
                self.assertEqual(state(machines[0]),state(machines[1]));count+=1
        self.receipt('faults',fired_prefix_pairs=count,normalized_literal_retail=True,
            raw_fault_prefix_equivalence_not_claimed=True,hardware_exceptions_not_emulated=True)


if __name__=='__main__':unittest.main()
