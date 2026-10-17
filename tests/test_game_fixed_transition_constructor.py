"""Direct constructor, actual factory/copies, original caller and whole image."""
from functools import lru_cache
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_fixed_transition_constructor as source
from tools.experiments import game_fixed_transition_installation as install
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_fixed_transition_oracle as model
from tools.tests import game_fixed_transition_native as native
from tools.tests import fixed_transition_checkpoint as checkpoint
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols
from tools.check_game_data_layout import audit_layout


def state(m):
    return model.point.state(m),m.io,m.forwarded,m.descriptors,m.payloads,m.copies


class FixedTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]; cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>96I',cls.rom,source.ROM))
        cls.factory,cls.copy=model.helper_words(cls.rom)
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-constructor',
            (cls.out/'before-tile_original').read_text(),source.FUNCTION)
        cls.original_factory=assembly.ViewListSetupTests.original.__func__(context,'original-factory',
            (cls.out/'before-transition_factory').read_text(),'func_1515548C')

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_all96_raw_padded_words_correct_frame_bindings_and24_neighbors(self):
        self.assertEqual(self.images,[self.truth,self.truth])
        self.assertEqual(self.row,dict(words=96,frame=152,prologue_word=3,bindings=4,new_guards=0,
            unchanged_raw_padded_neighbors=24))
        source.checked_parts(*source.parts(self.obj))

    def test_02_full_memory_reference_actual_factory_copies_padding_and_clobbers(self):
        count=0; seen=set(); factory_seen=set(); padding=set()
        for memory,args,phase,outcome,mode in model.cases():
            expected,calls=model.reference(memory,args,phase,outcome,mode)
            initial=dict(memory); sp=model.STACK+phase-152
            model.descriptor(initial,sp+0x40,args[0],model.read(initial,source.MODE))
            model.payload(initial,sp+0x30)
            descriptor=bytes(model.read(initial,sp+0x40+i,1) for i in range(88))
            payload=bytes(model.read(initial,sp+0x30+i,1) for i in range(16))
            states=[]
            for words in (self.truth,*self.images):
                m=model.ConstructorOracle(words,memory,args,self.factory,self.copy,phase,outcome,mode)
                m.f[:20]=[0x7FC12345+i for i in range(20)]
                m.run()
                self.assertEqual(m.memory,expected,(args,phase,outcome,mode))
                self.assertEqual(m.calls,calls)
                self.assertEqual((m.descriptors,m.payloads),([descriptor],[payload]))
                if outcome:
                    event=model.EVENT+outcome-1
                    copied=bytes(expected[event+16+i] for i in range(88))
                    attached=bytes(expected[event+112+i] for i in range(16))
                    self.assertEqual(m.copies,[copied,attached])
                    self.assertTrue(set(range(source.MEMCPY,source.MEMCPY+44,4))<=m.visits)
                    padding.update(copied[i] for i in model.DESCRIPTOR_PADDING)
                    padding.update(attached[i] for i in model.PAYLOAD_PADDING)
                else:
                    self.assertFalse(m.copies)
                for register in (*range(16,24),28,29,30,31):
                    self.assertEqual(m.r[register],m.before[register])
                seen.update(m.visits)
                factory_seen.update(pc-source.FACTORY for pc in m.visits if source.FACTORY<=pc<source.FACTORY+216)
                states.append(state(m))
            self.assertTrue(states[0]==states[1]==states[2]); count+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+source.SIZE,4))<=seen)
        self.assertNotIn(source.FACTORY+7*4,seen)
        self.assertNotIn(source.FACTORY+112,seen)
        self.assertIn(0x5A,padding); self.assertIn(0xA0,padding)
        self.receipt('guest',three_way_cases=count,natural_constructor_words=96,connected_factory_words=54,
            visited_factory_offsets=sorted(factory_seen),actual_memcpy_words=11,copied_lengths=[88,16],
            all_memory_and_nine_live_padding_bytes=True,arbitrary_initial_volatile_FP=True,
            lower_allocator_is_scripted=True,optional_pair_factory_branch_not_qualified=True,
            flag_clear_factory_path_not_qualified=True)

    def test_03_native32_full_body_typed_caller_ten_controls_and_padding_limit(self):
        caller,driver=self.out/'native-caller.c',self.out/'native-driver.c'
        caller.write_text(native.CALLER); driver.write_text(native.DRIVER)
        forms=[('o2','-O2',source.SELECTED,0),('o0','-O0',source.SELECTED,0),
            ('zero-padding','-O2',native.ZERO_PADDING,0)]
        forms += [(n,'-O2',b,22) for n,b in native.controls(source.SELECTED).items()]
        exits={}
        for name,opt,body,wanted in forms:
            unit=self.out/('native-'+name+'.c'); unit.write_text(native.HEADER+body+'\n'); exe=unit.with_suffix('.elf')
            result=subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double',
                *[str(p.relative_to(self.root)) for p in (unit,caller,driver)],'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120)
            exits[name]=ran.returncode; self.assertEqual(ran.returncode,wanted,(name,ran.stderr))
        obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(
            (self.out/'before-tile_owner').read_text(),native.ZERO_PADDING),'zero-padding')
        self.assertFalse(diag)
        data,functions=source.build.link_owner(self.root,self.out,obj,source.OWNER); f=functions[source.FUNCTION]
        words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
        with self.assertRaises(ValueError):
            source.checked_parts(*source.parts(obj))
        args=(0xFFFF,255,0x8765ABCD); memory=model.fixture(0x10002)
        original=model.ConstructorOracle(self.truth,memory,args,self.factory,self.copy).run()
        changed=model.ConstructorOracle(words,memory,args,self.factory,self.copy).run()
        self.assertNotEqual(original.memory,changed.memory)
        for at in (model.EVENT+16+17,model.EVENT+112+1):
            self.assertNotEqual(original.memory[at],0); self.assertEqual(changed.memory[at],0)
        self.receipt('native',cases_each=864,exits=exits,UBSan=True,separate_full_body_and_typed_caller=True,
            descriptor_size=88,payload_size=16,all95_initialized_bytes_and_external_canaries=True,
            nine_padding_bytes_excluded_only=True,zero_padding_passes_native_but_changes_guest=True,
            not_portable_padding_or_heap_allocator_acceptance=True)

    def link(self,obj,entry,anchors,count,label,name=source.FUNCTION):
        script=self.out/(label+'.ld'); script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        elf=script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,
            *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
        return list(struct.unpack('>%dI'%count,source.projection.sections(elf)['.text'][1][:count*4]))

    def test_04_independent_constructor_factory_and_copy_rebases(self):
        raw,bindings=source.parts(self.obj); count=0
        for index,mode_address in enumerate((0x80117FFC,0x80128004,0x80127FFC)):
            entry=0x15208004+index*0x10000; factory=0x16317FFC+index*0x10000
            allocator=0x17428004+index*0x10000; copy=0x18537FFC+index*0x10000
            anchors=dict(D_80082FA0=mode_address,func_1515548C=factory,memcpy=copy)
            text,unresolved=emit_function(raw,dict(value=0,size=source.SIZE),bindings,source.FUNCTION,anchors)
            self.assertFalse(unresolved)
            path=self.out/('rebase-C-%d.s'%index); path.write_text(text); obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            original=self.link(self.original,entry,anchors,96,'rebase-original-%d'%index)
            candidate=self.link(obj,entry,anchors,96,'rebase-C-%d'%index)
            self.assertEqual(original,candidate)
            helper=self.link(self.original_factory,factory,
                dict(func_15167A68=allocator,memcpy=copy,func_151555AC=0x151555AC),54,'rebase-factory-%d'%index,'func_1515548C')
            for variant,outcome,mode,phase in itertools.product(range(8),(0,1,2),(0,1,2),(0,8)):
                memory=model.fixture(0x80000000+variant,mode_address=mode_address)
                args=(0x8000+variant,0x10081+variant,0x8765ABCD)
                expected,calls=model.reference(memory,args,phase,outcome,mode,entry,factory,allocator,copy,mode_address)
                m=model.ConstructorOracle(candidate,memory,args,helper,self.copy,phase,outcome,mode,
                    entry=entry,constructor=entry,factory=factory,allocator=allocator,memcpy=copy,mode_address=mode_address).run()
                self.assertEqual((m.memory,m.calls),(expected,calls)); count+=1
        self.receipt('rebases',independent_constructor_link_pairs=3,independent_factory_links=3,state_cases=count,
            all96_constructor_words_exact=True,global_signed_low_carries_and_all_helper_targets=True,
            optional_factory_pair_path_not_qualified=True)

    def test_05_every_actual_access_fault_prefix_full_state_and_live_padding(self):
        count=0; totals=[]
        for outcome,mode,phase in itertools.product((0,1),(0,2),(0,8)):
            memory=model.fixture(255); args=(0x8001,0x10081,0x8765ABCD)
            completed=model.ConstructorOracle(self.truth,memory,args,self.factory,self.copy,phase,outcome,mode).run()
            totals.append(completed.all_accesses)
            for fault in range(completed.all_accesses):
                states=[]
                for words in (self.truth,*self.images):
                    m=model.ConstructorOracle(words,memory,args,self.factory,self.copy,phase,outcome,mode)
                    m.access_fault=fault
                    with self.assertRaises(faults.AccessBoundary):
                        m.run()
                    self.assertEqual(m.all_accesses,fault); states.append(state(m))
                self.assertTrue(states[0]==states[1]==states[2]); count+=1
        self.receipt('faults',three_way_positively_fired_prefixes=count,accesses_each=totals,
            actual_constructor_factory_and_both_copies=True,not_portable_C_CP0_or_hardware_timing=True)

    def test_06_all96_word_five_binding_and182_input_corruptions_fail_closed(self):
        raw,bindings=source.parts(self.obj)
        for i in range(96):
            bad=bytearray(raw); bad[i*4]^=1
            with self.assertRaises(ValueError):
                source.checked_parts(bytes(bad),bindings)
        for at in (*bindings,-4):
            bad=dict(bindings); bad[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):
                source.checked_parts(raw,bad)
        read=lru_cache(None)(Path.read_bytes)
        self.assertEqual(len(source.PATHS),182)
        for relative in source.PATHS.values():
            target=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==target else read(p)):
                with self.assertRaises(ValueError):
                    source.freeze(self.root,self.out)
        source.freeze(self.root,self.out)
        self.receipt('inputs',word_controls=96,binding_controls=5,protected_entries=182,
            distinct_paths=len(set(source.PATHS.values())),all_live_inputs_reread=True)

    def test_07_actual_caller_six_word_packet_narrow_inputs_and_later_return_one(self):
        entry,join=0x15027A04,0x15029BA4
        packet=list(struct.unpack_from('>6I',self.rom,0x54EB4))
        class Join(Exception):
            pass
        class Code(faults.TrackedCode):
            def __getitem__(self,pc):
                if pc==join:
                    raise Join
                return super().__getitem__(pc)
        count=0
        for id,slot,view,outcome,mode,phase in itertools.product((0,32767,32768,65535),
                (0,1,255),(0,0x10002,0x80000003),(0,1),(0,2),(0,8)):
            memory=model.fixture(view); args=(((id^32768)-32768)&0xFFFFFFFF,slot,1)
            for offset,size in ((0x662,2),(0x773,1)):
                for i in range(size):
                    memory[model.STACK+phase+offset+i]=0xA5
            model.put(memory,model.STACK+phase+0x662,id,2)
            model.put(memory,model.STACK+phase+0x773,slot,1)
            expected,calls=model.reference(memory,args,phase,outcome,mode,return_address=entry+16)
            states=[]
            for words in (self.truth,*self.images):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+source.SIZE,4),words)); connected[join]=0
                m=model.ConstructorOracle(packet,memory,(0xBAD00BAD,0xBAD00BAD,0xBAD00BAD),self.factory,self.copy,
                    phase,outcome,mode,entry=entry,connected=connected)
                m.code=Code(m.code,m)
                with self.assertRaises(Join):
                    m.run()
                self.assertEqual((m.memory,m.calls),(expected,calls))
                self.assertEqual(m.forwarded,[args]); self.assertEqual(m.r[2],1)
                self.assertEqual(m.r[29],model.STACK+phase)
                states.append(state(m))
            self.assertTrue(states[0]==states[1]==states[2]); count+=1
        self.receipt('caller',three_way_cases=count,original_words=6,actual_constructor_factory_and_copy=True,
            signed_LH_unsigned_LBU_and_A2_delay_one=True,later_caller_return_one_not_callee_contract=True,
            not_full_dispatcher_or_gameplay=True)

    def test_08_first_complete_installed_image_and_exact_successor_controls(self):
        out=self.root/install.BUILD; expected=install.expected_inputs(self.root,out)
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        before=(out/'before-elf').read_bytes(); actual=(self.root/source.PATHS['elf']).read_bytes()
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),actual)
        for key,path in source.PATHS.items():
            self.assertEqual((self.root/path).read_bytes(),expected.get(key,(out/('before-'+key)).read_bytes()),key)
        self.assertEqual(len(before),len(actual)); self.assertEqual(sum(a!=b for a,b in zip(before,actual)),294)
        wanted=canonical_symbols(before); row=next(k for k in wanted if k[0]==source.FUNCTION)
        successor=tuple([*row[:2],source.SIZE,*row[3:]])
        wanted[row]-=1; wanted[successor]+=1
        self.assertEqual(+wanted,canonical_symbols(actual))
        at=elf_slot_offset(actual,source.ENTRY,source.SIZE)
        self.assertEqual(sum(a!=b for a,b in zip(before[at:at+source.SIZE],actual[at:at+source.SIZE])),292)
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        read=Path.read_bytes
        for relative,key in checkpoint.PATHS.items():
            current=(self.root/relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(current,relative,self.root),checkpoint.fixture(self.root,'before',key))
            for offset in (0,len(current)//2,len(current)-1):
                bad=bytearray(current); bad[offset]^=1
                self.assertEqual(checkpoint.previous_input(bytes(bad),relative,self.root),bytes(bad))
            for stage in ('before','after'):
                target=out/(stage+'-'+key)
                with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==target else read(p)):
                    with self.assertRaises(AssertionError):
                        checkpoint.fixture(self.root,stage,key)
        self.receipt('installed',first_complete_image_exact=True,changed_bytes=294,code_bytes=292,extent_bytes=2,
            metadata_bytes=0,metadata_exclusions=0,new_guards=0,after=checkpoint.AFTER,protected_layout=layout)


if __name__=='__main__':
    unittest.main()
