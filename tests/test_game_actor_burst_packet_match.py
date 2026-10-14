"""Mixed packet bits and holes, real mode-1 consumer, owner/image and own cuts."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_burst_packet_candidates as source
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.tests import test_game_actor_mask_scan_match as scan
from tools.tests import test_game_actor_vector_snapshot_match as vector
from tools.tests import test_game_record_constructor_match as image
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_record_callback_update_match import external, public
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import SYMBOL, parse_object, emit_padded_assembly
from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols
from tools import pad_c_object
from tools.check_game_data_layout import audit_layout

STACK, ACTOR, TABLE, PARENT, PARENT_ROM = image.STACK, 0x21000, 0x80086110, 0x1506AC8C, 0x9813C
PROVIDER, PROVIDER_ROM, RNG, RANDOM, TRIG = 0x151A6F00, 0x1D43B0, 0x150ADA20, 0x150ADA68, 0x151423D8
FACTORY, ANIMATION, MEMCPY, CREATED = 0x15132A4C, 0x15134908, 0x10022EC0, 0x25000
RAW = vector.RAW
ORIGINAL_COEFFICIENTS = (0x43178000, 0x4171999A, 0x41C9999A, 0x3EC6A7F0, 0x3E78D4FF, 0xBF828F5D)
HOLES = (2, 3, 0x12, 0x13, *range(0x28, 0x30), 0x5A, 0x5B)
INITIALIZED = tuple(i for i in range(0x5C) if i not in HOLES)

SERIALIZATION = (
    (('D_80099A18', 'D_800962E8', 'func_150F00EC'), (1, 2, 0),
        ((0x80099A18, 0, 16, 0, 65521), (0x800962E8, 0, 16, 0, 65521), (0x150F00EC, 12, 18, 0, 5))),
    (('D_80099A20', 'D_800E0D20'), (1, 0),
        ((0x80099A20, 0, 16, 0, 65521), (0x800E0D20, 0, 16, 0, 65521))),
    (('D_80099A14', 'D_800CC284', 'D_800A3D14'), (1, 2, 0),
        ((0x80099A14, 0, 16, 0, 65521), (0x800CC284, 0, 16, 0, 65521), (0x800A3D14, 0, 16, 0, 6))),
)


def apply_burst_symbol_serialization(expected):
    names = {n for group, _, _ in SERIALIZATION for n in group}
    rows = {name: (offset, fields, string) for offset, name, fields, string in symbol_rows(expected) if name in names}
    assert set(rows) == names
    for group, order, definitions in SERIALIZATION:
        first = rows[group[0]]
        cursor = first[2]
        for index, (name, definition) in enumerate(zip(group, definitions)):
            offset, fields, string = rows[name]
            assert offset == first[0] + index * SYMBOL.size and fields[1:] == definition
            assert string == cursor and expected[string:string + len(name) + 1] == name.encode() + b'\0'
            cursor += len(name) + 1
        string_base, cursor = first[2] - first[1][0], first[2]
        for index in order:
            name = group[index]
            fields = list(rows[name][1])
            fields[0] = cursor - string_base
            SYMBOL.pack_into(expected, first[0] + order.index(index) * SYMBOL.size, *fields)
            expected[cursor:cursor + len(name) + 1] = name.encode() + b'\0'
            cursor += len(name) + 1


def controls():
    return dict(wrong_count=source.SELECTED.replace('count = 3', 'count = 4'),
        wrong_coordinate=source.SELECTED.replace('actor + 0x14', 'actor + 0x10'),
        wrong_radius=source.SELECTED.replace('radius = D_80099A10', 'radius = D_80099A14'),
        wrong_kind=source.SELECTED.replace('&packet, 1,', '&packet, 0,'),
        wrong_slot=source.SELECTED.replace('0xFF, 1);', '0xFE, 1);'),
        wrong_signed_angle=source.SELECTED.replace('angle1 = -64', 'angle1 = 64'))


def fixture(values=None, coefficients=ORIGINAL_COEFFICIENTS, actor=ACTOR, phase=0, symbols=None, seed=0):
    s = symbols or source.SYMBOLS
    memory = {STACK + i: (i * 17 + seed * 31 + 0xA5) & 255 for i in range(-0x700, 0x180)}
    for base, size in ((ACTOR - 32, 160), (actor - 32, 160), (TABLE, 64),
            (0x800D1560, 32), (0x800D1570, 32), (0x800CC254, 12),
            (CREATED - 32, 0x800), (0x800A8DC0, 8)):
        for i in range(size):
            memory.setdefault(base + i, (i * 13 + seed * 11 + 0xA5) & 255)
    for address in (s[n] for n in source.COEFFICIENTS):
        for i in range(16):
            memory.setdefault(address - 8 + i, 0xA5)
    for i, v in enumerate(values or (bits(1.5), bits(-2.5), bits(3.5))):
        put(memory, actor + 0x14 + i * 4, v)
    for name, v in zip(source.COEFFICIENTS, coefficients):
        put(memory, s[name], v)
    put(memory, TABLE, source.ENTRY)
    put(memory, 0x800A8DC0, bits(0.25))
    put(memory, 0x800A8DC4, bits(0.125))
    return memory


def mutations(actor, symbols, packet, mode):
    if mode == 1:
        return ((actor + 0x14, 0x12345678, 4), (symbols[source.COEFFICIENTS[0]], 0x76543210, 4))
    if mode == 2:
        return ((packet, 0, 2), (packet + 0x54, 0x5A, 1))
    return ()


def reference(memory, actor=ACTOR, phase=0, mode=0, symbols=None):
    s, m, events = symbols or source.SYMBOLS, dict(memory), []
    frame, packet = STACK + phase - 0x78, STACK + phase - 0x5C
    put(m, frame + 0x14, 0xDEAD0000)
    put(m, STACK + phase, actor)
    put(m, STACK + phase + 4, 0x8765ABCD)
    def get(address):
        v = read(m, address)
        events.append(('R', address, 4, v))
        return v
    def store(offset, value, size=4):
        put(m, packet + offset, value, size)
    # Use the retail read/store order for declared private aliases, not field order.
    store(0, 3, 2)
    x, radius = get(actor + 0x14), get(s[source.COEFFICIENTS[0]])
    store(4, x)
    y, speed = get(actor + 0x18), get(s[source.COEFFICIENTS[1]])
    store(8, y)
    z = get(actor + 0x1C)
    speed_range, scale, scale_range = (get(s[n]) for n in source.COEFFICIENTS[2:5])
    store(0xC, z)
    extra = get(s[source.COEFFICIENTS[5]])
    store(0x20, speed)
    store(0x14, radius)
    store(0x24, speed_range)
    for offset, value in ((0x10, 90), (0x18, 0), (0x1A, 255), (0x1C, 0xFFC0), (0x1E, 40)):
        store(offset, value, 2)
    for offset in (0x30, 0x34, 0x38):
        store(offset, 0)
    store(0x54, 0, 1)
    store(0x55, 0, 1)
    store(0x56, 50, 2)
    store(0x58, 25, 2)
    for offset, value in ((0x3C, scale), (0x40, scale_range), (0x44, extra),
            (0x4C, bits(-4.0)), (0x48, 0), (0x50, bits(8.0))):
        store(offset, value)
    args = (packet, 1, 255, 1)
    payload = bytes(m[packet + i] for i in INITIALIZED)
    calls = [(s['func_151A6F00'], args, payload)]
    events.append(('CALL', s['func_151A6F00'], args))
    for address, value, size in mutations(actor, s, packet, mode):
        put(m, address, value, size)
        events.append(('W', address, size, value))
    for i in range(4):
        put(m, frame + i * 4, 0xB5000000 + i)
    return m, public(events), calls


class BurstOracle(scan.MaskOracle):
    def __init__(self, words, memory, actor=ACTOR, phase=0, mode=0, symbols=None,
            entry=source.ENTRY, connected=None, arguments=None, outcome=0, fault=None):
        super().__init__(words, memory, phase, mode, symbols or source.SYMBOLS, entry,
            arguments or (actor, 0x8765ABCD), connected, fault=fault)
        self.actor, self.outcome, self.hi = actor, outcome, 0
        self.packet = None
        self.factory_count = self.random_count = self.integer_count = 0

    def execute(self, word):
        op, rs, rt, rd, shift, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        if op == 0 and fn == 27:
            assert self.r[rt] != 0, 'outside bounded unsigned-divisor domain'
            self.lo, self.hi = divmod(self.r[rs], self.r[rt])
        elif op == 0 and fn == 16:
            self.r[rd] = self.hi
            self.r[0] = 0
        elif op == 17 and rs == 16 and fn == 7:
            self.f[shift] = self.f[rd] ^ 0x80000000
        else:
            super().execute(word)

    def record_call(self, target):
        if target == source.ENTRY:
            self.callbacks.append(self.arguments(2))
        elif target == self.symbols['func_151A6F00']:
            args = self.arguments(4)
            self.packet = args[0]
            payload = bytes(self.get(args[0] + i, 1) for i in INITIALIZED)
            self.calls.append((target, args, payload))
            self.events.append(('CALL', target, args))
        elif target == MEMCPY:
            destination, pointer, size = self.arguments(3)
            self.calls.append((target, (destination, pointer, size),
                bytes(self.get(pointer + i, 1) for i in range(size))))
        else:
            counts = {RNG: 0, RANDOM: 0, TRIG: 1, FACTORY: 6, ANIMATION: 4}
            args = self.arguments(counts[target])
            self.calls.append((target, args))

    def hook(self, target):
        result, value = 0x11223344, None
        if target == self.symbols['func_151A6F00']:
            for address, v, size in mutations(self.actor, self.symbols, self.packet, self.mode):
                self.put(address, v, size)
        elif target == RNG:
            result = (0, 0xFFFFFFFF, 0x12345678, 0x80000000)[self.integer_count % 4]
            self.integer_count += 1
        elif target == RANDOM:
            value = bits((0.0, 0.25, 0.5, 0.75)[self.random_count % 4])
            self.random_count += 1
        elif target == TRIG:
            value = bits((0.0, 0.5, -0.5, 1.0)[self.r[4] & 3])
        elif target == FACTORY:
            result = CREATED + self.factory_count * 0x200 if self.outcome else 0
            self.factory_count += 1
        else:
            assert target == ANIMATION
            result = CREATED + 0x680 if self.outcome == 2 else 0
        for i in range(4 if target == self.symbols['func_151A6F00'] else 0):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result
        if value is not None:
            self.f[0] = value


def complete_state(model):
    return scan.state(model), model.hi


class GameActorBurstPacketMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-burst-packet-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=source.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            makefile='conker/Makefile', layout='conker/retail_layout.us.txt',
            assembly='conker/asm/97AA0.s', table='conker/asm/data/22ABD0.rodata.s',
            callee='conker/asm/1D43B0.s', constants='conker/asm/data/23E4D0.rodata.s')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == 'c84410d77e5e56f893997cd7de2b1ee15a6be993dc7434dafd7ee264bedffb65'
        assert cls.baseline['elf'] == '9ba0f2793d2c40711359d86135f7408814827df987aae711c5dc153922ec9772'
        for name, digest in cls.baseline.items():
            assert hashlib.sha256((cls.out / ('before-' + name)).read_bytes()).hexdigest() == digest, name
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_after = source.recovered_owner(cls.owner_before)
        cls.meta, cls.words = source.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>67I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, actor=ACTOR, phase=0, mode=0, symbols=None, entry=source.ENTRY, bodies=None):
        expected, events, calls = reference(memory, actor, phase, mode, symbols)
        models = [BurstOracle(w, memory, actor, phase, mode, symbols, entry).run()
            for w in (bodies or (self.retail, self.words))]
        for model in models:
            self.assertEqual((model.memory, public(model.events), model.calls), (expected, events, calls))
            self.assertEqual(model.r[2], 0x11223344)
        self.assertEqual(complete_state(models[0]), complete_state(models[1]))
        return models

    def test_01_direct_slot_profiles_and_integer_zero_provenance(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (67, 0x78, 0, 0, ''))
        self.assertEqual(self.words, self.retail)
        measured = json.loads((self.root / 'conker/build/game-actor-burst-packet/measurements.json').read_text())
        self.assertEqual(len(measured), 40)
        self.assertEqual([m['name'] for m in measured if m['differences'] == 0],
            ['selected-integer-zero-o2g3', 'last-zero-0-o2g3', 'last-zero-0.0-o2g3', 'last-zero-f320-o2g3'])
        meta, wrong = source.compile_candidate(self.root, self.out, 'float-zero-control', source.BASE)
        self.assertEqual((meta['body_words'], meta['differences']), (66, 35))
        self.assertNotEqual(wrong, self.retail)
        self.assertEqual(self.meta['relocations'][0xF4], [('R_MIPS_26', 'func_151A6F00')])
        self.receipt('shape', words=67, frame=120, direct_C=True, guards=0,
            measurements=40, old_float_literal66_words35_differences=True,
            actual_packet_offset=28, RA_offset=20, packet_size=92, holes=list(HOLES))

    def test_02_raw_actor_coefficients_provider_changes_and_full_coverage(self):
        cases, seen = 0, set()
        for indices in itertools.product(range(12), repeat=3):
            values = tuple(RAW[i] for i in indices)
            coefficients = tuple(RAW[(sum(indices) + i * 3) % 12] for i in range(6))
            for phase, mode in itertools.product((0, 8), range(3)):
                for model in self.compare(fixture(values, coefficients, seed=sum(indices)), phase=phase, mode=mode):
                    seen.update(model.visits)
                cases += 1
        for field, value, phase, mode in itertools.product(range(6), RAW, (0, 8), range(3)):
            coefficients = list(ORIGINAL_COEFFICIENTS)
            coefficients[field] = value
            self.compare(fixture(coefficients=coefficients, seed=field), phase=phase, mode=mode)
            cases += 1
        self.assertEqual(seen, set(range(source.ENTRY, source.ENTRY + 268, 4)))
        self.receipt('guest', cases=cases, raw_actor_triples=1728, six_independent_coefficient_axes=True,
            full_modeled_state_and_ordered_public_accesses=True, all67_words_reached=True,
            no_root_float_arithmetic_or_NaN_arithmetic_claim=True)

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
        return list(struct.unpack_from('>67I', source.compiler.sections(elf)['.text'][1]))

    def test_03_private_public_and_coefficient_aliases(self):
        cases = 0
        for phase, mode in itertools.product((0, 8), range(3)):
            packet = STACK + phase - 0x5C
            for actor in (ACTOR, 0x80099A10 - 0x14, packet - 0x14, packet - 0x10,
                    STACK + phase - 0x14, STACK + phase - 0x10):
                self.compare(fixture(actor=actor), actor, phase, mode)
                cases += 1
        for index, name in enumerate(source.COEFFICIENTS):
            for phase in (0, 8):
                for kind, address in (('packet', STACK + phase - 0x5C + index * 4),
                        ('home', STACK + phase + (index & 1) * 4)):
                    symbols = dict(source.SYMBOLS, **{name: address})
                    with patch.object(source, 'SYMBOLS', symbols):
                        _, emitted = source.compile_candidate(self.root, self.out, 'alias-%d-%d-%s' % (index, phase, kind))
                    original = self.rebased_original(source.ENTRY, symbols, 'alias-original-%d-%d-%s' % (index, phase, kind))
                    self.assertEqual(original, emitted)
                    for mode in range(3):
                        self.compare(fixture(symbols=symbols), phase=phase, mode=mode, symbols=symbols, bodies=(original, emitted))
                        cases += 1
        self.receipt('aliases', cases=cases, independent_original_source_links=24,
            stack_packet_incoming_homes_and_public_actor_coefficient_aliases=True)

    def test_04_required_bytes_untouched_holes_and_zero_literal_cut(self):
        cases = 0
        addresses = [ACTOR + 0x14 + i * 4 for i in range(3)] + [source.SYMBOLS[n] for n in source.COEFFICIENTS]
        for phase, address, byte in itertools.product((0, 8), addresses, range(4)):
            memory = fixture()
            del memory[address + byte]
            models = [BurstOracle(w, memory, phase=phase) for w in (self.retail, self.words)]
            for model in models:
                with self.assertRaises(AssertionError):
                    model.run()
                self.assertEqual(model.calls, [])
            self.assertEqual(complete_state(models[0]), complete_state(models[1]))
            cases += 1
        for phase in (0, 8):
            memory = fixture(phase=phase)
            packet = STACK + phase - 0x5C
            for hole in HOLES:
                del memory[packet + hole]
            self.compare(memory, phase=phase)
        self.receipt('inputs', missing_byte_prefixes=cases, all14_packet_holes_unreadable_and_untouched=True)

    def test_05_six_effective_compiled_semantic_controls(self):
        memory = fixture()
        expected = reference(memory)
        for name, body in controls().items():
            _, wrong = source.compile_candidate(self.root, self.out, 'negative-' + name, body)
            model = BurstOracle(wrong, memory).run()
            self.assertNotEqual((model.memory, public(model.events), model.calls), expected, name)
        self.receipt('controls', effective_guest_controls=list(controls()))

    def test_06_complete_owner_pools_neighbors_and_both_padders(self):
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
        self.assertEqual(target['size'], 268)
        raw, functions, _ = parse_object(self.out / 'selected.o')
        start = functions[source.FUNCTION]['value']
        self.assertEqual(padded[0][0][target['value']:target['value'] + 268], raw[start:start + 268])
        self.receipt('owner', neighbors=len(neighbors), both_padders_and_direct_slot=True,
            pools_neighbor_words_relocations_and_existing_SDK_include_fixed=True)

    def test_07_literal_image_source_and_protected_history(self):
        current_source = (self.root / self.paths['source']).read_text()
        self.assertIn(current_source, (self.owner_before, self.owner_after))
        expected = bytearray(self.before)
        if current_source == self.owner_after:
            offset = image.elf_slot_offset(self.before, source.ENTRY, 268)
            expected[offset:offset + 268] = struct.pack('>67I', *self.retail)
            with patch.object(image.screen, 'ENTRY', source.ENTRY):
                size = image.elf_symbol_size_offset(self.before, source.FUNCTION)
            self.assertEqual(struct.unpack_from('>I', expected, size)[0], 12)
            struct.pack_into('>I', expected, size, 268)
            apply_burst_symbol_serialization(expected)
        current = (self.root / self.paths['elf']).read_bytes()
        self.assertEqual(current, bytes(expected))
        self.assertEqual(canonical_symbols(current), canonical_symbols(expected))
        for name in set(self.paths) - {'source', 'elf'}:
            before = (self.out / ('before-' + name)).read_bytes()
            self.assertEqual(hashlib.sha256(before).hexdigest(), self.baseline[name])
            self.assertEqual((self.root / self.paths[name]).read_bytes(), before, name)
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('linked-audit', installed=current_source == self.owner_after,
            changed_bytes=sum(a != b for a, b in zip(self.before, current)), protected_data=data)

    def test_14_closed_serialization_accounting_and_effective_corruptions(self):
        current = (self.root / self.paths['elf']).read_bytes()
        installed = (self.root / self.paths['source']).read_text() == self.owner_after
        rows = {n: (at, fields, string) for at, n, fields, string in symbol_rows(current)
            if n in {n for group, _, _ in SERIALIZATION for n in group}}
        old_rows = {n: (at, fields, string) for at, n, fields, string in symbol_rows(self.before) if n in rows}
        record_changes = string_changes = 0
        for group, _, _ in SERIALIZATION:
            first = old_rows[group[0]]
            span = len(group) * SYMBOL.size
            record_changes += sum(a != b for a, b in zip(self.before[first[0]:first[0] + span], current[first[0]:first[0] + span]))
            span = sum(len(n) + 1 for n in group)
            string_changes += sum(a != b for a, b in zip(self.before[first[2]:first[2] + span], current[first[2]:first[2] + span]))
        slot = image.elf_slot_offset(current, source.ENTRY, 268)
        code_changes = sum(a != b for a, b in zip(self.before[slot:slot + 268], current[slot:slot + 268]))
        with patch.object(image.screen, 'ENTRY', source.ENTRY):
            size = image.elf_symbol_size_offset(current, source.FUNCTION)
        size_changes = sum(a != b for a, b in zip(self.before[size:size + 4], current[size:size + 4]))
        self.assertEqual((code_changes, size_changes, record_changes + string_changes), (214, 1, 77) if installed else (0, 0, 0))
        read_bytes = Path.read_bytes
        path = self.root / self.paths['elf']
        for name, (at, fields, string) in rows.items():
            for offset in (at, string):
                bad = bytearray(current)
                bad[offset] ^= 1
                with patch.object(Path, 'read_bytes', lambda p, *a, **k: bytes(bad) if p == path else read_bytes(p, *a, **k)):
                    with self.assertRaises(AssertionError):
                        self.test_07_literal_image_source_and_protected_history()
        expected = bytearray(self.before)
        expected[old_rows['D_80099A18'][0] + 7] ^= 1
        with self.assertRaises(AssertionError):
            apply_burst_symbol_serialization(expected)
        self.receipt('serialization', instruction_bytes=code_changes, named_size_bytes=size_changes,
            symbol_record_bytes=record_changes, string_bytes=string_changes,
            three_exact_adjacent_permutations=True, all16_current_record_string_corruptions_effective=True,
            corrupted_baseline_definition_rejected=True, no_metadata_section_exclusion=True)

    def test_08_native32_raw_packet_fields_and_input_canaries(self):
        native = '''typedef unsigned char u8;typedef unsigned short u16;typedef short s16;
typedef unsigned int u32;typedef int s32;typedef float f32;
static union{u32 alignment;u8 bytes[128];} arena[7];
static u8 *input;static u32 values[6],coords[3];static int mode,count,error;
''' + ''.join('#define %s (*(f32*)(arena[%d].bytes+32))\n' % (n, i + 1) for i, n in enumerate(source.COEFFICIENTS)) + source.RECORD + '''
void func_151A6F00(ActorBurstPacket97AA0 *p,u8 kind,u8 slot,s32 context){
 int i;count++;if(kind!=1||slot!=255||context!=1||p->count!=3||p->duration!=90||p->angle0||p->range0!=255||p->angle1!=-64||p->range1!=40||p->unk54||p->unk55||p->unk56!=50||p->unk58!=25)error=1;
 for(i=0;i<3;i++)if(((u32*)p->position)[i]!=coords[i]||((u32*)p->direction)[i])error=2;
 if(*(u32*)&p->radius!=values[0]||*(u32*)&p->speed!=values[1]||*(u32*)&p->speedRange!=values[2]||*(u32*)&p->scale!=values[3]||*(u32*)&p->scaleRange!=values[4]||*(u32*)&p->unk44!=values[5]||*(u32*)&p->unk48||*(u32*)&p->unk4C!=0xC0800000u||*(u32*)&p->unk50!=0x41000000u)error=3;
 if(mode==1){*(u32*)(input+0x14)=0x12345678u;*(u32*)(arena[1].bytes+32)=0x76543210u;}
 if(mode==2){p->count=0;p->unk54=0x5A;}
}
''' + source.SELECTED + '''
static const u32 raw[]={''' + ','.join('0x%Xu' % v for v in RAW) + '''};
static void (*volatile invoke)(u8*,s32)=func_1506A5F0;
int run(void){int p,m,a,i,j;u8 expected[7][128];
 if(sizeof(void*)!=4||sizeof(ActorBurstPacket97AA0)!=92||__builtin_offsetof(ActorBurstPacket97AA0,radius)!=0x14||__builtin_offsetof(ActorBurstPacket97AA0,unk58)!=0x58)return 10;
 for(p=0;p<1728;p++)for(m=0;m<3;m++)for(a=0;a<4;a++){
  for(i=0;i<7;i++)for(j=0;j<128;j++)arena[i].bytes[j]=0xA5;
  input=a==0?arena[0].bytes:a==1?arena[1].bytes+12:a==2?arena[6].bytes+12:arena[1].bytes+16;
  *(u32*)(input+0x14)=raw[p%12];*(u32*)(input+0x18)=raw[p/12%12];*(u32*)(input+0x1C)=raw[p/144];
  for(i=0;i<6;i++)values[i]=*(u32*)(arena[i+1].bytes+32)=raw[(p+i*3)%12];
  for(i=0;i<3;i++)coords[i]=*(u32*)(input+0x14+i*4);
  for(i=0;i<7;i++)for(j=0;j<128;j++)expected[i][j]=arena[i].bytes[j];
  mode=m;count=error=0;invoke(input,(s32)0x8765ABCDu);if(error||count!=1)return 11;
  if(m==1){u8 *e=a==0?expected[0]:a==1?expected[1]+12:a==2?expected[6]+12:expected[1]+16;*(u32*)(e+0x14)=0x12345678u;*(u32*)(expected[1]+32)=0x76543210u;}
  for(i=0;i<7;i++)for(j=0;j<128;j++)if(arena[i].bytes[j]!=expected[i][j])return 12;
 }return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''
        for name, body, profile, success in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + n, b, '-O2', False) for n, b in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(native.replace(source.SELECTED, body))
            binary = path.with_suffix('')
            result = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing', '-msse2',
                '-mfpmath=sse', '-mstackrealign', '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie',
                '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, timeout=20)
            self.assertEqual(result.returncode == 0, success, (name, result.returncode))
        self.receipt('native', cases_per_profile=20736, profiles=['O2', 'O0'], six_controls_effective=True,
            actual_32bit_packet_offsets_raw_fields_and_all_input_canaries=True, unspecified_padding_not_read=True)

    def test_09_original_dispatcher_table0_and_complete_mode1_consumer(self):
        parent = list(struct.unpack_from('>38I', self.rom, PARENT_ROM))
        provider = list(struct.unpack_from('>315I', self.rom, PROVIDER_ROM))
        memcpy = list(struct.unpack_from('>11I', self.rom, 0x22EC0))
        offset = image.elf_slot_offset(self.before, TABLE, 4)
        self.assertEqual(self.before[offset:offset + 4], struct.pack('>I', source.ENTRY))
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x22ABD0)[0], source.ENTRY)
        # The provider is still a production placeholder; execute frozen retail, not that stub.
        functions, _, _ = image.load_elf_functions(str(self.out / 'before-elf'), 'mips-linux-gnu-objdump')
        self.assertEqual(functions['func_1506AC8C'], list(struct.unpack_from('>41I', self.rom, PARENT_ROM)))
        self.assertEqual(functions['memcpy'], memcpy)
        cases, visited = 0, set()
        for phase, outcome, parent_call, missing in itertools.product((0, 8), range(3), (False, True), (False, True)):
            memory = fixture(phase=phase)
            actual_phase = phase - (0x18 if parent_call else 0)
            packet = STACK + actual_phase - 0x5C
            if missing:
                for hole in HOLES:
                    del memory[packet + hole]
            if parent_call:
                for i in range(3):
                    put(memory, ACTOR + 0x2C + i * 4, bits(float(i + 1)))
            models = []
            for body in (self.retail, self.words):
                connected = dict(zip(range(PROVIDER, PROVIDER + 1260, 4), provider))
                connected.update(zip(range(MEMCPY, MEMCPY + 44, 4), memcpy))
                if parent_call:
                    connected.update(zip(range(source.ENTRY, source.ENTRY + 268, 4), body))
                model = BurstOracle(parent if parent_call else body, memory, phase=phase,
                    entry=PARENT if parent_call else source.ENTRY, connected=connected,
                    arguments=(ACTOR, 0, 0x8765ABCD) if parent_call else None, outcome=outcome).run()
                self.assertEqual(model.factory_count, 3)
                self.assertEqual((model.integer_count, model.random_count), (6, 18))
                self.assertEqual(model.calls[0][1], (packet, 1, 255, 1))
                self.assertEqual(model.callbacks, [(ACTOR, 0x8765ABCD)] if parent_call else [])
                self.assertIn(0x151A71CC, model.visits)
                self.assertNotIn(0x151A717C, model.visits)
                self.assertFalse(any(a <= packet + hole < a + size for a, size, _ in model.reads for hole in HOLES))
                visited.update(model.visits)
                models.append(model)
            self.assertEqual(complete_state(models[0]), complete_state(models[1]))
            cases += 1
        self.assertTrue(set(range(source.ENTRY, source.ENTRY + 268, 4)) <= visited)
        self.receipt('connected', cases=cases, original_provider315_parent38_memcpy11_words=True,
            real_table0_mode1_three_iterations_and_all14_holes_unreadable=True,
            RNG_trig_random_factory_animation_are_bounded_hooks=True,
            provider_production_stub_not_restored_or_claimed=True)

    def test_13_independent_original_provider_and_bounded_extra_opcodes(self):
        block = (self.out / 'before-callee').read_text().split('glabel func_151A6F00\n', 1)[1].split(
            'endlabel func_151A6F00', 1)[0]
        assembly = self.out / 'provider-original.s'
        assembly.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') +
            '"\nglabel func_151A6F00\n' + block + 'endlabel func_151A6F00\n')
        obj = assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(assembly)], check=True, capture_output=True)
        script = self.out / 'provider-original.ld'
        script.write_text('SECTIONS { .text 0x151A6F00 : SUBALIGN(4) { *(.text) } }\n')
        symbols = dict(func_150ADA20=RNG, func_150ADA68=RANDOM, func_151423D8=TRIG,
            func_15132A4C=FACTORY, func_15134908=ANIMATION, memcpy=MEMCPY,
            D_800A8DC0=0x800A8DC0, D_800A8DC4=0x800A8DC4)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', 'func_151A6F00',
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
        self.assertEqual(list(struct.unpack_from('>315I', source.compiler.sections(elf)['.text'][1])),
            list(struct.unpack_from('>315I', self.rom, PROVIDER_ROM)))
        functions, _, _ = image.load_elf_functions(str(self.out / 'before-elf'), 'mips-linux-gnu-objdump')
        self.assertNotEqual(functions['func_151A6F00'], list(struct.unpack_from('>315I', self.rom, PROVIDER_ROM)))
        for left, right, quotient, remainder in ((0, 41, 0, 0), (1, 41, 0, 1),
                (0xFFFFFFFF, 256, 0xFFFFFF, 255), (0x80000000, 256, 0x800000, 0)):
            model = BurstOracle(self.words, fixture())
            model.r[8], model.r[9] = left, right
            model.execute(8 << 21 | 9 << 16 | 27)
            model.execute(10 << 11 | 16)
            self.assertEqual((model.lo, model.hi, model.r[10]), (quotient, remainder, remainder))
        model.r[9] = 0
        with self.assertRaises(AssertionError):
            model.execute(8 << 21 | 9 << 16 | 27)
        for value, expected in ((0, 0x80000000), (0x80000000, 0), (0x3F800000, 0xBF800000)):
            model.f[4] = value
            model.execute(17 << 26 | 16 << 21 | 4 << 11 | 6 << 6 | 7)
            self.assertEqual(model.f[6], expected)
        self.receipt('provider-proof', independent_full315_word_original_link=True,
            production_provider_still_nonmatching=True, local_DIVU_MFHI_and_finite_NEGS_controls=True,
            zero_divisor_explicitly_outside_bounded_connected_domain=True)

    def test_10_three_independent_HI_LO_carry_links(self):
        cases = 0
        for index, (entry, base) in enumerate(((source.ENTRY, 0x80099A10),
                (0x15207FF0, 0x80107FF4), (0x15318004, 0x80217FF4))):
            symbols = dict(func_151A6F00=PROVIDER + index * 0x200000,
                **dict(zip(source.COEFFICIENTS, range(base, base + 24, 4))))
            original = self.rebased_original(entry, symbols, 'rebase-' + str(index))
            with patch.object(source, 'ENTRY', entry), patch.object(source, 'SYMBOLS', symbols):
                _, emitted = source.compile_candidate(self.root, self.out, 'rebase-source-' + str(index))
            self.assertEqual(original, emitted)
            for phase, mode in itertools.product((0, 8), range(3)):
                self.compare(fixture(symbols=symbols), phase=phase, mode=mode, symbols=symbols, entry=entry, bodies=(original, emitted))
                cases += 1
        self.receipt('rebases', independent_original_source_links=3, cases=cases, six_data_HI_LO_and_JAL=True)

    def test_11_all_fired_own_access_cuts_and_float_zero_negative(self):
        pairs, domains = 0, 0
        for phase, mode in itertools.product((0, 8), range(3)):
            packet = STACK + phase - 0x5C
            for actor in (ACTOR, 0x80099A10 - 0x14, packet - 0x14, packet - 0x10,
                    STACK + phase - 0x14, STACK + phase - 0x10):
                memory = fixture(actor=actor)
                self.assertEqual(BurstOracle(self.words, memory, actor, phase, mode).run().accesses, 39)
                for cut in range(39):
                    models = [BurstOracle(w, memory, actor, phase, mode, fault=cut) for w in (self.retail, self.words)]
                    for model in models:
                        with self.assertRaises(scan.AccessFault):
                            model.run()
                        self.assertEqual(model.accesses, cut)
                    self.assertEqual(complete_state(models[0]), complete_state(models[1]))
                    self.assertEqual(models[0].dispatched_word, models[1].dispatched_word)
                    pairs += 1
                domains += 1
        _, wrong = source.compile_candidate(self.root, self.out, 'float-zero-fault', source.BASE)
        effective = []
        for cut in range(39):
            models = [BurstOracle(w, fixture(), fault=cut) for w in (self.retail, wrong)]
            for model in models:
                with self.assertRaises(scan.AccessFault):
                    model.run()
            if complete_state(models[0]) != complete_state(models[1]):
                effective.append(cut)
        self.assertTrue(effective)
        self.receipt('faults', domains=domains, fired_pairs=pairs, all39_own_accesses=True,
            wrong_float_literal_effective_cuts=effective, provider_accesses_excluded=True)

    def test_12_effective_whole_image_source_guard_and_symbol_corruptions(self):
        read_bytes, read_text = Path.read_bytes, Path.read_text
        path = self.root / self.paths['elf']
        data = path.read_bytes()
        target = image.elf_slot_offset(data, source.ENTRY, 268)
        with patch.object(image.screen, 'ENTRY', source.ENTRY):
            size = image.elf_symbol_size_offset(data, source.FUNCTION)
        for offset in (0, target, target + 267, size - 8, size,
                image.elf_slot_offset(data, 0x1506A968, 160), len(data) - 1):
            bad = bytearray(data)
            bad[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p, *a, **k: bytes(bad) if p == path else read_bytes(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_07_literal_image_source_and_protected_history()
        path = self.root / self.paths['source']
        with patch.object(Path, 'read_text', lambda p, *a, **k: read_text(p, *a, **k) + '\n' if p == path else read_text(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_literal_image_source_and_protected_history()
        path = self.root / self.paths['guards']
        with patch.object(Path, 'read_bytes', lambda p, *a, **k: read_bytes(p, *a, **k) + b'\n' if p == path else read_bytes(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_literal_image_source_and_protected_history()
        self.receipt('image-controls', target_header_tail_previous_mode1_source_guard_symbol_mutations_effective=True)


if __name__ == '__main__':
    unittest.main()
