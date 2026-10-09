"""Direct factory match, defined payload bytes, caller ABI and linked restoration audit."""

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
from tools.experiments import game_record_constructor_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_callback_update_match import public, external, outcome
from tools.tests import test_game_record_ring_shaping_recovery as shaping
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game/generated_204660.c'
MARKER = '/* Non-matching placeholders for the text-only asm slice asm/204660.s. */'
INSERT = screen.DECLARATIONS.split('void *memcpy', 1)[0] + '\n'
CREATED, ACTOR, ALTERNATE = 0x20000, 0x21000, 0x22000
PATTERNS = (0, 0x80000000, 1, 0x80000001, 0x3F800000, 0x41400000,
    0x7F7FFFFF, 0xFF7FFFFF, 0x7F800000, 0xFF800000, 0x7FC12345, 0x7F812345)
DURATIONS = (0, 1, 0x7FFF, 0x8000, 0xFFFF, 0xFFFF0001, 0x7FFFFFFF, 0x80000000)


def source_shapes(root):
    source = (root / SOURCE).read_text()
    old = source.replace(screen.SELECTED, screen.ORIGINAL).replace(INSERT, '').replace(
        screen.CALLER_SELECTED, screen.CALLER_ORIGINAL)
    assert old.count(screen.ORIGINAL) == 1 and old.count(screen.CALLER_ORIGINAL) == 1
    return old, old.replace(MARKER, INSERT + MARKER).replace(screen.ORIGINAL, screen.SELECTED).replace(
        screen.CALLER_ORIGINAL, screen.CALLER_SELECTED)


def fixture(seed=0):
    memory = {STACK + i: (i * 17 + seed * 31 + 0xA5) & 255 for i in range(-0x600, 0x140)}
    for base in (CREATED, ACTOR, ALTERNATE):
        memory.update({base + i: (i * 13 + seed * 11 + 0xA5) & 255 for i in range(-16, 0x200)})
    put(memory, ACTOR + 0x3B, 0x87, 1)
    return memory


def payload(memory, args, phase):
    _, _, selector, threshold, _, _, _ = args
    packet = bytearray(24)
    packet[4] = selector & 255
    packet[6:8] = bytes(memory[STACK + phase - 0x16 + i] for i in range(2))
    struct.pack_into('>I', packet, 20, threshold)
    return bytes(packet)


def creator_args(args):
    duration, active, _, _, extra, slot, context = args
    duration &= 65535
    if duration & 32768:
        duration -= 65536
    return (duration & 0xFFFFFFFF, 0xFFFFFFFF, 0x42, 0xFFFFFFFF,
        active & 255, 0x36, (extra + 24) & 0xFFFFFFFF, slot & 255, context & 0xFFFFFFFF)


class ConstructorReference:
    def __init__(self, memory, args, result=CREATED, mode=0, phase=0):
        self.memory, self.events, self.calls = dict(memory), [], []
        self.args, self.result, self.mode, self.phase = args, result, mode, phase

    def put(self, address, value, size=1):
        self.events.append(('W', address, size, value & ((1 << (size * 8)) - 1)))
        assert all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        put(self.memory, address, value, size)

    def run(self):
        packet = payload(self.memory, self.args, self.phase)
        args = creator_args(self.args)
        self.calls.append(('create', args))
        self.events.append(('CALL', 'create', args))
        if self.result and self.mode == 2:
            self.put(self.result + 4, 0x12345678, 4)
        if self.result:
            self.calls.append(('copy', self.result + 0x28, packet, 24))
            self.events.append(('CALL', 'copy', (self.result + 0x28, packet, 24)))
            for i, byte in enumerate(packet):
                self.put(self.result + 0x28 + i, byte)
        return self


