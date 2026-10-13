"""Timer O32 holes, unsigned64 arithmetic, opaque providers and linked isolation."""
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_one_shot_timer_candidates as screen
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, parse_object, read_c_string
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.check_game_data_layout import audit_layout

LATCH, CLOCK, TIMER, QUEUE, MUL, DIV, SET = screen.SYMBOLS.values()
MASK64 = (1 << 64) - 1
CLOCKS = (0, 1, 39999, 40000, 46875000, 0xFFFFFFFF, 0x100000000,
          0x7FFFFFFFFFFFFFFF, 0x8000000000000000, MASK64 // 25,
          MASK64 // 25 + 1, MASK64)
RESULTS = (0, 0xFFFFFFFF, 0x12345678)


def countdown(clock):
    return ((clock * 25) & MASK64) // 1000000


def fixture(flag=1, clock=46875000):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x80, 0x80)}
    for base, length in ((LATCH, 1), (CLOCK, 8), (TIMER, 32), (QUEUE, 24)):
        memory.update({base + i: (i * 13 + 0xA5) & 255 for i in range(length)})
    put(memory, LATCH, flag, 1)
    put(memory, CLOCK, clock, 8)
    return memory


def symbol_rows(data):
    header = ELF_HEADER.unpack_from(data)
    sections = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
    table = next(section for section in sections if section[1] == 2)
    strings = sections[table[6]]
    names = data[strings[4]:strings[4] + strings[5]]
    return [(offset, read_c_string(names, fields[0]), fields, strings[4] + fields[0])
        for offset in range(table[4], table[4] + table[5], table[9] or SYMBOL.size)
        for fields in [SYMBOL.unpack_from(data, offset)]]


def canonical_symbols(data):
    return Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(data))


def apply_timer_symbol_serialization(expected):
    rows = {name: (offset, fields, string) for offset, name, fields, string in symbol_rows(expected)
            if name in ('D_800BE6E0', 'D_800BE2F0')}
    assert set(rows) == {'D_800BE6E0', 'D_800BE2F0'}
    first, second = rows['D_800BE6E0'], rows['D_800BE2F0']
    for name, value in (('D_800BE6E0', 0x800BE6E0), ('D_800BE2F0', 0x800BE2F0)):
        _, fields, string = rows[name]
        assert fields[1:] == (value, 0, 16, 0, 65521)
        assert expected[string:string + 11] == name.encode() + b'\0'
    assert abs(first[0] - second[0]) == SYMBOL.size
    assert abs(first[2] - second[2]) == 11
    struct.pack_into('>I', expected, first[0] + 4, second[1][1])
    struct.pack_into('>I', expected, second[0] + 4, first[1][1])
    expected[first[2]:first[2] + 11] = b'D_800BE2F0\0'
    expected[second[2]:second[2] + 11] = b'D_800BE6E0\0'


class AccessFault(Exception):
    pass


class TimerOracle(TriangleOracle):
    def __init__(self, words, memory, phase=0, mutation=0, status=0):
        self.fault, self.accesses, self.in_hook = None, 0, False
        super().__init__(words, memory, phase=phase, entry=screen.ENTRY, arguments=())
        self.mutation, self.status = mutation, status
        self.product, self.quotient = None, None
        self.raw_calls, self.timer_entry_latch = [], None

    def gate(self):
        if self.recording and not self.in_hook:
            if self.fault == self.accesses:
                raise AccessFault()
            self.accesses += 1

    def get(self, address, size):
        self.gate()
        return super().get(address, size)

    def put(self, address, value, size):
        self.gate()
        return super().put(address, value, size)

    def record_call(self, target):
        assert target in (MUL, DIV, SET)
        args = tuple(self.r[4:8])
        if target == SET:
            raw = args + tuple(self.peek(self.r[29] + 0x10 + i * 4, 4) for i in range(4))
            self.raw_calls.append(raw)
            # Slot1 is the O32 alignment hole, not an argument value.
            args = tuple(raw[i] for i in (0, 2, 3, 4, 5, 6, 7))
            self.timer_entry_latch = self.peek(LATCH, 1)
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        self.in_hook = True
        try:
            args = self.calls[-1][1]
            if target == MUL:
                a, b = args[0] << 32 | args[1], args[2] << 32 | args[3]
                self.product = (a * b) & MASK64
                result = self.product
                if self.mutation:
                    self.put(CLOCK, self.peek(CLOCK, 8) ^ MASK64, 8)
                    self.put(LATCH, 0, 1)
            elif target == DIV:
                numerator, denominator = args[0] << 32 | args[1], args[2] << 32 | args[3]
                assert denominator == 1000000
                self.quotient = numerator // denominator
                result = self.quotient
            else:
                pointer, high, low, interval_high, interval_low, queue, message = args
                assert (pointer, interval_high, interval_low, queue, message) == (TIMER, 0, 0, QUEUE, 6)
                result = self.status
                self.put(TIMER + 8, 0, 8)
                self.put(TIMER + 16, high << 32 | low, 8)
                self.put(TIMER + 24, queue, 4)
                self.put(TIMER + 28, message, 4)
                if self.mutation:
                    self.put(LATCH, 0x80, 1)
            for register in (1, 2, 3, *range(4, 16), 24, 25):
                self.r[register] = 0xA5000000 + register
            self.f[:20] = [0xA5000000 + i for i in range(20)]
            if target in (MUL, DIV):
                self.r[2], self.r[3] = result >> 32, result & 0xFFFFFFFF
            else:
                self.r[2] = result
        finally:
            self.in_hook = False


class GameOneShotTimerMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-one-shot-timer-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            layout='conker/retail_layout.us.txt', makefile='conker/Makefile')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_before = cls.owner_before.replace(screen.SELECTED, screen.ORIGINAL).replace(screen.DECLARATIONS, '')
        cls.owner_after = screen.recovered_owner(cls.owner_before)
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'direct')
        cls.old_meta, cls.old = screen.compile_candidate(cls.root, cls.out, 'placeholder', screen.ORIGINAL)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>38I', cls.rom, screen.ROM))
        cls.original = (cls.root / 'conker/asm/48FD0.s').read_text().split('glabel ' + screen.FUNCTION + '\n', 1)[1]
        cls.original = 'glabel ' + screen.FUNCTION + '\n' + cls.original.split('endlabel ' + screen.FUNCTION, 1)[0] + 'endlabel ' + screen.FUNCTION + '\n'

    def test_01_complete_direct_body_frame_and_frozen_actual_helpers(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
                          self.meta['pool_bytes'], self.meta['diagnostics']), (38, 40, 0, 0, ''))
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.old_meta['body_words'], self.old_meta['differences']), (3, 37))
        self.assertTrue(all(not value[1] for name, value in sections(self.out / 'direct.o').items()
            if name.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))))
        for address, length in ((MUL, 48), (DIV, 60), (SET, 224)):
            offset = elf_slot_offset(self.before, address, length)
            self.assertEqual(self.before[offset:offset + length], self.rom[address - 0x10000000:address - 0x10000000 + length])
        self.assertNotIn('OS_USEC_TO_CYCLES', screen.SELECTED)

    def test_02_latches_clock_overflow_o32_hole_provider_mutation_and_complete_state(self):
        count = 0
        for flag, clock, phase, mutation, status in itertools.product(range(256), CLOCKS, (0, 8), (0, 1), RESULTS):
            memory = fixture(flag, clock)
            pair = [TimerOracle(words, memory, phase, mutation, status).run() for words in (self.retail, self.words)]
            for field in ('memory', 'events', 'r', 'f', 'calls'):
                self.assertEqual(getattr(pair[0], field), getattr(pair[1], field))
            expected = dict(memory)
            if flag:
                wanted = countdown(clock)
                self.assertEqual(pair[1].calls, [
                    (MUL, (0, 25, clock >> 32, clock & 0xFFFFFFFF)),
                    (DIV, (((clock * 25) & MASK64) >> 32, (clock * 25) & 0xFFFFFFFF, 0, 1000000)),
                    (SET, (TIMER, wanted >> 32, wanted & 0xFFFFFFFF, 0, 0, QUEUE, 6))])
                self.assertEqual(pair[1].timer_entry_latch, 0 if mutation else flag)
                put(expected, LATCH, 0, 1)
                if mutation:
                    put(expected, CLOCK, clock ^ MASK64, 8)
                put(expected, TIMER + 8, 0, 8)
                put(expected, TIMER + 16, wanted, 8)
                put(expected, TIMER + 24, QUEUE)
                put(expected, TIMER + 28, 6)
            else:
                self.assertEqual(pair[1].calls, [])
            external = lambda m: {a: b for a, b in m.items() if not STACK - 0x80 <= a < STACK + 0x80}
            self.assertEqual(external(pair[1].memory), external(expected))
            count += 1
        self.assertEqual(count, 36864)
        old = TimerOracle(self.old, fixture()).run()
        self.assertEqual(old.calls, [])
        self.assertNotEqual(old.memory[LATCH], 0)
        (self.out / 'guest.json').write_text(json.dumps(dict(cases=count,
            alignment_hole_not_argument=True, helpers_are_bounded_opaque_providers=True,
            hardware_interrupt_queue_and_64bit_helper_instructions_not_exercised=True), indent=2) + '\n')

    def test_03_inactive_unmapped_clock_fail_closed_and_fired_own_access_cuts(self):
        inactive = {a: b for a, b in fixture(0).items() if STACK - 0x80 <= a < STACK + 0x80 or a == LATCH}
        self.assertEqual(TimerOracle(self.words, inactive).run().calls, [])
        for base, length in ((LATCH, 1), (CLOCK, 8)):
            for byte in range(length):
                memory = fixture()
                del memory[base + byte]
                with self.assertRaises(AssertionError):
                    TimerOracle(self.words, memory).run()
        count = 0
        for flag, phase, mutation in itertools.product((0, 1, 0xFF), (0, 8), (0, 1)):
            memory = fixture(flag, MASK64)
            normal = TimerOracle(self.words, memory, phase, mutation, 0xFFFFFFFF).run()
            for fault in range(normal.accesses):
                pair = [TimerOracle(words, memory, phase, mutation, 0xFFFFFFFF) for words in (self.retail, self.words)]
                for model in pair:
                    model.fault = fault
                    with self.assertRaises(AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, fault)
                self.assertEqual((pair[0].memory, pair[0].events, pair[0].r, pair[0].f),
                                 (pair[1].memory, pair[1].events, pair[1].r, pair[1].f))
                count += 1
            terminal = TimerOracle(self.words, memory, phase, mutation)
            terminal.fault = normal.accesses
            terminal.run()
        (self.out / 'faults.json').write_text(json.dumps(dict(fired_pairs=count,
            own_accesses_only=True, argument_observation_and_provider_accesses_excluded=True), indent=2) + '\n')

    def run_native(self, name, source, profile='-O2'):
        path, binary = self.out / (name + '.c'), self.out / name
        path.write_text(source)
        runtime = Path('/lib/i386-linux-gnu/libgcc_s.so.1')
        self.assertTrue(runtime.is_file(), 'Prepared 32-bit libgcc runtime is required; do not install it from this test')
        result = subprocess.run(['cc', '-m32', profile, '-std=c99', '-D_LANGUAGE_C', '-D_MIPS_SZLONG=32',
            '-I', str(self.root / 'conker/include'), '-I', str(self.root / 'conker/include/2.0L'),
            '-fno-strict-aliasing', '-mstackrealign', '-ffreestanding', '-nostdlib',
            '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
            '-Wno-unused-parameter', str(path), str(runtime), '-o', str(binary)], capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stdout + result.stderr), (0, ''))
        result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout + result.stderr

    def native_source(self, body):
        clocks = list(CLOCKS)
        seed = 0x123456789ABCDEF0
        for _ in range(64):
            seed = (seed * 6364136223846793005 + 1442695040888963407) & MASK64
            clocks.append(seed)
        table = ',\n'.join('{0x%XULL,0x%XULL}' % (clock, countdown(clock)) for clock in clocks)
        return '''#include <ultra64.h>
u8 D_80084064;u64 D_8002BD10;OSTimer D_800BE6E0;OSMesgQueue D_8003B218;
typedef char ABI[(sizeof(void*)==4 && sizeof(OSTime)==8 && sizeof(OSTimer)==32 && sizeof(OSMesg)==4)?1:-1];
static struct ClockCase {u64 clock,expected;} vectors[]={
''' + table + '''};
static int calls,error,mutation,status;static u8 entryFlag;static u64 expectedCount;
int osSetTimer(OSTimer *timer,OSTime count,OSTime interval,OSMesgQueue *queue,OSMesg message){
 if(timer!=&D_800BE6E0 || queue!=&D_8003B218 || count!=expectedCount || interval!=0 || message!=(OSMesg)6 || D_80084064!=entryFlag)error=1;
 calls++;timer->value=count;timer->interval=interval;timer->mq=queue;timer->msg=message;
 if(mutation){D_80084064=0x80;D_8002BD10^=~0ULL;}
 return status;
}
''' + body + '''
static int check(void){
 unsigned int f,i,j;int m,s;OSTimer expected;
 for(f=0;f<256;f++)for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++)for(m=0;m<2;m++)for(s=0;s<3;s++){
  D_800BE6E0.next=&D_800BE6E0;D_800BE6E0.prev=&D_800BE6E0;
  D_800BE6E0.value=0xABCDEF1234567890ULL;D_800BE6E0.interval=0x1234567890ABCDEFULL;
  D_800BE6E0.mq=&D_8003B218;D_800BE6E0.msg=(OSMesg)0x55;
  expected=D_800BE6E0;entryFlag=(u8)f;D_80084064=entryFlag;D_8002BD10=vectors[i].clock;expectedCount=vectors[i].expected;
  mutation=m;status=s==0?0:s==1?-1:0x12345678;calls=error=0;
  func_1501BB20();
  if(error || calls!=(f!=0) || D_80084064!=0)return 1;
  if(D_8002BD10!=(vectors[i].clock^((f && m)?~0ULL:0ULL)))return 2;
  if(f){expected.value=expectedCount;expected.interval=0;expected.mq=&D_8003B218;expected.msg=(OSMesg)6;}
  for(j=0;j<sizeof(expected);j++)if(((u8*)&expected)[j]!=((u8*)&D_800BE6E0)[j])return 3;
 }
 return 0;
}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");for(;;){}}
'''

    def test_04_native32_actual_sdk_types_libgcc_arithmetic_and_effective_controls(self):
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-' + profile[1:], self.native_source(screen.SELECTED), profile), (0, ''))
        controls = [('wrong-scale', screen.SELECTED.replace('25 *', '24 *')),
                    ('narrow-clock', screen.SELECTED.replace('25 * D_8002BD10', '25ULL * (u32)D_8002BD10')),
                    ('missing-clear', screen.SELECTED.replace('        D_80084064 = 0;', '')),
                    ('early-clear', screen.SELECTED.replace('        osSetTimer', '        D_80084064 = 0;\n        osSetTimer')
                        .replace('        D_80084064 = 0;\n    }', '    }'))]
        for name, body in controls:
            self.assertNotEqual(body, screen.SELECTED)
            code, _ = self.run_native('negative-' + name, self.native_source(body))
            self.assertIn(code, (1, 2, 3))
        (self.out / 'native.json').write_text(json.dumps(dict(cases_per_profile=116736,
            comparisons=233472, profiles=['O2', 'O0'], actual_sdk_header=True,
            existing_shared_libgcc_arithmetic=True, native_abi_not_o32=True), indent=2) + '\n')

    def test_05_actual_owner_postprocess_neighbors_pools_and_both_padders(self):
        objects, diagnostics = [], []
        for name, source in (('before', self.owner_before), ('after', self.owner_after)):
            obj, warnings = compile_owner(self.root, self.out, source, 'owner-' + name)
            diagnostics.append(warnings)
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(obj)
        self.assertEqual(diagnostics[0], diagnostics[1])
        before, after = [parse_object(obj) for obj in objects]
        self.assertEqual(before[1].keys(), after[1].keys())
        for name in before[1]:
            a, b = before[1][name], after[1][name]
            if name != screen.FUNCTION:
                self.assertEqual(before[0][a['value']:a['value'] + a['size']], after[0][b['value']:b['value'] + b['size']], name)
                self.assertEqual({o - a['value']: r for o, r in before[2].items() if a['value'] <= o < a['value'] + a['size']},
                                 {o - b['value']: r for o, r in after[2].items() if b['value'] <= o < b['value'] + b['size']}, name)
        isolated = parse_object(self.out / 'direct.o')
        target = after[1][screen.FUNCTION]
        self.assertEqual(after[0][target['value']:target['value'] + 152], isolated[0][:152])
        self.assertEqual({o - target['value']: r for o, r in after[2].items()
            if target['value'] <= o < target['value'] + 152}, isolated[2])
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        padded = []
        for script in ('pad_c_object.py', 'pad_generated_object.py'):
            asm = self.out / (script + '.s')
            args = [str(objects[1]), str(self.root / 'conker/retail_layout.us.txt'), 'generated_48FD0', str(asm)] if script == 'pad_c_object.py' else [
                str(objects[1]), str(self.root / 'conker/asm/48FD0.s'), str(asm), '--filename', 'generated_48FD0']
            result = subprocess.run([sys.executable, str(self.root / 'tools' / script), *args,
                '--word-patches', str(self.root / 'conker/retail_word_patches.us.csv')], capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
            obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
                '-o', str(obj), str(asm)], check=True, capture_output=True)
            padded.append(parse_object(obj))
        self.assertEqual(padded[0], padded[1])
        self.assertEqual(padded[0][1][screen.FUNCTION]['size'], 152)
        (self.out / 'owner.json').write_text(json.dumps(dict(neighbors=len(after[1]) - 1,
            both_full_owner_padders_identical=True, postprocessed_assembly_retained=True,
            warnings_unchanged=len(diagnostics[1]), normalized_pools_equal=True), indent=2) + '\n')

    def test_06_independent_original_rebases_and_static_void_caller_contract(self):
        asm = self.out / 'original.s'
        asm.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + self.original)
        obj = asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        layouts = [(screen.ENTRY, screen.SYMBOLS),
            (0x1521BB20, dict(screen.SYMBOLS, D_80084064=0x80108004, D_8002BD10=0x80207FF8,
                             D_800BE6E0=0x80308000, D_8003B218=0x80407FFC)),
            (0x1531BB20, dict(screen.SYMBOLS, D_80084064=0x80217FFC, D_8002BD10=0x80318000,
                             D_800BE6E0=0x80418000, D_8003B218=0x80518004))]
        for i, (entry, symbols) in enumerate(layouts):
            self.assertEqual(symbols['D_8002BD10'] % 8, 0)
            with patch.object(screen, 'ENTRY', entry), patch.object(screen, 'SYMBOLS', symbols):
                _, candidate = screen.compile_candidate(self.root, self.out, 'rebase-' + str(i))
            original_symbols = dict(symbols, D_8002BD14=symbols['D_8002BD10'] + 4)
            ld = self.out / ('original-' + str(i) + '.ld')
            ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            elf = ld.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(ld), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in original_symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            original_text = sections(elf)['.text'][1]
            self.assertEqual(candidate, list(struct.unpack_from('>38I', original_text)))
            self.assertFalse(any(original_text[152:]))
        caller = (self.root / 'conker/asm/nonmatchings/game_34F20/func_15007B3C.s').read_text()
        self.assertIn('/* 35358 15007EA8 0D406EC8 */  jal        func_1501BB20', caller)
        self.assertIn('/* 35360 15007EB0 0D40221C */  jal        func_15008870', caller)
        self.assertIn('func_1501BB20();', (self.root / 'conker/src/game_45B80.c').read_text())
        self.assertTrue(screen.SELECTED.startswith('void func_1501BB20(void)'))
        (self.out / 'rebases.json').write_text(json.dumps(dict(layouts=3, clock_alignment8=True,
            low_word_alias_plus4=True, caller_return_ignored_static_only=True), indent=2) + '\n')

    def test_07_literal_whole_image_protected_inputs_and_game_data(self):
        current = (self.root / self.paths['elf']).read_bytes()
        offset = elf_slot_offset(current, screen.ENTRY, 152)
        self.assertEqual(offset, elf_slot_offset(self.before, screen.ENTRY, 152))
        source = (self.root / screen.SOURCE).read_text()
        expected = bytearray(self.before)
        if source == self.owner_after:
            expected[offset:offset + 152] = struct.pack('>38I', *self.retail)
            with patch.multiple(descriptor.screen, FUNCTION=screen.FUNCTION, ENTRY=screen.ENTRY):
                size_offset = descriptor.size_field(self.before)
                self.assertEqual(size_offset, descriptor.size_field(current))
            struct.pack_into('>I', expected, size_offset, 152)
            self.assertEqual(canonical_symbols(bytes(expected)), canonical_symbols(current))
            if self.before[offset:offset + 152] != struct.pack('>38I', *self.retail):
                apply_timer_symbol_serialization(expected)
        else:
            self.assertEqual(source, self.owner_before)
        self.assertEqual(current, bytes(expected))
        # Corruptions outside the closed serialization permutation still fail.
        for location in (offset + 8, 0x100, size_offset if source == self.owner_after else offset):
            corrupted = bytearray(current)
            corrupted[location] ^= 1
            with self.assertRaises(AssertionError):
                self.assertEqual(bytes(corrupted), bytes(expected))
        for name in ('guards', 'progress', 'layout', 'makefile'):
            self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        (self.out / 'linked-audit.json').write_text(json.dumps(dict(installed=source == self.owner_after,
            literal_image_only_target_slot_size_and_closed_abs_symbol_serialization=True,
            named_symbols_unchanged_except_target_size=True,
            abs_pair=['D_800BE6E0', 'D_800BE2F0'], data=data), indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
