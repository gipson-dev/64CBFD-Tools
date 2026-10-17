"""Complete direct reset qualification, original caller and whole-image adoption."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_overlay_defaults as source
from tools.experiments import game_overlay_defaults_installation as install
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_overlay_defaults_oracle as model
from tools.tests import game_overlay_defaults_native as native
from tools.tests import overlay_defaults_checkpoint as checkpoint
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import canonical_symbols, symbol_rows
from tools.check_game_data_layout import audit_layout


class OverlayDefaultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/source.BUILD
        cls.obj, cls.padded, cls.images, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.out/'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>50I', cls.rom, source.ROM))
        context = type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original = assembly.ViewListSetupTests.original.__func__(context,'original-reset',
            (cls.out/'before-color_provider_original').read_text(),source.FUNCTION)

    def receipt(self, name, **data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_all50_raw_padded_words22_bindings_pool_and27_neighbors(self):
        self.assertEqual(self.images,[self.truth,self.truth])
        self.assertEqual((self.row['frame'],self.row['new_guards'],self.row['bindings'],self.row['unchanged_raw_padded_neighbors']),(0,0,22,27))
        source.checked_parts(*source.parts(self.obj),source.projection.sections(self.obj)['.rodata'][1])

    def test_02_independent_memory_access_order_full_state_both_branches_and_all50_words(self):
        count, seen = 0, set()
        for memory,channel,phase in model.corpus():
            expected,events = model.reference(memory,channel)
            states = []
            for words in (self.truth,*self.images):
                m = model.ResetOracle(words,memory,channel,phase).run()
                self.assertEqual(m.memory,expected,(channel,phase))
                self.assertEqual(m.io,events)
                self.assertFalse(m.calls)
                self.assertEqual(m.r[29],model.STACK+phase)
                seen.update(m.visits)
                states.append(model.point.state(m))
            self.assertTrue(states[0] == states[1] == states[2])
            count += 1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+source.SIZE,4)))
        self.receipt('guest',three_way_cases=count,natural_words=50,all_memory_registers_accesses=True,
            invalid_index_overflow_is_guest_only=True,no_CP0_or_hardware_FCSR_claim=True)

    def test_03_native32_full_body_separate_typed_caller_all_canaries_and8_controls(self):
        caller,driver = self.out/'native-caller.c',self.out/'native-driver.c'
        caller.write_text(native.CALLER)
        driver.write_text(native.DRIVER)
        exits = {}
        for name,opt,body in [('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[
                (n,'-O2',b) for n,b in native.controls(source.SELECTED).items()]:
            unit = self.out/('native-'+name+'.c')
            unit.write_text(native.HEADER+body+'\n')
            exe = unit.with_suffix('.elf')
            built = subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double','-fno-strict-aliasing',
                *[str(p.relative_to(self.root)) for p in (unit,caller,driver)],'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran = subprocess.run([str(exe)],capture_output=True,text=True,timeout=120)
            exits[name] = ran.returncode
            self.assertEqual(ran.returncode,0 if name in ('o2','o0') else 22,(name,ran.stderr))
        self.receipt('native',cases_each=640,exits=exits,UBSan=True,separate_full_body_typed_caller=True,
            all1024_canary_bytes=True,aligned_live_constant_and_mixed_bank_aliases=True,
            aliases_use_existing_GNU_union_and_fno_strict_aliasing_convention=True,invalid_indices_guest_only=True)

    def rebase(self, index, anchors):
        raw, bindings = source.parts(self.obj)
        text, unresolved = emit_function(raw,dict(value=0,size=source.SIZE),bindings,source.FUNCTION,anchors)
        self.assertFalse(unresolved)
        path = self.out/('rebase-C-%d.s'%index)
        path.write_text(text)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
        images = []
        for name,target in (('original',self.original),('C',obj)):
            script = self.out/('rebase-%d-%s.ld'%(index,name))
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
            elf = script.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(target)],capture_output=True,check=True)
            images.append(source.projection.sections(elf)['.text'][1][:source.SIZE])
        self.assertEqual(*images)
        return list(struct.unpack('>50I',images[0]))

    def test_04_independent_original_C_rebases_carries_and_late_constant_aliases(self):
        late_read_changed = False
        for index in range(3):
            anchors = {name:(0x80117FFC+i*0x1010)&0xFFFFFFFF for i,name in enumerate(model.NAMES)}
            if index == 1:
                anchors[model.CONSTANT] = anchors[model.PROJECTED]
            elif index == 2:
                anchors.update({n:0x80128004 for n in model.NAMES if n != model.MODE})
            words = self.rebase(index,anchors)
            for channel in (0,1,3):
                for flag in (0,1,2,255):
                    memory = model.fixture(channel,flag,anchors=anchors)
                    expected,events = model.reference(memory,channel,anchors)
                    m = model.ResetOracle(words,memory,channel).run()
                    self.assertEqual(m.memory,expected)
                    self.assertEqual(m.io,events)
                    if index == 1 and channel == 0 and flag == 0:
                        self.assertEqual(model.read(m.memory,anchors[model.SPEED]),0)
                        late_read_changed = True
        self.assertTrue(late_read_changed)
        self.receipt('rebases',independent_original_C_links=6,all11_anchors=True,paired_cases=36,
            exact_all50_words=True,signed_low_carries_and_late_constant_alias=True)

    def test_05_every_access_fault_prefix_positive_gate_and_full_state(self):
        count = 0
        for flag in (0,2):
            for phase in (0,8):
                memory = model.fixture(1,flag)
                full = model.ResetOracle(self.truth,memory,1,phase).run()
                for fault in range(full.all_accesses):
                    states = []
                    for words in (self.truth,*self.images):
                        m = model.ResetOracle(words,memory,1,phase)
                        m.access_fault = fault
                        with self.assertRaises(faults.AccessBoundary):
                            m.run()
                        self.assertEqual(m.all_accesses,fault)
                        states.append((model.point.state(m),m.io))
                    self.assertTrue(states[0] == states[1] == states[2])
                    count += 1
        self.receipt('faults',three_way_positively_fired_prefixes=count,not_portable_C_or_CP0_fault_acceptance=True)

    def test_06_all50_word22_binding16_pool_and158_input_corruptions_fail_closed(self):
        raw,bindings = source.parts(self.obj)
        pool = source.projection.sections(self.obj)['.rodata'][1]
        for i in range(50):
            bad = bytearray(raw)
            bad[i*4] ^= 1
            with self.assertRaises(ValueError):
                source.checked_parts(bytes(bad),bindings,pool)
        for i in range(len(pool)):
            bad = bytearray(pool)
            bad[i] ^= 1
            with self.assertRaises(ValueError):
                source.checked_parts(raw,bindings,bytes(bad))
        for at in (*bindings,-4):
            bad = dict(bindings)
            bad[at] = [('R_MIPS_HI16','wrong')]
            with self.assertRaises(ValueError):
                source.checked_parts(raw,bad,pool)
        read = Path.read_bytes
        self.assertEqual(len(source.PATHS),158)
        for relative in source.PATHS.values():
            target = self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p == target else read(p)):
                with self.assertRaises(ValueError):
                    source.freeze(self.root,self.out)
        self.receipt('inputs',word_controls=50,binding_controls=23,pool_controls=16,
            protected_entries=158,distinct_paths=len(set(source.PATHS.values())))

    def test_07_actual_four_word_caller_channel_zero_delay_and_return_zero(self):
        entry, join = 0x1509DFF8, 0x1509E3C8
        packet = list(struct.unpack_from('>4I',self.rom,0xCB4A8))
        self.assertEqual(packet,[0x0D460786,0x00002025,0x100000F1,0x00001025])
        class Join(Exception):
            pass
        class Code(faults.TrackedCode):
            def __getitem__(self, pc):
                if pc == join:
                    raise Join
                return super().__getitem__(pc)
        count = 0
        for flag in (0,1,2,255):
            for constant in (0xBB83126F,0x80000000,0x7FC12345,0):
                for phase in (0,8):
                    memory = model.fixture(0,flag,constant)
                    expected,_ = model.reference(memory,0)
                    states = []
                    for words in (self.truth,*self.images):
                        connected = dict(zip(range(source.ENTRY,source.ENTRY+source.SIZE,4),words))
                        connected[join] = 0
                        m = model.ResetOracle(packet,memory,0x12345678,phase,entry,connected)
                        m.code = Code(m.code,m)
                        with self.assertRaises(Join):
                            m.run()
                        self.assertEqual(m.calls,[(source.ENTRY,(0,))])
                        self.assertEqual(m.memory,expected)
                        self.assertEqual(m.r[2],0)
                        states.append(model.point.state(m))
                    self.assertTrue(states[0] == states[1] == states[2])
                    count += 1
        self.receipt('caller',original_sites=1,original_packet_words=4,three_way_cases=count,
            actual50word_body=True,channel_zero_delay_and_caller_return_zero=True,not_full_dispatcher_execution=True)

    def test_08_first_complete_image_source_all_inputs_symbols_and_data(self):
        out = self.root/install.BUILD
        expected = install.expected_inputs(self.root,out)
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        for key,path in source.PATHS.items():
            self.assertEqual((self.root/path).read_bytes(),expected.get(key,(out/('before-'+key)).read_bytes()),key)
        before, actual = (out/'before-elf').read_bytes(),expected['elf']
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),actual)
        self.assertEqual((len(before),len(actual)),(3257636,3257636))
        prediction = json.loads((out/'prelink-prediction.json').read_text())
        self.assertEqual(tuple(prediction[k] for k in ('changed_ELF_bytes','code_bytes','extent_bytes','metadata_bytes','metadata_exclusions')),
            (201,170,1,30,0))
        wanted = canonical_symbols(before)
        row = next(k for k in wanted if k[0] == source.FUNCTION)
        successor = tuple([*row[:2],source.SIZE,*row[3:]])
        wanted[row] -= 1
        wanted[successor] += 1
        self.assertEqual(+wanted,canonical_symbols(actual))
        for address,length in ((0x1517FB9C,2532),(0x1517F814,480),(0x1517F9F4,424),(0x800A7280,16)):
            at = elf_slot_offset(actual,address,length)
            self.assertEqual(before[at:at+length],actual[at:at+length])
        layout = audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        checkpoint.freeze_after(self.root)
        self.receipt('installed',after=checkpoint.AFTER,whole_image_exact=True,protected_layout=layout,
            changed_bytes=201,metadata_bytes=30,metadata_exclusions=0,new_guards=0)

    def test_09_exact_successor_fixtures_and_symbol_permutation_controls(self):
        read = Path.read_bytes
        count = 0
        for relative,key in checkpoint.PATHS.items():
            current = (self.root/relative).read_bytes()
            self.assertEqual(checkpoint.previous_input(current,relative,self.root),checkpoint.fixture(self.root,'before',key))
            for at in (0,len(current)//2,len(current)-1):
                bad = bytearray(current)
                bad[at] ^= 1
                self.assertEqual(checkpoint.previous_input(bytes(bad),relative,self.root),bytes(bad))
                count += 1
            for stage in ('before','after'):
                target = self.root/install.BUILD/(stage+'-'+key)
                with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p == target else read(p)):
                    with self.assertRaises(AssertionError):
                        checkpoint.fixture(self.root,stage,key)
                count += 1
        from tools.tests import test_game_actor_burst_packet_match as serialization
        before = (self.root/install.BUILD/'before-elf').read_bytes()
        names = set(install.SERIALIZATION[0][0])
        for row in symbol_rows(before):
            if row[1] not in names:
                continue
            for at in (row[0]+4,row[0]+8,row[0]+12,row[0]+14,row[3]):
                bad = bytearray(before)
                bad[at] ^= 1
                with patch.object(serialization,'SERIALIZATION',install.SERIALIZATION), self.assertRaises(AssertionError):
                    serialization.apply_burst_symbol_serialization(bad)
                count += 1
        self.receipt('successor-controls',effective_controls=count,exact_four_symbol_permutation=True,
            no_metadata_exclusions_or_generic_hash_acceptance=True)


if __name__ == '__main__':
    unittest.main()
