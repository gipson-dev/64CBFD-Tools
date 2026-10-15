"""Full-word fade clamps, literal callback ABI, native C and real dispatch chain."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_fade_callback as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_dual_factory_preset import state
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests import test_game_packed_record_updater as updater
from tools.tests import test_game_packed_record_updater_installed as archive

RECORD, OTHER, BINDING = 0x20000, 0x24000, 0x22000
STEPS = (0, 1, 2, 15, 16, 31, 0xFFFFFFFF, 0xFFFFFFE1, 0x80000000, 0x7FFFFFFF, 0x10000000, 0x40000001)


def signed(value):
    return (value & 0xFFFFFFFF) - (0x100000000 if value & 0x80000000 else 0)


def short(value):
    return (value & 65535) - (65536 if value & 32768 else 0)


def external(memory):
    return {a: v for a, v in memory.items() if not STACK - 1024 <= a < STACK + 1024}


def fixture(value=123, enabled=1, delta=1, record=RECORD, phase=0, step=source.STEP, binding=BINDING):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-1024, 1024)}
    for base in (record, OTHER, BINDING):
        memory.update({base + i: (i * 13 + 0xC5) & 255 for i in range(-16, 128)})
    for i, target in enumerate(updater.TARGETS):
        put(memory, source.TABLE + i * 4, target)
    for offset, data, width in ((0, 18, 1), (0x1F, value, 1), (0x24, enabled, 1),
            (0x23, 3, 1), (0x30, binding, 4), (0xE, -1234, 2), (0x10, 2345, 2),
            (0x12, -3456, 2), (0x18, -321, 2), (0x25, 0xA5, 1),
            (0x26, -2, 1), (0x27, 0x81, 1), (0x28, 3, 1), (0x29, 0xFE, 1),
            (0x2A, 0x40, 1), (0x2B, 0x80, 1)):
        put(memory, record + offset, data, width)
    put(memory, step, delta)
    for kind in (0, 1, 2, 18):
        put(memory, updater.TYPE_TABLE + kind * 52, updater.DESTRUCTOR)
    return memory


def reference(memory, mode=0, record=RECORD, step=source.STEP, move=source.MOVE, scale=source.SCALE):
    memory, calls = dict(memory), []
    value, enabled = read(memory, record + 0x1F, 1), read(memory, record + 0x24, 1)

    def store_byte():
        put(memory, record + 0x1F, value, 1)
        if mode == 3:
            put(memory, record + 0x24, not read(memory, record + 0x24, 1), 1)

    if enabled:
        if value != 255:
            value = signed(value + read(memory, step) * 16)
            if value > 255:
                value = 255
            store_byte()
    else:
        if value:
            value = max(0, signed(value - read(memory, step) * 8))
            store_byte()
        extent = signed(value * 512) >> 8
        put(memory, record + 0x16, extent, 2)
        put(memory, record + 0x14, extent, 2)
    if read(memory, record + 0x24, 1) == 0 and value == 0:
        return external(memory), calls, 1
    calls.append((move, record))
    if mode == 2:
        put(memory, record + 0x1F, 0xA5, 1)
        put(memory, record + 0x24, 0, 1)
        put(memory, step, 0x87654321)
    calls.append((scale, OTHER if mode == 1 else record, 240))
    return external(memory), calls, 0


class FadeOracle(updater.UpdaterOracle):
    def __init__(self, words, memory, phase=0, mode=0, fault=None, record=RECORD,
            entry=source.ENTRY, step=source.STEP, move=source.MOVE, scale=source.SCALE, connected=None):
        symbols = dict(delta=step, table=source.TABLE, remove=source.REMOVE)
        super().__init__(words, memory, phase=phase, mode=mode, fault=fault, record=record,
            entry=entry, connected=connected, symbols=symbols)
        self.move, self.scale = move, scale
        self.flip_store = True

    def put(self, address, value, width):
        super().put(address, value, width)
        if (self.mode == 3 and self.flip_store and self.own_instruction
                and address == self.record + 0x1F and width == 1):
            self.own_instruction = False
            try:
                super().put(self.record + 0x24, not self.peek(self.record + 0x24, 1), 1)
            finally:
                self.own_instruction = True

    def record_call(self, target):
        assert target in (self.move, self.scale), hex(target)
        args = self.arguments(1 if target == self.move else 2)
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        if target == self.move:
            if self.mode == 1:
                self.put(STACK + self.phase, OTHER, 4)
            elif self.mode == 2:
                self.put(self.r[4] + 0x1F, 0xA5, 1)
                self.put(self.r[4] + 0x24, 0, 1)
                self.put(self.symbols['delta'], 0x87654321, 4)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.lo = 0x87654321
        self.condition = True
        self.r[2] = 0xABCD0000 + len(self.calls)


def controls():
    return {
        'truncate-update': source.SELECTED.replace('value = (s32)((u32)value', 'value = (u8)(s32)((u32)value'),
        'signed-value': source.SELECTED.replace('s32 value = record[0x1F]', 's32 value = (s8)record[0x1F]'),
        'wide-load': source.SELECTED.replace('s32 value = record[0x1F]', 's32 value = *(u32 *)(record + 0x1C)'),
        'wide-store': source.SELECTED.replace('record[0x1F] = value;', '*(u32 *)(record + 0x1C) = value;'),
        'wrong-pointer': source.SELECTED.replace('func_1516F864(record);', 'func_1516F864(record + 0x24);'),
        'wrong-scale': source.SELECTED.replace('record, 0xF0', 'record, 0xF1'),
        'byte-completion': source.SELECTED.replace('record[0x24] == 0 && value == 0', 'record[0x24] == 0 && record[0x1F] == 0'),
        'wrong-extent': source.SELECTED.replace('(u32)value << 9) >> 8', '(u32)value << 9) >> 7'),
    }


def chain_reference(memory, release_type=0, record=RECORD):
    memory, calls = dict(memory), [(source.ENTRY, record)]
    counter = read(memory, record + 0x24, 1)
    if counter:
        put(memory, record + 0x24, max(0, signed(counter - read(memory, source.STEP))), 1)
    data, _, result = reference(memory, record=record)
    memory.update(data)
    if result:
        binding = read(memory, record + 0x30)
        if binding:
            put(memory, binding + 4, 0, 2)
        calls.extend(((source.REMOVE, record), (updater.UNLINK, record)))
        put(memory, record, release_type, 1)
        if release_type >= 2:
            target = read(memory, updater.TYPE_TABLE + release_type * 52) or updater.DEFAULT
            calls.append((target, record))
            put(memory, record + 47, 0x6D, 1)
    else:
        calls.extend(((source.MOVE, record), (source.SCALE, record, 240), (0x1516F94C, record, 240),
            (0x1516F8EC, record, 240), (0x1516F91C, record, 240)))
        for position, velocity, fraction in ((0xE, 0x26, 0x2A), (0x12, 0x28, 0x2B)):
            fixed_velocity = (read(memory, record + velocity, 1) - (256 if read(memory, record + velocity, 1) & 128 else 0)) * 256
            fixed_velocity += read(memory, record + velocity + 1, 1)
            fixed = short(read(memory, record + position, 2)) * 256 + read(memory, record + fraction, 1)
            fixed = signed(fixed + fixed_velocity * read(memory, source.STEP))
            put(memory, record + position, fixed >> 8, 2)
            put(memory, record + fraction, fixed, 1)
        for velocity in (0x26, 0x28):
            high = read(memory, record + velocity, 1)
            fixed = (high - (256 if high & 128 else 0)) * 256 + read(memory, record + velocity + 1, 1)
            scaled = signed(fixed * 240) >> 8
            put(memory, record + velocity, scaled >> 8, 1)
            put(memory, record + velocity + 1, scaled, 1)
        put(memory, record + 0x18, signed(short(read(memory, record + 0x18, 2)) * 240) >> 8, 2)
        fixed = short(read(memory, record + 0x10, 2)) * 256 + read(memory, record + 0x25, 1)
        fixed = signed(fixed + short(read(memory, record + 0x18, 2)) * read(memory, source.STEP))
        put(memory, record + 0x10, fixed >> 8, 2)
        put(memory, record + 0x25, fixed, 1)
    return external(memory), calls, result


class FadeCandidateTests(unittest.TestCase):
    def test_scope_placeholder_and_direct_gate(self):
        self.assertEqual(len(source.PATHS), 57)
        self.assertEqual(len(set(source.PATHS.values())), 57)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        for count, differences, size, diagnostic in ((50, 0, 24, ''), (49, 1, 24, ''), (49, 0, 32, ''), (49, 0, 24, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=count,
                    differences=differences, frame=size, diagnostics=diagnostic))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))
        before = 's32 func_1516F9C4() {\n    return 0;\n}\nvoid other(void) {}\n'
        self.assertTrue(source.recovered_owner(before).endswith('void other(void) {}\n'))
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))


class FadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>49I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_09_all_801_archive_fingerprints = archive.PackedRecordUpdaterInstalledTests.test_04_all_original_801_archive_fingerprints

    def test_01_direct_padded_and_all_29_neighbors(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual((self.row['words'], self.row['differences'], self.row['frame'], self.row['diagnostics']), (49, 0, 24, ''))
        old_obj, diagnostic = source.build.compile_owner(self.root, self.out, (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostic, '')
        old, new = parse_object(old_obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            rel = lambda o, f: [(at - f['value'], value) for at, value in o[2].items() if f['value'] <= at < f['value'] + f['size']]
            self.assertEqual(rel(old, f), rel(new, g), name)
        self.assertEqual(normalized_pools(old_obj), normalized_pools(self.obj))
        self.receipt('direct', raw_padded_words=49, frame=24, unchanged_neighbors=29,
            relative_relocations_and_pools_fixed=True, guards_added=0, profile_changes=0)

    def test_02_full_private_state_wrap_clamps_and_live_homes(self):
        cases = [(v, flag, delta) for v in (0, 1, 15, 16, 127, 128, 254, 255)
            for flag in (0, 1, 128, 255) for delta in (0, 1, 2, 0xFFFFFFFF, 0xFFFFFFE1, 0x80000000, 0x7FFFFFFF, 0x10000000)]
        cases += [(i & 255, (0, 1, 128, 255)[i & 3], (i * 1664525 + 1013904223) & 0xFFFFFFFF) for i in range(128)]
        visits = set()
        for value, enabled, delta in cases:
            for phase in (0, 8):
                for mode in range(4):
                    memory = fixture(value, enabled, delta, phase=phase)
                    pair = [FadeOracle(w, memory, phase, mode).run() for w in (self.words, self.truth)]
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    self.assertEqual((external(pair[0].memory), pair[0].calls, pair[0].r[2]), reference(memory, mode))
                    self.assertEqual(pair[0].r[29], STACK + phase)
                    visits |= pair[0].visits
                    if pair[0].calls:
                        call = next(i for i, event in enumerate(pair[0].events) if event[0] == 'CALL')
                        self.assertEqual(pair[0].events[call - 1], ('W', STACK + phase, 4, RECORD))
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 196, 4)))
        self.receipt('private', paired_cases=len(cases) * 8, every_word_visited=True,
            literal_private_and_independent_public_states_equal=True, source_pointer_saved_in_call_delay=True,
            private_home_and_store_side_mutations_are_guest_probes_not_portable_C=True)

    def test_03_every_fired_fault_prefix_and_skipped_reads(self):
        cases = ((0, 0, 1), (255, 1, 1), (254, 1, 1), (1, 0, 1), (8, 0, 0xFFFFFFE1), (16, 1, 0xFFFFFFFF))
        count = 0
        for args in cases:
            for phase in (0, 8):
                for mode in range(4):
                    memory = fixture(*args, phase=phase)
                    whole = FadeOracle(self.truth, memory, phase, mode).run()
                    for fault in range(whole.accesses):
                        pair = [FadeOracle(w, memory, phase, mode, fault) for w in (self.words, self.truth)]
                        for model in pair:
                            with self.assertRaises(AccessFault):
                                model.run()
                        self.assertEqual(state(pair[0]), state(pair[1]))
                        count += 1
        for args in ((0, 0, 1), (255, 1, 1)):
            memory = fixture(*args)
            for at in range(source.STEP, source.STEP + 4):
                del memory[at]
            for words in (self.words, self.truth):
                model = FadeOracle(words, memory).run()
                self.assertFalse(any(event[0] == 'R' and event[1] == source.STEP for event in model.events))
        memory = fixture(255, 1)
        for at in range(RECORD + 0x1C, RECORD + 0x1F):
            del memory[at]
        self.assertEqual(FadeOracle(self.words, memory).run().r[2], 0)
        self.receipt('prefixes', paired_fired_faults=count, complete_literal_prefixes_equal=True,
            conditional_delta_and_byte_only_loads_checked=True, opaque_helpers_not_hardware_faults=True)

    def test_04_global_aliases_and_full_word_completion(self):
        count = 0
        for record in (RECORD + 4, source.STEP - 0x14, source.STEP - 0x24):
            for args in ((8, 0, 0xFFFFFFE1), (1, 0, 1), (255, 1, 0x12345678), (16, 1, 0xFFFFFFFF)):
                for mode in range(4):
                    memory = fixture(*args, record=record)
                    pair = [FadeOracle(w, memory, mode=mode, record=record).run() for w in (self.words, self.truth)]
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    self.assertEqual((external(pair[0].memory), pair[0].calls, pair[0].r[2]), reference(memory, mode, record))
                    count += 1
        model = FadeOracle(self.words, fixture(8, 0, 0xFFFFFFE1)).run()
        self.assertEqual(model.memory[RECORD + 0x1F], 0)
        self.assertEqual(model.r[2], 0)
        self.assertEqual(len(model.calls), 2)
        self.receipt('aliases', paired_cases=count, global_delta_aliases=True,
            low_byte_zero_full_word_256_still_calls_both_helpers=True, bounded_physical_alias_not_hardware_or_portable_C_claim=True)

    def test_05_effective_compiled_negative_controls(self):
        cases = ((250, 1, 1), (1, 0, 1), (8, 0, 0xFFFFFFE1), (128, 1, 0), (10, 0, 0))
        effective = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            failed = False
            for args in cases:
                memory = fixture(*args)
                model = FadeOracle(words, memory).run()
                failed |= (external(model.memory), model.calls, model.r[2]) != reference(memory)
            self.assertTrue(failed, name)
            self.assertGreater(row['differences'], 0, name)
            effective.append(name)
        self.receipt('controls', effective_compiled_guest_controls=effective, each_fired_public_mismatch=True)

    def test_06_independent_original_C_symbol_rebases(self):
        raw, functions, rel = parse_object(self.obj)
        names = {'D_800BE9E4': source.STEP, 'func_1516F864': source.MOVE, 'func_1516F984': source.SCALE}
        emitted, missing = emit_function(raw, functions[source.FUNCTION], rel, source.FUNCTION, names)
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for name, body in (('selected', emitted), ('original', 'glabel ' + source.FUNCTION + '\n' + original)):
            path = self.out / (name + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        for index, delta, step in ((0, 0, source.STEP), (1, 0x10000, 0x80207FFC), (2, -0x10000, 0x80318004)):
            entry, move, scale = source.ENTRY + delta, source.MOVE - delta, source.SCALE + delta * 2
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            outputs = []
            for name in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (name, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=D_800BE9E4=0x%X' % step, '--defsym=func_1516F864=0x%X' % move,
                    '--defsym=func_1516F984=0x%X' % scale, '-o', str(elf), str(self.out / (name + '-reloc.o'))], check=True, capture_output=True)
                outputs.append(list(struct.unpack_from('>49I', sections(elf)['.text'][1])))
            expected = list(self.truth)
            for hi, lo in ((8, 9), (20, 21)):
                expected[hi] = expected[hi] & 0xFFFF0000 | ((step + 0x8000) >> 16 & 65535)
                expected[lo] = expected[lo] & 0xFFFF0000 | (step & 65535)
            expected[39] = 0x0C000000 | (move >> 2 & 0x3FFFFFF)
            expected[42] = 0x0C000000 | (scale >> 2 & 0x3FFFFFF)
            self.assertEqual(outputs[0], expected)
            self.assertEqual(outputs[1], expected)
            for args in ((0, 0, 1), (255, 1, 1), (8, 0, 0xFFFFFFE1), (250, 1, 1)):
                for mode in range(4):
                    memory = fixture(*args, step=step)
                    pair = [FadeOracle(w, memory, mode=mode, entry=entry, step=step, move=move, scale=scale).run() for w in outputs]
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    self.assertEqual((external(pair[0].memory), pair[0].calls, pair[0].r[2]), reference(memory, mode, step=step, move=move, scale=scale))
        self.receipt('rebases', independent_original_C_pairs=3, both_calls_and_delta_signed_low_carry=True, complete_49_word_equality=True)

    def test_07_native_full_byte_range_O2_O0_and_eight_controls(self):
        harness = '''typedef signed char s8; typedef unsigned char u8;
typedef short s16; typedef unsigned short u16; typedef int s32; typedef unsigned int u32; typedef unsigned long long u64;
static s32 D_800BE9E4; static u32 mode,count,scaleValue; static u8 *pointers[2];
static u8 record[96] __attribute__((aligned(8))), expected[96] __attribute__((aligned(8)));
static __attribute__((noinline)) void func_1516F864(u8 *p){if(count<2)pointers[count]=p;count++;
 if(mode==2){p[0x1F]=0xA5;p[0x24]=0;D_800BE9E4=(s32)0x87654321u;}}
static __attribute__((noinline)) void func_1516F984(u8 *p,u32 n){if(count<2)pointers[count]=p;count++;scaleValue=n;}
BODY
static s32 (*volatile invoke)(u8*)=func_1516F9C4;
static int check(u32 v,u32 flag,u32 delta,u32 provider){u32 i,word=v,done,expectedDelta=delta;s32 result;
 for(i=0;i<96;i++)record[i]=(u8)(i*13+0xC5);record[0x1F]=(u8)v;record[0x24]=(u8)flag;
 for(i=0;i<96;i++)expected[i]=record[i];
 if(flag){if(v!=255){word=(u32)((u64)v+((u64)delta<<4));if(!(word&0x80000000u)&&word>255)word=255;expected[0x1F]=(u8)word;}}
 else{if(v){word=(u32)((u64)v-((u64)delta<<3));if(word&0x80000000u)word=0;expected[0x1F]=(u8)word;}
  *(u16*)(expected+0x16)=(u16)(word*2);*(u16*)(expected+0x14)=(u16)(word*2);}
 done=flag==0&&word==0;mode=provider;count=scaleValue=0;D_800BE9E4=(s32)delta;result=invoke(record);
 if(result!=(s32)done)return 10;if(count!=(done?0u:2u))return 12;
 if(!done){if(pointers[0]!=record||pointers[1]!=record||scaleValue!=240)return 13;
  if(provider==2){expected[0x1F]=0xA5;expected[0x24]=0;expectedDelta=0x87654321u;}}
 for(i=0;i<96;i++)if(record[i]!=expected[i])return 11;if((u32)D_800BE9E4!=expectedDelta)return 15;return 0;}
static int run(void){static const u32 steps[]={0,1,2,15,16,31,0xFFFFFFFFu,0xFFFFFFE1u,0x80000000u,0x7FFFFFFFu,0x10000000u,0x40000001u};
 static const u32 flags[]={0,1,128,255};u32 v,f,d,m;int r;if(sizeof(void*)!=4||sizeof(s32)!=4)return 14;
 for(v=0;v<256;v++)for(f=0;f<4;f++)for(d=0;d<12;d++)for(m=0;m<2;m++){r=check(v,flags[f],steps[d],m*2);if(r)return r;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''
        runs = [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)]
        runs += [('negative-' + name, body, '-O2', False) for name, body in controls().items()]
        exits = {}
        for name, body, profile, success in runs:
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace('BODY', body))
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-ffreestanding',
                '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter', str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            exits[name] = result.returncode
            if success:
                self.assertEqual(result.returncode, 0, name)
            else:
                self.assertIn(result.returncode, (10, 11, 12, 13, 15), name)
        self.receipt('native', cases_each_O2_O0=24576, all_256_values=True, public_provider_modes=[0, 2],
            effective_source_controls=8, controlled_exits=exits, host32_not_guest_private_or_hardware_claim=True)

    def test_08_actual_current_dispatcher_helpers_and_cleanup(self):
        image = (self.root / source.PATHS['elf']).read_bytes()
        symbols = {row[1]: row[2] for row in symbol_rows(image)}
        self.assertEqual(symbols['D_8008CBA0'][1], source.TABLE)
        table = image[elf_slot_offset(image, source.TABLE, 36):][:36]
        self.assertEqual(table, self.rom[0x231660:0x231660 + 36])
        self.assertEqual(struct.unpack('>9I', table), updater.TARGETS)
        self.assertEqual(struct.unpack_from('>I', table, 12)[0], source.ENTRY)
        specs = ((source.CALLER, 0x19AB28, 48), (source.ENTRY, source.ROM, 49),
            (source.MOVE, 0x19CD14, 34), (source.SCALE, 0x19CE34, 16),
            (0x1516F94C, 0x19CDFC, 14), (0x1516F8EC, 0x19CD9C, 12),
            (0x1516F91C, 0x19CDCC, 12), (source.REMOVE, 0x196BDC, 28))
        bodies, connected = {}, {}
        for entry, rom, count in specs:
            words = list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)), hex(entry))
            bodies[entry] = words
            if entry != source.CALLER:
                connected.update(zip(range(entry, entry + count * 4, 4), words))
        class Chain(FadeOracle):
            def record_call(model, target):
                counts = {source.ENTRY: 1, source.MOVE: 1, source.SCALE: 2, 0x1516F94C: 2,
                    0x1516F8EC: 2, 0x1516F91C: 2, source.REMOVE: 1, updater.UNLINK: 1,
                    updater.DESTRUCTOR: 1, updater.DEFAULT: 1}
                self.assertIn(target, counts)
                args = model.arguments(counts[target])
                model.calls.append((target, *args))
                model.events.append(('CALL', target, args))
            def hook(model, target):
                self.assertIn(target, (updater.UNLINK, updater.DEFAULT, updater.DESTRUCTOR))
                updater.UpdaterOracle.hook(model, target)
        cases = [(0, 0, 1), (1, 0, 1), (8, 0, 0xFFFFFFE1), (255, 1, 1), (250, 1, 1)]
        cases += [(i * 37 & 255, (0, 1, 128, 255)[i & 3], STEPS[i % len(STEPS)]) for i in range(64)]
        visits, count, completed = set(), 0, 0
        for i, args in enumerate(cases):
            for binding in (0, BINDING):
                for phase in (0, 8):
                    record = (RECORD, source.STEP - 0x14, source.STEP - 0x24)[i % 3]
                    memory = fixture(*args, record=record, phase=phase, binding=binding)
                    pointer = updater.DESTRUCTOR if i & 4 else 0
                    put(memory, updater.TYPE_TABLE + 2 * 52, pointer)
                    memory.update({source.TABLE + j: value for j, value in enumerate(table)})
                    pair = []
                    for words in (self.words, self.truth):
                        code = dict(connected)
                        code.update(zip(range(source.ENTRY, source.ENTRY + 196, 4), words))
                        model = Chain(bodies[source.CALLER], memory, phase=phase, record=record,
                            entry=source.CALLER, connected=code)
                        model.flip_store = False
                        model.release_type = i % 3
                        pair.append(model.run())
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    expected_memory, expected_calls, result = chain_reference(memory, i % 3, record)
                    self.assertEqual(external(pair[0].memory), expected_memory)
                    self.assertEqual(pair[0].calls, expected_calls)
                    if result:
                        self.assertEqual(pair[0].unlink_lifetime, [0 if binding else None])
                        completed += 1
                    visits |= pair[0].visits
                    count += 1
        self.assertGreater(completed, 0)
        self.assertLess(completed, count)
        for entry in bodies:
            self.assertIn(entry, visits, hex(entry))
        self.receipt('chain', paired_cases=count, completion_cleanup_cases=completed,
            actual_current_bodies=[dict(entry=entry, words=len(words)) for entry, words in bodies.items()],
            live_original_table_slot=3, all_9_pointers_fixed=True, all_connected_bodies_reached=True,
            independent_public_arithmetic_and_cleanup_order=True, lower_unlink_and_type_destructors_opaque=True,
            no_inverse_staged_image_or_full_gameplay_claim=True)


if __name__ == '__main__':
    unittest.main()
