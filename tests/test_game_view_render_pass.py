"""215-word view rendering: gates, live providers, guarded roles and ABI."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_view_render_pass as source
from tools.tests import game_view_render_pass_oracle as model
from tools.tests import game_view_render_pass_native as native
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_projected_packet_draw import native_command


class ViewRenderPassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.raw,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>215I',cls.rom,source.ROM))
        data,functions=source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.words=list(struct.unpack_from('>215I',data,functions[source.FUNCTION]['value']))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_full215_frame_homes_closed_roles_and_15_neighbors(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['new_guards']),(215,48,5,5))
        self.assertEqual(self.words[22],0xAFB9002C)
        before=(self.out/'before-dispatch_owner').read_text()
        after=source.recovered_owner(before)
        self.assertIn('s32 func_15018E88(void *arg0, s16 arg1)',after)
        self.assertIn('return func_15174AA4(arg0, D_800BE9F0, arg1);',after)
        old,new=parse_object(self.out/'neighbor-before.o'),parse_object(self.obj)
        bindings=lambda parsed,f:{a-f['value']:v for a,v in parsed[2].items() if f['value']<=a<f['value']+f['size']}
        self.assertEqual(set(old[1]),set(new[1]))
        for name,f in old[1].items():
            if name==source.FUNCTION:continue
            g=new[1][name]
            self.assertEqual(old[0][f['value']:f['value']+f['size']],new[0][g['value']:g['value']+g['size']],name)
            self.assertEqual(bindings(old,f),bindings(new,g),name)
        self.assertEqual(len(old[1])-1,15)
        self.assertEqual(source.previous.warning_sites(before,(self.out/'neighbor-before-diagnostics.txt').read_text()),
            source.previous.warning_sites(after,self.row['diagnostics']))
        # T8 and T9 are dead after their commutative address sum; neither is a saved role.
        self.assertEqual(self.raw[0x108//4],self.truth[0x108//4])
        self.assertEqual(self.truth[0x108//4],0x03194021)

    def compare(self,view,count,pattern,gate,mode,phase=0,raw_view=None):
        raw_view=view if raw_view is None else raw_view
        memory=model.fixture(view,count,pattern,gate)
        expected,calls,observations,_,fired,value=model.reference(memory,raw_view,pattern,gate,mode)
        models=[]
        for words in (self.truth,self.raw,self.words):
            m=model.RenderOracle(words,memory,raw_view,pattern,gate,mode,phase).run()
            self.assertEqual((model.public(m.memory),m.calls,m.observations,m.fired,m.r[2]),
                (model.public(expected),calls,observations,fired,value),(view,count,pattern,gate,mode,phase))
            models.append(m)
        self.assertEqual(model.state(models[0]),model.state(models[2]))
        return models[0]

    def test_02_all_gates_orders_live_globals_and_complete_instruction_coverage(self):
        count,visits,fired=0,set(),set()
        for view,views,pattern,mode,phase in itertools.product(range(4),(-1,0,1),range(4),range(7),(0,8)):
            m=self.compare(view,views,pattern,0,mode,phase)
            visits.update(m.visits);fired.update(m.fired);count+=1
        for view,pattern,gate in itertools.product(range(4),range(4),(1,2,3,4)):
            m=self.compare(view,1,pattern,gate,0)
            visits.update(m.visits);count+=1
        for views in (-0x80000000,0x7FFFFFFF):
            for view in range(4):self.compare(view,views,2,0,0);count+=1
        for raw_view in (0x12340002,0xABCD0003,0xFFFF0001):
            self.compare(raw_view&65535,1,2,0,0,raw_view=raw_view);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+860,4)))
        self.assertEqual({mode for _,_,mode in fired},set(range(1,7)))
        self.receipt('guest',three_way_cases=count,root_words_visited=len(visits),fired_effect_sites=len(fired),
            raw_C_public_protocol_equivalence=True,guarded_original_complete_modeled_state=True,
            active_C_domain='four valid allocated views; no portable out-of-range pointer/shift claim',
            opaque_helpers_are_contracts_not_rendering_or_gameplay=True)

    def test_03_every_access_fault_prefix_on_representative_paths(self):
        count=0
        for view,views,pattern,gate,mode in ((0,1,2,0,0),(3,0,3,0,5),(1,1,0,0,3),(2,1,2,0,6),(0,1,0,1,0),(1,1,1,3,0)):
            memory=model.fixture(view,views,pattern,gate)
            complete=model.RenderOracle(self.words,memory,view,pattern,gate,mode).run()
            for cut in range(complete.root_accesses):
                models=[model.RenderOracle(words,memory,view,pattern,gate,mode,fault=cut) for words in (self.truth,self.words)]
                for m in models:
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut)
                self.assertEqual(model.state(models[0]),model.state(models[1]));count+=1
        self.receipt('faults',fired_memory_access_prefix_pairs=count,paths=6,portable_C_fault_semantics_claim=False)

    def test_04_every_object_word_binding_pool_and_guard_history_is_fail_closed(self):
        text,functions,relocations=parse_object(self.obj)
        f=functions[source.FUNCTION]
        for index in range(215):
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
        guards=source.guarded_manifest(self.out,self.obj)
        self.assertTrue(guards.startswith((self.out/'before-guards').read_bytes()))
        self.assertEqual(len(source.derived_guards(self.obj)),5)
        self.assertEqual(sum(bool(v['expected_relocations']!='-') for v in source.derived_guards(self.obj)),2)

    def test_05_independent_original_and_padded_three_HI_LO_carry_links(self):
        text,functions,relocations=parse_object(self.padded)
        f=functions[source.FUNCTION]
        anchors={name:int(name.split('_',1)[1],16) for rows in source.RELOCATIONS.values() for _,name in rows}
        original='.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+(self.out/'before-render_assembly').read_text()
        original_path=self.out/'independent-retail.s';original_path.write_text(original)
        original_obj=original_path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(original_obj),str(original_path)],capture_output=True,check=True)
        for index,entry in enumerate((source.ENTRY,0x15207FF0,0x15318004)):
            symbols={name:(value if not index else (value+index*0x200000)&0xFFFFFFFF) for name,value in anchors.items()}
            if index:
                for n,name in enumerate(sorted(k for k in symbols if k.startswith('D_'))):
                    symbols[name]=0x80100000+index*0x100000+n*0x10000+(0x7FFC if n%2 else 0x8004)
            emitted,unresolved=emit_function(text,f,relocations,source.FUNCTION,symbols)
            self.assertFalse(unresolved)
            path=self.out/('rebase-%d-source.s'%index);path.write_text(emitted)
            obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            script=path.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            results=[]
            for label,input_obj in (('retail',original_obj),('source',obj)):
                elf=self.out/('rebase-%d-%s.elf'%(index,label))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(input_obj)],capture_output=True,check=True)
                results.append(sections(elf)['.text'][1][:860])
            self.assertEqual(results[0],results[1])
        self.receipt('rebases',independent_original_source_links=3,complete_words=215,HI_LO_carry_and_JAL=True)

    def test_06_native32_actual_C_O2_O0_UBSan_and_effective_controls(self):
        harness=self.out/'native.c';harness.write_text(native.program())
        exits={}
        for name,opt,body in [('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[
                (name,'-O2',body) for name,body in native.controls().items()]:
            unit=self.out/('native-'+name+'.c');unit.write_text(native.HEADER+body+'\n')
            exe=unit.with_suffix('.elf')
            result=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',
                str(unit.relative_to(self.root)),str(harness.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True)
            exits[name]=run.returncode
            if name in ('o2','o0'):self.assertEqual(run.returncode,0,run.stderr)
            else:self.assertIn(run.returncode,range(21,28),name)
        self.receipt('native',cases_each=len(list(native.corpus())),exits=exits,
            actual_C_both_optimizations_and_UBSan=True,full_cursor_buffer_and_struct_canaries=True,
            opaque_packets_previously_checked_against_retail_guest=True)

    def test_07_actual_neighbor_cursor_return_and_pointer_out_lifetimes(self):
        extra={0x15174AA4:3,0x15174B48:3,0x1517D7B0:2}
        signatures=dict(model.SIGNATURES)
        signatures.update(extra)
        class HelperOracle(model.RenderOracle):
            def hook(self,target):
                args=self.calls[-1][1]
                old=self.get(args[0],4) if target==0x1517D7B0 else None
                super().hook(target)
                if old is not None:self.put(args[0],old+24,4)
        data,functions=source.build.link_owner(self.root,self.out,self.padded,source.OWNER)
        cases=0
        for name,count in (('func_15018E88',32),('func_15018F08',30)):
            address=int(name[5:],16);f=functions[name]
            words=list(struct.unpack_from('>%dI'%count,data,f['value']))
            self.assertEqual(words,list(struct.unpack_from('>%dI'%count,self.rom,address-0x15000000+0x2D4B0)))
            for view,pattern,disabled,phase in itertools.product(range(4),range(4),(0,255),(0,8)):
                memory=model.fixture(view,1,pattern)
                memory[0x800BE616]=disabled;model.put(memory,0x800BE9F0,0x12348001)
                cursor,expected,counts=model.CURSOR,[],{}
                def call(target,*args):
                    nonlocal cursor
                    expected.append((target,tuple(a&0xFFFFFFFF for a in args)))
                    counts[target]=counts.get(target,0)+1
                    return model.returned(target,args,counts[target],pattern,0)
                if name=='func_15018E88':
                    if not disabled:call(0x1517D7B0,model.STACK+phase,1);cursor+=24
                    cursor=call(0x151674F8,cursor,0,view,0)
                    cursor=call(0x151674F8,cursor,0,view,1)
                    cursor=call(0x15174AA4,cursor,0x12348001,view)
                else:
                    cursor=call(0x15174B48,cursor,0x12348001,view)
                    cursor=call(0x151674F8,cursor,1,view,0)
                    cursor=call(0x151674F8,cursor,1,view,1)
                    call(0x1517D7B0,model.STACK+phase,2);cursor+=24
                with patch.object(model,'SIGNATURES',signatures):
                    m=HelperOracle(words,memory,view,pattern,phase=phase,entry=address).run()
                self.assertEqual((m.calls,m.r[2]),(expected,cursor))
                self.assertEqual(model.public(m.memory),model.public(memory));cases+=1
        self.receipt('neighbor-ABI',actual_retail_and_C_words=[32,30],cases=cases,
            recovered_cursor_return_and_mutable_pointer_out=True,SDK_helpers_remain_contracts=True)


if __name__=='__main__':unittest.main()
