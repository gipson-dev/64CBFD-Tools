"""Complete mixed-ABI trail constructor; explicitly not a byte-exact match."""

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
from tools.experiments import game_trail_effect_constructor_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_callback_update_match import public, external, outcome
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_record_ring_shaping_recovery as shaping
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game_2062D0.c'
POSITION, VELOCITY, CREATED, PAYLOAD = 0x20000, 0x21000, 0x22000, 0x23000
PATTERNS = (0, 0x80000000, 1, 0x80000001, 0x3F800000, 0x41400000,
    0x7F7FFFFF, 0xFF7FFFFF, 0x7F800000, 0xFF800000, 0x7FC12345, 0x7F812345)
WIDTHS = (0, 1, 0x7FFF, 0x8000, 0xFFFF, 0xFFFF0001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)


def source_shapes(root):
    source = (root / SOURCE).read_text()
    old = source.replace(screen.INSERT, '').replace(screen.SELECTED, screen.ORIGINAL).replace(
        screen.DECLARATION, screen.OLD_DECLARATION)
    assert old.count(screen.ORIGINAL) == 1 and old.count(screen.OLD_DECLARATION) == 1
    new = old.replace('/* Generated placeholder declarations. */',
        screen.INSERT + '/* Generated placeholder declarations. */').replace(
        screen.ORIGINAL, screen.SELECTED).replace(screen.OLD_DECLARATION, screen.DECLARATION)
    return old, new


def fixture(selector=0, tables=0, seed=0, symbols=None):
    symbols = symbols or screen.SYMBOLS
    memory = {STACK + i: (i * 13 + seed * 31 + 0xA5) & 255 for i in range(-0x600, 0x160)}
    for base in (POSITION, VELOCITY, CREATED, PAYLOAD):
        memory.update({base + i: (i * 17 + seed * 11 + 0xA5) & 255 for i in range(-16, 0x200)})
    for name in ('D_800AB404', 'D_800AB330', 'D_800AB3F4'):
        memory.update({symbols[name] + i: 0 for i in range(16)})
    put(memory, symbols['D_800AB404'] + selector, 129 if tables & 1 else 0, 1)
    put(memory, symbols['D_800AB330'] + selector, 254 if tables & 2 else 0, 1)
    put(memory, symbols['D_800AB3F4'] + selector, (selector * 13 + 129) & 255, 1)
    put(memory, symbols['D_800AB498'], 0xC61C4000)
    put(memory, CREATED + 0x98, PAYLOAD)
    for i, value in enumerate(PATTERNS[:6]):
        put(memory, (POSITION if i < 3 else VELOCITY) + i % 3 * 4, value)
    return memory


def arguments(selector=0, opaque=0, fade=0, width=0xFFFF, pattern=0x80000000):
    return (POSITION, VELOCITY, pattern, width, 0xFE, pattern, 0x81234580, opaque,
        pattern, pattern, fade, selector, 0x81234567, width, width,
        0xFEDCBA98, 0x81, 0x89ABCDEF)


def defined(packet, ignored):
    return bytes(byte for i, byte in enumerate(packet) if i not in ignored)


def defined_events(model):
    result = []
    for event in public(model.events):
        if event[0] != 'W':
            result.append(event)
            continue
        _, address, size, value = event
        for i in range(size):
            if address + i not in (PAYLOAD + 0x46, PAYLOAD + 0x47):
                result.append(('W', address + i, 1, value >> ((size - i - 1) * 8) & 255))
    return result


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


