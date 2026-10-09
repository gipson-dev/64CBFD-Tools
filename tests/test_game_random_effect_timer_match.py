"""Complete random-effect timer, live RNG mutations, owner and linked restoration."""

import csv
import hashlib
import itertools
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_random_effect_timer_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object, ELF_HEADER, SECTION_HEADER, SYMBOL
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_callback_update_match import public, external, outcome
from tools.tests.test_game_random_reload_timer_match import TimerOracle
from tools.tests import test_game_record_ring_shaping_recovery as shaping
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game_2062D0.c'
OWNER, TABLE, CALLER = 0x20000, 0x8008A4E8, 0x15149264
STEP, SCALE, BIAS = (screen.SYMBOLS[n] for n in ('D_800BE9E4', 'D_800AB464', 'D_800AB468'))
TIMERS = (0, 1, 0x7FFF, 0x8000, 0x8001, 0xFFFE, 0xFFFF)
STEPS = (0, 1, 2, 0x7FFF, 0x8000, 0x10000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
RANDOMS = (0, 1, 40, 41, 110, 111, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)


def source_shapes(root):
    source = (root / SOURCE).read_text()
    old = source.replace(screen.SELECTED, screen.ORIGINAL).replace(screen.DECLARATION,
        screen.OLD_DECLARATION).replace(screen.EFFECT, screen.OLD_EFFECT)
    assert old.count(screen.ORIGINAL) == 1 and old.count(screen.OLD_EFFECT) == 1
    return old, old.replace(screen.ORIGINAL, screen.SELECTED).replace(screen.OLD_DECLARATION,
        screen.DECLARATION).replace(screen.OLD_EFFECT, screen.EFFECT)


def fixture(timer=0, step=1, symbols=None):
    symbols = symbols or screen.SYMBOLS
    memory = {STACK + i: (i * 13 + 0xA5) & 255 for i in range(-0x600, 0x140)}
    memory.update({OWNER + i: (i * 17 + 0xA5) & 255 for i in range(-16, 256)})
    for name, value in (('D_800BE9E4', step), ('D_800AB464', bits(4.)), ('D_800AB468', bits(3.))):
        put(memory, symbols[name], value)
    for offset, value, width in ((0x28, timer, 2), (0x2C, bits(0.75), 4),
            (0x3C, 255, 1), (0x3D, 128, 1), (0x3E, 254, 1), (0xC, 129, 1), (1, 255, 1)):
        put(memory, OWNER + offset, value, width)
    return memory


def mutations(role, mode, symbols):
    if role == 'float' and mode == 1:
        return ((symbols['D_800AB464'], bits(2.), 4), (symbols['D_800AB468'], bits(-1.), 4),
            (OWNER + 0x2C, 0x80000000, 4))
    if role == 'integer-first' and mode == 2:
        return ((OWNER + 0x3C, 1, 1), (OWNER + 0x3D, 255, 1), (OWNER + 0x3E, 128, 1),
            (OWNER + 1, 2, 1), (OWNER + 0xC, 0, 1), (OWNER + 0x30, bits(-8.), 4))
    if role == 'effect' and mode == 3:
        return ((OWNER + 0x28, 0x1234, 2), (symbols['D_800BE9E4'], 999, 4),
            (OWNER + 0x3C, 128, 1), (OWNER + 0x30, bits(8.), 4))
    if role == 'integer-last' and mode == 4:
        return ((OWNER + 0x28, 0xFFFF, 2), (OWNER + 0xC, 17, 1))
    return ()


class EffectTimerReference:
    def __init__(self, memory, sample=0x3E800000, randoms=(0, 0), mode=0, symbols=None):
        self.memory, self.events, self.calls = dict(memory), [], []
        self.sample, self.randoms, self.mode = sample, randoms, mode
        self.symbols = symbols or screen.SYMBOLS

    def get(self, address, size=4):
        assert all(address + i in self.memory for i in range(size)), ('unmapped read', address, size)
        value = read(self.memory, address, size)
        self.events.append(('R', address, size, value))
        return value

    def put(self, address, value, size):
        value &= (1 << (size * 8)) - 1
        self.events.append(('W', address, size, value))
        assert all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        put(self.memory, address, value, size)

    def call(self, role, args=()):
        self.calls.append((role, args))
        self.events.append(('CALL', role, args))
        for address, value, size in mutations(role, self.mode, self.symbols):
            self.put(address, value, size)

    def run(self):
        step = self.get(self.symbols['D_800BE9E4'])
        timer = (self.get(OWNER + 0x28, 2) - step) & 65535
        self.put(OWNER + 0x28, timer, 2)
        if self.get(OWNER + 0x28, 2) & 32768:
            self.call('float')
            self.call('integer-first')
            scale = self.get(self.symbols['D_800AB464'])
            bias = self.get(self.symbols['D_800AB468'])
            first = self.randoms[0] % 41 + 35
            selector = self.get(OWNER + 0x3E, 1)
            kind = self.get(OWNER + 0x3C, 1)
            record_scale = self.get(OWNER + 0x2C)
            mode = self.get(OWNER + 0x3D, 1)
            channel = self.get(OWNER + 0xC, 1)
            context = self.get(OWNER + 1, 1)
            value = bits(floating(bits(floating(self.sample) * floating(scale))) + floating(bias))
            self.call('effect', (OWNER + 0x30, self.symbols['D_800A5480'], selector, value,
                first, kind, record_scale, 0, 0x3F800000, 0x3F800000, mode, 0, 1, 0, channel, context))
            self.call('integer-last')
            self.put(OWNER + 0x28, self.randoms[1] % 111 + 30, 2)
        return self


class EffectTimerOracle(TimerOracle, shaping.ShapingOracle):
    def __init__(self, words, memory, sample=0x3E800000, randoms=(0, 0), mode=0, phase=0,
            entry=screen.ENTRY, symbols=None, connected=None):
        TriangleOracle.__init__(self, words, memory, phase=phase, entry=entry,
            arguments=(OWNER,), connected=connected)
        self.fcsr = self.initial_fcsr = self.hi = self.lo = 0
        self.sample, self.randoms, self.mode = sample, randoms, mode
        self.symbols, self.random_index = symbols or screen.SYMBOLS, 0

    def record_call(self, target):
        if target == screen.ENTRY:
            self.calls.append(('callback', self.arguments(1)))
            return
        if target == self.symbols['func_150ADA68']:
            role, args = 'float', ()
        elif target == self.symbols['func_150ADA20']:
            role, args = ('integer-first' if self.random_index == 0 else 'integer-last'), ()
            self.random_index += 1
        else:
            assert target == self.symbols['func_151D9014'], hex(target)
            role, args = 'effect', self.arguments(16)
        self.calls.append((role, args))
        self.events.append(('CALL', role, args))

    def hook(self, target):
        role, args = self.calls[-1]
        for address, value, size in mutations(role, self.mode, self.symbols):
            self.put(address, value, size)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        if role == 'float':
            self.f[0] = self.sample
        elif role.startswith('integer'):
            self.r[2] = self.randoms[role == 'integer-last']
        elif self.mode == 5:
            for i in range(16):
                self.put(self.r[29] + i * 4, 0x76543210 + i, 4)


def symbol_size_offset(data):
    header = ELF_HEADER.unpack_from(data)
    headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
    offsets = []
    for section in headers:
        if section[1] != 2:
            continue
        strings = headers[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for offset in range(section[4], section[4] + section[5], section[9]):
            symbol = SYMBOL.unpack_from(data, offset)
            if names[symbol[0]:].split(b'\0', 1)[0].decode() == screen.FUNCTION:
                assert symbol[1] == screen.ENTRY and symbol[3] & 15 == 2
                offsets.append(offset + 8)
    assert len(offsets) == 1
    return offsets[0]


class GameRandomEffectTimerMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-random-effect-timer-test'
        cls.out.mkdir(exist_ok=True)
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected', screen.SELECTED)
        cls.retail = list(struct.unpack_from('>68I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        baseline = cls.out / 'baseline.json'
        if not baseline.exists():
            old, _ = source_shapes(cls.root)
            assert (cls.root / SOURCE).read_text() == old
            elf = cls.root / 'conker/build/conker.us.elf'
            functions, _, addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
            slots = {n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(
                struct.pack('>%dI' % len(w), *w)).hexdigest()) for n, w in functions.items()}
            previous = json.loads((cls.root / 'conker/build/game-record-constructor-test/after.json').read_text())
            assert slots == previous['slots'] and len(slots) == 6058
            with (cls.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
                guards = list(csv.DictReader(stream))
            with (cls.root / 'conker/progress.csv').open(newline='') as stream:
                progress = list(csv.DictReader(stream))
            assert guards == previous['guards'] and len(guards) == 11475
            assert progress == previous['progress']
            baseline.write_text(json.dumps(dict(slots=slots, guards=guards, progress=progress,
                source_sha256=hashlib.sha256(old.encode()).hexdigest()), indent=2) + '\n')
            (cls.out / 'before.elf').write_bytes(elf.read_bytes())
            for name in ('retail_word_patches.us.csv', 'progress.csv'):
                (cls.out / ('before-' + name)).write_bytes((cls.root / 'conker' / name).read_bytes())

    def receipt(self, name, value):
        (self.out / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')

    def compare(self, memory, sample=0x3E800000, randoms=(0, 0), mode=0, phase=0):
        reference = EffectTimerReference(memory, sample, randoms, mode)
        complete = outcome(reference)
        models = []
        for body in (self.words, self.retail):
            model = EffectTimerOracle(body, memory, sample, randoms, mode, phase)
            self.assertEqual(outcome(model), complete)
            self.assertEqual((external(model.memory), public(model.events), model.calls),
                (external(reference.memory), reference.events, reference.calls))
            models.append(model)
        self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events),
            (models[1].r, models[1].f, models[1].memory, models[1].events))
        return models[0], complete

    def test_01_direct_complete_slot_profiles_and_no_guards(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (68, 96, 0))
        self.assertEqual((self.words, self.meta['diagnostics'], self.meta['pool_bytes']), (self.retail, '', 0))
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, screen.SELECTED, p)[0] for p in screen.PROFILES]
        self.receipt('slot', dict(words=68, bytes=272, frame=96, direct_words=68, guards=0, profiles=profiles))

    def test_02_wrap_live_reads_rng_order_and_mixed_call_abi(self):
        count, seen = 0, set()
        for timer, step, random_word, mode, phase in itertools.product(TIMERS, STEPS, RANDOMS, range(6), (0, 8)):
            model, complete = self.compare(fixture(timer, step), randoms=(random_word, RANDOMS[-1 - RANDOMS.index(random_word)]),
                mode=mode, phase=phase)
            self.assertTrue(complete)
            seen.update(model.visits)
            count += 1
        for byte, offset in itertools.product(range(256), (1, 0xC, 0x3C, 0x3D, 0x3E)):
            memory = fixture()
            put(memory, OWNER + offset, byte, 1)
            self.compare(memory, randoms=(0xFFFFFFFF, 0x80000000))
            count += 1
        for sample in (0, 0x80000000, 1, 0x80000001, 0x3E800000, 0x3F400000, 0x7F7FFFFF, 0xFF7FFFFF):
            self.compare(fixture(), sample)
            count += 1
        self.assertTrue(set(range(screen.ENTRY, screen.ENTRY + 272, 4)) <= seen)
        self.receipt('guest', dict(cases=count, executions=count * 2, all_68_words_reached=True,
            all_unsigned_byte_fields=True, signed_halfword_wrap=True, exact_public_access_order=True,
            sixteen_argument_words=True, saved_GP_FP=True, void_return_not_invented=True,
            hardware_FCSR_flags=False))

    def test_03_real_missing_bytes_and_lazy_expiry_reads(self):
        count = 0
        for timer, phase, mode in itertools.product((0, 1, 0x8000), (0, 8), (0, 1, 3, 5)):
            memory = fixture(timer)
            ref = EffectTimerReference(memory, mode=mode).run()
            addresses = {e[1] + i for e in ref.events if e[0] in ('R', 'W') for i in range(e[2])}
            for address in sorted(addresses):
                missing = dict(memory)
                del missing[address]
                self.compare(missing, mode=mode, phase=phase)
                count += 1
            if timer == 1:
                lazy = {a: v for a, v in memory.items() if STACK - 0x600 <= a < STACK + 0x140
                    or OWNER + 0x28 <= a < OWNER + 0x2A or STEP <= a < STEP + 4}
                self.compare(lazy, mode=mode, phase=phase)
        self.receipt('faults', dict(real_missing_byte_pairs=count, expiry_fields_lazy=True,
            hardware_traps=False, portable_invalid_C=False))

    def test_04_complete_forms_and_effective_compiled_negatives(self):
        records, negatives = [], []
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, 'form-' + name, body)
            records.append(meta)
            equal = []
            for timer, step, random_word, mode in itertools.product((0, 1, 0x8000), (1, 0x10000),
                    (40, 0xFFFFFFFF), (0, 2, 3)):
                memory = fixture(timer, step)
                ref = EffectTimerReference(memory, randoms=(random_word, random_word), mode=mode).run()
                model = EffectTimerOracle(words, memory, randoms=(random_word, random_word), mode=mode).run()
                equal.append((external(model.memory), public(model.events), model.calls) ==
                    (external(ref.memory), ref.events, ref.calls))
            if name.startswith('negative-'):
                self.assertFalse(all(equal), name)
                negatives.append(name)
            else:
                self.assertTrue(all(equal), name)
        self.receipt('forms', dict(forms=len(records), samples=36, compiled_negatives=negatives, measurements=records))

    def test_05_complete_copied_owner_pools_padding_and_independent_links(self):
        objects, diagnostics = [], []
        for name, source in zip(('baseline', 'selected'), source_shapes(self.root)):
            obj, warnings = compile_owner(self.root, self.out, source, 'owner-' + name)
            processed = self.out / ('owner-' + name + '-post.o')
            processed.write_bytes(obj.read_bytes())
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(processed.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(processed)
            diagnostics.append(warnings)
        self.assertEqual(diagnostics[0], diagnostics[1])
        old, before, old_rel = parse_object(objects[0])
        text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), before.keys())
        for name, fn in current.items():
            if name == screen.FUNCTION:
                continue
            prior = before[name]
            self.assertEqual(fn['size'], prior['size'], name)
            self.assertEqual(text[fn['value']:fn['value'] + fn['size']], old[prior['value']:prior['value'] + prior['size']], name)
            self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                {o - prior['value']: r for o, r in old_rel.items() if prior['value'] <= o < prior['value'] + prior['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        asm = self.out / 'padded.s'
        subprocess.run([sys.executable, str(self.root / 'tools/pad_c_object.py'), str(objects[1]),
            str(self.root / 'conker/retail_layout.us.txt'), 'game_2062D0', str(asm), '--word-patches',
            str(self.root / 'conker/retail_word_patches.us.csv')], check=True, capture_output=True)
        assembly = asm.read_text()
        begin = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), begin)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[begin:end])
        solo, obj = self.out / 'solo.s', self.out / 'solo.o'
        solo.write_text('.text\n.set noreorder\n' + assembly[begin:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(solo)], check=True, capture_output=True)
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 272)
        self.assertEqual(parse_object(obj)[2], self.meta['relocations'])
        count = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10007FFC, 0x80008000, 0x8FFF7FFC)):
            defs = dict(screen.SYMBOLS)
            if variant:
                for i, name in enumerate(defs):
                    defs[name] = ((entry & 0xF0000000) + 0x208000 + i * 0x100) if name.startswith('func_') else 0x81007FFC + i * 4
            script, elf = self.out / ('rebase-%d.ld' % variant), self.out / ('rebase-%d.elf' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in defs.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>68I', sections(elf)['.text'][1]))
            for timer, mode, phase in itertools.product((0, 1, 0x8000), range(6), (0, 8)):
                memory = fixture(timer, symbols=defs)
                ref = EffectTimerReference(memory, randoms=(0xFFFFFFFF, 0x80000000), mode=mode, symbols=defs).run()
                model = EffectTimerOracle(words, memory, randoms=(0xFFFFFFFF, 0x80000000), mode=mode,
                    phase=phase, entry=entry, symbols=defs).run()
                self.assertEqual((external(model.memory), public(model.events), model.calls),
                    (external(ref.memory), ref.events, ref.calls))
                count += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, pools_and_relative_relocations_unchanged=True,
            diagnostics=len(diagnostics[0]), direct_padded_bytes=272, guards=0, independent_links=4, cases=count))

    def test_06_linked_only_target_slot_and_symbol_size_change(self):
        baseline = json.loads((self.out / 'baseline.json').read_text())
        old, selected = source_shapes(self.root)
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), baseline['source_sha256'])
        installed = (self.root / SOURCE).read_text() == selected
        elf = self.root / 'conker/build/conker.us.elf'
        functions, _, addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
        slots = {n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(
            struct.pack('>%dI' % len(w), *w)).hexdigest()) for n, w in functions.items()}
        expected = dict(baseline['slots'])
        data = bytearray((self.out / 'before.elf').read_bytes())
        if installed:
            expected[screen.FUNCTION] = dict(address=screen.ENTRY, words=68,
                sha256=hashlib.sha256(struct.pack('>68I', *self.retail)).hexdigest())
            header = ELF_HEADER.unpack_from(data)
            sections_ = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
            offsets = [s[4] + screen.ENTRY - s[3] for s in sections_ if s[1] == 1
                and s[3] <= screen.ENTRY and screen.ENTRY + 272 <= s[3] + s[5]]
            self.assertEqual(len(offsets), 1)
            data[offsets[0]:offsets[0] + 272] = struct.pack('>68I', *self.retail)
            offset = symbol_size_offset(data)
            self.assertEqual(struct.unpack_from('>I', data, offset)[0], 12)
            struct.pack_into('>I', data, offset, 272)
            self.assertEqual(functions[screen.FUNCTION], self.retail)
        self.assertEqual(slots, expected)
        self.assertEqual(elf.read_bytes(), data)
        self.assertTrue(audit_layout(elf, self.root / 'conker')['exact'])
        for name in ('retail_word_patches.us.csv', 'progress.csv'):
            self.assertEqual((self.root / 'conker' / name).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        self.receipt('linked', dict(installed=installed, symbols=len(slots), target_words=68,
            full_ELF_except_target_and_its_symbol_size_unchanged=True, symbol_size_change=[12, 272] if installed else None,
            guards=11475, progress_unchanged=True, elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()))
        if installed:
            self.receipt('after', dict(slots=slots, guards=baseline['guards'], progress=baseline['progress']))

    def test_07_native32_exhaustive_timer_width_fields_and_canaries(self):
        self.fixture = r'''typedef unsigned char u8; typedef signed char s8;
typedef signed short s16; typedef int s32; typedef unsigned int u32; typedef float f32;
static union { u32 align; u8 bytes[512]; } storage;
static u8 *owner=storage.bytes+16;
static s32 D_800BE9E4; static f32 D_800AB464, D_800AB468, D_800A5480;
static u32 firstRandom, lastRandom, sampleBits;
static int calls,error;
static u32 toBits(f32 value) { union { f32 f; u32 u; } v; v.f=value; return v.u; }
static f32 fromBits(u32 value) { union { f32 f; u32 u; } v; v.u=value; return v.f; }
static f32 func_150ADA68(void) {
    if(calls++!=0) error=1;
    return fromBits(sampleBits);
}
static s32 func_150ADA20(void) {
    int before=calls++;
    if(before!=1 && before!=3) error=2;
    return (s32)(before==1?firstRandom:lastRandom);
}
static void *func_151D9014(void *position,f32 *basis,u8 selector,f32 scale,s16 duration,
    u8 kind,f32 recordScale,u8 flag,f32 sx,f32 sy,u8 mode,s32 extra,u8 active,u8 zero,
    u8 channel,s32 context) {
    volatile f32 product=fromBits(sampleBits)*D_800AB464;
    f32 wanted=product+D_800AB468;
    if(calls++!=2 || position!=owner+0x30 || basis!=&D_800A5480 || selector!=owner[0x3E]
       || toBits(scale)!=toBits(wanted) || duration!=(s16)(firstRandom%41U+35)
       || kind!=owner[0x3C] || toBits(recordScale)!=*(u32 *)(owner+0x2C) || flag
       || sx!=1.0f || sy!=1.0f || mode!=owner[0x3D] || extra || active!=1 || zero
       || channel!=owner[0xC] || context!=owner[1]) error=3;
    return owner;
}
static void initialize(u32 timer,u32 step) {
    int i; for(i=0;i<512;i++) storage.bytes[i]=(u8)(i*17+0xA5);
    *(u16 *)(owner+0x28)=(u16)timer; *(u32 *)(owner+0x2C)=0x80000000;
    D_800BE9E4=(s32)step; D_800AB464=4.0f; D_800AB468=3.0f;
    firstRandom=0xFFFFFFFF; lastRandom=0x80000000; sampleBits=0x3E800000;
    calls=error=0;
}
'''.replace('typedef int s32;', 'typedef unsigned short u16; typedef int s32;') + screen.SELECTED + '\n'
        self.run_host(r'''
u32 timer, index, reduced; int i,field,byte; u8 before[512];
static u32 steps[]={0,1,0x10000,0x7FFFFFFF,0x80000000};
static int fields[]={1,0xC,0x3C,0x3D,0x3E};
static u32 samples[]={0,0x80000000,1,0x80000001,0x3E800000,0x3F400000,0x7F7FFFFF,0xFF7FFFFF};
for(timer=0;timer<65536;timer++) for(index=0;index<5;index++) {
    initialize(timer,steps[index]);
    for(i=0;i<512;i++) before[i]=storage.bytes[i];
    func_151D9EB0(owner);
    reduced=(timer-steps[index])&65535;
    if(error || calls!=((reduced&32768)?4:0)) return 1;
    if(*(u16 *)(owner+0x28)!=((reduced&32768)?lastRandom%111U+30:reduced)) return 2;
    for(i=0;i<512;i++) if(i!=16+0x28 && i!=16+0x29 && before[i]!=storage.bytes[i]) return 3;
}
for(field=0;field<5;field++) for(byte=0;byte<256;byte++) {
    initialize(0,1); owner[fields[field]]=(u8)byte;
    for(i=0;i<512;i++) before[i]=storage.bytes[i];
    func_151D9EB0(owner);
    if(error || calls!=4 || *(u16 *)(owner+0x28)!=lastRandom%111U+30) return 4;
    for(i=0;i<512;i++) if(i!=16+0x28 && i!=16+0x29 && before[i]!=storage.bytes[i]) return 5;
}
for(index=0;index<8;index++) {
    initialize(0,1); sampleBits=samples[index];
    func_151D9EB0(owner);
    if(error || calls!=4) return 6;
}
''')
        self.receipt('native', dict(cases=65536 * 5 + 256 * 5 + 8, actual_native32_C=True,
            all_timer_values=True, five_unsigned_byte_fields=True, full_512_byte_canaries=True,
            signed_overflow_avoided=True, RNG_and_effect_bounded=True))

    def test_08_actual_callback_table_and_complete_record_dispatcher(self):
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        caller = functions['func_15149264']
        self.assertEqual((addresses['func_15149264'], len(caller)), (CALLER, 45))
        address, pool = sections(self.root / 'conker/build/conker.us.elf')['.game_data']
        self.assertEqual(struct.unpack_from('>I', pool, TABLE + 74 * 4 - address)[0], screen.ENTRY)
        count, seen, caller_seen = 0, set(), set()
        for timer, flag, step, mode, phase in itertools.product((0, 1, 0x8000), (0, 1), (0, 1), range(5), (0, 8)):
            memory = fixture(timer, step)
            put(memory, OWNER + 0xD, flag, 1)
            put(memory, OWNER + 0xE, 10, 2)
            put(memory, OWNER + 0x10, 255, 1)
            put(memory, OWNER + 0x11, 74, 1)
            put(memory, TABLE + 74 * 4, screen.ENTRY)
            before_callback = dict(memory)
            if flag:
                put(before_callback, OWNER + 0xE, 10 - step, 2)
            ref = EffectTimerReference(before_callback, randoms=(0xFFFFFFFF, 0x80000000), mode=mode).run()
            models = []
            for body in (self.words, self.retail):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 272, 4), body))
                model = EffectTimerOracle(caller, memory, randoms=(0xFFFFFFFF, 0x80000000), mode=mode,
                    phase=phase, entry=CALLER, connected=connected).run()
                self.assertEqual(external(model.memory), external(ref.memory))
                self.assertEqual(model.calls, [('callback', (OWNER,)), *ref.calls])
                seen.update(model.visits & set(connected))
                caller_seen.update(model.visits & set(range(CALLER, CALLER + 180, 4)))
                models.append(model)
            self.assertEqual((models[0].memory, models[0].events, models[0].r, models[0].f),
                (models[1].memory, models[1].events, models[1].r, models[1].f))
            count += 1
        self.assertEqual(len(seen), 68)
        self.receipt('caller', dict(cases=count, executions=count * 2, actual_table_index=74,
            complete_dispatcher_words=45, reached_dispatcher_words=len(caller_seen), all_68_callback_words=True,
            cleanup_paths_not_claimed=True, RNG_and_effect_bounded=True, hardware_gameplay=False))
