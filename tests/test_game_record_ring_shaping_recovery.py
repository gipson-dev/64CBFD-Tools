"""Full ring shaping with closed guards and bounded numeric/FCSR evidence."""

import csv
import hashlib
import itertools
import json
import math
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_record_ring_shaping_candidates as screen
from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_record_ring_update_match as ring
from tools.tests import test_game_random_curve_record as native
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK

OWNER, PAYLOAD, RECORDS, ALT_PAYLOAD, ALT_RECORDS = 0x20000, 0x21000, 0x28000, 0x23000, 0x30000
MAGNITUDE, WRAP = screen.SYMBOLS['func_15143E64'], screen.SYMBOLS['func_15144528']
DISPATCHER, RELEASE, TABLE = 0x15147740, 0x1516972C, 0x8008A284
GLOBALS = dict(D_800BE9A4=0x3F800000, D_800AB2DC=0x467FFC00,
    D_800AB2E0=0x423B851E, D_800AB2E4=0x467FFC00, D_800AB2E8=0x3E991688)
SOURCE = 'conker/src/game/generated_204660.c'
INSERT = screen.DECLARATIONS[screen.DECLARATIONS.index('extern f32 D_800AB2DC'):] + '\n'


def fround(value):
    return floating(bits(value))


def divide(left, right):
    if right:
        return fround(left / right)
    return math.nan if not left else math.copysign(math.inf, left * math.copysign(1.0, right))


def unsigned_byte(value):
    return math.trunc(value) & 255 if math.isfinite(value) and 0 <= math.trunc(value) < 2**32 else 255


def fixture(state=3, current=3, goal=0, count=4, flags=2, spacing=20., phase=0., layout=0, symbols=None):
    symbols = symbols or screen.SYMBOLS
    records = (RECORDS, PAYLOAD, OWNER + 0x40)[layout]
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    for base, length in ((OWNER, 0x200), (PAYLOAD, 0x100), (ALT_PAYLOAD, 0x100)):
        memory.update({base + i: (i * 17 + 0xA5) & 255 for i in range(-16, length)})
    for base in dict.fromkeys((records, RECORDS, ALT_RECORDS)):
        for index in range(-1, 256):
            for offset in range(28):
                memory[base + index * 28 + offset] = (index + offset * 17 + 0xA5) & 255
            for axis, value in enumerate((index * spacing, 0., 0., 0., 0., 0., 0.)):
                put(memory, base + index * 28 + axis * 4, bits(value))
    for address, value, width in ((OWNER + 0x2C, state, 1), (OWNER + 0x2E, current, 1),
        (OWNER + 0x2D, goal, 1), (OWNER + 0x25, count, 1), (OWNER + 0x1E, flags, 2),
        (OWNER + 0x98, PAYLOAD, 4), (OWNER + 0x94, records, 4),
        (PAYLOAD + 0x18, bits(phase), 4), (ALT_PAYLOAD + 0x18, bits(100.), 4)):
        put(memory, address, value, width)
    for axis, value in enumerate((4 * spacing, 0., 0.)):
        put(memory, OWNER + 0x10 + axis * 4, bits(value))
    for name, value in GLOBALS.items():
        put(memory, symbols[name], value)
    return memory


def changes(target, magnitude_index, wrap_index, mode, symbols):
    if target == symbols['func_15143E64'] and magnitude_index == 0:
        return {1: [(OWNER + 0x2D, 1, 1)], 2: [(OWNER + 0x2C, 1, 1)],
            3: [(OWNER + 0x94, ALT_RECORDS, 4)], 4: [(OWNER + 0x98, ALT_PAYLOAD, 4)],
            5: [(symbols['D_800BE9A4'], bits(2.), 4)]}.get(mode, [])
    if target == symbols['func_15144528']:
        if wrap_index == 0:
            return {6: [(symbols['D_800AB2E0'], bits(80.), 4)],
                7: [(OWNER + 0x2C, 1, 1)], 9: [(OWNER + 0x2E, 1, 1)]}.get(mode, [])
        if wrap_index == 1 and mode == 8:
            return [(PAYLOAD + 0x18, bits(100.), 4)]
    return []


def wrap_value(value, upper, lower):
    step = fround(upper - lower)
    for _ in range(64):
        if not upper < value:
            break
        value = fround(value - step)
    else:
        raise AssertionError('wrapper reference domain does not terminate')
    for _ in range(64):
        if not value < lower:
            return value
        value = fround(value + step)
    raise AssertionError('wrapper reference domain does not terminate')


