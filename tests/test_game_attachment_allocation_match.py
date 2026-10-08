"""Two stack packets, eleven-argument allocation and captured attachment lifetime."""

import csv
import itertools
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_attachment_allocation_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_random_curve_record as native
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK

SOURCE = 'conker/src/game/generated_204660.c'
OWNER, RECORD, ALTERNATE, NESTED, ALT_NESTED = 0x20000, 0x21000, 0x22000, 0x24000, 0x25000
CALLER, CALLBACK, DISTANCE, ALLOCATOR, ZERO = 0x151D7264, 0x15200000, 0x15143E64, 0x15167A68, 0x100226F0
COORDINATES = (0, 0x80000000, 1, 0x80000001, 0x3F800000, 0xBF800000, 0x7F7FFFFF,
               0xFF7FFFFF, 0x7F800000, 0xFF800000, 0x7FC12345, 0xFFC12345)
INSERT = screen.DECLARATIONS.replace('void *memcpy(void *, const void *, unsigned int);\n', '') + '\nvoid func_151D7830(u8 *owner);\n\n'


def source_shapes(root):
    source = (root / SOURCE).read_text()
    baseline = source.replace(screen.SELECTED, screen.ORIGINAL).replace(INSERT, '')
    assert baseline.count(screen.ORIGINAL) == 1
    selected = baseline.replace('#include <ultra64.h>\n\n', '#include <ultra64.h>\n\n' + INSERT, 1).replace(screen.ORIGINAL, screen.SELECTED)
    return baseline, selected


def public(address):
    return not STACK - 0x300 <= address < STACK + 0x100


def public_memory(model):
    return {a: v for a, v in model.memory.items() if public(a)}


def public_events(model):
    return [e for e in model.events if e[0] == 'CALL' or public(e[1])]


def fixture(slot=0, context=0, pattern=0, layout=0):
    memory = {STACK + i: 0xA5 for i in range(-0x300, 0x100)}
    for base, length in ((OWNER, 0xC0), (RECORD, 0x400), (ALTERNATE, 0x400), (NESTED, 64), (ALT_NESTED, 64)):
        memory.update({base + i: (i * 17 + 0xA5) & 255 for i in range(-16, length)})
    destination = (NESTED, OWNER + 0x28, RECORD + 0x98)[layout]
    for record in (OWNER, RECORD, ALTERNATE):
        put(memory, record + 0x98, destination)
    for axis in range(3):
        put(memory, OWNER + 0x30 + axis * 4, COORDINATES[(pattern + axis) % len(COORDINATES)])
    put(memory, OWNER + 0xC, slot, 1)
    put(memory, OWNER + 1, context, 1)
    put(memory, OWNER + 0x28, 0)
    return memory


def actions(role, mode, record):
    if role == 'construct' and mode in (1, 4):
        return [(OWNER + 0x30 + i * 4, 0x11223344 + i, 4) for i in range(3)] + [(OWNER + 1, 255, 1), (OWNER + 0xC, 255, 1)]
    if role == 'construct' and mode == 2 and record:
        return [(OWNER + 0x28, ALTERNATE, 4), (record + 0x98, ALT_NESTED, 4)]
    if role == 'copy' and mode in (3, 4):
        return [(OWNER + 0x28, ALTERNATE, 4), (record + 0x98, ALT_NESTED, 4)]
    return []


