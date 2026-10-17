"""Actual full scan padder, scratch/LO proof, rebases and positively fired controls."""
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_sequence_event_scan as source
from tools.experiments import game_sequence_event_scan_matching as fit
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import game_sequence_event_scan_oracle as model
from tools.tests import test_game_sequence_event_scan as recovery
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_sequence_record_setup_connected as setup_chain


def state(m): return (m.memory,m.r,m.f,m.lo,m.calls,m.events,m.raw_packets,m.cuts,m.fired,m.current_pc,m.delay_of,m.all_accesses)


def color_reference(memory,packet):
    red,green,blue,duration,flag,channel=packet
    byte=(flag^128)-128; old=(model.read(memory,0x800DDDAC+channel,1)^128)-128
    ticks=model.signed(model.read(memory,0x800DDDB0+channel*4))
    limit=model.signed(model.read(memory,0x800DDE28+channel*4))
    if byte!=old or ticks<limit or model.read(memory,0x800DDDC0+channel,1):
        for i,value in enumerate((red,green,blue)):model.put(memory,0x800DDDA0+channel*3+i,value,1)
        model.put(memory,0x800DDE28+channel*4,duration);model.put(memory,0x800DDDB0+channel*4,0)
        model.put(memory,0x800DDDAC+channel,flag,1);model.put(memory,0x800DDDC0+channel,0,1)


class ColorReference(model.Reference):
    def call(self,target,packet,ordinal=None):
        result=super().call(target,packet,ordinal)
        if target==model.COLOR:color_reference(self.memory,packet)
        return result


class SetupReference(setup_chain.Reference):
    def call(self,target,*args):
        result=super().call(target,*args)
        if target==source.ENTRY:
            self.child=ColorReference(self.memory,(args[0],),self.scan_config).run()
            self.memory=self.child.memory
        return result


class SetupOracle(setup_chain.Connected):
    def __init__(self,words,memory,args,config,plan,scan_config,helpers):
        super().__init__(words,memory,args,config,plan,entry=0x1501D348,helpers=helpers)
        self.slot=args[2];self.config=scan_config;self.raw_packets=[];self.cuts=[];self.fired=[];self.snapshots=[]

    def execute(self,word):
        if word>>26==32:model.load_signed_byte(self,word)
        else:super().execute(word)

    def record_call(self,target):
        if target in (model.QUERY,model.COLOR):model.EventOracle.record_call(self,target)
        else:super().record_call(target)

    def hook(self,target):
        if target in (model.QUERY,model.COLOR):model.EventOracle.hook(self,target)
        else:super().hook(target)


class SequenceEventScanMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/fit.BUILD
        cls.obj,cls.padded,cls.guarded,cls.qualification=fit.guarded(cls.root,cls.out)
        cls.raw,cls.bindings,_=fit.parts(cls.obj)
        cls.original=cls.out/'original-event-scan-match.o';cls.wanted,cls.wanted_bindings,_=fit.parts(cls.original)
        data,functions=source.build.link_owner(cls.root,cls.out,cls.obj,source.OWNER)
        cls.compiled=fit.linked_words(data,functions[source.FUNCTION])
        cls.truth=list(struct.unpack_from('>219I',(cls.out/'before-retail_rom').read_bytes(),source.ROM))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_all219_words_actual_padder_and_56_raw_padded_neighbors(self):
        self.assertEqual(self.guarded,self.truth);self.assertEqual(self.qualification['guards'],77)
        before,diagnostics=source.compile_owner(self.root,self.out,(self.out/'before-view_list_caller_owner').read_text(),'neighbor-before',True)
        self.assertEqual(diagnostics,'');self.assertEqual(same_functions(before,self.obj,(source.FUNCTION,)),56)
        script=self.out/'neighbor-before-padded.s';script.write_text(emit_padded_assembly(before,
            self.out/'before-view_list_caller_original',word_patches_path=self.out/'before-guards',filename=source.OWNER))
        padded=script.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],capture_output=True,check=True)
        self.assertEqual(same_functions(padded,self.padded,(source.FUNCTION,)),56)
        a=(self.out/'before-guards').read_bytes();b=(self.out/'qualified-guards.csv').read_bytes();fit.checked_guards(a,b)
        self.assertEqual(a.count(b'\r\n'),298);self.assertTrue(b.startswith(a))
        self.receipt('matched-owner',all219_words=True,guards=77,insertions=0,omissions=0,
            frame=128,homes_and_saved_roles_emit_directly=True,unchanged_raw_neighbors=56,
            unchanged_padded_neighbors=56,old_guard_bytes_and_298_CRLF_lines_preserved=True,not_installed=True)

    def test_02_three_way_full_memory_call_cut_roles_homes_and_all_words(self):
        count=0;seen=[set(),set(),set()]
        for memory,args,config in model.cases():
            ref=model.Reference(memory,args,config).run()
            for phase in (0,8):
                machines=[]
                for i,words in enumerate((self.truth,self.compiled,self.guarded)):
                    m=model.EventOracle(words,memory,args,config,phase).run()
                    self.assertTrue(model.public(m.memory)==model.public(ref.memory),(args,config,phase,i))
                    self.assertEqual(m.calls,ref.calls);self.assertEqual(m.fired,ref.fired)
                    seen[i].update(m.visits);machines.append(m)
                for m in machines[1:]:
                    self.assertTrue(m.memory==machines[0].memory,(args,config,phase))
                    self.assertEqual(m.cuts,machines[0].cuts)
                self.assertTrue(state(machines[0])==state(machines[2]),(args,config,phase));count+=1
        for visited in seen:self.assertTrue(set(range(source.ENTRY,source.ENTRY+876,4))<=visited)
        self.receipt('matched-guest',three_way_cases=count,all219_words_each=True,
            full_memory_including_private_stack_and_saved_roles_at_every_call=True,
            original_guarded_literal_GPR_FPR_LO_PC_delay_and_events=True,
            raw_C_reordered_load_store_and_empty_path_delay_not_fault_equivalent=True)

    def test_03_schedule_live_operands_loop_LO_and_call_contract_controls(self):
        normalized,moved,_=fit.schedule(self.raw,self.bindings)
        for at in (0x4C,0x64,0x68,0x70,0x74,0x78,0x90):
            bad=list(self.raw);bad[at//4]^=1
            with self.assertRaises(ValueError):fit.schedule(bad,self.bindings)
        bad=list(self.raw);bad[0x324//4]=0x03004021
        with self.assertRaisesRegex(ValueError,'Empty path'):fit.schedule(bad,self.bindings)
        for at,shift in ((0xC4,16),(0xEC,16),(0x318,16)):
            bad=list(self.wanted);bad[at//4]=bad[at//4]&~(31<<shift)|(14<<shift)
            with self.assertRaises(ValueError):fit.certify(normalized,bad,moved)
        a=list(normalized);b=list(self.wanted);a[0x2B0//4]=b[0x2B0//4]=0x0000C012
        with self.assertRaisesRegex(ValueError,'Unrelated scan LO'):fit.certify(a,b,moved)
        bad=dict(moved);bad[0xE4]=[('R_MIPS_26','unknown')]
        with self.assertRaisesRegex(ValueError,'Unknown event scan call'):fit.certify(normalized,self.wanted,bad)
        self.receipt('matched-proof-controls',opening_controls=8,live_store_load_and_backedge_controls=3,
            effective_unrelated_LO_and_unknown_call_controls=True,proofs_execute_beyond_hash_gates=True)

    def test_04_all_words_bindings_pools_and_847_guard_fields_rejected(self):
        for original,words in ((False,self.raw),(True,self.wanted)):
            for i in range(len(words)):
                bad=list(words);bad[i]^=1
                with self.assertRaises(ValueError):fit.checked_pair(self.raw if original else bad,self.bindings,
                    bad if original else self.wanted,self.wanted_bindings)
        for original,uses in ((False,self.bindings),(True,self.wanted_bindings)):
            for at in (*uses,-4):
                bad=dict(uses);bad[at]=[('R_MIPS_HI16','wrong')]
                with self.assertRaises(ValueError):fit.checked_pair(self.raw,self.bindings if original else bad,
                    self.wanted,bad if original else self.wanted_bindings)
        with patch.object(source,'sections',return_value={'.data':(0,b'bad')}):
            for obj in (self.obj,self.original):
                with self.assertRaises(ValueError):fit.parts(obj)
        before=(self.out/'before-guards').read_bytes();after=(self.out/'qualified-guards.csv').read_bytes()
        names=next(csv.reader(io.StringIO(before.decode())));rows=list(csv.DictReader(io.StringIO(after[len(before):].decode()),fieldnames=names));count=0
        for row in rows:
            for name in names:
                value=row[name];row[name]='bad';stream=io.StringIO(newline='')
                csv.DictWriter(stream,fieldnames=names,lineterminator='\n').writerows(rows)
                with self.assertRaises(ValueError):fit.checked_guards(before,before+stream.getvalue().encode())
                row[name]=value;count+=1
        self.assertEqual(count,847)
        with self.assertRaises(ValueError):fit.checked_guards(before+b'\n',after)
        self.receipt('matched-input-controls',word_corruptions=438,binding_corruptions=78,
            guard_field_corruptions=count,unexpected_private_pools_and_guard_predecessor_rejected=True)

    def test_05_three_independent_original_guarded_carry_rebases(self):
        text,functions,relocations=parse_object(self.padded)
        names=sorted({name for uses in self.bindings.values() for _,name in uses});code=set(fit.CALLS)
        for index in range(3):
            entry=0x15207FF0+index*0x100000
            symbols={name:entry+0x10000+n*0x1000 if name in code else
                0x80100000+n*0x10000+(0x7FFC,0x8004,0x7FD0)[index] for n,name in enumerate(names)}
            emitted,unresolved=emit_function(text,functions[source.FUNCTION],relocations,source.FUNCTION,symbols)
            self.assertFalse(unresolved);asm=self.out/('rebase-C-%d.s'%index);asm.write_text(emitted);obj=asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],capture_output=True,check=True)
            images=[]
            for label,path in (('original',self.original),('C',obj)):
                script=self.out/('rebase-%s-%d.ld'%(label,index));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(path)],capture_output=True,check=True)
                images.append(source.sections(elf)['.text'][1][:876])
            self.assertEqual(images[0],images[1])
        self.receipt('matched-rebases',independent_original_links=3,independent_guarded_links=3,all219_words=True,HI_LO_carries=True)

    def test_06_original_guarded_every_fired_access_fault_prefix(self):
        count=0
        for fixture,phase in ((model.fixture(),0),(model.fixture(slot=1,mode=31),8),(model.fixture(count=0),0)):
            memory,args,config=fixture;full=model.EventOracle(self.truth,memory,args,config,phase).run()
            for fault in range(full.all_accesses):
                machines=[]
                for words in (self.truth,self.guarded):
                    m=model.EventOracle(words,memory,args,config,phase);m.access_fault=fault
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault);machines.append(m)
                self.assertTrue(state(machines[0])==state(machines[1]),(phase,fault));count+=1
        self.receipt('matched-faults',positively_fired_original_guarded_prefixes=count,
            literal_memory_GPR_FPR_LO_events_PC_delay_and_provider_state=True,
            bounded_hook_bulk_accesses_not_instruction_level_callee_emulation=True,
            raw_C_fault_equivalence_not_claimed=True)

    def test_07_complete_native32_C_and_effective_controls(self):
        recovery.SequenceEventScanTests.test_05_full_native32_C_O2_O0_UBSan_and_seven_effective_controls(self)

    def test_08_actual_48word_color_helper_linked_and_opaque_query_boundary(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        obj=assembly.ViewListSetupTests.original.__func__(context,'actual-color-provider',
            (self.out/'before-color_provider_original').read_text(),'func_1517EE40')
        data,functions=source.build.link_owner(self.root,self.out,obj,'generated_1AC2F0')
        function=functions['func_1517EE40'];body=data[function['value']:function['value']+function['size']]
        self.assertEqual(len(body),192)
        self.assertEqual(body,(self.out/'before-retail_rom').read_bytes()[0x1AC2F0:0x1AC3B0])
        helper=dict(zip(range(model.COLOR,model.COLOR+192,4),struct.unpack('>48I',body)));count=0;seen=set()
        for slot,pattern,flag,ticks,limit,busy in itertools.product((0,1),(0,3,8),(0,1),(0,2),(0,1),(0,1)):
            memory,args,config=model.fixture(slot=slot,pattern=pattern)
            memory.update({0x800DDDA0+i:0xA5 for i in range(0x90)})
            for at,value,width in ((0x800DDDAC,flag,1),(0x800DDDB0,ticks,4),(0x800DDE28,limit,4),(0x800DDDC0,busy,1)):
                model.put(memory,at,value,width)
            ref=ColorReference(memory,args,config).run();machines=[]
            for words in (self.truth,self.compiled,self.guarded):
                m=model.EventOracle(words,memory,args,config,helpers=helper).run()
                self.assertTrue(model.public(m.memory)==model.public(ref.memory),(slot,pattern,flag,ticks,limit,busy))
                self.assertEqual(m.calls,ref.calls);seen.update(m.visits);machines.append(m)
            self.assertTrue(state(machines[0])==state(machines[2]));count+=1
        self.assertTrue(set(helper)<=seen)
        self.receipt('matched-color-chain',three_way_cases=count,actual_color_helper_words=48,all48_executed=True,
            independent_color_state_reference=True,query_provider_still_opaque=True,
            not_full_sequence_query_or_rendering_acceptance=True)

    def test_09_complete_actual_setup_caller_six_helpers_scan_and_color_chain(self):
        setup=list(struct.unpack_from('>473I',(self.out/'before-retail_rom').read_bytes(),0x4A7F8))
        data,functions=source.build.link_owner(self.root,self.out,self.padded,source.OWNER);helpers={}
        for entry,length in setup_chain.HELPERS:
            function=functions['func_%08X'%entry];self.assertEqual(function['size'],length*4)
            body=data[function['value']:function['value']+length*4]
            self.assertEqual(body,(self.out/'before-retail_rom').read_bytes()[entry-0x15000000+0x2D4B0:entry-0x15000000+0x2D4B0+length*4])
            helpers.update(zip(range(entry,entry+length*4,4),struct.unpack('>%dI'%length,body)))
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        obj=assembly.ViewListSetupTests.original.__func__(context,'setup-actual-color',
            (self.out/'before-color_provider_original').read_text(),'func_1517EE40')
        color,fs=source.build.link_owner(self.root,self.out,obj,'generated_1AC2F0');function=fs['func_1517EE40']
        helpers.update(zip(range(model.COLOR,model.COLOR+192,4),struct.unpack_from('>48I',color,function['value'])))
        count=0
        for slot,records,pattern in itertools.product((0,1),(0,1,3),(0,3,8)):
            memory,args,config=setup_chain.fixture(slot=slot,count=records)
            scan_memory,_,scan_config=model.fixture(slot=slot,pattern=pattern)
            for at,value in scan_memory.items():
                if model.EVENTS<=at<model.EVENTS+768 or model.COLORS<=at<model.COLORS+8:memory[at]=value
            memory.update({0x800DDDA0+i:0xA5 for i in range(0x90)})
            reference=SetupReference(memory,args,config);reference.scan_config=scan_config;reference.run()
            machines=[]
            for words in (self.truth,self.compiled,self.guarded):
                connected=dict(helpers);connected.update(zip(range(source.ENTRY,source.ENTRY+876,4),words))
                m=SetupOracle(setup,memory,args,config,reference.allocations,scan_config,connected).run()
                self.assertTrue(model.public(m.memory)==model.public(reference.memory),(slot,records,pattern))
                self.assertEqual([c for c in m.calls if c[0] in (model.QUERY,model.COLOR)],reference.child.calls)
                machines.append(m)
            self.assertTrue(state(machines[0])==state(machines[2]));count+=1
        self.receipt('matched-setup-chain',three_way_cases=count,actual_setup_caller_words=473,
            actual_six_setup_helpers_words=304,actual_scan_words=219,actual_color_words=48,
            independent_composed_reference=True,resource_query_and_allocation_still_bounded=True,
            not_full_sequence_engine_or_gameplay_acceptance=True)


if __name__=='__main__':unittest.main()