class ConstructorOracle(shaping.ShapingOracle):
    def __init__(self, words, memory, args, result=CREATED, mode=0, phase=0, entry=screen.ENTRY, symbols=None, connected=None):
        TriangleOracle.__init__(self, words, memory, phase=phase, entry=entry, arguments=args, connected=connected)
        self.fcsr = self.initial_fcsr = 0
        self.result, self.mode = result, mode
        self.symbols = symbols or screen.SYMBOLS
        self.raw_calls = []

    def record_call(self, target):
        if target == self.symbols['func_15149130']:
            args = self.arguments(9)
            self.raw_calls.append(('create', args))
            self.calls.append(('create', args))
            self.events.append(('CALL', 'create', args))
        else:
            assert target == self.symbols['memcpy'], hex(target)
            destination, source, size = self.arguments(3)
            packet = bytes(self.get(source + i, 1) for i in range(size))
            self.raw_calls.append(('copy', (destination, source, size)))
            self.calls.append(('copy', destination, packet, size))
            self.events.append(('CALL', 'copy', (destination, packet, size)))

    def hook(self, target):
        role, args = self.raw_calls[-1]
        if role == 'create':
            if self.mode == 1:
                for i in range(9):
                    self.put(self.r[29] + i * 4, 0x76543210 + i, 4)
            if self.result and self.mode == 2:
                self.put(self.result + 4, 0x12345678, 4)
            result = self.result
        else:
            destination, source, size = args
            assert 0 <= size <= 24
            for i in range(size):
                self.put(destination + i, self.get(source + i, 1), 1)
            result = destination
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result & 0xFFFFFFFF