class AllocationReference:
    def __init__(self, memory, record, mode=0):
        self.memory, self.events, self.calls = dict(memory), [], []
        self.record, self.mode = record, mode

    def get(self, address, size=4):
        assert address % size == 0, ('unaligned read', address, size)
        assert all(address + i in self.memory for i in range(size)), ('unmapped read', address, size)
        value = read(self.memory, address, size)
        self.events.append(('R', address, size, value))
        return value

    def put(self, address, value, size=4):
        assert address % size == 0, ('unaligned store', address, size)
        self.events.append(('W', address, size, value & ((1 << (size * 8)) - 1)))
        assert all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        put(self.memory, address, value, size)

    def call(self, role, args):
        self.calls.append((role, *args))
        self.events.append(('CALL', role, args))

    def run(self):
        payload = [OWNER, *[self.get(OWNER + 0x30 + i * 4) for i in range(3)], 0, 0, 0]
        request = (tuple(self.get(OWNER + 0x30 + i * 4) for i in range(3)), 300, 0x76, 0x12, 4, 25, 0)
        slot, context = self.get(OWNER + 0xC, 1), self.get(OWNER + 1, 1)
        self.call('construct', (request, (32, 28, 13, 16, 16, 0, 0, 0, slot, context)))
        for address, value, size in actions('construct', self.mode, self.record):
            self.put(address, value, size)
        if not self.record:
            return self
        destination = self.get(self.record + 0x98)
        self.call('copy', (destination, tuple(payload), 28))
        data = struct.pack('>7I', *payload)
        for i, byte in enumerate(data):
            self.put(destination + i, byte, 1)
        for address, value, size in actions('copy', self.mode, self.record):
            self.put(address, value, size)
        self.put(OWNER + 0x28, self.record)
        return self


