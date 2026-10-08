"""Uninstalled full shaping recovery; bounded numeric/FCSR evidence, not a match."""

import csv
import hashlib
import itertools
import json
import math
import struct
import subprocess
import sys
import unittest
from pathlib import Path

from tools.experiments import game_record_ring_shaping_candidates as screen
from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_record_ring_update_match as ring
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
    assert source.count(screen.ORIGINAL) == 1 and screen.SELECTED not in source
    marker = '/* Non-matching placeholders for the text-only asm slice asm/204660.s. */'
    additions = screen.DECLARATIONS.replace('extern f32 D_800BE9A4;\n', '') + '\n'
    return source, source.replace(marker, additions + marker).replace(screen.ORIGINAL, screen.SELECTED)


class GameRecordRingShapingRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-ring-shaping-test'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>253I', cls.rom, screen.ROM))

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, mode=0, lengths=None, phase=0, fcsr=0, words=None, symbols=None):
        ref = ShapingReference(memory, mode, lengths, symbols)
        complete = ring.outcome(ref)
        models = []
        for body in (self.words if words is None else words, self.retail):
            model = ShapingOracle(body, memory, mode, lengths, phase, fcsr, symbols=symbols)
            self.assertEqual(ring.outcome(model), complete)
            self.assertEqual((ring.public_memory(model), model.calls), (ring.public_memory(ref), ref.calls))
            if complete:
                self.assertEqual(model.r[2], ref.result)
                self.assertEqual(model.fcsr, fcsr)
            models.append(model)
        self.assertEqual(ring.public_events(models[-1]), ref.events)
        return models, complete

    def test_01_complete_profiles_and_explicit_uninstalled_boundary(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), (256, 0x98, 253))
        self.assertNotEqual(self.words, self.retail)
        self.assertEqual((self.record['pool_bytes'], self.record['diagnostics']), (0, ''))
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, profile=p)[0] for p in PROFILES]
        self.receipt('slot', dict(retail_words=253, candidate_words=len(self.words),
            candidate_frame=self.record['frame'], raw_differences=self.record['differences'],
            profiles=profiles, candidate_only=True, guards_added=0, no_match_claim=True))

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
            raw_C_public_memory_calls_return=True, retail_independent_public_trace=True,
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
                self.assertFalse(ring.outcome(reference))
                self.assertFalse(ring.outcome(retail))
                self.assertEqual((ring.public_memory(retail), ring.public_events(retail), retail.calls),
                    (ring.public_memory(reference), reference.events, reference.calls))
                faults += 1
        self.receipt('faults', dict(required_retail_prefixes=faults, lazy_cases=lazy,
            independent_retail_partial_public_state_and_trace=True,
            raw_C_fault_prefix_private_state_CP0_and_portability_not_claimed=True))

    def test_04_bounded_unsigned_conversion_and_FCSR_preservation(self):
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
            for body in (self.words, self.retail):
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
        self.receipt('connected', dict(cases=cases, executions=cases * 2, actual_magnitude_words=12,
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
        options = dict(word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_204660')
        emit_padded_assembly(objects[0], self.root / 'conker/asm/204660.s', **options)
        with self.assertRaisesRegex(ValueError, r'patched func_151D7CD0 is 0x400 bytes but its retail span is only 0x3F4'):
            emit_padded_assembly(objects[1], self.root / 'conker/asm/204660.s', **options)
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
        self.assertEqual(guards, baseline['guards'])
        self.assertEqual(hashlib.sha256((self.root / 'conker/progress.csv').read_bytes()).hexdigest(), baseline['progress_sha256'])
        found = [struct.unpack_from('>I', data, TABLE + 16 - address)[0] for address, data in
            sections(self.root / 'conker/build/conker.us.elf').values() if address <= TABLE + 16 < address + len(data)]
        self.assertEqual(found, [screen.ENTRY])
        self.receipt('owner', dict(compact_neighbors=len(current) - 1, warning_count=len(diagnostics[0]),
            isolated_copied_candidate_identical=True, pools_relative_relocations_unchanged=True,
            all_6058_installed_bodies_addresses_extents_unchanged=True, guards=len(guards),
            protected_sections_unchanged=True, progress_unchanged=True, target_still_original_assembly=True,
            real_padder_baseline_accepted_candidate_oversize_rejected=True,
            native32_independent_rebases_and_installation_pending=True))
