"""Direct SDK match, live alias reads, actual callers and complete image."""
import hashlib
from functools import lru_cache
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_scrolling_tile_windows as source
from tools.experiments import game_scrolling_tile_installation as install
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_scrolling_tile_oracle as model
from tools.tests import game_scrolling_tile_native as native
from tools.tests import scrolling_tile_checkpoint as checkpoint
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols
from tools.check_game_data_layout import audit_layout


class ScrollingTileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row = source.qualify(cls.root,cls.out)
        cls.rom = (cls.out/'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>38I',cls.rom,source.ROM))
        context = type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original = assembly.ViewListSetupTests.original.__func__(context,'original-tiles',
            (cls.out/'before-tile_original').read_text(),source.FUNCTION)

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_all38_raw_padded_words_bindings_and24_owner_neighbors(self):
        self.assertEqual(self.images,[self.truth,self.truth])
        self.assertEqual(self.row,dict(words=38,frame=0,bindings=8,new_guards=0,unchanged_raw_padded_neighbors=24))
        source.checked_parts(*source.parts(self.obj))

    def test_02_full_guest_live_alias_reference_all_words_order_and_state(self):
        count = 0; seen=set(); late_alias=False
        for memory,cursor,phase in model.cases():
            expected,events,result = model.reference(memory,cursor)
            states = []
            for words in (self.truth,*self.images):
                m = model.TileOracle(words,memory,cursor,phase).run()
                self.assertEqual((m.memory,m.io,m.r[2]),(expected,events,result))
                self.assertFalse(m.calls)
                for reg in (*range(16,24),28,29,30,31):
                    self.assertEqual(m.r[reg],m.before[reg])
                seen.update(m.visits); states.append((model.point.state(m),m.io))
            self.assertTrue(states[0]==states[1]==states[2])
            if cursor==model.ANCHORS[model.NAMES[2]]:
                late_alias |= events[4][3]!=model.read(memory,model.ANCHORS[model.NAMES[2]])
            count += 1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+source.SIZE,4)))
        self.assertTrue(late_alias)
        self.receipt('guest',three_way_cases=count,natural_words=38,live_second_pair_alias=True,
            full_memory_read_store_order_and_modeled_state=True,guest_aliases_not_portable_C_claim=True)

    def test_03_native32_full_SDK_body_typed_caller_and_eight_effective_controls(self):
        caller,driver = self.out/'native-caller.c',self.out/'native-driver.c'
        caller.write_text(native.CALLER); driver.write_text(native.DRIVER)
        exits = {}
        for name,opt,body in [('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[
                (n,'-O2',b) for n,b in native.controls(source.SELECTED).items()]:
            unit = self.out/('native-'+name+'.c'); unit.write_text(native.HEADER+body+'\n')
            exe = unit.with_suffix('.elf')
            result = subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double',
                *[str(p.relative_to(self.root)) for p in (unit,caller,driver)],'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            ran = subprocess.run([str(exe)],capture_output=True,text=True,timeout=120)
            exits[name] = ran.returncode
            self.assertEqual(ran.returncode,0 if name in ('o2','o0') else 22,(name,ran.stderr))
        self.receipt('native',cases_each=384,exits=exits,UBSan=True,separate_full_body_and_typed_caller=True,
            all_commands_external_canaries_and_global_preservation=True,alias_cases_guest_only=True)

    def test_04_three_independent_rebase_pairs_all_four_anchors_and_aliases(self):
        raw,bindings = source.parts(self.obj); count=0
        for index,values in enumerate(((0x80117FFC,0x80128004,0x80137FF8,0x80148000),
                (0x80128000,)*4,(0x80127FF8,0x80127FFC,0x80128000,0x80128004))):
            anchors = dict(zip(model.NAMES,values)); entry=0x15208004+index*0x10000
            text,unresolved = emit_function(raw,dict(value=0,size=source.SIZE),bindings,source.FUNCTION,anchors)
            self.assertFalse(unresolved)
            path = self.out/('rebase-C-%d.s'%index); path.write_text(text); obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            images=[]
            for name,target in (('original',self.original),('C',obj)):
                script=self.out/('rebase-%d-%s.ld'%(index,name))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(target)],capture_output=True,check=True)
                images.append(source.projection.sections(elf)['.text'][1][:source.SIZE])
            self.assertEqual(*images)
            words=list(struct.unpack('>38I',images[0]))
            for variant,alias,phase in itertools.product(range(16),range(7),(0,8)):
                memory,cursor=model.fixture((variant*128-129,0x80000000+variant,variant*513,0xFFFFFFFF-variant),alias,anchors)
                expected,events,result=model.reference(memory,cursor,anchors)
                m=model.TileOracle(words,memory,cursor,phase,entry).run()
                self.assertEqual((m.memory,m.io,m.r[2]),(expected,events,result)); count+=1
        self.receipt('rebases',independent_original_C_links=6,paired_cases=count,all38_words_exact=True,
            four_anchors_signed_low_carries_and_shared_live_storage=True)

    def test_05_all_read_store_fault_prefixes_both_stack_phases_and_aliases(self):
        count=0
        for alias,phase in itertools.product(range(7),(0,8)):
            memory,cursor=model.fixture((0xFFFFFFFF,128,0x80000000,0x7FFFFFFF),alias)
            completed=model.TileOracle(self.truth,memory,cursor,phase).run()
            self.assertEqual(completed.all_accesses,8)
            for fault in range(8):
                states=[]
                for words in (self.truth,*self.images):
                    m=model.TileOracle(words,memory,cursor,phase); m.access_fault=fault
                    with self.assertRaises(faults.AccessBoundary):
                        m.run()
                    self.assertEqual(m.all_accesses,fault)
                    states.append((model.point.state(m),m.io))
                self.assertTrue(states[0]==states[1]==states[2]); count+=1
        self.receipt('faults',three_way_positively_fired_prefixes=count,
            all_eight_accesses_each=True,not_portable_C_or_hardware_fault_acceptance=True)

    def test_06_all38_word_nine_binding_and178_input_corruptions_fail_closed(self):
        raw,bindings=source.parts(self.obj)
        for i in range(38):
            bad=bytearray(raw); bad[i*4]^=1
            with self.assertRaises(ValueError):
                source.checked_parts(bytes(bad),bindings)
        for at in (*bindings,-4):
            bad=dict(bindings); bad[at]=[('R_MIPS_HI16','wrong')]
            with self.assertRaises(ValueError):
                source.checked_parts(raw,bad)
        # Cache only the corruption fixture; re-read every live input afterwards.
        read=lru_cache(None)(Path.read_bytes)
        self.assertEqual(len(source.PATHS),178)
        for relative in source.PATHS.values():
            target=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==target else read(p)):
                with self.assertRaises(ValueError):
                    source.freeze(self.root,self.out)
        source.freeze(self.root,self.out)
        self.receipt('inputs',word_controls=38,binding_controls=9,protected_entries=178,
            distinct_paths=len(set(source.PATHS.values())))

    def test_07_actual_three_caller_windows(self):
        class Join(Exception):
            pass
        class Code(faults.TrackedCode):
            def __getitem__(self,pc):
                if pc==self.join:
                    raise Join
                return super().__getitem__(pc)
        count=0
        for entry,rom,size,join in ((0x1510BB7C,0x13902C,16,0x1510BB98),
                (0x1510BDD8,0x139288,12,0x1510BDE4),(0x15113B70,0x141020,12,0x15113B7C)):
            packet=list(struct.unpack_from('>%dI'%(size//4),self.rom,rom))
            for variant,alias,phase in itertools.product(range(4),range(7),(0,8)):
                memory,cursor=model.fixture((variant*128-129,0x80000000+variant,variant*513,0xFFFFFFFF-variant),alias)
                expected,events,result=model.reference(memory,cursor); states=[]
                for words in (self.truth,*self.images):
                    connected=dict(zip(range(source.ENTRY,source.ENTRY+source.SIZE,4),words)); connected[join]=0
                    m=model.TileOracle(packet,memory,0xBAD00BAD,phase,entry,connected); m.r[16]=cursor
                    m.code=Code(m.code,m); m.code.join=join
                    with self.assertRaises(Join):
                        m.run()
                    self.assertEqual((m.memory,m.io,m.r[2]),(expected,events,result))
                    self.assertEqual(m.calls,[(source.ENTRY,(cursor,))])
                    if entry!=0x1510BDD8:
                        self.assertEqual(m.r[16],result)
                    self.assertEqual(m.r[29],model.STACK+phase)
                    states.append((model.point.state(m),m.io))
                self.assertTrue(states[0]==states[1]==states[2]); count+=1
        self.receipt('callers',three_way_cases=count,actual_sites=3,argument_capture_after_delay=True,
            actual38_word_body=True,not_full_dispatchers=True)

    def test_08_first_complete_installed_image_and_exact_successor_controls(self):
        from tools.tests import fixed_transition_checkpoint as installed
        out=self.root/install.BUILD; expected=install.expected_inputs(self.root,out)
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        before=(out/'before-elf').read_bytes()
        actual=installed.previous_input((self.root/source.PATHS['elf']).read_bytes(),source.PATHS['elf'],self.root)
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),actual)
        for key,path in source.PATHS.items():
            current=installed.previous_input((self.root/path).read_bytes(),path,self.root)
            self.assertEqual(current,expected.get(key,(out/('before-'+key)).read_bytes()),key)
        self.assertEqual(len(before),len(actual))
        self.assertEqual(sum(a!=b for a,b in zip(before,actual)),128)
        wanted=canonical_symbols(before); row=next(k for k in wanted if k[0]==source.FUNCTION)
        successor=tuple([*row[:2],source.SIZE,*row[3:]])
        wanted[row]-=1; wanted[successor]+=1
        self.assertEqual(+wanted,canonical_symbols(actual))
        at=elf_slot_offset(actual,source.ENTRY,source.SIZE)
        self.assertEqual(sum(a!=b for a,b in zip(before[at:at+source.SIZE],actual[at:at+source.SIZE])),127)
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
        self.receipt('installed',actual_sites=3,not_full_dispatchers=True,
            first_complete_image_exact=True,changed_bytes=128,code_bytes=127,extent_bytes=1,
            metadata_bytes=0,metadata_exclusions=0,new_guards=0,after=checkpoint.AFTER,protected_layout=layout)


if __name__=='__main__':
    unittest.main()