class AllocationOracle(TriangleOracle):
    def __init__(self, words, memory, record, mode=0, phase=0, symbols=None, entry=screen.ENTRY, connected=None):
        super().__init__(words, memory, phase=phase, entry=entry, arguments=(OWNER,), connected=connected)
        self.record, self.mode = record, mode
        self.symbols = symbols or screen.SYMBOLS
        self.roles = {value: key for key, value in self.symbols.items()}
        self.roles.update({CALLBACK: 'callback', DISTANCE: 'distance', ALLOCATOR: 'allocator', ZERO: 'zero', screen.ENTRY: 'target'})
        self.raw_calls = []

    def execute(self, word):
        if word >> 26 == 32:
            CopyOracle.execute(self, word)
        else:
            super().execute(word)

    def get(self, address, size):
        assert address % size == 0, ('unaligned read', address, size)
        return super().get(address, size)

    def put(self, address, value, size):
        assert address % size == 0, ('unaligned store', address, size)
        super().put(address, value, size)

    def arguments(self, count):
        return tuple(self.r[4:4 + min(count, 4)]) + tuple(self.get(self.r[29] + 0x10 + 4 * i, 4) for i in range(max(0, count - 4)))

    def record_call(self, target):
        role = self.roles[target]
        count = {'func_15147A80': 11, 'memcpy': 3, 'allocator': 6, 'zero': 2}.get(role, 1)
        args = self.arguments(count)
        self.raw_calls.append((role, args))
        if role == 'func_15147A80':
            p = args[0]
            fields = (tuple(self.get(p + i * 4, 4) for i in range(3)), self.get(p + 12, 2),
                self.get(p + 14, 2), self.get(p + 16, 4), self.get(p + 20, 1), self.get(p + 21, 1), self.get(p + 24, 4))
            canonical = ('construct', fields, args[1:])
        elif role == 'memcpy':
            canonical = ('copy', args[0], tuple(self.get(args[1] + i * 4, 4) for i in range(args[2] // 4)), args[2])
        else:
            canonical = (role, *args)
        self.calls.append(canonical)
        self.events.append(('CALL', canonical[0], canonical[1:]))

    def hook(self, target):
        role, args = self.raw_calls[-1]
        if role == 'func_15147A80':
            result = self.record
            for address, value, size in actions('construct', self.mode, self.record):
                self.put(address, value, size)
            if self.mode == 5:
                for i in range(4):
                    self.put(self.r[29] + i * 4, ALTERNATE + i, 4)
        elif role == 'memcpy':
            destination, source, size = args
            assert size <= 36
            for i in range(size):
                self.put(destination + i, self.get(source + i, 1), 1)
            for address, value, width in actions('copy', self.mode, self.record):
                self.put(address, value, width)
            result = ALTERNATE
        elif role == 'allocator':
            result = self.record
        elif role == 'zero':
            for i in range(args[1]):
                self.put(args[0] + i, 0, 1)
            result = 0
        elif role == 'callback':
            result = 1
        else:
            assert role == 'distance'
            result = 0
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        if role == 'distance':
            self.f[0] = 0
        self.r[2] = result


def outcome(model):
    try:
        model.run()
        return True
    except AssertionError as error:
        assert error.args and isinstance(error.args[0], tuple) and error.args[0][0] in (
            'unaligned read', 'unaligned store', 'unmapped read', 'unmapped store'), error
        return False


class GameAttachmentAllocationTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-attachment-allocation-test'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>63I', cls.rom, screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, record=RECORD, mode=0, phase=0, words=None, entry=screen.ENTRY, symbols=None):
        reference = AllocationReference(memory, record, mode)
        completed = outcome(reference)
        models = []
        for body in (self.words if words is None else words, self.retail):
            model = AllocationOracle(body, memory, record, mode, phase, symbols, entry)
            self.assertEqual(outcome(model), completed)
            self.assertEqual((public_memory(model), public_events(model), model.calls),
                             (public_memory(reference), reference.events, reference.calls))
            models.append(model)
        if words is None:
            self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events),
                             (models[1].r, models[1].f, models[1].memory, models[1].events))
        return models[0], completed

    def test_01_complete_direct_slot_profiles_and_defined_layouts(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), (63, 0x88, 0))
        self.assertEqual((self.record['diagnostics'], self.record['pool_bytes']), ('', 0))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.record['relocations'], {0xC0: [('R_MIPS_26', 'func_15147A80')], 0xD8: [('R_MIPS_26', 'memcpy')]})
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, profile=p)[0] for p in ('o2g3', 'o2', 'o1g3', 'o1')]
        self.assertEqual([(m['body_words'], m['frame'], m['differences']) for m in profiles],
                         [(63, 0x88, 0), (63, 0x88, 43), (71, 0x78, 70), (71, 0x78, 70)])
        self.receipt('slot', dict(words=63, bytes=252, frame=0x88, direct_words=63, guards=0,
            relocations=2, profiles=profiles, request_padding_not_initialized_or_claimed=True))

    def test_02_packets_unsigned_bytes_aliases_calls_and_coverage(self):
        count, seen = 0, set()
        for slot, context, pattern, record, mode, layout, phase in itertools.product(
                (0, 1, 127, 128, 255), (0, 127, 128, 255), range(2), (0, RECORD, OWNER), range(5), range(3), (0, 8)):
            model, completed = self.compare(fixture(slot, context, pattern, layout), record, mode, phase)
            self.assertTrue(completed)
            seen.update(model.visits)
            count += 1
        for byte, field in itertools.product(range(256), (0, 1)):
            self.compare(fixture(byte if not field else 255, byte if field else 255, byte % len(COORDINATES)), phase=(byte & 1) * 8)
            count += 1
        for phase in (0, 8):
            self.compare(fixture(), mode=5, phase=phase)
            count += 1
        self.assertEqual(seen, set(range(screen.ENTRY, screen.ENTRY + 252, 4)))
        self.receipt('guest', dict(cases=count, all_256_both_unsigned_bytes=True, raw_XYZ_zero_NaN_inf_subnormal=True,
            allocation_failure_success_owner_alias=True, destination_aliases=3, public_mutation_modes=5,
            GP_FP_clobbers_and_home_writes=True, all_63_words_reached=True,
            complete_retail_GP_FP_private_memory_trace_equality=True, independent_public_reference=True))

    def test_03_lazy_failure_and_required_fault_prefixes(self):
        count = 0
        for phase in (0, 8):
            memory = fixture()
            for address in list(memory):
                if public(address) and address not in (*range(OWNER + 0x30, OWNER + 0x3C), OWNER + 1, OWNER + 0xC):
                    del memory[address]
            self.assertTrue(self.compare(memory, record=0, phase=phase)[1])
        for layout, phase, mode in itertools.product(range(3), (0, 8), (0, 2, 3)):
            memory = fixture(layout=layout)
            ref = AllocationReference(memory, RECORD, mode).run()
            for address, size in dict.fromkeys((e[1], e[2]) for e in ref.events if e[0] != 'CALL'):
                broken = dict(memory)
                del broken[address + size - 1]
                self.assertFalse(self.compare(broken, mode=mode, phase=phase)[1])
                count += 1
        for destination in (0,):
            memory = fixture()
            put(memory, RECORD + 0x98, destination)
            self.assertFalse(self.compare(memory)[1])
            count += 1
        memory = fixture()
        self.assertFalse(self.compare(memory, record=RECORD + 1)[1])
        count += 1
        memory = fixture()
        put(memory, RECORD + 0x98, NESTED + 1)
        self.assertTrue(self.compare(memory)[1])
        self.receipt('faults', dict(cases=count, lazy_failure_cases=2, complete_partial_GP_FP_state_and_public_prefix=True,
            mapping_alignment_not_portable_C_or_CP0_exception_metadata=True))

    def test_04_actual_native32_all_byte_pairs_and_canaries(self):
        self.fixture = NATIVE_PREFIX + screen.DECLARATIONS + screen.SELECTED + NATIVE_CHECK
        self.run_host('unsigned pair,failed,mode,layout; if(sizeof(void*)!=4 || sizeof(AttachmentRequest151D7830)!=28 || sizeof(AttachmentPayload151D7830)!=28)return 10;\n'
            'for(pair=0;pair<65536;pair++)for(failed=0;failed<2;failed++)if(check(pair,failed,0,0))return 11;\n'
            'for(pair=0;pair<256;pair++)for(mode=0;mode<5;mode++)for(layout=0;layout<3;layout++)for(failed=0;failed<2;failed++)if(check(pair*257,failed,mode,layout))return 12;')
        self.receipt('native', dict(executions=65536 * 2 + 256 * 5 * 3 * 2, all_unsigned_byte_pairs=True,
            allocation_failure_success=True, full_1024_byte_canaries=True, actual_C_volatile_typed_call=True,
            independent_defined_packet_offsets=True, request_padding_not_examined=True, mutation_modes=5, alias_layouts=3))

    def test_05_compiled_source_controls_and_effective_negatives(self):
        records, ordinary, negatives = [], 0, 0
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, 'control-' + name, body)
            records.append(meta)
            agreement = []
            for record, mode, layout, pattern in itertools.product((0, RECORD, OWNER), range(5), range(3), (0, 10)):
                memory = fixture(255, 128, pattern, layout)
                ref = AllocationReference(memory, record, mode)
                expected = outcome(ref)
                model = AllocationOracle(words, memory, record, mode)
                complete = outcome(model)
                agreement.append((complete, public_memory(model), public_events(model), model.calls) ==
                    (expected, public_memory(ref), ref.events, ref.calls))
            if name.startswith('negative-'):
                self.assertFalse(all(agreement), name)
                negatives += 1
            else:
                self.assertTrue(all(agreement), name)
                ordinary += len(agreement)
        self.receipt('controls', dict(forms=len(records), ordinary_executions=ordinary, effective_negatives=negatives, measurements=records))

    def test_06_copied_owners_real_padder_and_independent_rebased_links(self):
        objects, diagnostics = [], []
        for name, source in zip(('baseline', 'selected'), source_shapes(self.root)):
            obj, warnings = compile_owner(self.root, self.out, source, 'owner-' + name)
            diagnostics.append(warnings)
            processed = self.out / ('owner-' + name + '-processed.o')
            processed.write_bytes(obj.read_bytes())
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(processed.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(processed)
        self.assertEqual(diagnostics[0], diagnostics[1])
        old, previous, old_rel = parse_object(objects[0])
        text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), previous.keys())
        for name, fn in current.items():
            before = previous[name]
            if name != screen.FUNCTION:
                self.assertEqual(text[fn['value']:fn['value'] + fn['size']], old[before['value']:before['value'] + before['size']], name)
                self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                                 {o - before['value']: r for o, r in old_rel.items() if before['value'] <= o < before['value'] + before['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        target = current[screen.FUNCTION]
        isolated, _, isolated_rel = parse_object(self.out / 'selected.o')
        self.assertEqual(text[target['value']:target['value'] + 252], isolated[:252])
        self.assertEqual({o - target['value']: r for o, r in rel.items() if target['value'] <= o < target['value'] + 252}, isolated_rel)
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/204660.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_204660')
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[end:assembly.find('.type ', end)])
        asm, obj = self.out / 'padded.s', self.out / 'padded.o'
        asm.write_text('.text\n.set noreorder\n.globl %s\n' % screen.FUNCTION + assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        _, functions, relocations = parse_object(obj)
        self.assertEqual((functions[screen.FUNCTION]['size'], relocations), (252, isolated_rel))
        executions = 0
        for index, entry in enumerate((screen.ENTRY, 0x10007FFC, 0x7FFF8000, 0x80000000, 0x8FFF7FFC, 0x1FFF8000)):
            symbols = {name: (entry & 0xF0000000) + 0x00108000 + i * 0x10004 for i, name in enumerate(screen.SYMBOLS)}
            script, elf = self.out / 'padded.ld', self.out / ('rebased-%d.elf' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>63I', sections(elf)['.text'][1]))
            expected = list(self.retail)
            for offset, name in ((0xC0, 'func_15147A80'), (0xD8, 'memcpy')):
                self.assertEqual((entry + offset + 4) & 0xF0000000, symbols[name] & 0xF0000000)
                expected[offset // 4] = 0x0C000000 | ((symbols[name] >> 2) & 0x3FFFFFF)
            self.assertEqual(words, expected)
            for record, mode, phase in itertools.product((0, RECORD, OWNER), range(5), (0, 8)):
                memory = fixture(255, 128, 10)
                ref = AllocationReference(memory, record, mode).run()
                model = AllocationOracle(words, memory, record, mode, phase, symbols, entry).run()
                self.assertEqual((public_memory(model), public_events(model), model.calls), (public_memory(ref), ref.events, ref.calls))
                executions += 1
        self.receipt('owner-padder', dict(neighbors=len(current) - 1, unchanged_warning_count=len(diagnostics[0]),
            relative_relocations_and_pools_unchanged=True, padded_bytes=252, guards=0, independent_links=6,
            independently_expected_R_MIPS_26_sites=2, rebased_executions=executions))

    def test_07_full_original_constructor_and_full_caller_allocation_arm(self):
        constructor = list(struct.unpack_from('>115I', self.rom, 0x174F30))
        caller = list(struct.unpack_from('>81I', self.rom, 0x204714))
        count, seen = 0, set()
        for actual, with_caller, record, phase, byte in itertools.product((False, True), (False, True), (0, RECORD), (0, 8), (0, 127, 128, 255)):
            memory = fixture(byte, 255 - byte, 4)
            put(memory, OWNER + 0x2C, 0, 1)
            put(memory, OWNER + 0x2D, 1, 1)
            put(memory, OWNER + 0x3C, 0x3F800000)
            put(memory, 0x8008FCA0, CALLBACK)
            models = []
            for body in (self.words, self.retail):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 252, 4), body))
                if actual:
                    connected.update(zip(range(screen.SYMBOLS['func_15147A80'], screen.SYMBOLS['func_15147A80'] + 460, 4), constructor))
                model = AllocationOracle(caller if with_caller else body, memory, record, phase=phase,
                    entry=CALLER if with_caller else screen.ENTRY, connected=connected).run()
                seen.update(model.visits)
                self.assertEqual(read(model.memory, OWNER + 0x28), record)
                if actual:
                    self.assertEqual([args for role, args in model.raw_calls if role == 'allocator'], [(0x4D, 255 - byte, 892, 1, byte, 1)])
                    self.assertFalse(any(e[0] == 'R' and e[1] == 0x80082FA0 for e in model.events))
                    if record:
                        self.assertEqual(read(model.memory, record + 0x98), record + 0xA0)
                        self.assertEqual(read(model.memory, record + 0x94), record + 0xC0)
                        self.assertEqual(tuple(read(model.memory, record + 0xA0 + 4 * i) for i in range(7)),
                            (OWNER, *[read(memory, OWNER + 0x30 + i * 4) for i in range(3)], 0, 0, 0))
                        self.assertEqual((read(model.memory, record + 0x1C, 2), read(model.memory, record + 0x1E, 2)), (300, 0x76))
                        self.assertEqual(tuple(read(model.memory, record + 0x10 + i * 4) for i in range(3)),
                                         tuple(read(memory, OWNER + 0x30 + i * 4) for i in range(3)))
                        self.assertEqual((read(model.memory, record + 0x20), read(model.memory, record + 0x24, 1),
                            read(model.memory, record + 0x25, 1), read(model.memory, record + 0x28)), (0x12, 4, 25, 0))
                        self.assertEqual(tuple(read(model.memory, record + i, 1) for i in range(0x2C, 0x32)), (0, 0, 0, 13, 16, 16))
                        self.assertEqual(bytes(model.memory[record + 0x84 + i] for i in range(16)), bytes(16))
                models.append(model)
            self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events, models[0].calls),
                             (models[1].r, models[1].f, models[1].memory, models[1].events, models[1].calls))
            count += 1
        self.assertIn(CALLER + 0x140, seen)
        self.receipt('connected', dict(cases=count, original_constructor_words=115, original_caller_words=81,
            full_functions_including_return_epilogues=True, caller_allocation_arm_only=True,
            constructor_null_arg8_and_arg6_arms_only=True, allocator_copy_zero_and_float_distance_bounded_hooks=True,
            linked_constructor_still_zero_return_placeholder=True, hardware_gameplay_not_qualified=True))

    def test_08_current_linked_slot_and_unchanged_guard_history(self):
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        self.assertEqual((addresses[screen.FUNCTION], functions[screen.FUNCTION]), (screen.ENTRY, self.retail))
        self.assertEqual(functions['func_151D7264'], list(struct.unpack_from('>81I', self.rom, 0x204714)))
        baseline, selected = source_shapes(self.root)
        source = (self.root / SOURCE).read_text()
        self.assertIn(source, (baseline, selected))
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            guards = list(csv.DictReader(stream))
        assert_guard_history(self, guards)
        self.assertEqual(len(guards), 11155)
        self.receipt('installed', dict(complete_linked_target_and_caller_exact=True, guards_added=0,
            complete_11155_row_history_checked=True, constructor_not_restored_by_this_conversion=True))