class ShapingReference(ring.RingReference):
    def __init__(self, memory, mode=0, lengths=None, symbols=None):
        super().__init__(memory, mode, symbols or screen.SYMBOLS)
        self.lengths, self.magnitude_index, self.wrap_index = lengths, 0, 0

    def number(self, address):
        return floating(self.get(address))

    def scalar_call(self, target, args):
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))
        if target == self.symbols['func_15143E64']:
            x, y, z = map(floating, args)
            result = fround(math.sqrt(fround(fround(fround(x*x) + fround(y*y)) + fround(z*z))))
            if self.lengths is not None:
                result = fround(self.lengths[min(self.magnitude_index, len(self.lengths) - 1)])
        else:
            result = wrap_value(*map(floating, args))
        for address, value, width in changes(target, self.magnitude_index, self.wrap_index, self.mode, self.symbols):
            self.put(address, value, width)
        if target == self.symbols['func_15143E64']:
            self.magnitude_index += 1
        else:
            self.wrap_index += 1
        return result

    def previous_index(self, index):
        return self.get(OWNER + 0x25, 1) - 1 if index < 0 else index

    def run(self):
        state = ring.byte_signed(self.get(OWNER + 0x2C, 1))
        payload, records = self.get(OWNER + 0x98), self.get(OWNER + 0x94)
        if state >= 2:
            flags = self.get(OWNER + 0x1E, 2)
            index, total = ring.byte_signed(self.get(OWNER + 0x2E, 1)), 0.
            if flags & 2:
                previous = OWNER + 0x10
            else:
                index = self.previous_index(index - 1)
                previous = records + index * 28
            for _ in range(512):
                index = self.previous_index(index - 1)
                record = records + index * 28
                vector = []
                for axis in range(3):
                    before = self.number(previous + axis * 4)
                    current = self.number(record + axis * 4)
                    vector.append(bits(current - before))
                length = self.scalar_call(self.symbols['func_15143E64'], tuple(vector))
                total = fround(total + length)
                self.put(record + 0x10, bits(length))
                if total > 80.:
                    length = self.number(record + 0x10)
                    if length != 0.:
                        ratio = fround(fround(total - 80.) * divide(1., length))
                        x, y = self.number(record), self.number(record + 4)
                        self.put(record, bits(x - fround(floating(vector[0]) * ratio)))
                        z = self.number(record + 8)
                        self.put(record + 4, bits(y - fround(floating(vector[1]) * ratio)))
                        self.put(record + 8, bits(z - fround(floating(vector[2]) * ratio)))
                        self.put(record + 0x10, bits(length * fround(1. - ratio)))
                    total = 80.
                    goal = ring.byte_signed(self.get(OWNER + 0x2D, 1))
                    for _ in range(256):
                        if index == goal:
                            break
                        self.put(OWNER + 0x2D, goal + 1, 1)
                        goal, count = ring.byte_signed(self.get(OWNER + 0x2D, 1)), self.get(OWNER + 0x25, 1)
                        if goal == count:
                            self.put(OWNER + 0x2D, 0, 1)
                            goal = ring.byte_signed(self.get(OWNER + 0x2D, 1))
                        self.put(OWNER + 0x2C, ring.byte_signed(self.get(OWNER + 0x2C, 1)) - 1, 1)
                    else:
                        raise AssertionError('prune reference domain does not terminate')
                previous = record
                if index == ring.byte_signed(self.get(OWNER + 0x2D, 1)):
                    break
            else:
                raise AssertionError('first reference pass does not terminate')
            state = ring.byte_signed(self.get(OWNER + 0x2C, 1))
        if state >= 2:
            delta, phase = self.number(self.symbols['D_800BE9A4']), self.number(payload + 0x18)
            self.put(payload + 0x18, bits(phase + fround(-41. * delta)))
            upper = self.get(self.symbols['D_800AB2DC'])
            phase = self.get(payload + 0x18)
            value = self.scalar_call(self.symbols['func_15144528'], (phase, upper, bits(-16384.)))
            self.put(payload + 0x18, bits(value))
            distance, index = 0., ring.byte_signed(self.get(OWNER + 0x2E, 1))
            for _ in range(512):
                index = self.previous_index(index - 1)
                record = records + index * 28
                scale, phase = self.number(self.symbols['D_800AB2E0']), self.number(payload + 0x18)
                upper, length = self.get(self.symbols['D_800AB2E4']), self.number(record + 0x10)
                distance = fround(distance + length)
                value = self.scalar_call(self.symbols['func_15144528'],
                    (bits(phase + fround(distance * scale)), upper, bits(-16384.)))
                self.put(record + 0x18, bits(value))
                if index == ring.byte_signed(self.get(OWNER + 0x2D, 1)):
                    break
            else:
                raise AssertionError('phase reference pass does not terminate')
            state = ring.byte_signed(self.get(OWNER + 0x2C, 1))
        if state >= 2:
            start = fround(total * self.number(self.symbols['D_800AB2E8']))
            index = ring.byte_signed(self.get(OWNER + 0x2E, 1))
            width, distance = fround(total - start), 0.
            inverse = divide(1., width)
            for _ in range(512):
                index = self.previous_index(index - 1)
                record = records + index * 28
                value = 60
                if start < distance:
                    fraction = fround(distance - start)
                    if width < fraction:
                        fraction = width
                    value = unsigned_byte(fround(fround(fround(width - fraction) * inverse) * 60.))
                self.put(record + 0x14, value, 1)
                distance = fround(distance + self.number(record + 0x10))
                if index == ring.byte_signed(self.get(OWNER + 0x2D, 1)):
                    break
            else:
                raise AssertionError('fade reference pass does not terminate')
        self.result = 1
        return self


class ExcessCall(RuntimeError):
    pass


class ShapingOracle(AreaOracle):
    def __init__(self, words, memory, mode=0, lengths=None, phase=0, fcsr=0, entry=screen.ENTRY,
                 connected=None, symbols=None, max_calls=None):
        super().__init__(words, memory, (OWNER,), phase=phase, fcsr=fcsr, entry=entry, connected=connected)
        self.mode, self.lengths, self.symbols, self.max_calls = mode, lengths, symbols or screen.SYMBOLS, max_calls
        self.magnitude_index = self.wrap_index = 0
        self.callbacks, self.releases = [], []

    def get(self, address, size):
        assert address % size == 0, ('unaligned read', address, size)
        return super().get(address, size)

    def put(self, address, value, size):
        assert address % size == 0, ('unaligned store', address, size)
        super().put(address, value, size)

    def execute(self, word):
        if word >> 26 == 32:
            CopyOracle.execute(self, word)
        elif word >> 26 == 0 and word & 63 == 38:
            self.r[word >> 11 & 31] = self.r[word >> 21 & 31] ^ self.r[word >> 16 & 31]
        elif word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 in (4, 13):
            value = floating(self.f[word >> 11 & 31])
            self.f[word >> 6 & 31] = bits(math.sqrt(value)) if word & 63 == 4 else (
                math.trunc(value) & 0xFFFFFFFF if math.isfinite(value) and -(2**31) <= value < 2**31 else 0x80000000)
        else:
            super().execute(word)
        self.r[0] = 0

    def record_call(self, target):
        assert self.fcsr == self.initial_fcsr
        if target == screen.ENTRY:
            self.callbacks.append(self.r[4])
            return
        if target == RELEASE:
            self.releases.append(self.r[4])
            return
        if target == self.symbols['func_15143E64']:
            assert STACK - 0x600 <= self.r[4] < STACK
            args = tuple(read(self.memory, self.r[4] + axis * 4) for axis in range(3))
        else:
            assert target == self.symbols['func_15144528'], hex(target)
            args = self.f[12], self.f[14], self.r[6]
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))
        if self.max_calls is not None and len(self.calls) > self.max_calls:
            raise ExcessCall(('excess call', target))

    def hook(self, target):
        if target == RELEASE:
            result = 0.
        elif target == self.symbols['func_15143E64']:
            values = list(map(floating, self.calls[-1][1]))
            squares = [fround(value * value) for value in values]
            result = fround(math.sqrt(fround(fround(squares[0] + squares[1]) + squares[2])))
            if self.lengths is not None:
                result = fround(self.lengths[min(self.magnitude_index, len(self.lengths) - 1)])
        else:
            result = wrap_value(*map(floating, self.calls[-1][1]))
        for address, value, width in changes(target, self.magnitude_index, self.wrap_index, self.mode, self.symbols):
            self.put(address, value, width)
        if target == self.symbols['func_15143E64']:
            self.magnitude_index += 1
        elif target == self.symbols['func_15144528']:
            self.wrap_index += 1
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.f[0] = bits(result)


