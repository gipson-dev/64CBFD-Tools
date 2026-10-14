"""Eleven-slot factory ABI, signed coordinates, untouched header byte and copy gate."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_descriptor_spawn_candidates as source
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.tests import test_game_record_constructor_match as shared
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_record_callback_update_match import external, public
from tools.tests.test_game_matrix_reflection_roles import state
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import SYMBOL, parse_object, emit_padded_assembly
from tools import pad_c_object
from tools.check_game_data_layout import audit_layout
from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols

STACK, ACTOR, CREATED, BODY = shared.STACK, 0x21000, 0x23000, 0x24000
TABLE, PARENT, PARENT_ROM = 0x80086110, 0x1506AC8C, 0x9813C
FACTORY, WRAPPER, SPAWN, ALLOCATE, FREE = 0x151602C0, 0x1516037C, 0x1515D5F8, 0x15167A68, 0x1515F10C
VALUES = tuple(map(bits, (0.0, -0.0, 1.75, -0.75, 50.5, -49.5,
    -50.5, 123.75, -123.75, 16777216.0, 2147483520.0, -2147483648.0)))
COEFFICIENTS = (0x3DD119CE, 0, 0x80000000, 1, 0x807FFFFF, 0x3F800000,
    0xC0200000, 0x7F800000, 0xFF800000, 0x7FC12345, 0x7F812345, 0xA55A00FF)


def apply_spawn_symbol_serialization(expected):
    names = ('D_80099A28', '__osProbeTLB')
    definitions = ((0x80099A28, 0, 16, 0, 65521), (0x100273D0, 184, 18, 0, 3))
    rows = {name: (offset, fields, string) for offset, name, fields, string in symbol_rows(expected) if name in names}
    assert set(rows) == set(names)
    first = rows[names[0]]
    cursor = first[2]
    for index, (name, definition) in enumerate(zip(names, definitions)):
        offset, fields, string = rows[name]
        assert offset == first[0] + index * SYMBOL.size and fields[1:] == definition
        assert string == cursor and expected[string:string + len(name) + 1] == name.encode() + b'\0'
        cursor += len(name) + 1
    string_base, cursor = first[2] - first[1][0], first[2]
    for index, name in enumerate(reversed(names)):
        fields = list(rows[name][1])
        fields[0] = cursor - string_base
        SYMBOL.pack_into(expected, first[0] + index * SYMBOL.size, *fields)
        expected[cursor:cursor + len(name) + 1] = name.encode() + b'\0'
        cursor += len(name) + 1


def controls():
    return {
        'wrong-height': source.SELECTED.replace('50.0f', '49.0f'),
        'premature-truncation': source.SELECTED.replace('(s32)(*(f32 *)(actor + 0x18) + 50.0f)', '(s32)*(f32 *)(actor + 0x18) + 50'),
        'wrong-duration': source.SELECTED.replace('header.unk2 = 300', 'header.unk2 = 301'),
        'wrong-payload': source.SELECTED.replace('80.0f', '81.0f'),
        'short-copy': source.SELECTED.replace('payload, sizeof(payload));', 'payload, 12);'),
        'late-global-read': source.SELECTED.replace('    payload[3] = D_80099A28;\n', '').replace(
            '    if (created != NULL) {', '    if (created != NULL) {\n        payload[3] = D_80099A28;'),
    }


def truncation(word):
    value = floating(word)
    return math.trunc(value) & 0xFFFFFFFF if math.isfinite(value) and -(2 ** 31) <= value < 2 ** 31 else 0x80000000


def fixture(values=None, coefficient=0x3DD119CE, actor=ACTOR, result=CREATED, symbols=None, seed=0):
    s = symbols or source.SYMBOLS
    memory = {STACK + i: (i * 17 + seed * 31 + 0xA5) & 255 for i in range(-0x600, 0x140)}
    for base, size in ((ACTOR - 32, 160), (actor - 32, 160), (CREATED - 32, 160),
            (BODY - 32, 160), (s['D_80099A28'] - 32, 160), (TABLE, 64), (0x800CC254, 12),
            (0x800D1560, 32), (0x800D1570, 32)):
        for i in range(size):
            memory.setdefault((base + i) & 0xFFFFFFFF, (i * 13 + seed * 11 + 0xA5) & 255)
    for i, value in enumerate(values or (bits(1.75), bits(-0.75), bits(-3.75))):
        put(memory, actor + 0x14 + i * 4, value)
    put(memory, s['D_80099A28'], coefficient)
    put(memory, TABLE + 6 * 4, source.ENTRY)
    return memory


def mutation(memory, actor, symbols, mode, header):
    if mode == 1:
        put(memory, actor + 0x14, 0x12345678)
        put(memory, symbols['D_80099A28'], 0x76543210)
    elif mode == 2:
        put(memory, header + 5, 0x5A, 1)


def reference(memory, actor=ACTOR, result=CREATED, mode=0, phase=0, symbols=None, outcome=None, with_return=False):
    s, m = symbols or source.SYMBOLS, dict(memory)
    frame, events = STACK + phase - 0x60, []
    header, position, payload = frame + 0x54, frame + 0x38, frame + 0x44
    put(m, frame + 0x34, 0xDEAD0000)
    put(m, STACK + phase, actor)
    put(m, STACK + phase + 4, 0x8765ABCD)
    def get(address):
        value = read(m, address)
        events.append(('R', address, 4, value))
        return value
    x = truncation(get(actor + 0x14))
    put(m, position, x)
    y = truncation(bits(floating(get(actor + 0x18)) + 50.0))
    coefficient = get(s['D_80099A28'])
    put(m, position + 4, y)
    z = truncation(get(actor + 0x1C))
    put(m, payload, 0)
    put(m, payload + 8, 0)
    put(m, header, 2, 1)
    put(m, header + 1, 15, 1)
    put(m, header + 2, 300, 2)
    put(m, position + 8, z)
    put(m, header + 4, 5, 1)
    put(m, payload + 4, bits(80.0))
    put(m, payload + 12, coefficient)
    args = (header, position, 0, 255, 255, 90, 255, 0, 16, 255, 1)
    calls = [('factory', args, bytes(m[header + i] for i in range(5)), (x, y, z))]
    events.append(('CALL', 'factory', args))
    mutation(m, actor, s, mode, header)
    if mode == 1:
        events.extend((('W', actor + 0x14, 4, 0x12345678), ('W', s['D_80099A28'], 4, 0x76543210)))
    if outcome is not None:
        calls.append(('body', (x, y, z, 0, 255, 255, 90, 255, 0, 0)))
        if outcome:
            calls.extend((('object', (header, BODY, 16, 255, 1)), ('allocate', (53, 1, 40, 1, 255, 1))))
            if outcome == 1:
                calls.append(('free', (BODY,)))
    if result:
        descriptor = bytes(m[header + i] for i in range(6))
        if outcome is not None:
            calls.append(('copy', result + 0xE, descriptor, 6))
        for i in range(6):
            put(m, result + 0xE + i, m[header + i], 1)
        put(m, result + 0x14, BODY)
        put(m, result + 0xE, m[result + 0xE] | 2, 1)
        block = bytes(m[payload + i] for i in range(16))
        calls.append(('copy', result + 0x18, block, 16))
        for i in range(16):
            put(m, result + 0x18 + i, m[payload + i], 1)
    result_state = (external(m), calls)
    return (*result_state, read(m, frame + 0x34)) if with_return else result_state


class AccessFault(Exception):
    pass


class SpawnOracle(shared.ConstructorOracle):
    def __init__(self, words, memory, actor=ACTOR, result=CREATED, mode=0, phase=0,
            entry=source.ENTRY, symbols=None, connected=None, outcome=None, fault=None):
        self.own_instruction, self.accesses, self.fault = False, 0, fault
        super().__init__(words, memory, (actor, 0x8765ABCD), result, mode, phase, entry,
            symbols or source.SYMBOLS, connected)
        self.actor, self.outcome, self.callbacks = actor, outcome, []
        self.factory_header = self.factory_position = None

    def execute(self, word):
        self.dispatched_word = word
        self.own_instruction = True
        try:
            super().execute(word)
        finally:
            self.own_instruction = False

    def access(self):
        if self.own_instruction:
            if self.accesses == self.fault:
                raise AccessFault
            self.accesses += 1

    def get(self, address, size):
        self.access()
        return super().get(address, size)

    def put(self, address, value, size):
        if self.recording:
            self.access()
        super().put(address, value, size)

    def record_call(self, target):
        if target == source.ENTRY:
            self.callbacks.append(self.arguments(2))
            return
        if target == self.symbols['func_151602C0']:
            args = self.arguments(11)
            self.factory_header, self.factory_position = args[:2]
            header = bytes(self.get(args[0] + i, 1) for i in range(5))
            coordinates = tuple(self.get(args[1] + i * 4, 4) for i in range(3))
            self.calls.append(('factory', args, header, coordinates))
            self.raw_calls.append(('factory', args))
            self.events.append(('CALL', 'factory', args))
        elif target == self.symbols['memcpy']:
            destination, pointer, size = self.arguments(3)
            data = bytes(self.get(pointer + i, 1) for i in range(size))
            self.calls.append(('copy', destination, data, size))
            self.raw_calls.append(('copy', (destination, pointer, size)))
        else:
            role, count = {SPAWN: ('body', 10), WRAPPER: ('object', 5),
                ALLOCATE: ('allocate', 6), FREE: ('free', 1)}[target]
            args = self.arguments(count)
            self.calls.append((role, args))
            self.raw_calls.append((role, args))

    def hook(self, target):
        if target in (self.symbols['func_151602C0'], SPAWN):
            mutation(self.memory, self.actor, self.symbols, self.mode, self.factory_header)
        if target == self.symbols['func_151602C0']:
            if self.result:
                for i in range(6):
                    self.put(self.result + 0xE + i, self.get(self.factory_header + i, 1), 1)
                self.put(self.result + 0x14, BODY, 4)
                self.put(self.result + 0xE, self.get(self.result + 0xE, 1) | 2, 1)
            value, homes = self.result, 11
        elif target == self.symbols['memcpy']:
            destination, pointer, size = self.raw_calls[-1][1]
            for i in range(size):
                self.put(destination + i, self.get(pointer + i, 1), 1)
            value, homes = destination, 3
        elif target == SPAWN:
            value, homes = BODY if self.outcome else 0, 10
        elif target == ALLOCATE:
            value, homes = self.result if self.outcome == 2 else 0, 6
        else:
            assert target == FREE
            value, homes = 0xA5000002, 1
        for i in range(homes):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = value & 0xFFFFFFFF


class GameActorDescriptorSpawnMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-descriptor-spawn-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=source.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            makefile='conker/Makefile', layout='conker/retail_layout.us.txt',
            assembly='conker/asm/97AA0.s', table='conker/asm/data/22ABD0.rodata.s', structs='conker/include/structs.h')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == '5eabc37b7142d9d137ad5ffd5ba1be01f8dadd4f97bc4a0ae07a86a5c1fcf23b'
        assert cls.baseline['elf'] == '15efd3983e27e174640763a68c61373320bc891173593bf619eea5a6d60fe14b'
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_after = source.recovered_owner(cls.owner_before)
        cls.meta, cls.words = source.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>65I', cls.rom, source.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, actor=ACTOR, result=CREATED, mode=0, phase=0,
            symbols=None, entry=source.ENTRY, bodies=None):
        storage, calls, saved_return = reference(memory, actor, result, mode, phase, symbols, with_return=True)
        expected = storage, calls
        models = []
        for words in (bodies or (self.retail, self.words)):
            model = SpawnOracle(words, memory, actor, result, mode, phase, entry, symbols)
            if saved_return == 0xDEAD0000:
                model.run()
            else:
                with self.assertRaises(AssertionError) as stopped:
                    model.run()
                self.assertEqual(stopped.exception.args, (('unowned jump', saved_return),))
                self.assertEqual(model.r[31], saved_return)
            models.append(model)
        for model in models:
            self.assertEqual((external(model.memory), model.calls), expected)
            self.assertEqual(model.r[2], result + 0x18 if result else 0)
        self.assertEqual(state(models[0]), state(models[1]))
        return models

    def test_01_complete_direct_slot_two_screens_and_real_local_order(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (65, 96, 0, 0, ''))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.meta['relocations'], {0x60: [('R_MIPS_HI16', 'D_80099A28')],
            0x64: [('R_MIPS_LO16', 'D_80099A28')], 0xD8: [('R_MIPS_26', 'func_151602C0')],
            0xEC: [('R_MIPS_26', 'memcpy')]})
        out = self.root / 'conker/build/game-actor-descriptor-spawn'
        measured = json.loads((out / 'measurements.json').read_text())
        old = json.loads((out / 'header-before-zero-measurements.json').read_text())
        self.assertEqual((len(measured), len(old)), (96, 96))
        self.assertEqual([m['name'] for m in measured if m['differences'] == 0], ['created-header-payload-position-o2g3'])
        self.assertFalse(any(m['differences'] == 0 for m in old))
        _, prior = source.compile_candidate(self.root, self.out, 'wrong-store-order', source.BASE)
        self.assertEqual(sum(a != b for a, b in zip(prior, self.retail)), 6)
        self.receipt('shape', words=65, frame=96, direct_C=True, guards=0, screens=192,
            actual_SDK_Header6_Header2_12=True, zero_stores_before_header=True,
            header_offset=84, position_offset=56, payload_offset=68, old_store_schedule_differences=6)

    def test_02_finite_coordinates_raw_coefficients_failures_and_provider_mutation(self):
        cases, seen = 0, set()
        for indices in itertools.product(range(len(VALUES)), repeat=3):
            values = tuple(VALUES[i] for i in indices)
            coefficient = COEFFICIENTS[(indices[0] + 3 * indices[1] + 5 * indices[2]) % len(COEFFICIENTS)]
            for result, mode, phase in itertools.product((0, CREATED), range(3), (0, 8)):
                for model in self.compare(fixture(values, coefficient, seed=sum(indices)), result=result, mode=mode, phase=phase):
                    seen.update(model.visits)
                cases += 1
        self.assertEqual(seen, set(range(source.ENTRY, source.ENTRY + 260, 4)))
        self.receipt('guest', cases=cases, all_12_cubed_coordinate_patterns=True,
            all_raw_coefficient_bits_and_signed_integer_edges=True, two_results_three_modes_two_phases=True,
            full_states_and_independent_external_reference=True, all65_words_reached=True,
            native_integer_conversion_domain_finite_in_range_only=True)

    def test_03_public_private_and_coefficient_aliases(self):
        cases = 0
        for phase, mode in itertools.product((0, 8), range(3)):
            frame = STACK + phase - 0x60
            for actor in (ACTOR, frame + 0x24, frame + 0x30, frame + 0x40,
                    STACK + phase - 0x14, STACK + phase - 0x10):
                for result in (0, CREATED, actor, source.SYMBOLS['D_80099A28'] - 0x18):
                    memory = fixture(actor=actor, result=result)
                    self.compare(memory, actor, result, mode, phase)
                    cases += 1
        for phase, offset in itertools.product((0, 8), (0x38, 0x44, 0x50, 0x54, 0x60, 0x64)):
            symbols = dict(source.SYMBOLS, D_80099A28=STACK + phase - 0x60 + offset)
            with patch.object(source, 'SYMBOLS', symbols):
                _, emitted = source.compile_candidate(self.root, self.out, 'alias-source-%d-%d' % (phase, offset))
            original = self.rebased_original(source.ENTRY, symbols, 'alias-original-%d-%d' % (phase, offset))
            self.assertEqual(emitted, original)
            for result, mode in itertools.product((0, CREATED), range(3)):
                self.compare(fixture(symbols=symbols), result=result, mode=mode, phase=phase,
                    symbols=symbols, bodies=(original, emitted))
                cases += 1
        self.receipt('aliases', cases=cases, actor_destination_global_and_private_home_aliases=True,
            same_shape_rebased_originals=True, overwritten_return_addresses_checked_as_terminal_prefixes=True,
            physical_private_aliases_not_portable_C_promises=True)

    def test_04_required_inputs_failure_gate_and_bounded_invalid_conversions(self):
        faults, invalid = 0, 0
        for phase, base, size in itertools.product((0, 8), (ACTOR + 0x14, source.SYMBOLS['D_80099A28']), (4,)):
            length = 12 if base == ACTOR + 0x14 else 4
            for offset in range(length):
                memory = fixture()
                del memory[base + offset]
                models = [SpawnOracle(w, memory, result=0, phase=phase) for w in (self.retail, self.words)]
                for model in models:
                    with self.assertRaises(AssertionError):
                        model.run()
                    self.assertEqual(model.calls, [])
                self.assertEqual(state(models[0]), state(models[1]))
                faults += 1
        for phase, word, axis in itertools.product((0, 8), (0x7F800000, 0xFF800000, 0x7FC12345, 0x7F812345, 0x4F000000, 0xCF000001), range(3)):
            values = [bits(1.75), bits(-0.75), bits(-3.75)]
            values[axis] = word
            self.compare(fixture(values), result=0, phase=phase)
            invalid += 1
        self.receipt('inputs', missing_input_byte_prefixes=faults, invalid_machine_subset_cases=invalid,
            inputs_read_even_on_failure=True, no_null_or_conversion_clamp_added=True,
            invalid_conversion_checks_not_portable_C_or_hardware_FCSR_acceptance=True)

    def test_05_six_effective_native_and_guest_semantic_controls(self):
        memory = fixture()
        expected = reference(memory, mode=1)
        for name, body in controls().items():
            _, wrong = source.compile_candidate(self.root, self.out, 'negative-' + name, body)
            model = SpawnOracle(wrong, memory, mode=1).run()
            self.assertNotEqual((external(model.memory), model.calls), expected, name)
        self.receipt('controls', effective_compiled_controls=list(controls()))

    def test_06_complete_owner_SDK_include_neighbors_and_both_padders(self):
        objects = [compile_owner(self.root, self.out, text, 'owner-' + name)
            for name, text in (('before', self.owner_before), ('after', self.owner_after))]
        self.assertEqual(objects[0][1], objects[1][1])
        for name in ('before', 'after'):
            obj = self.out / ('owner-' + name + '.o')
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
        before, after = [parse_object(p[0]) for p in objects]
        self.assertEqual(set(before[1]), set(after[1]))
        neighbors = set(before[1]) - {source.FUNCTION}
        for name in neighbors:
            a, b = before[1][name], after[1][name]
            self.assertEqual(before[0][a['value']:a['value'] + a['size']], after[0][b['value']:b['value'] + b['size']], name)
            relative = lambda obj, f: {at - f['value']: uses for at, uses in obj[2].items() if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(before, a), relative(after, b), name)
        self.assertEqual(normalized_pools(objects[0][0]), normalized_pools(objects[1][0]))
        padded = []
        for kind in ('layout', 'slice'):
            path = self.out / ('owner-padded-' + kind + '.s')
            kwargs = dict(word_patches_path=self.root / self.paths['guards'])
            text = pad_c_object.emit_padded_assembly(objects[1][0], self.root / self.paths['layout'], 'generated_97AA0', **kwargs) if kind == 'layout' else emit_padded_assembly(
                objects[1][0], self.root / self.paths['assembly'], filename='generated_97AA0', **kwargs)
            path.write_text(text)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
                '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
            padded.append(parse_object(path.with_suffix('.o')))
        self.assertEqual(padded[0], padded[1])
        target = padded[0][1][source.FUNCTION]
        self.assertEqual(target['size'], 260)
        raw, isolated, _ = parse_object(self.out / 'selected.o')
        start = isolated[source.FUNCTION]['value']
        self.assertEqual(padded[0][0][target['value']:target['value'] + 260], raw[start:start + 260])
        self.receipt('owner', neighbors=len(neighbors), both_complete_padders=True,
            adding_existing_SDK_types_changes_no_other_body_pool_or_relocation=True, direct_target_preserved=True)

    def test_07_literal_image_source_and_protected_history(self):
        current_source = (self.root / self.paths['source']).read_text()
        self.assertIn(current_source, (self.owner_before, self.owner_after))
        expected = bytearray(self.before)
        if current_source == self.owner_after:
            offset = shared.elf_slot_offset(self.before, source.ENTRY, 260)
            expected[offset:offset + 260] = struct.pack('>65I', *self.retail)
            with patch.object(shared.screen, 'ENTRY', source.ENTRY):
                size = shared.elf_symbol_size_offset(self.before, source.FUNCTION)
            self.assertEqual(struct.unpack_from('>I', expected, size)[0], 12)
            struct.pack_into('>I', expected, size, 260)
            apply_spawn_symbol_serialization(expected)
        current = (self.root / self.paths['elf']).read_bytes()
        self.assertEqual(current, bytes(expected))
        self.assertEqual(canonical_symbols(current), canonical_symbols(bytes(expected)))
        for name in set(self.paths) - {'source', 'elf'}:
            before = (self.out / ('before-' + name)).read_bytes()
            self.assertEqual(hashlib.sha256(before).hexdigest(), self.baseline[name])
            self.assertEqual((self.root / self.paths[name]).read_bytes(), before, name)
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('linked-audit', installed=current_source == self.owner_after,
            changed_bytes=sum(a != b for a, b in zip(self.before, current)),
            only_target260_bytes_exact_named_size12_to260_and_asserted_symbol_pair_serialization=True,
            all_named_symbol_definitions_equal_except_target_size=True, protected_data=data)

    def test_08_actual_native32_bounded_truncation_padding_and_canaries(self):
        values = ','.join('0x%Xu' % v for v in VALUES)
        coefficients = ','.join('0x%Xu' % v for v in COEFFICIENTS)
        coordinates = ','.join('0x%Xu' % truncation(v) for v in VALUES)
        heights = ','.join('0x%Xu' % truncation(bits(floating(v) + 50.0)) for v in VALUES)
        fixture_c = '''typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;
typedef struct {s8 unk0,unk1;s16 unk2;s8 unk4;u8 pad5;} Header;
typedef struct {s32 unk0,unk4,unk8;} Header2;typedef struct {u8 data[40];} struct225;
#define NULL ((void*)0)
static union {u32 align;u8 bytes[96];} actor,coefficient,output;
#define D_80099A28 (*(f32*)(coefficient.bytes+32))
static u8 *input,*result;static int mode,calls,copies,error;static u32 want[3];
static const u32 values[]={''' + values + '''},coefficients[]={''' + coefficients + '''},coordinates[]={''' + coordinates + '''},heights[]={''' + heights + '''};
struct225 *func_151602C0(Header *h,Header2 *p,s32 a,s32 b,s32 c,s32 d,u8 e,u8 f,s32 n,u8 slot,s32 context){
 int i;calls++;if(h->unk0!=2||h->unk1!=15||h->unk2!=300||h->unk4!=5||
  (u32)p->unk0!=want[0]||(u32)p->unk4!=want[1]||(u32)p->unk8!=want[2]||a||b!=255||c!=255||d!=90||e!=255||f||n!=16||slot!=255||context!=1)error=1;
 if(mode==1){*(u32*)(input+0x14)=0x12345678u;*(u32*)(coefficient.bytes+32)=0x76543210u;}
 if(mode==2)h->pad5=0x5A;
 if(result){for(i=0;i<6;i++)result[0xE + i]=((u8*)h)[i];*(u32*)(result+0x14)=0x24000u;result[0xE]|=2;}return (struct225*)result;}
void *memcpy(void *to,const void *from,unsigned int n){unsigned int i;copies++;if(n!=16)error=2;
 for(i=0;i<n;i++){((u8*)to)[i]=((const u8*)from)[i];}return to;}
''' + source.SELECTED + '''
static void (*volatile invoke)(u8*,s32)=func_1506A864;
int run(void){int p,m,kind,i;u8 expectedActor[96],expectedCoefficient[96],expectedOutput[96],*expectedResult;u32 coeff;
 if(sizeof(void*)!=4||sizeof(Header)!=6||sizeof(Header2)!=12)return 10;
 for(p=0;p<1728;p++)for(m=0;m<3;m++)for(kind=0;kind<4;kind++){
  for(i=0;i<96;i++)actor.bytes[i]=coefficient.bytes[i]=output.bytes[i]=0xA5;
  input=actor.bytes;*(u32*)(input+0x14)=values[p%12];*(u32*)(input+0x18)=values[p/12%12];*(u32*)(input+0x1C)=values[p/144];
  want[0]=coordinates[p%12];want[1]=heights[p/12%12];want[2]=coordinates[p/144];coeff=coefficients[p%12];*(u32*)(coefficient.bytes+32)=coeff;
  result=kind==0?NULL:kind==1?output.bytes:kind==2?actor.bytes:coefficient.bytes+8;
  for(i=0;i<96;i++){expectedActor[i]=actor.bytes[i];expectedCoefficient[i]=coefficient.bytes[i];expectedOutput[i]=output.bytes[i];}
  if(m==1){*(u32*)(expectedActor+0x14)=0x12345678u;*(u32*)(expectedCoefficient+32)=0x76543210u;}
  expectedResult=kind==0?NULL:kind==1?expectedOutput:kind==2?expectedActor:expectedCoefficient+8;
  if(expectedResult){expectedResult[0xE]=2;expectedResult[0xF]=15;*(s16*)(expectedResult+0x10)=300;expectedResult[0x12]=5;
   if(m==2){expectedResult[0x13]=0x5A;}*(u32*)(expectedResult+0x14)=0x24000u;
   *(u32*)(expectedResult+0x18)=0;*(u32*)(expectedResult+0x1C)=0x42A00000u;*(u32*)(expectedResult+0x20)=0;*(u32*)(expectedResult+0x24)=coeff;}
  mode=m;calls=copies=error=0;invoke(input,(s32)0x8765ABCDu);if(error||calls!=1||copies!=(kind!=0))return 11;
  for(i=0;i<96;i++){int unknown=expectedResult&&m!=2&&kind!=0;
   if(actor.bytes[i]!=expectedActor[i]&&!(unknown&&kind==2&&i==0x13))return 12;
   if(coefficient.bytes[i]!=expectedCoefficient[i]&&!(unknown&&kind==3&&i==0x1B))return 13;
   if(output.bytes[i]!=expectedOutput[i]&&!(unknown&&kind==1&&i==0x13))return 14;}
 }return 0;}
void _start(void){int value=run();__asm__ volatile("int $0x80"::"a"(1),"b"(value));__builtin_unreachable();}
'''
        for name, body, profile, success in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + n, b, '-O2', False) for n, b in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(fixture_c.replace(source.SELECTED, body))
            binary = path.with_suffix('')
            result = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing',
                '-msse2', '-mfpmath=sse', '-mstackrealign', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static',
                '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-unused-parameter', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, timeout=20)
            self.assertEqual(result.returncode == 0, success, (name, result.returncode))
        self.receipt('native', profiles=['O2', 'O0'], cases_per_profile=1728 * 3 * 4,
            signed_conversion_inputs_finite_in_range=True, raw_coefficient_bits_and_all_canaries=True,
            uninitialized_header_byte5_not_portably_fixed=True, provider_defined_byte5_checked=True,
            six_semantic_controls_effective=True, bounded_32_bit_domain_only=True)

    def test_09_original_factory_wrapper_memcpy_and_parent_outcomes(self):
        functions, _, addresses = shared.load_elf_functions(str(self.out / 'before-elf'), 'mips-linux-gnu-objdump')
        specs = (('func_151602C0', FACTORY, 0x18D770, 47), ('func_1516037C', WRAPPER, 0x18D82C, 32),
            ('memcpy', 0x10022EC0, 0x22EC0, 11), ('func_1506AC8C', PARENT, PARENT_ROM, 41))
        code = {}
        for name, address, rom, size in specs:
            words = list(struct.unpack_from('>%dI' % size, self.rom, rom))
            self.assertEqual((addresses[name], functions[name]), (address, words))
            code.update(zip(range(address, address + size * 4, 4), words))
        self.assertEqual(self.before[shared.elf_slot_offset(self.before, TABLE + 24, 4):
            shared.elf_slot_offset(self.before, TABLE + 24, 4) + 4], struct.pack('>I', source.ENTRY))
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x22ABE8)[0], source.ENTRY)
        cases, seen = 0, set()
        for parent, outcome, mode, phase in itertools.product((False, True), range(3), range(3), (0, 8)):
            result = CREATED if outcome == 2 else 0
            memory = fixture()
            if outcome != 2 and mode == 0:
                del memory[STACK + phase - (0x18 if parent else 0) - 0x60 + 0x59]
            initialized = dict(memory)
            if parent:
                for i in range(3):
                    put(initialized, 0x800D1560 + i * 4, read(memory, ACTOR + 0x2C + i * 4))
                    put(initialized, 0x800D1570 + i * 4, read(memory, 0x800CC254 + i * 4))
            expected, calls = reference(initialized, result=result, mode=mode,
                phase=phase - 0x18 if parent else phase, outcome=outcome)
            models = []
            for body in (self.retail, self.words):
                connected = dict(code)
                connected.update(zip(range(source.ENTRY, source.ENTRY + 260, 4), body))
                if parent:
                    root = code
                    words = [root[PARENT + i * 4] for i in range(38)]
                    model = SpawnOracle(words, memory, result=result, mode=mode, phase=phase,
                        entry=PARENT, connected=connected, outcome=outcome)
                    model.r[5], model.r[6] = 6, 0x8765ABCD
                else:
                    model = SpawnOracle(body, memory, result=result, mode=mode, phase=phase,
                        connected=connected, outcome=outcome)
                model.run()
                self.assertEqual((external(model.memory), model.calls), (expected, calls))
                self.assertEqual(model.callbacks, [(ACTOR, 0x8765ABCD)] if parent else [])
                seen.update(model.visits)
                models.append(model)
            self.assertEqual(state(models[0]), state(models[1]))
            cases += 1
        self.assertTrue(set(range(source.ENTRY, source.ENTRY + 260, 4)) <= seen)
        self.receipt('connected', cases=cases, actual_factory47_wrapper32_memcpy11_and_dispatcher38=True,
            body_failure_object_failure_and_success=True, real_descriptor6_byte_copy_and_pointer_flag=True,
            failure_does_not_require_untouched_header_byte5=True,
            generic_body_allocator_object_allocator_and_cleanup_are_bounded=True)

    def rebased_original(self, entry, symbols, name):
        assembly = self.out / 'original.s'
        if not assembly.exists():
            block = (self.root / self.paths['assembly']).read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1]
            assembly.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') +
                '"\nglabel ' + source.FUNCTION + '\n' + block.split('endlabel ' + source.FUNCTION, 1)[0] +
                'endlabel ' + source.FUNCTION + '\n')
        obj = assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(assembly)], check=True, capture_output=True)
        script = self.out / (name + '.ld')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
        return list(struct.unpack_from('>65I', source.compiler.sections(elf)['.text'][1]))

    def test_10_three_independent_carry_boundary_links(self):
        cases = 0
        for index, (entry, coefficient) in enumerate(((source.ENTRY, 0x80099A28), (0x15207FF0, 0x80107FFC), (0x15318004, 0x80218004))):
            symbols = dict(source.SYMBOLS, D_80099A28=coefficient,
                func_151602C0=FACTORY + index * 0x200000, memcpy=0x10022EC0 + index * 0x200000)
            original = self.rebased_original(entry, symbols, 'rebase-' + str(index))
            with patch.object(source, 'ENTRY', entry), patch.object(source, 'SYMBOLS', symbols):
                _, emitted = source.compile_candidate(self.root, self.out, 'rebase-source-' + str(index))
            self.assertEqual(original, emitted)
            for result, mode, phase in itertools.product((0, CREATED), range(3), (0, 8)):
                self.compare(fixture(symbols=symbols), result=result, mode=mode, phase=phase,
                    symbols=symbols, entry=entry, bodies=(original, emitted))
                cases += 1
        self.receipt('rebases', independent_original_source_links=3, cases=cases,
            coefficient_HI_LO_carries_and_both_JALs=True, complete_words_and_states=True)

    def test_11_fired_own_access_cuts_and_old_store_order_negative(self):
        pairs, domains = 0, 0
        for phase, mode, result in itertools.product((0, 8), range(3), (0, CREATED)):
            frame = STACK + phase - 0x60
            for actor in (ACTOR, frame + 0x24, frame + 0x30, frame + 0x40,
                    STACK + phase - 0x14, STACK + phase - 0x10):
                memory = fixture(actor=actor)
                completed = SpawnOracle(self.words, memory, actor, result, mode, phase).run()
                self.assertEqual(completed.accesses, 27)
                for cut in range(27):
                    models = [SpawnOracle(w, memory, actor, result, mode, phase, fault=cut) for w in (self.retail, self.words)]
                    for model in models:
                        with self.assertRaises(AccessFault):
                            model.run()
                        self.assertEqual(model.accesses, cut)
                    self.assertEqual(state(models[0]), state(models[1]))
                    self.assertEqual(models[0].dispatched_word, models[1].dispatched_word)
                    pairs += 1
                domains += 1
        _, wrong = source.compile_candidate(self.root, self.out, 'wrong-store-order-fault', source.BASE)
        models = [SpawnOracle(w, fixture(), fault=11) for w in (self.retail, wrong)]
        for model in models:
            with self.assertRaises(AccessFault):
                model.run()
        self.assertNotEqual(state(models[0]), state(models[1]))
        self.receipt('faults', domains=domains, fired_pairs=pairs, full_modeled_states=True,
            old_six_word_store_schedule_cut11_negative_effective=True, provider_accesses_excluded=True,
            hardware_PC_BD_complete_FCSR_not_claimed=True)

    def test_12_effective_literal_image_source_and_guard_corruptions(self):
        read_bytes, read_text = Path.read_bytes, Path.read_text
        path = self.root / self.paths['elf']
        data = path.read_bytes()
        target = shared.elf_slot_offset(data, source.ENTRY, 260)
        metadata_rows = {name: (offset, string) for offset, name, _, string in symbol_rows(data)
            if name in ('D_80099A28', '__osProbeTLB')}
        metadata_offsets = [at for pair in metadata_rows.values() for at in pair]
        for offset in (0, target, target + 259, shared.elf_slot_offset(data, 0x1506A79C, 160), len(data) - 1, *metadata_offsets):
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p, *a, **k: bytes(bad) if p == path else read_bytes(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_07_literal_image_source_and_protected_history()
        path = self.root / self.paths['source']
        bad_text = path.read_text() + '\n'
        with patch.object(Path, 'read_text', lambda p, *a, **k: bad_text if p == path else read_text(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_literal_image_source_and_protected_history()
        path = self.root / self.paths['guards']
        bad_bytes = path.read_bytes() + b'\n'
        with patch.object(Path, 'read_bytes', lambda p, *a, **k: bad_bytes if p == path else read_bytes(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_literal_image_source_and_protected_history()
        expected = bytearray(self.before)
        rows = symbol_rows(expected)
        damaged = next(offset for offset, name, _, _ in rows if name == 'D_80099A28')
        expected[damaged + 4] ^= 1
        with self.assertRaises(AssertionError):
            apply_spawn_symbol_serialization(expected)
        self.receipt('image-controls', target_previous_vector_header_tail_source_guard_mutations_effective=True,
            both_serialized_symbol_records_and_names_mutations_effective=True, invalid_baseline_definition_rejected=True)


if __name__ == '__main__':
    unittest.main()