class ConnectedConstructorOracle(ConstructorOracle):
    def record_call(self, target):
        if target == screen.ENTRY:
            self.calls.append(('factory', self.arguments(7)))
        elif target == 0x15167A68:
            self.raw_calls.append(('allocate', self.arguments(6)))
            self.calls.append(self.raw_calls[-1])
        elif target == 0x100226F0:
            self.raw_calls.append(('zero', self.arguments(2)))
            self.calls.append(self.raw_calls[-1])
        else:
            super().record_call(target)

    def hook(self, target):
        if target not in (0x15167A68, 0x100226F0):
            return super().hook(target)
        role, args = self.raw_calls[-1]
        if role == 'zero':
            address, length = args
            assert length == 16
            for i in range(length):
                self.put(address + i, 0, 1)
        elif self.mode == 1:
            for i in range(6):
                self.put(self.r[29] + i * 4, 0x76543210 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = self.result if role == 'allocate' else 0x87654321


def elf_slot_offset(data, address, size):
    header = ELF_HEADER.unpack_from(data)
    headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
    matches = [h[4] + address - h[3] for h in headers if h[1] == 1 and h[3] <= address and address + size <= h[3] + h[5]]
    assert len(matches) == 1
    return matches[0]


def elf_symbol_size_offset(data, name):
    header = ELF_HEADER.unpack_from(data)
    headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
    matches = []
    for section in headers:
        if section[1] != 2:
            continue
        strings = headers[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for offset in range(section[4], section[4] + section[5], section[9]):
            symbol = SYMBOL.unpack_from(data, offset)
            if names[symbol[0]:].split(b'\0', 1)[0].decode() == name:
                assert symbol[1] == screen.ENTRY and symbol[3] & 15 == 2
                matches.append(offset + 8)
    assert len(matches) == 1
    return matches[0]


class GameRecordConstructorMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-constructor-test'
        cls.out.mkdir(exist_ok=True)
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>45I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        baseline_path = cls.out / 'baseline.json'
        if not baseline_path.exists():
            old, _ = source_shapes(cls.root)
            assert (cls.root / SOURCE).read_text() == old
            elf = cls.root / 'conker/build/conker.us.elf'
            functions, _, addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
            slots = {n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(
                struct.pack('>%dI' % len(w), *w)).hexdigest()) for n, w in functions.items()}
            previous = json.loads((cls.root / 'conker/build/game-record-actor-position-test/after.json').read_text())
            assert slots == previous['slots'] and len(slots) == 6058
            with (cls.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
                guards = list(csv.DictReader(stream))
            assert guards == previous['guards'] and len(guards) == 11475
            with (cls.root / 'conker/progress.csv').open(newline='') as stream:
                progress = list(csv.DictReader(stream))
            assert progress == previous['progress']
            baseline_path.write_text(json.dumps(dict(slots=slots, guards=guards, progress=progress,
                source_sha256=hashlib.sha256(old.encode()).hexdigest(),
                elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()), indent=2) + '\n')
            (cls.out / 'before.elf').write_bytes(elf.read_bytes())
            (cls.out / 'before-manifest.csv').write_bytes((cls.root / 'conker/retail_word_patches.us.csv').read_bytes())
            (cls.out / 'before-progress.csv').write_bytes((cls.root / 'conker/progress.csv').read_bytes())

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, args, result=CREATED, mode=0, phase=0, memory=None):
        memory = fixture(mode) if memory is None else memory
        ref = ConstructorReference(memory, args, result, mode, phase)
        complete = outcome(ref)
        models = [ConstructorOracle(body, memory, args, result, mode, phase) for body in (self.words, self.retail)]
        for model in models:
            self.assertEqual(outcome(model), complete)
            self.assertEqual((external(model.memory), public(model.events), model.calls),
                (external(ref.memory), ref.events, ref.calls))
            if complete:
                self.assertEqual(model.r[2], result)
        self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events),
            (models[1].r, models[1].f, models[1].memory, models[1].events))
        return models[0], complete

    def test_01_direct_slot_all_profiles_and_no_guards(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (45, 80, 0))
        self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes'], self.words), ('', 0, self.retail))
        self.assertEqual(self.meta['relocations'], {0x78: [('R_MIPS_26', 'func_15149130')], 0x94: [('R_MIPS_26', 'memcpy')]})
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, profile=p)[0] for p in screen.PROFILES]
        self.receipt('slot', dict(words=45, bytes=180, frame=80, direct_words=45, guards=0, profiles=profiles))

    def test_02_complete_payload_abi_padding_mutations_and_return_lifetime(self):
        count, seen = 0, set()
        for duration, selector, pattern, result, mode, phase in itertools.product(
                DURATIONS, (0, 128, 255), PATTERNS, (0, CREATED), (0, 1, 2), (0, 8)):
            args = (duration, 0x12345680, selector | 0xA5000000, pattern,
                (0, 8, 0x7FFFFFFF, 0xFFFFFFE8, 0xFFFFFFFF)[pattern % 5], 0x123456FF, 0x80000001)
            model, complete = self.compare(args, result, mode, phase)
            self.assertTrue(complete)
            seen.update(model.visits)
            count += 1
        for index in range(256):
            for field in (1, 2, 5):
                args = [300, 1, 2, 0x41400000, 8, 3, 1]
                args[field] = 0x76543200 | index
                self.compare(tuple(args))
                count += 1
        self.assertTrue(set(range(screen.ENTRY, screen.ENTRY + 180, 4)) <= seen)
        self.receipt('guest', dict(cases=count, executions=count * 2, all_45_words_reached=True,
            all_active_selector_slot_bytes=True, private_padding_untouched=True, memcpy_return_ignored=True,
            integer_addition_wrap=True, full_s32_context=True, all_saved_registers=True))

    def test_03_real_missing_bytes_and_failure_lazy_copy(self):
        count = 0
        args = (0x8000, 255, 128, 0x7F812345, 0xFFFFFFE8, 255, 0x80000000)
        for phase, result, mode in itertools.product((0, 8), (0, CREATED), (0, 1, 2)):
            memory = fixture(mode)
            reference = ConstructorReference(memory, args, result, mode, phase).run()
            for address in sorted({e[1] + i for e in reference.events if e[0] == 'W' for i in range(e[2])}):
                missing = dict(memory)
                del missing[address]
                self.compare(args, result, mode, phase, missing)
                count += 1
            if not result:
                trimmed = {a: v for a, v in memory.items() if STACK - 0x600 <= a < STACK + 0x140}
                self.compare(args, result, mode, phase, trimmed)
        self.receipt('faults', dict(real_missing_byte_pairs=count, no_copy_on_failure=True,
            hardware_traps=False, portable_invalid_pointer_semantics=False))

    def test_04_complete_forms_and_effective_compiled_negatives(self):
        records, negatives, exploratory, rejected = [], [], [], []
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, 'form-' + name, body)
            records.append(meta)
            same, witness = [], None
            for duration, result, selector, threshold in itertools.product((0x8000, 0xFFFF0001), (0, CREATED),
                    (128, 255), (0x41400000, 0x80000000)):
                args = (duration, 0x12345680, selector, threshold, 8, 255, 0x80000001)
                memory = fixture()
                expected = ConstructorReference(memory, args, result).run()
                model = ConstructorOracle(words, memory, args, result)
                complete = outcome(model)
                # Alternate local layouts may copy different unspecified padding bytes.
                def defined(memory):
                    return {a: v for a, v in external(memory).items() if a not in (CREATED + 0x2E, CREATED + 0x2F)}
                args_equal = model.calls[0] == expected.calls[0]
                same.append(complete and defined(model.memory) == defined(expected.memory) and model.r[2] == result and args_equal)
                if not same[-1] and witness is None:
                    witness = dict(arguments=args, result=result, actual_create=model.calls[0],
                        expected_create=expected.calls[0], physical_arguments_equal=args_equal)
            if name.startswith('negative-'):
                self.assertFalse(all(same), name)
                negatives.append(name)
            elif name.startswith('types-') and not all(same):
                self.assertFalse(witness['physical_arguments_equal'], name)
                rejected.append(dict(name=name, witness=witness))
            else:
                self.assertTrue(all(same), name)
                if meta['differences']:
                    exploratory.append(name)
        self.receipt('forms', dict(forms=len(records), samples=16, effective_compiled_negatives=negatives,
            exploratory_nonmatching_forms=exploratory, rejected_physical_argument_width_forms=rejected,
            padding_not_portably_fixed=True, measurements=records))

    def test_05_actual_copied_owner_typed_caller_and_padder(self):
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
            previous = before[name]
            self.assertEqual(text[fn['value']:fn['value'] + fn['size']], old[previous['value']:previous['value'] + previous['size']], name)
            self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                {o - previous['value']: r for o, r in old_rel.items() if previous['value'] <= o < previous['value'] + previous['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        fn = current[screen.FUNCTION]
        self.assertEqual(fn['size'], 180)
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/204660.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_204660')
        begin = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), begin)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[begin:end])
        asm, obj = self.out / 'padded.s', self.out / 'padded.o'
        asm.write_text('.text\n.set noreorder\n' + assembly[begin:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 180)
        self.assertEqual(parse_object(obj)[2], self.meta['relocations'])
        cases = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            defs = dict(screen.SYMBOLS)
            if variant:
                for i, name in enumerate(defs):
                    defs[name] = (entry & 0xF0000000) + 0x100800 + i * 0x100
            script = self.out / ('rebase-%d.ld' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            elf = self.out / ('rebase-%d.elf' % variant)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in defs.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>45I', sections(elf)['.text'][1]))
            for duration, result, mode, phase in itertools.product((0x8000, 0xFFFF0001), (0, CREATED), (0, 1), (0, 8)):
                args = (duration, 0x76543280, 0xA50000FF, 0x7F812345, 8, 255, 0x80000001)
                memory = fixture(mode)
                ref = ConstructorReference(memory, args, result, mode, phase).run()
                model = ConstructorOracle(words, memory, args, result, mode, phase, entry, defs).run()
                self.assertEqual((external(model.memory), public(model.events), model.calls, model.r[2]),
                    (external(ref.memory), ref.events, ref.calls, result))
                cases += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, typed_caller_bytes_unchanged=True,
            pools_and_relative_relocations_unchanged=True, diagnostics=len(diagnostics[0]),
            direct_padded_bytes=180, guards=0, independent_links=4, cases=cases))

    def test_06_full_linked_restoration_only_target_changes(self):
        baseline = json.loads((self.out / 'baseline.json').read_text())
        old, selected = source_shapes(self.root)
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), baseline['source_sha256'])
        installed = (self.root / SOURCE).read_text() == selected
        elf = self.root / 'conker/build/conker.us.elf'
        functions, _, addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
        slots = {n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(
            struct.pack('>%dI' % len(w), *w)).hexdigest()) for n, w in functions.items()}
        expected_slots = dict(baseline['slots'])
        expected_elf = bytearray((self.out / 'before.elf').read_bytes())
        if installed:
            expected_slots[screen.FUNCTION] = dict(address=screen.ENTRY, words=45,
                sha256=hashlib.sha256(struct.pack('>45I', *self.retail)).hexdigest())
            offset = elf_slot_offset(expected_elf, screen.ENTRY, 180)
            expected_elf[offset:offset + 180] = struct.pack('>45I', *self.retail)
            symbol_offset = elf_symbol_size_offset(expected_elf, screen.FUNCTION)
            self.assertEqual(struct.unpack_from('>I', expected_elf, symbol_offset)[0], 12)
            struct.pack_into('>I', expected_elf, symbol_offset, 180)
            self.assertEqual(functions[screen.FUNCTION], self.retail)
        self.assertEqual(slots, expected_slots)
        self.assertEqual(elf.read_bytes(), expected_elf)
        self.assertTrue(audit_layout(elf, self.root / 'conker')['exact'])
        self.assertEqual((self.root / 'conker/retail_word_patches.us.csv').read_bytes(),
            (self.out / 'before-manifest.csv').read_bytes())
        with (self.root / 'conker/progress.csv').open(newline='') as stream:
            progress = list(csv.DictReader(stream))
        self.assertEqual(progress, baseline['progress'])
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            guards = list(csv.DictReader(stream))
        self.assertEqual(guards, baseline['guards'])
        self.receipt('linked', dict(installed=installed, symbols=len(slots),
            changed_functions=[screen.FUNCTION] if installed else [], changed_bytes_confined_to_target=installed,
            full_ELF_except_target_and_its_symbol_size_unchanged=True,
            symbol_size_change=[12, 180] if installed else None,
            elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(),
            guards=len(guards), progress_rows_unchanged=True, target_words=45, differences=0 if installed else None))
        if installed:
            self.receipt('after', dict(slots=slots, guards=guards, progress=progress))

    def test_07_native32_complete_function_and_typed_caller(self):
        self.fixture = r'''typedef unsigned char u8; typedef signed char s8;
typedef signed short s16; typedef int s32; typedef unsigned int u32; typedef float f32;
#define NULL ((void *)0)
static union { u32 align; u8 bytes[512]; } storage, actorStorage;
static u8 *created=storage.bytes+16;
static int fail, error, copies, allocations;
static s16 expectedDuration; static u8 expectedActive, expectedSlot;
static s32 expectedSize, expectedContext;
static u32 expectedThreshold;
static void *func_15149130(s16 duration,s8 a,s8 b,s8 c,u8 active,u8 mode,
    s32 size,u8 slot,s32 context) {
    allocations++;
    if(duration!=expectedDuration || a!=-1 || b!=0x42 || c!=-1 || active!=expectedActive
       || mode!=0x36 || size!=expectedSize || slot!=expectedSlot || context!=expectedContext) error=1;
    return fail?NULL:created;
}
static void *memcpy(void *dst,const void *src,unsigned int size) {
    unsigned int i; u8 *d=dst; const u8 *s=src;
    for(i=0;i<size;i++) d[i]=s[i];
    copies++; return dst;
}
static void initialize(void) {
    int i; for(i=0;i<512;i++) storage.bytes[i]=actorStorage.bytes[i]=0xA5;
    allocations=copies=error=0;
}
static int checkPayload(void) {
    int i;
    for(i=0;i<24;i++) {
        if(i==6 || i==7) continue;
        if(i==4) { if(created[0x28+i]!=2) return 1; }
        else if(i>=20) { if(created[0x28+i]!=((u8 *)&expectedThreshold)[i-20]) return 2; }
        else if(created[0x28+i]) return 3;
    }
    return 0;
}
''' + screen.RECORD + screen.SELECTED + '\n' + screen.CALLER_SELECTED + '\n'
        self.run_host(r'''
u32 duration, pattern; int byte,i; u8 *answer;
static u32 patterns[]={0,0x80000000,1,0x80000001,0x3F800000,0x41400000,
    0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7F812345};
union { u32 bits; f32 value; } threshold;
if(sizeof(CallbackRecord151D7264)!=24 || sizeof(void *)!=4) return 1;
for(duration=0;duration<65536;duration++) {
    initialize(); fail=duration&1; expectedDuration=(s16)duration;
    expectedActive=1; expectedSlot=255; expectedSize=32; expectedContext=(s32)0x80000001;
    expectedThreshold=threshold.bits=patterns[duration%12];
    answer=func_151D71B0((s16)duration,1,2,threshold.value,8,255,expectedContext);
    if(error || allocations!=1 || copies!=!fail || answer!=(fail?NULL:created)) return 2;
    if(!fail && checkPayload()) return 3;
    for(i=0;i<512;i++) if((fail || i<16+0x28 || i>=16+0x40) && storage.bytes[i]!=0xA5) return 4;
}
for(byte=0;byte<256;byte++) for(pattern=0;pattern<12;pattern++) {
    initialize(); fail=0; expectedDuration=300; expectedActive=(u8)byte;
    expectedSlot=(u8)byte; expectedSize=32; expectedContext=(s32)0x80000001;
    expectedThreshold=threshold.bits=patterns[pattern];
    answer=func_151D71B0(300,(u8)byte,(u8)byte,threshold.value,8,(u8)byte,expectedContext);
    if(error || answer!=created || copies!=1 || created[0x2C]!=(u8)byte || created[0x2D]) return 5;
    for(i=0;i<4;i++) if(created[0x3C+i]!=((u8 *)&expectedThreshold)[i]) return 6;
    for(i=0;i<512;i++) if((i<16+0x28 || i>=16+0x40) && storage.bytes[i]!=0xA5) return 7;
}
for(byte=0;byte<256;byte++) for(fail=0;fail<2;fail++) {
    initialize(); expectedDuration=300; expectedActive=0; expectedSlot=(u8)byte;
    expectedSize=32; expectedContext=(s32)0x80000001; expectedThreshold=0x41400000;
    func_151D74B0(actorStorage.bytes,(u8)byte,(s8)byte,(u8)byte,expectedContext);
    if(error || allocations!=1 || copies!=(fail?0:2)) return 8;
    if(!fail && (*(u8 **)(created+0x40)!=actorStorage.bytes || created[0x44]!=0xA5
        || created[0x45]!=(u8)byte || created[0x46]!=(u8)byte)) return 9;
    for(i=0;i<512;i++) if((fail || i<16+0x28 || i>=16+0x48) && storage.bytes[i]!=0xA5) return 10;
}
''')
        self.receipt('native', dict(cases=65536 + 256 * 12 + 512, actual_native32_C=True,
            all_duration_values=True, all_active_selector_slot_bytes=True, typed_caller=True,
            full_512_byte_canaries=True, padding_not_portably_fixed=True))

    def test_08_real_allocator_wrapper_memcpy_and_typed_caller(self):
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        names = ('func_15149130', 'memcpy', 'func_151D74B0')
        self.assertEqual([len(functions[n]) for n in names], [49, 11, 34])
        connected = {addresses[n] + i * 4: w for n in names for i, w in enumerate(functions[n])}
        count, seen = 0, set()
        for duration, active, result, mode, phase, caller in itertools.product(
                (0x8000, 0xFFFF0001), (0, 2, 255), (0, CREATED), (0, 1), (0, 8), (False, True)):
            memory = fixture()
            args = (duration, active, 255, 0x7F812345, 8, 255, 0x80000001)
            actual = (300, 0, 0, 0x41400000, 8, 255, 0x80000001) if caller else args
            expected = dict(memory)
            if result:
                duration_word, _, _, _, active_word, _, size, slot, context = creator_args(actual)
                for offset, value, size_bytes in ((0xE, duration_word, 2), (0x10, 255, 1),
                        (0x11, 0x42, 1), (0x12, 255, 1), (0xD, active_word, 1), (0x13, 0x36, 1)):
                    put(expected, result + offset, value, size_bytes)
                for i in range(16):
                    put(expected, result + 0x14 + i, 0, 1)
                # The caller frame is 0x38 bytes; its nested factory keeps the same private packet shape.
                packet = payload(memory, actual, phase - (0x38 if caller else 0))
                expected.update({result + 0x28 + i: b for i, b in enumerate(packet)})
                if caller:
                    extension = struct.pack('>I3B', ACTOR, memory[ACTOR + 0x3B], 255, 128)
                    expected.update({result + 0x40 + i: b for i, b in enumerate(extension)})
            models = []
            for body in (self.words, self.retail):
                code = dict(connected)
                code.update(zip(range(screen.ENTRY, screen.ENTRY + 180, 4), body))
                entry = addresses['func_151D74B0'] if caller else screen.ENTRY
                arguments = (ACTOR, 255, 128, 255, 0x80000001) if caller else args
                model = ConnectedConstructorOracle(functions['func_151D74B0'] if caller else body,
                    memory, arguments, result, mode, phase, entry, connected=code).run()
                # The caller extension has one unspecified trailing byte.
                observed = external(model.memory)
                wanted = external(expected)
                if caller and result:
                    observed.pop(result + 0x47)
                    wanted.pop(result + 0x47)
                self.assertEqual(observed, wanted)
                expected_args = creator_args(actual)
                self.assertIn(('create', expected_args), model.calls)
                self.assertIn(('allocate', (0x5F if actual[1] & 2 else 0x23, actual[6],
                    (actual[4] + 24 + 40) & 0xFFFFFFFF, 1, actual[5], 1)), model.calls)
                self.assertEqual(sum(c[0] == 'zero' for c in model.calls), bool(result))
                self.assertEqual(sum(c[0] == 'copy' for c in model.calls), (2 if caller else 1) if result else 0)
                if not caller:
                    self.assertEqual(model.r[2], result)
                seen.update(model.visits)
                models.append(model)
            self.assertEqual((models[0].memory, models[0].events, models[0].r, models[0].f),
                (models[1].memory, models[1].events, models[1].r, models[1].f))
            count += 1
        for name in names:
            self.assertTrue(set(range(addresses[name], addresses[name] + len(functions[name]) * 4, 4)) <= seen, name)
        self.receipt('connected', dict(cases=count, executions=count * 2, actual_creator_words=49,
            actual_memcpy_words=11, actual_typed_caller_words=34, all_connected_words_reached=True,
            generic_allocator_and_bzero_bounded=True, hardware_gameplay=False))