def expected(memory, args, symbols=None):
    symbols = symbols or screen.SYMBOLS
    pos, vel, scale, duration, mode, time, request_selector, opaque, first, second, fade, selector, extra, v1, v2, value, channel, context = args
    selector &= 255
    position = bytes(memory[pos + i] for i in range(12))
    velocity = bytes(memory[vel + i] for i in range(12))
    flags = 0x48 | (0x20 if read(memory, symbols['D_800AB404'] + selector, 1) else 0) | (
        0x80 if read(memory, symbols['D_800AB330'] + selector, 1) else 0)
    request = position + struct.pack('>HHI', (duration + 16) & 65535, 53, 1) + bytes((255, request_selector & 255)) + struct.pack('>I', value)
    descriptor = struct.pack('>I', time) + velocity + struct.pack('>II', scale, read(memory, symbols['D_800AB498'])) + bytes((
        flags | (3 if opaque & 255 else 0), read(memory, symbols['D_800AB3F4'] + selector, 1), 255, mode & 255)) + struct.pack('>HH', v1 & 65535, v2 & 65535)
    render = struct.pack('>7I', 0, 0x220005, 0x50600, 3, 70, 128, 32) + bytes((0, 12))
    payload = struct.pack('>II', first, second) + bytes((selector,))
    call = ('create', request, descriptor, (16, 1, 0, 0, 7 if opaque & 255 else 0,
        4 if opaque & 255 else 0, 0, 2 if fade & 255 else 0, 255 if fade & 255 else 0),
        render, (extra, channel & 255, context))
    return call, payload


class ConstructorOracle(shaping.ShapingOracle):
    def __init__(self, words, memory, args, result=CREATED, phase=0, entry=screen.ENTRY,
            symbols=None, connected=None, mutation=False):
        TriangleOracle.__init__(self, words, memory, phase=phase, entry=entry,
            arguments=args, connected=connected)
        self.fcsr = self.initial_fcsr = 0
        self.result, self.mutation = result, mutation
        self.symbols = symbols or screen.SYMBOLS
        self.raw_calls = []

    def packet(self, address, size):
        return bytes(self.get(address + i, 1) for i in range(size))

    def record_call(self, target):
        if target == self.symbols['func_15147DA0']:
            args = self.arguments(15)
            self.raw_calls.append(('create', args))
            self.calls.append(('create', defined(self.packet(args[0], 28), (22, 23)),
                self.packet(args[1], 32), args[2:11], self.packet(args[11], 30), args[12:]))
        elif target == self.symbols['memcpy']:
            args = self.arguments(3)
            self.raw_calls.append(('copy', args))
            self.calls.append(('copy', args[0], defined(self.packet(args[1], args[2]),
                (9, 10, 11) if args[2] == 12 else (30, 31) if args[0] == PAYLOAD + 0x28 else ()), args[2]))
        else:
            assert target == 0x15147A80, hex(target)
            args = self.arguments(11)
            self.raw_calls.append(('allocate', args))
            self.calls.append(('allocate', defined(self.packet(args[0], 28), (22, 23)), args[1:]))

    def hook(self, target):
        role, args = self.raw_calls[-1]
        if role in ('create', 'allocate'):
            if self.mutation:
                for i in range(15 if role == 'create' else 11):
                    self.put(self.r[29] + i * 4, 0x76543210 + i, 4)
                for base in (POSITION, VELOCITY):
                    for i in range(12):
                        self.put(base + i, 0x5A, 1)
            result = self.result
        else:
            destination, source, size = args
            assert size in (12, 32)
            for i in range(size):
                self.put(destination + i, self.get(source + i, 1), 1)
            result = destination
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result


class GameTrailEffectConstructorRecoveryTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-trail-effect-constructor-test'
        cls.out.mkdir(exist_ok=True)
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>144I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
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
            prior = json.loads((cls.root / 'conker/build/game-random-effect-timer-test/after.json').read_text())
            with (cls.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
                guards = list(csv.DictReader(stream))
            with (cls.root / 'conker/progress.csv').open(newline='') as stream:
                progress = list(csv.DictReader(stream))
            assert slots == prior['slots'] and guards == prior['guards'] and progress == prior['progress']
            assert len(slots) == 6058 and len(guards) == 11475
            baseline.write_text(json.dumps(dict(slots=slots, guards=guards, progress=progress,
                source_sha256=hashlib.sha256(old.encode()).hexdigest(),
                elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()), indent=2) + '\n')
            (cls.out / 'before.elf').write_bytes(elf.read_bytes())
            for name in ('retail_word_patches.us.csv', 'progress.csv'):
                (cls.out / ('before-' + name)).write_bytes((cls.root / 'conker' / name).read_bytes())

    def receipt(self, name, value):
        (self.out / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')

    def compare(self, memory, args, result=CREATED, phase=0, mutation=False, words=None, entry=screen.ENTRY, symbols=None):
        call, payload = expected(memory, args, symbols)
        models = []
        bodies = (words,) if words is not None else (self.words, self.retail)
        for body in bodies:
            model = ConstructorOracle(body, memory, args, result, phase, entry, symbols, mutation=mutation).run()
            self.assertEqual(model.calls, [call] + ([('copy', PAYLOAD + 0x48, payload, 12)] if result else []))
            self.assertEqual(model.r[2], result)
            wanted = dict(memory)
            if mutation:
                for base in (POSITION, VELOCITY):
                    for i in range(12):
                        put(wanted, base + i, 0x5A, 1)
            if result:
                for i, byte in enumerate(payload):
                    put(wanted, PAYLOAD + 0x48 + i, byte, 1)
                for i in range(9, 12):
                    put(wanted, PAYLOAD + 0x48 + i, memory[STACK + phase - 0xD0 + 0x84 + i], 1)
            self.assertEqual(external(model.memory), external(wanted))
            models.append(model)
        if words is None:
            self.assertEqual(public(models[0].events), public(models[1].events))
        return models

    def test_01_complete_slot_and_minimal_consumed_types(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (144, 208, 61))
        self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes']), ('', 0))
        self.assertNotIn('unused[16]', screen.SELECTED_TYPES)
        self.receipt('slot', dict(words=144, bytes=576, frame=208, differences=61,
            byte_exact=False, guards=0, render_prefix_bytes=32))

    def test_02_complete_mixed_abi_records_flags_failure_and_return(self):
        count, seen = 0, set()
        for selector, tables, opaque, fade, result, phase in itertools.product(range(16), range(4),
                (0, 255), (0, 128), (0, CREATED), (0, 8)):
            models = self.compare(fixture(selector, tables, count % 3), arguments(selector, opaque, fade), result, phase)
            seen.update(models[0].visits)
            count += 1
        for width, pattern, mutation in itertools.product(WIDTHS, PATTERNS, (False, True)):
            self.compare(fixture(15, 3), arguments(15, 0x100, 0x101, width, pattern), mutation=mutation)
            count += 1
        for index, width in itertools.product((4, 6, 7, 10, 12, 13, 14, 15, 16, 17), WIDTHS):
            args = list(arguments(7, 1, 1))
            args[index] = width
            self.compare(fixture(7, 3), args)
            count += 1
        self.assertEqual(len(seen), 144)
        self.receipt('guest', dict(cases=count, executions=count * 2, all_144_words_reached=True,
            complete_18_argument_O32_ABI=True, saved_GP_FP_and_float_registers=True,
            record_sizes=[28, 32, 12, 32], undefined_padding_not_portable=True,
            all_16_valid_table_indices=True, exact_public_access_order=True,
            null_return_and_memcpy_return_ignored=True, raw_float_bits_including_NaNs=True,
            hardware_FCSR_flags=False))

    def test_03_complete_forms_and_effective_negative_controls(self):
        records = []
        bodies = list(screen.complete_candidates()) + [
            ('negative-duration', screen.SELECTED.replace('duration + 16', 'duration'), screen.SELECTED_TYPES),
            ('negative-selector', screen.SELECTED.replace('request.selector = requestSelector;', 'request.selector = 0;'), screen.SELECTED_TYPES),
            ('negative-fade', screen.SELECTED.replace('fadeAlpha = 255;', 'fadeAlpha = 0;'), screen.SELECTED_TYPES),
            ('negative-return', screen.SELECTED.replace('return created;', 'return NULL;'), screen.SELECTED_TYPES)]
        for name, body, types in bodies:
            meta, words = screen.compile_candidate(self.root, self.out, name, body, types)
            records.append(meta)
            cases = []
            for tables, opaque, fade, result in itertools.product(range(4), (0, 1), (0, 1), (0, CREATED)):
                ConstructorOracle(words, fixture(15, tables), arguments(15, opaque, fade), result).run()
                try:
                    self.compare(fixture(15, tables), arguments(15, opaque, fade), result, words=words)
                    cases.append(True)
                except AssertionError:
                    cases.append(False)
            self.assertEqual(all(cases), not name.startswith('negative-'), name)
        self.receipt('forms', dict(forms=records, cases_per_form=32, effective_compiled_negatives=4))

    def test_04_complete_retail_callee_and_memcpy_connection(self):
        retail = (self.root / 'conker/conker.us.bin').read_bytes()
        callee = struct.unpack_from('>70I', retail, 0x175250)
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        memcpy = functions['memcpy']
        self.assertEqual((addresses['memcpy'], len(memcpy)), (screen.SYMBOLS['memcpy'], 11))
        connected = dict(zip(range(0x15147DA0, 0x15147EB8, 4), callee))
        connected.update(zip(range(addresses['memcpy'], addresses['memcpy'] + 44, 4), memcpy))
        count, reached = 0, set()
        for selector, tables, opaque, fade, result, phase in itertools.product((0, 15), range(4), (0, 1),
                (0, 1), (0, CREATED), (0, 8)):
            memory, args = fixture(selector, tables), arguments(selector, opaque, fade)
            call, payload = expected(memory, args)
            models = []
            for body in (self.words, self.retail):
                model = ConstructorOracle(body, memory, args, result, phase, connected=connected).run()
                self.assertEqual(model.r[2], result)
                self.assertEqual(model.calls[0], call)
                self.assertEqual(model.calls[1], ('allocate', call[1],
                    (0x58, 0x14, 1, 0, 1, 2 if fade else 0, 255 if fade else 0, args[12], args[16], args[17])))
                if result:
                    self.assertEqual(model.calls[2:], [('copy', PAYLOAD, call[2], 32),
                        ('copy', PAYLOAD + 0x48, payload, 12)])
                    self.assertEqual(bytes(model.memory[PAYLOAD + i] for i in range(32)), call[2])
                    self.assertEqual(bytes(model.memory[PAYLOAD + 0x28 + i] for i in range(30)), call[4])
                    self.assertEqual(bytes(model.memory[PAYLOAD + 0x20 + i] for i in range(6)),
                        bytes((1, 0, 0, 7 if opaque else 0, 4 if opaque else 0, 0)))
                else:
                    self.assertEqual(len(model.calls), 2)
                reached.update(model.visits & set(connected))
                models.append(model)
            # Render padding is copied from different private stack slots in the two complete forms.
            masked = lambda m: {a: v for a, v in external(m.memory).items() if a not in (PAYLOAD + 0x46, PAYLOAD + 0x47)}
            self.assertEqual(masked(models[0]), masked(models[1]))
            self.assertEqual(defined_events(models[0]), defined_events(models[1]))
            count += 1
        self.assertEqual(len(reached), 81)
        self.receipt('callee', dict(cases=count, executions=count * 2, full_retail_callee_words=70,
            full_memcpy_words=11, all_81_connected_words=True, allocation_core_bounded=True,
            padding_locations_not_claimed_equal=True, hardware_gameplay=False))

    def test_05_copied_owner_neighbors_actual_padding_and_symbol_rebases(self):
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
        assembly = self.out / 'padded.s'
        subprocess.run([sys.executable, str(self.root / 'tools/pad_c_object.py'), str(objects[1]),
            str(self.root / 'conker/retail_layout.us.txt'), 'game_2062D0', str(assembly), '--word-patches',
            str(self.root / 'conker/retail_word_patches.us.csv')], check=True, capture_output=True)
        asm = assembly.read_text()
        begin = asm.index('.type %s, @function' % screen.FUNCTION)
        end = asm.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), begin)
        end = asm.index('\n', end) + 1
        self.assertNotIn('.space', asm[begin:end])
        solo, obj = self.out / 'solo.s', self.out / 'solo.o'
        solo.write_text('.text\n.set noreorder\n' + asm[begin:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(solo)], check=True, capture_output=True)
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 576)
        self.assertEqual(parse_object(obj)[2], self.meta['relocations'])
        count = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10007FFC, 0x80008000, 0x8FFF7FFC)):
            defs = dict(screen.SYMBOLS)
            if variant:
                for i, name in enumerate(defs):
                    defs[name] = ((entry & 0xF0000000) + 0x208000 + i * 0x100) if name.startswith('func_') or name == 'memcpy' else 0x81007FFC + i * 0x100
            script, elf = self.out / ('rebase-%d.ld' % variant), self.out / ('rebase-%d.elf' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in defs.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>144I', sections(elf)['.text'][1]))
            if not variant:
                self.assertEqual(words, self.words)
            for opaque, fade, result, phase in itertools.product((0, 255), (0, 128), (0, CREATED), (0, 8)):
                self.compare(fixture(15, 3, symbols=defs), arguments(15, opaque, fade), result, phase,
                    words=words, entry=entry, symbols=defs)
                count += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, pools_and_relative_relocations_unchanged=True,
            diagnostics=len(diagnostics[0]), direct_padded_bytes=576, guards=0, independent_links=4, cases=count))

    def test_06_linked_only_target_slot_and_symbol_size_change(self):
        baseline = json.loads((self.out / 'baseline.json').read_text())
        old, selected = source_shapes(self.root)
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), baseline['source_sha256'])
        installed = (self.root / SOURCE).read_text() == selected
        elf = self.root / 'conker/build/conker.us.elf'
        functions, _, addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
        slots = {n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(
            struct.pack('>%dI' % len(w), *w)).hexdigest()) for n, w in functions.items()}
        wanted = dict(baseline['slots'])
        data = bytearray((self.out / 'before.elf').read_bytes())
        if installed:
            wanted[screen.FUNCTION] = dict(address=screen.ENTRY, words=144,
                sha256=hashlib.sha256(struct.pack('>144I', *self.words)).hexdigest())
            offset = elf_slot_offset(data, screen.ENTRY, 576)
            data[offset:offset + 576] = struct.pack('>144I', *self.words)
            size_offset = symbol_size_offset(data)
            self.assertEqual(struct.unpack_from('>I', data, size_offset)[0], 12)
            struct.pack_into('>I', data, size_offset, 576)
            self.assertEqual(functions[screen.FUNCTION], self.words)
        self.assertEqual(slots, wanted)
        self.assertEqual(elf.read_bytes(), data)
        self.assertTrue(audit_layout(elf, self.root / 'conker')['exact'])
        for name in ('retail_word_patches.us.csv', 'progress.csv'):
            self.assertEqual((self.root / 'conker' / name).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        self.receipt('linked', dict(installed=installed, symbols=len(slots), target_words=144,
            full_ELF_except_target_and_its_symbol_size_unchanged=True, symbol_size_change=[12, 576] if installed else None,
            guards=11475, progress_unchanged=True, differences=61, byte_exact=False,
            elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()))
        if installed:
            self.receipt('after', dict(slots=slots, guards=baseline['guards'], progress=baseline['progress']))

    def test_07_native32_complete_types_widths_outputs_and_canaries(self):
        self.fixture = r'''typedef unsigned char u8; typedef signed char s8;
typedef unsigned short u16; typedef signed short s16; typedef int s32;
typedef unsigned int u32; typedef float f32;
#define NULL ((void *)0)
''' + screen.SELECTED_TYPES + r'''
static u8 D_800AB404[16],D_800AB330[16],D_800AB3F4[16];
static f32 D_800AB498=-10000.0f;
static union { u32 align; u8 bytes[512]; } storage, actor;
static u8 *output=storage.bytes+16,*created=actor.bytes+16;
static TrailPosition151DA6F8 position,velocity;
static u32 expectedDuration,expectedPattern;
static int selector,opaque,fade,failed,calls,copies,error;
static u32 bits(f32 f) { union { f32 f;u32 u; } v;v.f=f;return v.u; }
static f32 fromBits(u32 u) { union { f32 f;u32 u; } v;v.u=u;return v.f; }
static void *memcpy(void *destination,const void *source,unsigned int size) {
    unsigned int i;u8 *d=destination;const u8 *s=source;
    copies++;for(i=0;i<size;i++) d[i]=s[i];return destination;
}
static u8 *func_15147DA0(void *r,void *d,s32 extra,u8 active,u8 z0,u8 z1,
    u8 first,u8 second,u8 z2,u8 ff,u8 fa,void *p,s32 bytes,u8 channel,s32 context) {
    TrailRequest151DA6F8 *request=r;TrailDescriptor151DA6F8 *desc=d;TrailRender151DA6F8 *render=p;
    int flags=0x48|(D_800AB404[selector]?0x20:0)|(D_800AB330[selector]?0x80:0);
    if(calls++ || request->duration!=(s16)(expectedDuration+16) || request->kind!=53
      || request->active!=1 || request->mode!=-1 || request->selector!=128
      || (u32)request->value!=0xFEDCBA98 || bits(request->position.x)!=bits(position.x)
      || bits(request->position.y)!=bits(position.y) || bits(request->position.z)!=bits(position.z)
      || bits(desc->time)!=expectedPattern || bits(desc->scale)!=expectedPattern
      || bits(desc->velocity.x)!=bits(velocity.x) || bits(desc->velocity.y)!=bits(velocity.y)
      || bits(desc->velocity.z)!=bits(velocity.z) || bits(desc->limit)!=bits(D_800AB498)
      || desc->flags!=(flags|(opaque?3:0)) || desc->kind!=D_800AB3F4[selector]
      || desc->alpha!=255 || desc->mode!=254 || desc->first!=(s16)expectedDuration
      || desc->second!=(s16)expectedDuration || extra!=16 || active!=1 || z0 || z1 || z2
      || first!=(opaque?7:0) || second!=(opaque?4:0) || ff!=(fade?2:0) || fa!=(fade?255:0)
      || render->zero || render->command!=0x220005 || render->mode!=0x50600 || render->kind!=3
      || render->width!=70 || render->alpha!=128 || render->count!=32 || render->flags
      || render->payloadBytes!=12 || (u32)bytes!=0x81234567 || channel!=129
      || (u32)context!=0x89ABCDEF) error=1;
    if(failed) return NULL;
    memcpy(output,desc,32);memcpy(output+0x28,render,32);
    output[0x20]=active;output[0x21]=z0;output[0x22]=z1;
    output[0x23]=first;output[0x24]=second;output[0x25]=z2;
    return created;
}
static void initialize(void) {
    int i;for(i=0;i<512;i++) { storage.bytes[i]=(u8)(i*17+0xA5);actor.bytes[i]=(u8)(i*13+0x87); }
    *(u8 **)(created+0x98)=output;
    position.x=fromBits(0x80000000);position.y=1.0f;position.z=-2.0f;
    velocity.x=fromBits(1);velocity.y=3.0f;velocity.z=-4.0f;
    calls=copies=error=0;
}
''' + screen.SELECTED + '\n'
        self.run_host(r'''
u32 duration;int i,tables;u8 before[512],actorBefore[512];u8 *result;
static u32 patterns[]={0,0x80000000,1,0x80000001,0x3F800000,0x41400000,0x7F7FFFFF,0xFF7FFFFF};
if(sizeof(TrailRequest151DA6F8)!=28 || sizeof(TrailDescriptor151DA6F8)!=32
   || sizeof(TrailPayload151DA6F8)!=12 || sizeof(TrailRender151DA6F8)!=32) return 5;
for(duration=0;duration<65536;duration++) {
    expectedDuration=duration;selector=duration&15;opaque=(duration>>4)&1;
    fade=(duration>>5)&1;failed=(duration>>6)&1;tables=(duration>>7)&3;
    expectedPattern=patterns[(duration>>9)&7];
    D_800AB404[selector]=(tables&1)?129:0;D_800AB330[selector]=(tables&2)?254:0;
    D_800AB3F4[selector]=(u8)(selector*13+129);initialize();
    for(i=0;i<512;i++) { before[i]=storage.bytes[i];actorBefore[i]=actor.bytes[i]; }
    result=func_151DA6F8(&position,&velocity,fromBits(expectedPattern),(s16)duration,254,
        fromBits(expectedPattern),0x81234580,(u8)opaque,fromBits(expectedPattern),
        fromBits(expectedPattern),(u8)fade,(u8)selector,0x81234567,(s16)duration,
        (s16)duration,0xFEDCBA98,129,0x89ABCDEF);
    if(error || calls!=1 || copies!=(failed?0:3) || result!=(failed?NULL:created)) return 1;
    if(!failed && (*(u32 *)(output+0x48)!=expectedPattern || *(u32 *)(output+0x4C)!=expectedPattern
        || output[0x50]!=selector)) return 2;
    for(i=0;i<512;i++) {
        if(actor.bytes[i]!=actorBefore[i]) return 3;
        if((failed || i<16 || i>=16+0x54 || (i>=16+0x26 && i<16+0x28))
            && storage.bytes[i]!=before[i]) return 4;
    }
}
''')
        self.receipt('native', dict(cases=65536, actual_native32_C=True, all_signed_halfword_patterns=True,
            valid_indices_16=True, types_sizes=[28, 32, 12, 32], canary_regions=2,
            caller_and_memcpy_bounded=True, padding_values_unclaimed=True, hardware_FCSR_flags=False))

    def test_08_aliases_home_clobber_and_real_missing_public_bytes(self):
        count = 0
        for source, result, phase, mutation in itertools.product((POSITION, VELOCITY, CREATED, PAYLOAD),
                (0, CREATED), (0, 8), (False, True)):
            args = list(arguments(15, 1, 1))
            args[0] = args[1] = source
            self.compare(fixture(15, 3), args, result, phase, mutation)
            count += 1
        faults = 0
        for result, phase in itertools.product((0, CREATED), (0, 8)):
            memory, args = fixture(15, 3), arguments(15, 1, 1)
            complete = ConstructorOracle(self.retail, memory, args, result, phase).run()
            used = {e[1] + i for e in public(complete.events) if e[0] in ('R', 'W') for i in range(e[2])}
            for address in sorted(used):
                missing = dict(memory)
                del missing[address]
                models = [ConstructorOracle(body, missing, args, result, phase) for body in (self.words, self.retail)]
                self.assertEqual([outcome(model) for model in models], [False, False])
                self.assertEqual((external(models[0].memory), public(models[0].events), models[0].calls),
                    (external(models[1].memory), public(models[1].events), models[1].calls))
                faults += 1
        self.receipt('faults', dict(alias_cases=count, private_home_clobber_qualified=True,
            missing_public_byte_pairs=faults, emitted_fault_prefixes_only=True,
            portable_invalid_C=False, hardware_traps=False))


if __name__ == '__main__':
    unittest.main()