NATIVE_PREFIX = r'''
typedef signed char s8;typedef unsigned char u8;typedef unsigned short u16;typedef int s32;typedef unsigned int u32;typedef float f32;
#define NULL ((void *)0)
static u8 arena[1024] __attribute__((aligned(16))),expected[1024] __attribute__((aligned(16)));
static u8 *owner,*record,*destination;static u32 xyz[3];static unsigned mode,failed,slot,context;static int error,calls;
static u32 word(unsigned offset){return *(u32 *)(expected+offset);}
static void change(unsigned role){
 unsigned i;
 if(role==0&&(mode==1||mode==4)){
  for(i=0;i<3;i++){*(u32 *)(owner+0x30+i*4)=0x11223344+i;*(u32 *)(expected+0x70+i*4)=0x11223344+i;}
  owner[1]=255;owner[0xC]=255;expected[0x41]=255;expected[0x4C]=255;
 }
 if((role==0&&mode==2&&!failed)||(role==1&&(mode==3||mode==4))){
  *(u8 **)(owner+0x28)=arena+0x280;*(u8 **)(expected+0x68)=arena+0x280;
  *(u8 **)(record+0x98)=arena+0x3C0;*(u8 **)(expected+(unsigned)(record-arena)+0x98)=arena+0x3C0;
 }
}
'''