def source_shapes(root):
    source = (root / SOURCE).read_text()
    baseline = source.replace(screen.SELECTED, screen.ORIGINAL).replace(INSERT, '')
    assert baseline.count(screen.ORIGINAL) == 1
    marker = '/* Non-matching placeholders for the text-only asm slice asm/204660.s. */'
    return baseline, baseline.replace(marker, INSERT + marker).replace(screen.ORIGINAL, screen.SELECTED)


class GameRecordRingShapingRecoveryTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-ring-shaping-test'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>253I', cls.rom, screen.ROM))
        cls.normalized = screen.normalize(cls.words)
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, mode=0, lengths=None, phase=0, fcsr=0, words=None, symbols=None):
        ref = ShapingReference(memory, mode, lengths, symbols)
        complete = ring.outcome(ref)
        models = []
        for body in (self.words if words is None else words, self.normalized, self.retail):
            model = ShapingOracle(body, memory, mode, lengths, phase, fcsr, symbols=symbols)
            self.assertEqual(ring.outcome(model), complete)
            self.assertEqual((ring.public_memory(model), model.calls), (ring.public_memory(ref), ref.calls))
            if complete:
                self.assertEqual(model.r[2], ref.result)
                self.assertEqual(model.fcsr, fcsr)
            models.append(model)
        self.assertEqual(ring.public_events(models[-1]), ref.events)
        self.assertEqual((models[1].memory, models[1].r, models[1].f, models[1].events),
            (models[2].memory, models[2].r, models[2].f, models[2].events))
        return models, complete

    def test_01_complete_profiles_and_exact_guard_closure(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), (253, 0xB8, 70))
        self.assertEqual(self.normalized, self.retail)
        self.assertEqual((self.record['vector_offsets'], self.record['total_spills'], self.record['saved_FP']),
            ([0x98], [0xA8], [24, 22, 20]))
        self.assertNotEqual(self.words, self.retail)
        self.assertEqual((self.record['pool_bytes'], self.record['diagnostics']), (0, ''))
        for index in (0, *(int(row['offset'], 0) // 4 for row in screen.owner_guards())):
            broken = list(self.words)
            broken[index] ^= 1
            with self.assertRaises(AssertionError):
                screen.normalize(broken)
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, profile=p)[0] for p in PROFILES]
        self.receipt('slot', dict(retail_words=253, candidate_words=len(self.words),
            candidate_frame=self.record['frame'], raw_differences=self.record['differences'],
            profiles=profiles, proposed_guards=70, normalized_isolated_exact=True,
            header_and_all_70_expected_words_reject_stale_inputs=True))

    def test_02_live_three_passes_signed_bytes_trim_and_aliases(self):
        seen, cases = set(), 0
        for state, current, goal, flags, spacing, phase in itertools.product((1, 3, 127, 128),
                range(4), range(4), (0, 2), (0., 20., 60.), (0, 8)):
            models, complete = self.compare(fixture(state, current, goal, flags=flags, spacing=spacing), phase=phase)
            self.assertTrue(complete)
            seen.update(models[-1].visits)
            cases += 1
        for byte in range(256):
            for memory in (fixture(state=byte), fixture(current=byte),
                    fixture(count=byte, current=0, goal=255 if byte == 0 else 0), fixture(state=1, goal=byte)):
                models, complete = self.compare(memory, lengths=(0.,), phase=(byte & 1) * 8)
                self.assertTrue(complete)
                seen.update(models[-1].visits)
                cases += 1
        for mode, phase, layout in itertools.product(range(10), (0, 8), range(3)):
            models, complete = self.compare(fixture(layout=layout), mode, lengths=(0.,) if layout else None, phase=phase)
            self.assertTrue(complete)
            seen.update(models[-1].visits)
            cases += 1
        for value in (-20000., -16384., -0., 16383., 20000.):
            models, complete = self.compare(fixture(phase=value))
            self.assertTrue(complete)
            seen.update(models[-1].visits)
            cases += 1
        for factor, phase in itertools.product((0., 1.), (0, 8)):
            memory = fixture(current=3, goal=1)
            put(memory, screen.SYMBOLS['D_800AB2E8'], bits(factor))
            models, complete = self.compare(memory, lengths=(30., -10.), phase=phase)
            self.assertTrue(complete)
            seen.update(models[-1].visits)
            cases += 1
        self.receipt('guest', dict(cases=cases, reached_words=len(seen), missing_words=sorted(
            set(range(screen.ENTRY, screen.ENTRY + 1012, 4)) - seen),
            all_256_state_current_count_bytes_and_inactive_goals=True,
            zero_length_boundaries_prevent_unreachable_prune_goal_domains=True,
            two_stack_phases_ten_mutations_three_buffer_layouts=True,
            controlled_negative_lengths_cover_clamp_and_invalid_unsigned_fade=True,
            raw_normalized_retail_public_memory_calls_return=True, retail_independent_public_trace=True,
            candidate_private_GP_FP_and_raw_trace_identity_not_claimed=True))

    def test_03_required_retail_fault_prefixes_and_lazy_gates(self):
        faults = lazy = 0
        for state, flags in ((1, 2), (3, 0), (3, 2)):
            memory = fixture(state=state, flags=flags)
            ref = ShapingReference(memory).run()
            needed = {event[1] + i for event in ref.events if event[0] != 'CALL' for i in range(event[2])}
            trimmed = {a:v for a,v in memory.items() if not ring.public(a) or a in needed}
            self.assertTrue(self.compare(trimmed)[1])
            lazy += 1
            for address, size in dict.fromkeys((event[1], event[2]) for event in ref.events if event[0] != 'CALL'):
                broken = dict(memory)
                del broken[address + size - 1]
                reference = ShapingReference(broken)
                retail = ShapingOracle(self.retail, broken)
                normalized = ShapingOracle(self.normalized, broken)
                self.assertFalse(ring.outcome(reference))
                self.assertFalse(ring.outcome(retail))
                self.assertFalse(ring.outcome(normalized))
                self.assertEqual((ring.public_memory(retail), ring.public_events(retail), retail.calls),
                    (ring.public_memory(reference), reference.events, reference.calls))
                self.assertEqual((ring.public_memory(normalized), ring.public_events(normalized), normalized.calls),
                    (ring.public_memory(reference), reference.events, reference.calls))
                faults += 1
        self.receipt('faults', dict(required_retail_prefixes=faults, lazy_cases=lazy,
            independent_retail_partial_public_state_and_trace=True,
            raw_C_fault_prefix_private_state_CP0_and_portability_not_claimed=True))

    def test_04_bounded_unsigned_conversion_and_FCSR_preservation(self):
        for left, right in itertools.product((0, 1, 0x80000000, 0xFFFFFFFF), repeat=2):
            model = ShapingOracle([0x03E00008, 0], fixture(state=1))
            model.r[2], model.r[8] = left, right
            model.execute(0x00481826)
            self.assertEqual((model.r[3], model.r[2], model.r[8], model.r[0]), (left ^ right, left, right, 0))
        start, stop = 0x31C, 0x39C
        fragment = self.retail[start // 4:stop // 4] + [0x03E00008, 0]
        values = (0, 1, 0x80000000, bits(-1.), bits(0.5), bits(60.75), bits(2**31 - 128),
            bits(2**31), bits(2**32 - 256), bits(2**32), bits(-2**31),
            0x7F800000, 0xFF800000, 0x7FC12345)
        seen, cases = set(), 0
        for value, fcsr, phase in itertools.product(values, (0, 3, 0x123456), (0, 8)):
            memory = fixture(state=1)
            model = ShapingOracle(fragment, memory, phase=phase, fcsr=fcsr, entry=screen.ENTRY + start)
            model.r[1], model.r[3], model.r[25] = 0x4F000000, RECORDS, 1
            model.f[6] = value
            model.run()
            self.assertEqual((read(model.memory, RECORDS + 0x14, 1), model.fcsr), (unsigned_byte(floating(value)), fcsr))
            seen.update(model.visits)
            cases += 1
        self.receipt('conversion', dict(cases=cases, fragment_retail_words=32, reached_fragment_words=len(seen) - 2,
            missing_fragment_words=sorted(set(range(screen.ENTRY + start, screen.ENTRY + stop, 4)) - seen),
            unsigned_signed_fallback_NaN_Inf_sentinel_branches=True,
            FCSR_sequence_bounded_truncation_and_restore_only=True,
            hardware_flags_rounding_traps_and_NaN_payload_not_modeled=True))

    def test_05_complete_source_forms_and_discriminating_negatives(self):
        samples = [(fixture(state=state, current=current, count=count, goal=goal), mode, lengths)
            for state, current, count, goal, mode, lengths in ((3, 3, 4, 0, 0, None),
                (128, 3, 4, 0, 0, None), (3, 128, 4, 0, 0, (0.,)),
                (3, 0, 0, 255, 0, (0.,)), (3, 0, 128, 0, 0, (0.,)),
                (3, 3, 4, 2, 0, (80.5,)), (3, 3, 4, 0, 2, None),
                (3, 3, 4, 0, 3, None))]
        samples += [(fixture(), mode, None) for mode in range(10)]
        for length in (81.00000762939453, 83.1, 91.99920654296875, 97.3, 123.456, 255.1):
            samples.append((fixture(goal=2), 0, (length,)))
        memory = fixture(current=3, goal=1)
        put(memory, screen.SYMBOLS['D_800AB2E8'], bits(1.))
        samples.append((memory, 0, (30., -10.)))
        records, ordinary, negatives = [], 0, 0
        expected = [ShapingReference(m, mode, lengths).run() for m, mode, lengths in samples]
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, 'control-' + name, body)
            records.append(meta)
            equal = []
            for (memory, mode, lengths), ref in zip(samples, expected):
                model = ShapingOracle(words, memory, mode, lengths, max_calls=len(ref.calls))
                try:
                    complete = ring.outcome(model)
                except ExcessCall as error:
                    self.assertTrue(name.startswith('negative-'), (name, error))
                    self.assertEqual(error.args[0][0], 'excess call', (name, error))
                    complete = False
                equal.append(complete and (ring.public_memory(model), model.calls, model.r[2]) ==
                    (ring.public_memory(ref), ref.calls, ref.result))
            if name.startswith('negative-'):
                self.assertFalse(all(equal), name)
                negatives += 1
            else:
                self.assertTrue(all(equal), name)
                ordinary += len(equal)
        self.receipt('controls', dict(forms=len(records), ordinary_executions=ordinary,
            effective_negatives=negatives, measurements=records,
            excess_call_witness_not_timeout_or_unsupported_instruction=True))

    def test_06_actual_complete_callees_and_consuming_original_dispatcher(self):
        linked, _, _ = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        connected = {}
        for name, offset, count in (('func_15143E64', 0x171314, 12), ('func_15144528', 0x1719D8, 28)):
            words = list(struct.unpack_from('>%dI' % count, self.rom, offset))
            self.assertEqual(linked[name], words)
            connected.update(zip(range(screen.SYMBOLS[name], screen.SYMBOLS[name] + count * 4, 4), words))
        dispatcher = list(struct.unpack_from('>100I', self.rom, 0x174BF0))
        cases = 0
        for state, flags, spacing, phase, parent in itertools.product((1, 3), (0, 2), (0., 20., 60.), (0, 8), (False, True)):
            memory = fixture(state=state, flags=flags, spacing=spacing)
            put(memory, OWNER + 0x1E, flags | 0x10, 2)
            put(memory, OWNER + 0x2F, 0, 1)
            put(memory, OWNER + 0x30, 0, 1)
            put(memory, OWNER + 0x24, 4, 1)
            put(memory, TABLE + 4 * 4, screen.ENTRY)
            ref = ShapingReference(memory).run()
            for body in (self.words, self.normalized, self.retail):
                code = dict(connected)
                code.update(zip(range(screen.ENTRY, screen.ENTRY + len(body) * 4, 4), body))
                model = ShapingOracle(dispatcher if parent else body, memory, phase=phase,
                    entry=DISPATCHER if parent else screen.ENTRY, connected=code).run()
                self.assertEqual((ring.public_memory(model), model.calls), (ring.public_memory(ref), ref.calls))
                if parent:
                    self.assertEqual((model.callbacks, model.releases), ([OWNER], []))
                else:
                    self.assertEqual(model.r[2], 1)
            cases += 1
        self.receipt('connected', dict(cases=cases, executions=cases * 3, actual_magnitude_words=12,
            actual_wrapper_words=28, original_dispatcher_words=100,
            third_table_callback4_true_result_consumed=True,
            first_second_kind_zero_timer_off_player_gate_on=True,
            linked_dispatcher_placeholder_not_restored=True, no_hardware_gameplay_claim=True))

    def test_07_copied_owner_neighbors_and_unchanged_installed_baseline(self):
        objects, diagnostics = [], []
        for name, source in zip(('baseline', 'candidate'), source_shapes(self.root)):
            obj, warnings = compile_owner(self.root, self.out, source, 'owner-' + name)
            processed = self.out / ('owner-' + name + '-processed.o')
            processed.write_bytes(obj.read_bytes())
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(processed.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(processed)
            diagnostics.append(warnings)
        self.assertEqual(diagnostics[0], diagnostics[1])
        old, previous, old_rel = parse_object(objects[0])
        text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), previous.keys())
        for name, fn in current.items():
            before = previous[name]
            if name != screen.FUNCTION:
                self.assertEqual(text[fn['value']:fn['value'] + fn['size']], old[before['value']:before['value'] + before['size']], name)
                self.assertEqual({o - fn['value']: r for o,r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                    {o - before['value']: r for o,r in old_rel.items() if before['value'] <= o < before['value'] + before['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        isolated, _, isolated_rel = parse_object(self.out / 'selected.o')
        target = current[screen.FUNCTION]
        self.assertEqual(text[target['value']:target['value'] + len(self.words) * 4], isolated[:len(self.words) * 4])
        self.assertEqual({o - target['value']: r for o,r in rel.items() if target['value'] <= o < target['value'] + target['size']}, isolated_rel)
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            guards = list(csv.DictReader(stream))
        self.assertIn(len(guards), (11205, 11275))
        proposed = guards[:11205] + screen.owner_guards()
        assert_guard_history(self, proposed)
        for bad in (proposed[:-1], proposed + [dict(proposed[-1])],
                proposed[:11205] + list(reversed(screen.owner_guards()))):
            with self.assertRaises(AssertionError):
                assert_guard_history(self, bad)
        manifest = self.out / 'proposed.csv'

        def write_manifest(rows):
            with manifest.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=guards[0].keys())
                writer.writeheader()
                writer.writerows(rows)

        write_manifest(guards[:11205])
        emit_padded_assembly(objects[0], self.root / 'conker/asm/204660.s',
            word_patches_path=manifest, filename='generated_204660')

        for field, value, message in (('expected', '0xC4240001', 'stale word patch'),
                ('expected_relocations', '-', 'stale relocations'),
                ('expected_relocations', 'R_MIPS_LO16:D_800AB2E0', 'stale relocations'),
                ('expected_relocations', 'R_MIPS_LO16:D_800BE9A4;R_MIPS_LO16:D_800BE9A4', 'stale relocations')):
            broken = [dict(row) for row in proposed]
            row = next(r for r in broken if r['function'] == screen.FUNCTION and int(r['offset'], 0) == 0x1FC)
            row[field] = value
            write_manifest(broken)
            with self.assertRaisesRegex(ValueError, message):
                emit_padded_assembly(objects[1], self.root / 'conker/asm/204660.s',
                    word_patches_path=manifest, filename='generated_204660')
        write_manifest(proposed)
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/204660.s',
            word_patches_path=manifest, filename='generated_204660')
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[end:assembly.find('.type ', end)])
        asm, obj = self.out / 'padded.s', self.out / 'padded.o'
        asm.write_text('.text\n.set noreorder\n.globl %s\n' % screen.FUNCTION + assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        _, functions, relocations = parse_object(obj)
        self.assertEqual((functions[screen.FUNCTION]['size'], relocations), (1012, isolated_rel))
        sites = ((0xF0, 'call', 'func_15143E64'), (0x1F8, 'hi', 'D_800BE9A4'),
            (0x1FC, 'lo', 'D_800BE9A4'), (0x204, 'hi', 'D_800AB2DC'), (0x218, 'lo', 'D_800AB2DC'),
            (0x21C, 'call', 'func_15144528'), (0x248, 'hi', 'D_800AB2E0'), (0x24C, 'lo', 'D_800AB2E0'),
            (0x254, 'hi', 'D_800AB2E4'), (0x258, 'lo', 'D_800AB2E4'), (0x274, 'call', 'func_15144528'),
            (0x298, 'hi', 'D_800AB2E8'), (0x29C, 'lo', 'D_800AB2E8'))
        self.assertEqual(relocations, {offset: [('R_MIPS_' + {'call': '26', 'hi': 'HI16', 'lo': 'LO16'}[kind], symbol)]
            for offset, kind, symbol in sites})
        executions = 0
        boundaries = (0x7FFC, 0x8000, 0xFFF8, 0x80007FFC, 0x80008000, 0xFFFF8000)
        for index, entry in enumerate((screen.ENTRY, 0x10007FFC, 0x7FFF8000, 0x80000000, 0x8FFF7FFC, 0x1FFF8000)):
            symbols = {name: boundaries[(index + k) % 6] + (k + 1) * 0x100000 for k, name in enumerate(GLOBALS)}
            symbols.update(func_15143E64=(entry & 0xF0000000) + 0x108004,
                func_15144528=(entry & 0xF0000000) + 0x108088)
            symbols = {name: value & 0xFFFFFFFF for name, value in symbols.items()}
            script, elf = self.out / 'padded.ld', self.out / ('rebased-%d.elf' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>253I', sections(elf)['.text'][1]))
            expected = list(self.retail)
            for offset, kind, symbol in sites:
                value = symbols[symbol]
                cursor = offset // 4
                expected[cursor] = (expected[cursor] & (0xFC000000 if kind == 'call' else 0xFFFF0000)) | (
                    (value >> 2) & 0x3FFFFFF if kind == 'call' else
                    ((value + 0x8000) >> 16) & 65535 if kind == 'hi' else value & 65535)
            self.assertEqual(words, expected)
            for flags, mode, phase in itertools.product((0, 2), range(10), (0, 8)):
                memory = fixture(flags=flags, symbols=symbols)
                ref = ShapingReference(memory, mode, symbols=symbols).run()
                model = ShapingOracle(words, memory, mode, phase=phase, entry=entry, symbols=symbols).run()
                self.assertEqual((ring.public_memory(model), ring.public_events(model), model.calls, model.r[2]),
                    (ring.public_memory(ref), ref.events, ref.calls, ref.result))
                executions += 1
        baseline = json.loads((self.root / 'conker/build/game-record-ring-sampling-test/after.json').read_text())
        linked, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        slots = {name: dict(address=addresses[name], words=len(words),
            sha256=hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()) for name, words in linked.items()}
        self.assertEqual(slots, baseline['slots'])
        self.assertEqual(linked[screen.FUNCTION], self.retail)
        protected = {name: dict(address=address, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            for name, (address, data) in sections(self.root / 'conker/build/conker.us.elf').items()
            if name in ('.init', '.init_data', '.debugger', '.game_data')}
        self.assertEqual(protected, baseline['protected'])
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            guards = list(csv.DictReader(stream))
        assert_guard_history(self, guards)
        self.assertEqual(guards[:11205], baseline['guards'])
        source = (self.root / SOURCE).read_text()
        installed = screen.SELECTED in source
        self.assertIn(source, source_shapes(self.root))
        self.assertEqual(guards[11205:], screen.owner_guards() if installed else [])
        if not installed:
            self.assertEqual(hashlib.sha256((self.root / 'conker/progress.csv').read_bytes()).hexdigest(), baseline['progress_sha256'])
        with (self.root / 'conker/progress.csv').open() as stream:
            progress = [row for row in csv.DictReader(stream) if row['function'] == screen.FUNCTION]
        self.assertEqual([(row['language'], row['length']) for row in progress], [('c' if installed else 'asm', '1012')])
        found = [struct.unpack_from('>I', data, TABLE + 16 - address)[0] for address, data in
            sections(self.root / 'conker/build/conker.us.elf').values() if address <= TABLE + 16 < address + len(data)]
        self.assertEqual(found, [screen.ENTRY])
        self.receipt('owner', dict(compact_neighbors=len(current) - 1, warning_count=len(diagnostics[0]),
            isolated_copied_candidate_identical=True, pools_relative_relocations_unchanged=True,
            all_6058_installed_bodies_addresses_extents_unchanged=True, guards=len(guards),
            protected_sections_unchanged=True, live_source_installed=installed,
            real_padder_full_extent_1012_no_padding_identical_relocations=True,
            proposed_guards=70, independent_links=6, independently_expected_sites=13,
            rebased_executions=executions, stale_word_and_relocation_rejections=4,
            live_linked_target_callback4_exact=True))

    def test_08_native32_live_fields_unsigned_flags_and_full_canaries(self):
        self.fixture = NATIVE_PREFIX + screen.DECLARATIONS + screen.SELECTED + NATIVE_CHECK
        for start in range(0, 256, 32):
            self.run_host('unsigned cur,count,goal;\n'
                'for(cur=%d;cur<%d;cur++)for(count=0;count<256;count++){' % (start, start + 32) +
                'goal=!count&&signbyte(cur)<=0?255:0;if(check(3,cur,goal,count,2,0.0f,0,0))return 11;}')
        self.run_host('unsigned flag,state,cur,goal,layout,mode;\n'
            'for(flag=0;flag<65536;flag++)if(check(3,3,0,4,flag,5.0f,0,0))return 12;\n'
            'for(state=0;state<256;state++)for(cur=0;cur<4;cur++)for(goal=0;goal<4;goal++)for(flag=0;flag<2;flag++)'
            'for(layout=0;layout<3;layout++)if(check(state,cur,goal,4,flag*2,0.0f,0,layout))return 13;\n'
            'for(goal=0;goal<256;goal++)if(check(1,3,goal,4,2,5.0f,0,0))return 14;\n'
            'for(mode=0;mode<10;mode++)for(layout=0;layout<3;layout++)for(flag=0;flag<2;flag++)'
            'if(check(127,3,0,4,flag*2,layout?0.0f:90.0f,mode,layout))return 15;')
        self.receipt('native', dict(cases=65536 + 65536 + 256 * 4 * 4 * 2 * 3 + 256 + 60,
            all_current_count_pairs_all_65536_flag_words_all_state_bytes_inactive_goals=True,
            ten_live_mutations_three_buffer_layouts=True, canary_bytes=16384,
            actual_C_volatile_typed_call_independent_numeric_reference_memory_and_args=True,
            invalid_unsigned_float_casts_hardware_FCSR_and_nontermination_not_claimed=True))


NATIVE_PREFIX = r'''
typedef signed char s8;typedef unsigned char u8;typedef unsigned short u16;
typedef int s32;typedef unsigned int u32;typedef float f32;
f32 D_800BE9A4,D_800AB2DC,D_800AB2E0,D_800AB2E4,D_800AB2E8;
static u8 arena[16384] __attribute__((aligned(16))),expected[16384] __attribute__((aligned(16)));
static u32 args[1024][4],globals[5];static unsigned used,total,error,mutation,magCalls,wrapCalls;
static f32 lengthValue;
enum{OWN=32,PAY=224,ALT_PAY=384,BUF=1024,ALT_BUF=9216};
static u32 tobits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 frombits(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static int signbyte(unsigned value){return value<128?(int)value:(int)value-256;}
static f32 plus(f32 a,f32 b){volatile f32 value=a+b;return value;}
static f32 minus(f32 a,f32 b){volatile f32 value=a-b;return value;}
static f32 times(f32 a,f32 b){volatile f32 value=a*b;return value;}
static f32 quotient(f32 a,f32 b){volatile f32 value=a/b;return value;}
static f32 number(u8 *bytes,unsigned offset){return *(f32 *)(bytes+offset);}
static void store(u8 *bytes,unsigned offset,f32 value){*(f32 *)(bytes+offset)=value;}
static void effect(u8 *bytes,unsigned kind,unsigned index,u32 *g){
 if(!kind&&!index){
  if(mutation==1)bytes[OWN+0x2D]=1;
  if(mutation==2)bytes[OWN+0x2C]=1;
  if(mutation==3)*(u8 **)(bytes+OWN+0x94)=arena+ALT_BUF;
  if(mutation==4)*(u8 **)(bytes+OWN+0x98)=arena+ALT_PAY;
  if(mutation==5)g[0]=tobits(2.0f);
 }
 if(kind){
  if(!index){
   if(mutation==6)g[2]=tobits(80.0f);
   if(mutation==7)bytes[OWN+0x2C]=1;
   if(mutation==9)bytes[OWN+0x2E]=1;
  }
  if(index==1&&mutation==8)store(bytes,PAY+0x18,100.0f);
 }
}
static f32 wrapped(f32 value,f32 upper,f32 lower){
 f32 range=minus(upper,lower);unsigned limit=0;
 while(upper<value){value=minus(value,range);if(++limit>64){error=1;return 0.0f;}}
 while(value<lower){value=plus(value,range);if(++limit>128){error=1;return 0.0f;}}
 return value;
}
static f32 expected_call(unsigned kind,f32 a,f32 b,f32 c){
 f32 result=kind?wrapped(a,b,c):lengthValue;unsigned index=kind?wrapCalls++:magCalls++;
 if(total>=1024){error=1;return 0.0f;}
 args[total][0]=kind;args[total][1]=tobits(a);args[total][2]=tobits(b);args[total++][3]=tobits(c);
 effect(expected,kind,index,globals);return result;
}
static f32 actual_call(unsigned kind,f32 a,f32 b,f32 c){
 u32 g[5];unsigned index=kind?wrapCalls++:magCalls++;
 if(used>=total||args[used][0]!=kind||args[used][1]!=tobits(a)||args[used][2]!=tobits(b)||args[used][3]!=tobits(c)){
  error=1;return 0.0f;
 }
 used++;g[0]=tobits(D_800BE9A4);g[1]=tobits(D_800AB2DC);g[2]=tobits(D_800AB2E0);g[3]=tobits(D_800AB2E4);g[4]=tobits(D_800AB2E8);
 effect(arena,kind,index,g);D_800BE9A4=frombits(g[0]);D_800AB2DC=frombits(g[1]);D_800AB2E0=frombits(g[2]);D_800AB2E4=frombits(g[3]);D_800AB2E8=frombits(g[4]);
 return kind?wrapped(a,b,c):lengthValue;
}
f32 func_15143E64(f32 *vector){return actual_call(0,vector[0],vector[1],vector[2]);}
f32 func_15144528(f32 value,f32 upper,f32 lower){return actual_call(1,value,upper,lower);}
'''

NATIVE_CHECK = r'''
static int back(int index){return index<0?(int)expected[OWN+0x25]-1:index;}
static int reference(void){
 unsigned buffer=(u32)*(u8 **)(expected+OWN+0x94)-(u32)arena;
 unsigned payload=(u32)*(u8 **)(expected+OWN+0x98)-(u32)arena;
 int state=signbyte(expected[OWN+0x2C]),index,goal;unsigned point,previous,i,limit;
 f32 vector[3],sum=0.0f,length,ratio,distance,start,width,inverse,difference,value;
 if(state>=2){
  index=signbyte(expected[OWN+0x2E]);
  if(*(u16 *)(expected+OWN+0x1E)&2)previous=OWN+0x10;
  else{index=back(index-1);previous=buffer+(unsigned)(index*28);}
  limit=0;
  do{
   index=back(index-1);point=buffer+(unsigned)(index*28);
   if(point+28>16384||previous+12>16384||++limit>512)return 1;
   for(i=0;i<3;i++)vector[i]=minus(number(expected,point+i*4),number(expected,previous+i*4));
   length=expected_call(0,vector[0],vector[1],vector[2]);sum=plus(sum,length);store(expected,point+16,length);
   if(sum>80.0f){
    length=number(expected,point+16);
    if(length!=0.0f){
     ratio=times(minus(sum,80.0f),quotient(1.0f,length));
     for(i=0;i<3;i++)store(expected,point+i*4,minus(number(expected,point+i*4),times(vector[i],ratio)));
     store(expected,point+16,times(length,minus(1.0f,ratio)));
    }
    sum=80.0f;goal=signbyte(expected[OWN+0x2D]);
    for(i=0;index!=goal;i++){
     if(i>=256)return 2;
     expected[OWN+0x2D]=(u8)(goal+1);goal=signbyte(expected[OWN+0x2D]);
     if(goal==expected[OWN+0x25]){expected[OWN+0x2D]=0;goal=0;}
     expected[OWN+0x2C]=(u8)(expected[OWN+0x2C]-1);
    }
   }
   previous=point;
  }while(index!=signbyte(expected[OWN+0x2D]));
  state=signbyte(expected[OWN+0x2C]);
 }
 if(state>=2){
  store(expected,payload+24,plus(number(expected,payload+24),times(-41.0f,frombits(globals[0]))));
  value=expected_call(1,number(expected,payload+24),frombits(globals[1]),-16384.0f);store(expected,payload+24,value);
  index=signbyte(expected[OWN+0x2E]);distance=0.0f;limit=0;
  do{
   index=back(index-1);point=buffer+(unsigned)(index*28);if(point+28>16384||++limit>512)return 3;
   distance=plus(distance,number(expected,point+16));
   value=expected_call(1,plus(number(expected,payload+24),times(distance,frombits(globals[2]))),frombits(globals[3]),-16384.0f);
   store(expected,point+24,value);
  }while(index!=signbyte(expected[OWN+0x2D]));
  state=signbyte(expected[OWN+0x2C]);
 }
 if(state>=2){
  start=times(sum,frombits(globals[4]));width=minus(sum,start);inverse=quotient(1.0f,width);
  distance=0.0f;index=signbyte(expected[OWN+0x2E]);limit=0;
  do{
   index=back(index-1);point=buffer+(unsigned)(index*28);if(point+28>16384||++limit>512)return 4;
   value=60.0f;
   if(start<distance){difference=minus(distance,start);if(width<difference)difference=width;
    value=times(times(minus(width,difference),inverse),60.0f);if(!(value>=0.0f&&value<4294967296.0f))return 5;
   }
   expected[point+20]=(u8)(u32)value;distance=plus(distance,number(expected,point+16));
  }while(index!=signbyte(expected[OWN+0x2D]));
 }
 return error?6:0;
}
static int check(unsigned state,unsigned cursor,unsigned goal,unsigned count,unsigned flag,f32 magnitude,unsigned mode,unsigned layout){
 unsigned i,field,base,buffer=layout==1?PAY:layout==2?OWN+0x40:BUF;int index;
 u32 actual[5];s32 (*volatile invoke)(u8 *)=func_151D7CD0;
 if(sizeof(void*)!=4||sizeof(ShapingRecord151D7CD0)!=28)return 1;
 for(i=0;i<16384;i++)arena[i]=(u8)(i*17+0xA5);
 for(base=0;base<3;base++)for(index=-1;index<256;index++)for(field=0;field<7;field++){
  unsigned position=(base==0?buffer:base==1?BUF:ALT_BUF)+(unsigned)(index*28)+field*4;
  store(arena,position,field==0?(f32)(index*20):0.0f);
 }
 arena[OWN+0x2C]=(u8)state;arena[OWN+0x2E]=(u8)cursor;arena[OWN+0x2D]=(u8)goal;arena[OWN+0x25]=(u8)count;
 *(u16 *)(arena+OWN+0x1E)=(u16)flag;*(u8 **)(arena+OWN+0x94)=arena+buffer;*(u8 **)(arena+OWN+0x98)=arena+PAY;
 store(arena,PAY+24,0.0f);store(arena,ALT_PAY+24,100.0f);
 store(arena,OWN+0x10,80.0f);store(arena,OWN+0x14,0.0f);store(arena,OWN+0x18,0.0f);
 globals[0]=0x3F800000;globals[1]=0x467FFC00;globals[2]=0x423B851E;globals[3]=0x467FFC00;globals[4]=0x3E991688;
 D_800BE9A4=frombits(globals[0]);D_800AB2DC=frombits(globals[1]);D_800AB2E0=frombits(globals[2]);D_800AB2E4=frombits(globals[3]);D_800AB2E8=frombits(globals[4]);
 for(i=0;i<16384;i++)expected[i]=arena[i];
 used=total=error=magCalls=wrapCalls=0;mutation=mode;lengthValue=magnitude;
 if(reference())return 2;
 magCalls=wrapCalls=0;
 if(invoke(arena+OWN)!=1||used!=total||error)return 3;
 actual[0]=tobits(D_800BE9A4);actual[1]=tobits(D_800AB2DC);actual[2]=tobits(D_800AB2E0);actual[3]=tobits(D_800AB2E4);actual[4]=tobits(D_800AB2E8);
 for(i=0;i<5;i++)if(actual[i]!=globals[i])return 4;
 for(i=0;i<16384;i++)if(arena[i]!=expected[i])return 5;
 return 0;
}
'''