NATIVE_CHECK = r'''
u8 *func_15147A80(void *p,s32 size,s32 stride,s32 type,s32 a,s32 b,s32 c,s32 d,void *optional,u8 player,s32 category){
 unsigned i;u8 *bytes=p;
 if(calls++||size!=32||stride!=28||type!=13||a!=16||b!=16||c||d||optional||player!=slot||category!=(s32)context)error=1;
 for(i=0;i<3;i++)if(*(u32 *)(bytes+i*4)!=xyz[i])error=2;
 if(*(u16 *)(bytes+12)!=300||*(u16 *)(bytes+14)!=0x76||*(u32 *)(bytes+16)!=0x12||bytes[20]!=4||bytes[21]!=25||*(u32 *)(bytes+24))error=3;
 change(0);return failed?NULL:record;
}
void *memcpy(void *dst,const void *src,unsigned int size){
 unsigned i;const u8 *bytes=src;
 if(calls++!=1||dst!=*(u8 **)(record+0x98)||size!=28||*(u8 *const *)src!=owner)error=4;
 for(i=0;i<3;i++)if(*(const u32 *)(bytes+4+i*4)!=xyz[i]||*(const u32 *)(bytes+16+i*4))error=5;
 destination=dst;
 for(i=0;i<size;i++){((u8 *)dst)[i]=bytes[i];expected[(unsigned)(destination-arena)+i]=bytes[i];}
 change(1);return arena+0x280;
}
static int check(unsigned pair,unsigned fail,unsigned mutation,unsigned layout){
 unsigned i,recordOffset;u32 raw[7];void (*volatile invoke)(u8 *)=func_151D7830;
 static const u32 values[]={0,0x80000000,1,0x80000001,0x3F800000,0xBF800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0xFFC12345};
 for(i=0;i<1024;i++)arena[i]=(u8)(i*17+0xA5);
 owner=arena+0x40;record=layout==1?owner:arena+0x180;destination=layout==2?owner+0x28:arena+0x380;
 failed=fail;mode=mutation;slot=pair&255;context=pair>>8;error=0;calls=0;
 *(u8 **)(record+0x98)=destination;*(u8 **)(owner+0x28)=NULL;owner[1]=(u8)context;owner[0xC]=(u8)slot;
 for(i=0;i<3;i++){xyz[i]=values[(pair+i)%12];*(u32 *)(owner+0x30+i*4)=xyz[i];}
 for(i=0;i<1024;i++)expected[i]=arena[i];
 invoke(owner);
 if(error||calls!=(failed?1:2))return 1;
 if(!failed){
  recordOffset=(unsigned)(record-arena);*(u8 **)(expected+0x68)=record;
  raw[0]=(u32)owner;for(i=0;i<3;i++){raw[1+i]=xyz[i];raw[4+i]=0;}
  /* Validate the hook's copied bytes independently of its expected-byte writes. */
  for(i=0;i<28;i++)if(arena[(unsigned)(destination-arena)+i]!=((u8 *)raw)[i]&&
     !((mode==3||mode==4)&&((unsigned)(destination-arena)+i>=recordOffset+0x98&&(unsigned)(destination-arena)+i<recordOffset+0x9C))&&
     !((unsigned)(destination-arena)+i>=0x68&&(unsigned)(destination-arena)+i<0x6C))return 2;
 }
 for(i=0;i<1024;i++)if(arena[i]!=expected[i])return 3;
 return 0;
}
'''
