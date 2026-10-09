"""Uninstalled full ribbon recovery; setup callees remain bounded interfaces."""

import csv
import hashlib
import itertools
import json
import math
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_record_ring_renderer_candidates as screen
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests import test_game_random_curve_record as native

OWNER, RECORDS, PAYLOAD, ALTERNATE = 0x20000, 0x28000, 0x21000, 0x30000
VERTICES, OUTPUT = 0x60000, 0x70000
BACKEND, TEXTURE, GEOMETRY, COMBINE, MODE, COPY = (screen.SYMBOLS[n] for n in
    ('func_151D5D60', 'func_15142E24', 'func_15142B7C', 'func_1513F4E4', 'func_15142FBC', 'memcpy'))
TARGET_NAMES = {screen.SYMBOLS[name]: name for name in
    ('func_151D5D60', 'func_15142E24', 'func_15142B7C', 'func_1513F4E4', 'func_15142FBC', 'memcpy')}
DISPATCHER, TRANSFORM, RELEASE, TABLE, ALLOCATE = 0x15147C4C, 0x151462C8, 0x1516972C, 0x8008A2A4, 0x10003C40
SOURCE = 'conker/src/game/generated_204660.c'


def narrow(value, width):
    mask = (1 << width) - 1
    value &= mask
    return value - mask - 1 if value & (1 << (width - 1)) else value


def external(memory):
    return {a: v for a, v in memory.items() if not STACK - 0x600 <= a < STACK + 0x140}


def writes(model):
    return [e for e in model.events if e[0] == 'W' and not STACK - 0x600 <= e[1] < STACK + 0x140]


def rounded(value):
    return floating(bits(value))


def fixture(state=3, current=3, goal=0, count=4, flags=2, opacity=19, view=0, pattern=0, symbols=None):
    symbols = screen.SYMBOLS if symbols is None else symbols
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    for base, length in ((OWNER, 0x200), (PAYLOAD, 0x100), (VERTICES, 17000), (OUTPUT, 7000)):
        memory.update({base + i: (i * 17 + 13) & 255 for i in range(-16, length)})
    for base in (RECORDS, ALTERNATE):
        for index in range(-1, 256):
            for offset in range(28):
                memory[base + index * 28 + offset] = (index + offset * 17 + 13) & 255
            for axis, value in enumerate((index * 3.25 - 100., -2.75, index * -4.5 + 50.)):
                put(memory, base + index * 28 + axis * 4, bits(value + (10. if base == ALTERNATE else 0.)))
            put(memory, base + index * 28 + 0x14, (index * 61 + 255) & 255, 1)
            phase = index * 2500.25 - 10000. if pattern == 0 else -index * 1000.5 if pattern == 1 else 0.
            put(memory, base + index * 28 + 0x18, bits(phase))
    for offset, value in zip((0x10, 0x14, 0x18), (12.75, -3.5, -22.25)):
        put(memory, OWNER + offset, bits(value))
    for offset, value, width in ((0x2C, state, 1), (0x2E, current, 1), (0x2D, goal, 1),
        (0x25, count, 1), (0x1E, flags, 2), (0x1C, opacity, 2), (0x31, 16, 1),
        (0x94, RECORDS, 4), (0x98, PAYLOAD, 4)):
        put(memory, OWNER + offset, value, width)
    put(memory, PAYLOAD + 0x18, bits(12500.5))
    put(memory, symbols['D_800D2C9C'], 0xAA551234)
    for index, value in enumerate((0xFFFF0000, 0xABCDEF01, 0x00112233, 0x44008800)):
        put(memory, symbols['D_800A4AC8'] + index * 4, value)
        put(memory, symbols['D_800DD1E8'] + index * 4, bits(0.25))
        put(memory, symbols['D_800DD1D8'] + index * 4, bits(-0.75))
    put(memory, symbols['D_800DD1E8'] + narrow(view, 16) * 4, bits(0.25))
    put(memory, symbols['D_800DD1D8'] + narrow(view, 16) * 4, bits(-0.75))
    return memory


def mutations(target, mode, copies, symbols=None):
    symbols = screen.SYMBOLS if symbols is None else symbols
    if target == MODE:
        return {1: [(OWNER + 0x94, ALTERNATE, 4)], 2: [(OWNER + 0x98, ALTERNATE, 4)],
            3: [(OWNER + 0x2E, 1, 1)], 4: [(OWNER + 0x1E, 10, 2)],
            5: [(OWNER + 0x1C, -32768, 2)], 6: [(OWNER + 0x2C, 0, 1)]}.get(mode, [])
    if target == COPY and copies == 0:
        return {7: [(OWNER + 0x94, ALTERNATE, 4)], 8: [(OWNER + 0x2D, 1, 1)],
            9: [(OWNER + 0x1E, 0, 2), (OWNER + 0x1C, 0, 2)],
            10: [(symbols['D_800DD1E8'], bits(100.), 4)],
            11: [(RECORDS + 28 + 0x18, bits(15000.), 4)]}.get(mode, [])
    return []


class RibbonReference:
    def __init__(self, memory, view=0, success=True, mode=0, start=VERTICES, symbols=None, output=OUTPUT):
        self.memory, self.view, self.success, self.mode, self.start = dict(memory), narrow(view, 16), success, mode, start
        self.symbols = screen.SYMBOLS if symbols is None else symbols
        self.output = output
        self.calls, self.events, self.copies, self.segments = [], [], 0, 0

    def get(self, address, width=4):
        value = read(self.memory, address & 0xFFFFFFFF, width)
        self.events.append(('R', address & 0xFFFFFFFF, width, value))
        return value

    def number(self, address):
        return floating(self.get(address))

    def store(self, address, value, width=4):
        address &= 0xFFFFFFFF
        put(self.memory, address, value, width)
        self.events.append(('W', address, width, value & ((1 << (width * 8)) - 1)))

    def call(self, target, args):
        self.calls.append((self.symbols[TARGET_NAMES[target]], args))
        if target != COPY:
            for address, value, width in mutations(target, self.mode, self.copies, self.symbols):
                self.store(address, value, width)

    def pair(self, position, phase, alpha):
        for side in (1, -1):
            values = (math.trunc(rounded(position[0] + rounded(self.x * side))),
                math.trunc(position[1]), math.trunc(rounded(position[2] - rounded(self.z * side))))
            for axis, value in enumerate(values):
                self.store(self.cursor + axis * 2, value, 2)
            self.store(self.cursor + 8, math.trunc(phase), 2)
            self.store(self.cursor + 10, 0x800 if side == 1 else 0, 2)
            for channel in range(3):
                self.store(self.cursor + 12 + channel, 255, 1)
            self.store(self.cursor + 15, (alpha * self.factor) >> 8, 1)
            self.store(self.cursor + 6, 0, 2)
            self.cursor += 16

    def previous(self, index):
        return self.get(OWNER + 0x25, 1) - 1 if index < 0 else index

    def run(self):
        self.result = self.output
        if narrow(self.get(OWNER + 0x2C, 1), 8) < 2:
            return self
        count = self.get(OWNER + 0x25, 1)
        records, payload = self.get(OWNER + 0x94), self.get(OWNER + 0x98)
        self.call(BACKEND, (OWNER + 0x84, self.view & 0xFFFFFFFF, count * 32 + 160, 'cursor', 0))
        if not self.success:
            return self
        self.call(TEXTURE, (self.output, self.symbols['D_80090CD4'], 0, 0, 0, 0, 31, 0, 0, 'sync', 62))
        self.call(GEOMETRY, (self.output + 8, 0x200005, 0x1F0600))
        self.call(COMBINE, (self.output + 16, 0x4C, 'sync'))
        blend = self.get(self.symbols['D_800D2C9C']) | 0x80000 | 0x2CA0
        other = self.get(self.symbols['D_800A4AC8'] + 12) | self.get(self.symbols['D_800A4AC8'] + 8)
        self.call(MODE, (self.output + 24, blend, other, 'sync'))
        self.result = self.output + 32
        if self.get(OWNER + 0x1E, 2) & 2:
            index = self.previous(narrow(self.get(OWNER + 0x2E, 1), 8) - 1)
            previous = [self.number(OWNER + 0x10 + i * 4) for i in range(3)]
            previous_alpha, previous_phase = 0, self.number(payload + 0x18)
        else:
            prior = self.previous(narrow(self.get(OWNER + 0x2E, 1), 8) - 1)
            index = self.previous(prior - 1)
            previous = [self.number(records + prior * 28 + i * 4) for i in range(3)]
            previous_alpha = self.get(records + prior * 28 + 0x14, 1)
            previous_phase = self.number(records + prior * 28 + 0x18)
        point = records + index * 28
        current = [self.number(point + i * 4) for i in range(3)]
        self.x = rounded(self.number(self.symbols['D_800DD1E8'] + self.view * 4) * 5.5)
        self.z = rounded(self.number(self.symbols['D_800DD1D8'] + self.view * 4) * 5.5)
        self.factor = ((narrow(self.get(OWNER + 0x1C, 2), 16) * 12) & 255) if self.get(OWNER + 0x1E, 2) & 8 else 255
        alpha, phase = self.get(point + 0x14, 1), self.number(point + 0x18)
        self.cursor = self.start
        self.pair(previous, previous_phase, previous_alpha)
        for _ in range(256):
            self.pair(current, phase, alpha)
            for word, value in ((0x01004008, self.cursor - 64), (0x05000204, 0), (0x05020604, 0)):
                self.store(self.result, word); self.store(self.result + 4, value); self.result += 8
            self.segments += 1
            if phase < previous_phase:
                self.call(COPY, (self.cursor, self.cursor - 32, 32))
                snapshot = [self.get(self.cursor - 32 + i, 1) for i in range(32)]
                for i, value in enumerate(snapshot):
                    self.store(self.cursor + i, value, 1)
                for address, value, width in mutations(COPY, self.mode, self.copies, self.symbols):
                    self.store(address, value, width)
                self.copies += 1
                self.store(self.cursor - 24, narrow(self.get(self.cursor - 24, 2), 16) - 0x8000, 2)
                self.cursor += 16
                self.store(self.cursor - 24, narrow(self.get(self.cursor - 24, 2), 16) - 0x8000, 2)
                self.cursor += 16
            prior, index = index, index - 1
            point -= 28
            if index < 0:
                index = self.get(OWNER + 0x25, 1) - 1
                point = records + index * 28
            current = [self.number(point + i * 4) for i in range(3)]
            goal = narrow(self.get(OWNER + 0x2D, 1), 8)
            alpha = self.get(point + 0x14, 1)
            previous_phase, phase = self.number(records + prior * 28 + 0x18), self.number(point + 0x18)
            if prior == goal:
                return self
        raise AssertionError('reference ring domain does not terminate')


class RibbonOracle(AreaOracle):
    def __init__(self, words, memory, view=0, success=True, mode=0, phase=0, start=VERTICES,
                 connected=None, entry=screen.ENTRY, args=None, symbols=None):
        super().__init__(words, memory, args or (OWNER, OUTPUT, view), phase=phase, entry=entry, connected=connected)
        self.view, self.success, self.mode, self.start = narrow(view, 16), success, mode, start
        self.copies, self.forwarded, self.setup = 0, [], []
        self.symbols = screen.SYMBOLS if symbols is None else symbols
        self.targets = {self.symbols[name]: target for target, name in TARGET_NAMES.items()}

    def execute(self, word):
        if word >> 26 == 32:
            CopyOracle.execute(self, word)
        elif word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 13:
            value = floating(self.f[word >> 11 & 31])
            self.f[word >> 6 & 31] = math.trunc(value) & 0xFFFFFFFF if math.isfinite(value) and -(2**31) <= value < 2**31 else 0x80000000
        else:
            super().execute(word)
        self.r[0] = 0

    def record_call(self, target):
        actual_target, target = target, self.targets.get(target, target)
        if target == screen.ENTRY:
            self.forwarded.append(self.arguments(3)); return
        if target == TRANSFORM:
            self.setup.append(self.arguments(9)); return
        if target == ALLOCATE:
            self.alloc_args = self.arguments(4); return
        counts = {BACKEND: 5, TEXTURE: 11, GEOMETRY: 3, COMBINE: 3, MODE: 4, COPY: 3}
        assert target in counts, ('unexpected callee', hex(target))
        args = list(self.arguments(counts[target]))
        if target == BACKEND:
            self.cursor_slot = args[3]
            args[3] = 'cursor'
        elif target in (TEXTURE, COMBINE, MODE):
            index = {TEXTURE: 9, COMBINE: 2, MODE: 3}[target]
            sync = args[index]
            assert STACK - 0x600 <= sync < STACK
            assert self.get(sync, 1) == (1 if target == TEXTURE else 0)
            args[index] = 'sync'
            self.sync_slot = sync
        self.calls.append((actual_target, tuple(args)))

    def hook(self, target):
        target = self.targets.get(target, target)
        result = self.r[4]
        if target == BACKEND:
            self.put(self.cursor_slot, self.start if self.success else 0, 4)
        elif target in (TEXTURE, GEOMETRY, COMBINE, MODE, TRANSFORM):
            result += 8
            if target in (TEXTURE, COMBINE, MODE):
                self.put(self.sync_slot, 0, 1)
        elif target == ALLOCATE:
            result = self.start if self.success else 0
        else:
            assert target == COPY
            destination, source, length = self.arguments(3)
            assert length == 32
            snapshot = [self.get(source + i, 1) for i in range(length)]
            for i, value in enumerate(snapshot):
                self.put(destination + i, value, 1)
        for address, value, width in mutations(target, self.mode, self.copies, self.symbols):
            self.put(address, value, width)
        self.copies += target == COPY
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result


class GameRecordRingRendererRecoveryTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host
    FORM, body, expected_shape = 'selected', screen.SELECTED, (405, 0xE0, 319)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-ring-renderer-test'
        if hasattr(cls, 'OUT_NAME'):
            cls.out /= cls.OUT_NAME
        elif cls.FORM != 'selected':
            cls.out /= 'fitted'
        cls.out.mkdir(parents=True, exist_ok=True)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected', cls.body)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>%dI' % screen.WORDS, cls.rom, screen.ROM))
        cls.directory = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, view=0, success=True, mode=0, phase=0, words=None, write_order=True):
        reference = RibbonReference(memory, view, success, mode).run()
        models = []
        for body in (self.words if words is None else words, self.retail):
            model = RibbonOracle(body, memory, view, success, mode, phase).run()
            self.assertEqual(external(model.memory), external(reference.memory))
            self.assertEqual(model.calls, reference.calls)
            self.assertEqual(model.r[2], reference.result)
            if write_order:
                self.assertEqual(writes(model), [e for e in reference.events if e[0] == 'W'])
            models.append(model)
        return reference, models

    def test_complete_candidate_uninstalled_and_guard_history_unchanged(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), self.expected_shape)
        self.assertEqual((self.record['diagnostics'], self.record['saved_FP'], self.record['pool_bytes']), ('', [22, 20], 0))
        source = (self.root / SOURCE).read_text()
        self.assertEqual(source.count(screen.ORIGINAL), 1)
        self.assertNotIn(self.body, source)
        production = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')[0]
        self.assertEqual(production[screen.FUNCTION], self.retail)
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 11275)
        self.assertFalse(any(row['function'] == screen.FUNCTION for row in rows))
        digest = assert_guard_history(self, rows)
        self.receipt('status', dict(installed=False, candidate_words=self.record['body_words'], retail_words=405,
            candidate_frame=self.record['frame'], retail_frame=208, raw_differences=self.record['differences'],
            guard_rows=len(rows), guard_sha256=digest, form=self.FORM))

    def test_guest_full_footprints_calls_vertices_phase_wrap_and_lifetimes(self):
        coverage, count = [set(), set()], 0
        for flags, pattern, view, phase, opacity in itertools.product((0, 2, 8, 10), range(3),
                (0, 1, 3, 0x8000, 0xFFFF, 0x12340002), (0, 8), (-32768, -1, 0, 19, 32767)):
            ref, models = self.compare(fixture(flags=flags, pattern=pattern, opacity=opacity, view=view), view, phase=phase)
            for visited, model in zip(coverage, models):
                visited.update(model.visits)
            self.assertTrue(ref.segments)
            count += 1
        for mode in range(12):
            self.compare(fixture(flags=10), mode=mode)
            count += 1
        for state in range(256):
            self.compare(fixture(state=state), success=False)
            count += 1
        self.receipt('guest', dict(cases=count, complete_memory=True, exact_output_write_order=True,
            covered_words=[len(c) for c in coverage], GP_FP_saved_lifetimes=True, setup_callees='bounded interfaces'))

    def test_cursor_count_boundaries_and_lazy_inactive_allocation_failure(self):
        count = 0
        for current in range(256):
            start = 3 if narrow(current, 8) <= 0 else narrow(current, 8) - 1
            self.compare(fixture(current=current, goal=start))
            count += 1
        for units in range(256):
            self.compare(fixture(current=0, count=units, goal=units - 1)) if units <= 128 else self.compare(
                fixture(current=1, count=units, goal=0))
            count += 1
        for state, success in ((1, True), (128, True), (3, False)):
            memory = fixture(state=state)
            if not success:
                for base in (RECORDS, PAYLOAD):
                    memory = {a: b for a, b in memory.items() if not base - 16 <= a < base + 28 * 256}
            else:
                memory = {a: b for a, b in memory.items() if not OWNER + 0x94 <= a < OWNER + 0x9C}
            self.compare(memory, success=success)
        self.receipt('cursor', dict(cases=count, all_current_count_bytes=True, count_zero_negative_record=True,
            inactive_pointer_reads_lazy=True, null_allocation_record_reads_lazy=True))

    def test_required_vertex_and_final_lookahead_faults_fail_closed(self):
        memory = fixture(current=1, goal=0, pattern=2)
        targets = [RECORDS + 3 * 28 + i for i in (0, 4, 8, 0x14, 0x18)]
        targets += [VERTICES + i for i in (0, 2, 4, 6, 8, 10, 12, 13, 14, 15)]
        for missing in targets:
            changed = dict(memory); del changed[missing]
            for body in (self.words, self.retail):
                model = RibbonOracle(body, changed)
                with self.assertRaisesRegex(AssertionError, 'unmapped read|unmapped store'):
                    model.run()
                if missing < VERTICES:
                    self.assertTrue(writes(model), 'lookahead fault must occur after a rendered final segment')
        for missing in (OWNER + 0x2C, OWNER + 0x25, OWNER + 0x94, OWNER + 0x98,
                screen.SYMBOLS['D_800D2C9C'], screen.SYMBOLS['D_800A4AC8'] + 8,
                screen.SYMBOLS['D_800DD1E8']):
            changed = dict(memory); del changed[missing]
            for body in (self.words, self.retail):
                with self.assertRaisesRegex(AssertionError, 'unmapped read'):
                    RibbonOracle(body, changed).run()
        self.receipt('faults', dict(required_read_bytes=12, required_vertex_store_bytes=10, final_post_segment_lookahead=True,
            raw_vs_retail_prefix_equal=False, portable_C_fault_semantics=False, unmapped_stores=True))

    def test_full_source_profile_controls_and_effective_negative_witnesses(self):
        records = []
        forms = list(screen.setup_candidates() if self.FORM == screen.SETUP_FITTED_NAME
            else screen.candidates() if self.FORM == 'selected' else screen.fitting_candidates())
        self.assertEqual(len(forms), len(dict(forms)), 'source form names must be unique')
        for name, body in forms:
            record, words = screen.compile_candidate(self.root, self.out, 'control-' + name, body)
            records.append(record)
            self.compare(fixture(flags=10), mode=7, words=words)
        for profile in screen.PROFILES:
            record, words = screen.compile_candidate(self.root, self.out, 'profile-' + profile, self.body, profile)
            records.append(record)
            self.compare(fixture(flags=0, pattern=1), words=words, write_order=profile == 'o2g3')
        negatives = {
            'unsigned-state': self.body.replace('*(s8 *)(owner + 0x2C)', 'owner[0x2C]'),
            'lost-alpha-scale': self.body.replace(' >> 8', ' >> 7'),
            'wrong-width': self.body.replace('5.5f', '5.0f'),
            'lost-join': self.body.replace('currentPhase < previousPhase', 'currentPhase > previousPhase'),
            'wrong-old-pair': self.body.replace('cursor[-2].v.tc[0]', 'cursor[0].v.tc[0]'),
            'live-buffer': self.body.replace('point = records + index;', 'point = *(RibbonRecord151D80C4 **)(owner + 0x94) + index;').replace(
                'point = records + (index * 8 - index) * 4;', 'point = *(u8 **)(owner + 0x94) + (index * 8 - index) * 4;'),
            'wrong-request': self.body.replace('* 32 + 160', '* 32 + 128'),
            'unsigned-current': self.body.replace('*(s8 *)(owner + 0x2E)', 'owner[0x2E]'),
        }
        for name, body in negatives.items():
            self.assertNotEqual(body, self.body, name)
            _, words = screen.compile_candidate(self.root, self.out, 'negative-' + name, body)
            memory = fixture(state=128 if name == 'unsigned-state' else 3,
                current=128 if name == 'unsigned-current' else 3, goal=3 if name == 'unsigned-current' else 0, flags=10)
            reference = RibbonReference(memory, mode=1).run()
            model = RibbonOracle(words, memory, mode=1).run()
            self.assertTrue(external(model.memory) != external(reference.memory) or model.calls != reference.calls
                or model.r[2] != reference.result, name)
        self.receipt('controls', dict(full_semantic_forms=len(forms), profiles=4,
            measurements=records, effective_negatives=list(negatives)))

    def test_complete_original_dispatcher_render_table_and_allocator_connection(self):
        caller = list(struct.unpack_from('>52I', self.rom, 0x1750FC))
        allocator = list(struct.unpack_from('>52I', self.rom, 0x203210))
        for path, words in (('conker/asm/174BF0.s', caller),
                ('conker/asm/nonmatchings/generated_200930/func_151D5D60.s', allocator)):
            original = (self.root / path).read_text()
            if path.endswith('174BF0.s'):
                original = original.split('glabel func_15147C4C\n', 1)[1].split('endlabel func_15147C4C', 1)[0]
            self.assertEqual(words, [int(w, 16) for w in re.findall(r'/\* [0-9A-F]+ [0-9A-F]+ ([0-9A-F]{8}) \*/', original)])
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x22EDA4)[0], screen.ENTRY)
        production = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')[0]
        self.assertEqual(production['func_151D5D60'], allocator)
        coverage, count = set(), 0
        for view, success, existing, flip, phase, flags in itertools.product((0, 3, 0xFFFF, 0x12340002),
                (False, True), (False, True), (0, 1), (0, 8), (0, 2, 0x20, 0x22)):
            memory = fixture(view=view, flags=flags)
            slot = OWNER + 0x84 + narrow(view, 16) * 4
            put(memory, slot, VERTICES if existing else 0)
            put(memory, 0x800BE9C0, flip, 1)
            put(memory, TABLE + 16 * 4, screen.ENTRY)
            for body in (self.words, self.retail):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + len(body) * 4, 4), body))
                connected.update(zip(range(BACKEND, BACKEND + 208, 4), allocator))
                model = RibbonOracle(caller, memory, view, success, phase=phase, connected=connected,
                    entry=DISPATCHER, args=(OUTPUT - 8, OWNER, view)).run()
                self.assertEqual(model.forwarded, [(OWNER, OUTPUT, narrow(view, 16) & 0xFFFFFFFF)])
                self.assertEqual(model.setup, [(OUTPUT - 8, OWNER + 0x34, 0, 0, 0,
                    narrow(view, 16) & 0xFFFFFFFF, OWNER + 0x54, 2, read(memory, OWNER + 0x28) if flags & 0x20 else 0)])
                accepted = success or existing
                expected_start = VERTICES + (0 if flip else 4 * 32 + 160)
                ref = RibbonReference(memory, view, accepted, start=expected_start).run()
                # The real backend owns its slot, not the bounded reference.
                if not existing:
                    put(ref.memory, slot, VERTICES if success else 0)
                self.assertEqual(external(model.memory), external(ref.memory))
                self.assertEqual(model.calls, ref.calls)
                self.assertEqual(model.r[2], ref.result)
                if not existing:
                    self.assertEqual(model.alloc_args, (576, 1, 2, 1))
                coverage.update(model.visits)
            count += 1
        self.assertTrue(set(range(BACKEND, BACKEND + 208, 4)) <= coverage)
        self.receipt('connection', dict(cases=count, caller_words=52, backend_words=52,
            backend_all_words=True, caller='complete original render-table branch', render_callback=16,
            covered_caller_words=len(set(range(DISPATCHER, DISPATCHER + 208, 4)) & coverage),
            graphics_setup_and_deep_allocator='bounded hooks', original_caller_not_restored=True))

    def test_copied_owner_neighbors_pools_and_relocations(self):
        baseline = (self.root / SOURCE).read_text()
        marker = '/* Non-matching placeholders for the text-only asm slice asm/204660.s. */'
        selected = baseline.replace(marker, screen.DECLARATIONS + '\n' + marker).replace(screen.ORIGINAL, self.body)
        before, warnings_before = compile_owner(self.root, self.out, baseline, 'owner-baseline')
        after, warnings_after = compile_owner(self.root, self.out, selected, 'owner-selected')
        self.assertEqual(warnings_before, warnings_after)
        objects = []
        for name, obj in (('owner-baseline', before), ('owner-selected', after)):
            processed = self.out / (name + '-post.o')
            processed.write_bytes(obj.read_bytes())
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / (name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(processed.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(processed)
        before, after = objects
        bt, bf, br = parse_object(before); at, af, ar = parse_object(after)
        self.assertEqual(set(bf), set(af))
        for name in bf:
            if name == screen.FUNCTION:
                continue
            self.assertEqual(bt[bf[name]['value']:bf[name]['value'] + bf[name]['size']],
                at[af[name]['value']:af[name]['value'] + af[name]['size']], name)
            self.assertEqual({o - bf[name]['value']: r for o, r in br.items()
                if bf[name]['value'] <= o < bf[name]['value'] + bf[name]['size']},
                {o - af[name]['value']: r for o, r in ar.items()
                if af[name]['value'] <= o < af[name]['value'] + af[name]['size']}, name)
        self.assertEqual(normalized_pools(before), normalized_pools(after))
        expected = {o - bf[screen.FUNCTION]['value']: r for o, r in br.items()
            if bf[screen.FUNCTION]['value'] <= o < bf[screen.FUNCTION]['value'] + bf[screen.FUNCTION]['size']}
        actual = {o - af[screen.FUNCTION]['value']: r for o, r in ar.items()
            if af[screen.FUNCTION]['value'] <= o < af[screen.FUNCTION]['value'] + af[screen.FUNCTION]['size']}
        self.assertCountEqual([r for rows in expected.values() for r in rows], [r for rows in actual.values() for r in rows])
        isolated, _, isolated_rel = parse_object(self.out / 'selected.o')
        target = af[screen.FUNCTION]
        self.assertEqual(at[target['value']:target['value'] + 1620], isolated[:1620])
        self.assertEqual(actual, isolated_rel)
        padded = emit_padded_assembly(after, self.root / 'conker/asm/204660.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_204660')
        start = padded.index('.type %s, @function' % screen.FUNCTION)
        end = padded.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)
        self.assertNotIn('.space', padded[start:end])
        self.receipt('owner', dict(neighbors=len(bf) - 1, normalized_pools_unchanged=True,
            original_relocations=expected, candidate_relocations=actual, installed=False, isolated_target_identical=True,
            actual_padder_unchanged_guards=True, no_slot_padding=True, warnings=len(warnings_before),
            frame_and_register_schedule_still_open=True))

    def test_native32_independent_pairs_commands_canaries_and_callback_arguments(self):
        self.fixture = NATIVE_TYPES + screen.DECLARATIONS + NATIVE_FIXTURE + '\n' + self.body + '\n'
        self.run_host(r'''
int i,j,n=0;
for(i=0;i<256;i++) {if(check(i,3,0,4,10,19,0,0,0,1))return 1;n++;}
for(i=0;i<256;i++) {j=(signed char)i;if(check(3,i,j<=0?3:j-1,4,2,-1,0,0,0,1))return 2;n++;}
for(i=0;i<256;i++) {if(check(3,i>128?1:0,i>128?0:i-1,i,10,32767,0,0,0,1))return 3;n++;}
for(i=0;i<256;i++) {if(check(3,3,0,4,i*257,-32768+i,0,i%3,0,1))return 4;n++;}
for(i=0;i<12;i++)for(j=0;j<4;j++) {if(check(3,3,0,4,10,19,j,0,i,1))return 5;n++;}
for(i=0;i<4;i++)for(j=0;j<3;j++) {if(check(3,3,0,4,i==0?0:i==1?2:i==2?8:10,
 j==0?-32768:j==1?-1:32767,i,j,0,1)){return 6;}n++;}
for(i=-32768;i<=32767;i+=65535) {if(check(3,3,0,4,10,19,i,0,0,0))return 7;n++;}
if(n!=1086)return 8;
''')
        self.receipt('native', dict(cases=1086, native32=True, independent_offset_reference=True,
            full_65536_byte_canaries=True, volatile_typed_call=True, all_state_current_count_bytes=True,
            flag_patterns=256, live_mutations=12, signed_view_failure_boundaries=True, invalid_float_casts=False))

    def test_fresh_linked_baseline_source_data_manifest_and_progress_unchanged(self):
        elf = self.root / 'conker/build/conker.us.elf'
        # Complete artifact identity also preserves every address, extent and data byte.
        elf_hash = hashlib.sha256(elf.read_bytes()).hexdigest()
        self.assertEqual(elf_hash, 'f240ca73721dfd7a24c0a85fd5697d45ea1ebc724a11ebd76d965e6b3cd86e99')
        functions, _, _ = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
        self.assertEqual(len(functions), 6058)
        expected = {SOURCE: '73e090010650f383d2180dc482c3b9c24d28894f59fc3102fd8115c8fc1910e9',
            'conker/retail_word_patches.us.csv': '7241b12b96fb1036ac7f3dfd2536488386dbc923ad5c28f79832593c3a0773e9',
            'conker/Makefile': 'd5e4c8459b9bf1ac7485b913f559fe9e0242ec284d76cddf0650c210e2a73466',
            'conker/asm/204660.s': '14c690097e848287eb8f9e5f3f1031cfa7c3fd65ebdb31075cdafc30a732fa48',
            'conker/progress.csv': '7a5ef312df05097084d3d6986e0adfcdbdbe4f71eab33a8c82fb876d7c1851d9'}
        for path, digest in expected.items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), digest, path)
        self.receipt('baseline', dict(all_6058_bodies_addresses_extents_unchanged=True,
            protected_sections_unchanged=True, source_manifest_layout_progress_unchanged=True, hashes=expected,
            complete_ELF_sha256=elf_hash))


class GameRecordRingRendererFittingTests(GameRecordRingRendererRecoveryTests):
    FORM, body, expected_shape = screen.FITTED_NAME, screen.FITTED, (405, 0xD0, 198)

    def test_fitted_private_layout_and_complete_register_saves(self):
        self.assertEqual(self.words[0x88 // 4], 0x27A7008C)
        self.assertEqual(self.words[0x90 // 4], 0xAFA800A8)
        self.assertEqual(self.words[0x9C // 4], 0x27B000A7)
        addresses = {word & 65535 for word in self.words if word >> 26 == 9 and word >> 21 & 31 == 29
            and word >> 16 & 31 != 29}
        self.assertTrue({0x8C, 0xA7, 0xB4, 0xC0} <= addresses)
        gp_saves = {word >> 16 & 31: word & 65535 for word in self.words[:20]
            if word >> 26 == 43 and word >> 21 & 31 == 29 and word >> 16 & 31 in (*range(16, 24), 30, 31)}
        self.assertEqual(gp_saves, {**{r: 0x48 + (r - 16) * 4 for r in range(16, 24)}, 30: 0x68, 31: 0x6C})
        self.assertEqual(self.words[0x3E4 // 4], 0xC7A600C0)
        self.assertEqual(self.words[0x56C // 4], self.retail[0x56C // 4])
        ref, models = self.compare(fixture(flags=10))
        self.assertTrue(ref.copies)
        self.assertEqual(models[0].cursor_slot, models[1].cursor_slot)
        self.assertEqual(models[0].sync_slot, models[1].sync_slot)
        self.receipt('layout', dict(words=405, frame=208, cursor=140, sync=167, buffer=168,
            previous_XYZ=180, current_XYZ=192, gp_saves=gp_saves, FP_saved=[20, 22],
            loop_offset=996, memcpy_offset=1388, raw_differences=self.record['differences'], installed=False))

    def test_independent_original_and_fitted_symbol_rebases(self):
        asm, obj = self.out / 'original.s', self.out / 'original.o'
        original = (self.root / 'conker/asm/nonmatchings/generated_204660/func_151D80C4.s').read_text()
        asm.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n.type ' + screen.FUNCTION +
            ', @function\n' + original + '\n.size ' + screen.FUNCTION + ', . - ' + screen.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)],
            cwd=self.root, check=True, capture_output=True)
        _, original_functions, original_rel = parse_object(obj)
        self.assertEqual(original_functions[screen.FUNCTION]['size'], 1620)
        _, _, fitted_rel = parse_object(self.out / 'selected.o')
        self.assertCountEqual([r for rows in original_rel.values() for r in rows],
            [r for rows in fitted_rel.values() for r in rows])
        self.assertEqual(sum(map(len, original_rel.values())), 16)
        executions = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = dict(screen.SYMBOLS)
            if variant:
                globals_ = [name for name in symbols if name.startswith('D_')]
                for index, name in enumerate(globals_):
                    symbols[name] = (0x70000000 + (index + 1) * 0x100000 + (0x7FFC, 0x8000, 0xFFF8)[(index + variant) % 3])
                for index, name in enumerate(TARGET_NAMES.values()):
                    symbols[name] = (entry & 0xF0000000) + 0x100800 + index * 0x100
            script = self.out / ('rebase-%d.ld' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for kind, object_ in (('original', obj), ('fitted', self.out / 'selected.o')):
                elf = self.out / ('rebase-%d-%s.elf' % (variant, kind))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(object_)],
                    check=True, capture_output=True)
                words = list(struct.unpack_from('>405I', screen.sections(elf)['.text'][1]))
                if not variant:
                    self.assertEqual(words, self.retail if kind == 'original' else self.words)
                bodies.append(words)
            for flags, mode, phase, view in itertools.product((0, 2, 8, 10), (0, 1, 7, 8, 10, 11), (0, 8), (0, 3)):
                memory = fixture(flags=flags, view=view, symbols=symbols)
                ref = RibbonReference(memory, view, mode=mode, symbols=symbols).run()
                for words in bodies:
                    model = RibbonOracle(words, memory, view, mode=mode, phase=phase, entry=entry, symbols=symbols).run()
                    self.assertEqual((external(model.memory), model.calls, model.r[2], writes(model)),
                        (external(ref.memory), ref.calls, ref.result, [e for e in ref.events if e[0] == 'W']))
                    executions += 1
        self.receipt('rebases', dict(independent_GNU_links=True, symbol_sets=4, executions=executions,
            HI16_carry_LO16_sign_and_JAL_regions=True, relocation_uses=16, complete_body_words=405,
            complete_reference_memory_calls_result_store_order=True, normalization=False))

    def test_guest_input_output_aliases_with_post_segment_reads(self):
        cases = 0
        for start, output, flags, phase in itertools.product((VERTICES, RECORDS, RECORDS + 112, OWNER + 0x40),
                (OUTPUT, RECORDS, PAYLOAD, VERTICES + 64), (2, 10), (0, 8)):
            memory = fixture(current=1, goal=0, flags=flags, pattern=2)
            ref = RibbonReference(memory, start=start, output=output).run()
            for body in (self.words, self.retail):
                model = RibbonOracle(body, memory, phase=phase, start=start, args=(OWNER, output, 0)).run()
                self.assertEqual((external(model.memory), model.calls, model.r[2], writes(model)),
                    (external(ref.memory), ref.calls, ref.result, [e for e in ref.events if e[0] == 'W']))
            cases += 1
        self.receipt('aliases', dict(cases=cases, executions=cases * 2, two_SP_phases=True,
            vertex_record_owner_and_Gfx_record_payload_vertex_aliases=True, final_lookahead_reads=True,
            arbitrary_invalid_or_nonterminating_domains=False, native_aliases=False))


class RibbonAccessOracle(RibbonOracle):
    def record_call(self, target):
        super().record_call(target)
        self.events.append(('CALL', self.targets.get(target, target)))


def after_setup_events(model):
    start = model.events.index(('CALL', MODE)) + 1
    return [event for event in model.events[start:]
        if event[0] in ('R', 'W') and not STACK - 0x600 <= event[1] < STACK + 0x140]


def operand_masks(word):
    op, rs = word >> 26, word >> 21 & 31
    if op in (2, 3):
        return 0, 0
    if op == 0:
        return 0x03FFF800, 0
    if op == 1:
        return 0x03E00000, 0
    if op == 17:
        if rs in (0, 2, 4, 6):
            return 0x001F0000, 0x0000F800 if rs in (0, 4) else 0
        assert rs in (16, 17, 20), ('unexpected COP1 format', hex(word))
        return 0, 0x001FFFC0
    if op in (49, 53, 57, 61):
        return 0x03E00000, 0x001F0000
    assert op in (4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 20, 21, 22, 23, 32, 33, 35, 36, 37, 40, 41, 43), hex(word)
    return 0x03FF0000, 0


def operand_partition(words, retail):
    groups = dict(GP_fields_only=[], FP_fields_only=[], combined_operand_fields=[], other=[])
    for index, (word, original) in enumerate(zip(words, retail)):
        if word == original:
            continue
        gp, fp = operand_masks(word)
        original_gp, original_fp = operand_masks(original)
        if (gp, fp) != (original_gp, original_fp):
            group = 'other'
        elif word & ~gp == original & ~gp:
            group = 'GP_fields_only'
        elif word & ~fp == original & ~fp:
            group = 'FP_fields_only'
        elif word & ~(gp | fp) == original & ~(gp | fp):
            group = 'combined_operand_fields'
        else:
            group = 'other'
        groups[group].append(index * 4)
    return groups


class GameRecordRingRendererSchedulingTests(unittest.TestCase):
    compare = GameRecordRingRendererRecoveryTests.compare
    receipt = GameRecordRingRendererRecoveryTests.receipt

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-ring-renderer-test/scheduling'
        cls.out.mkdir(parents=True, exist_ok=True)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.out, 'fitted', screen.FITTED)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>405I', cls.rom, screen.ROM))

    def test_complete_scheduling_forms_preserve_public_results_and_order(self):
        forms, records, cases = list(screen.scheduling_candidates()), [], 0
        self.assertEqual(len(forms), len(dict(forms)))
        for name, body in forms:
            record, words = screen.compile_candidate(self.root, self.out, 'form-' + name, body)
            records.append(record)
            for flags, phase in itertools.product((0, 2, 8, 10), (0, 8)):
                self.compare(fixture(flags=flags), phase=phase, words=words)
                cases += 1
            for mode in (1, 7, 8, 9, 10, 11):
                self.compare(fixture(flags=10), mode=mode, words=words)
                cases += 1
        self.assertEqual(min(r['differences'] for r in records), 198)
        self.receipt('forms', dict(complete_forms=len(forms), cases=cases, measurements=records,
            exact_public_memory_calls_result_store_order=True, better_body_found=False, installed=False,
            full_domain_and_native_sweeps_for_every_form=False))

    def test_all_final_lookahead_bytes_preserve_post_setup_fault_prefixes(self):
        pairs = 0
        for flags, count, phase in itertools.product((0, 2, 8, 10), (4, 128, 255), (0, 8)):
            memory = fixture(current=1 if flags & 2 else 2, goal=0, count=count, flags=flags, pattern=2)
            offsets = (*range(12), 0x14, *range(0x18, 0x1C))
            for offset in offsets:
                changed = dict(memory)
                del changed[RECORDS + (count - 1) * 28 + offset]
                models = []
                for body in (self.words, self.retail):
                    model = RibbonAccessOracle(body, changed, phase=phase)
                    with self.assertRaisesRegex(AssertionError, 'unmapped read'):
                        model.run()
                    self.assertTrue(writes(model), 'the missing byte must fault after the final rendered segment')
                    models.append(model)
                self.assertEqual(after_setup_events(models[0]), after_setup_events(models[1]))
                self.assertEqual((external(models[0].memory), models[0].calls),
                    (external(models[1].memory), models[1].calls))
                pairs += 1
        self.receipt('lookahead-prefixes', dict(pairs=pairs, executions=pairs * 2, missing_byte_offsets=offsets,
            post_MODE_read_write_prefix_and_public_memory_calls_equal=True, full_entry_prefix=False,
            GP_FP_private_fault_state=False, hardware_or_portable_C_fault_semantics=False))

    def test_early_exit_negative_passes_ordinary_outputs_but_loses_lookahead_fault(self):
        marker = '        currentPosition = *(RibbonPosition151D80C4 *)point;'
        bad = screen.FITTED.replace(marker,
            '        if (previousIndex == *(s8 *)(owner + 0x2D)) { return output; }\n' + marker)
        self.assertEqual(bad.count('return output; }'), 1)
        record, words = screen.compile_candidate(self.root, self.out, 'negative-early-exit', bad)
        for flags in (0, 2, 8, 10):
            memory = fixture(current=1 if flags & 2 else 2, goal=0, flags=flags, pattern=2)
            self.compare(memory, words=words)
            del memory[RECORDS + 3 * 28 + 0x18]
            RibbonAccessOracle(words, memory).run()
            for body in (self.words, self.retail):
                with self.assertRaisesRegex(AssertionError, 'unmapped read'):
                    RibbonAccessOracle(body, memory).run()
        self.receipt('lookahead-negative', dict(ordinary_output_equivalent_cases=4,
            effective_required_lookahead_fault_witnesses=4, measurement=record,
            no_timeout_or_unsupported_instruction_witness=True))

    def test_structural_operand_difference_partition_is_not_match_evidence(self):
        groups = operand_partition(self.words, self.retail)
        self.assertEqual(sum(map(len, groups.values())), 198)
        self.receipt('operand-partition', dict(groups=groups, counts={k: len(v) for k,v in groups.items()},
            raw_differences=198, syntactic_partition_only=True, consistent_register_mapping_proven=False,
            guards_or_normalized_body=False, byte_match=False))


class GameRecordRingRendererSetupFittingTests(GameRecordRingRendererFittingTests):
    FORM, body, expected_shape = screen.SETUP_FITTED_NAME, screen.SETUP_FITTED, (405, 0xD0, 185)
    OUT_NAME = 'setup-fitted'
    test_all_final_lookahead_bytes_preserve_post_setup_fault_prefixes = (
        GameRecordRingRendererSchedulingTests.test_all_final_lookahead_bytes_preserve_post_setup_fault_prefixes)

    @staticmethod
    def public_events(model):
        return [event for event in model.events if event[0] == 'CALL'
            or event[0] in ('R', 'W') and not STACK - 0x600 <= event[1] < STACK + 0x140]

    def test_whole_entry_public_access_order_and_pre_vertex_fault_prefixes(self):
        cases, pairs, complete_private_memory_equal = 0, 0, 0
        for flags, pattern, view, phase, mode in itertools.product((0, 2, 8, 10), range(3),
                (0, 3, 0xFFFF), (0, 8), (0, 1, 7, 8, 10, 11)):
            memory = fixture(flags=flags, pattern=pattern, view=view)
            models = [RibbonAccessOracle(words, memory, view, mode=mode, phase=phase).run()
                for words in (self.words, self.retail)]
            self.assertEqual(self.public_events(models[0]), self.public_events(models[1]))
            self.assertEqual((external(models[0].memory), models[0].calls, models[0].r[2]),
                (external(models[1].memory), models[1].calls, models[1].r[2]))
            complete_private_memory_equal += models[0].memory == models[1].memory
            cases += 1
        self.assertEqual(complete_private_memory_equal, cases)
        for flags, phase in itertools.product((0, 2, 8, 10), (0, 8)):
            memory = fixture(flags=flags)
            ordinary = RibbonAccessOracle(self.retail, memory, phase=phase).run()
            missing = set()
            for event in self.public_events(ordinary):
                if event[0] == 'W' and event[1] == VERTICES:
                    break
                if event[0] == 'R':
                    missing.update(range(event[1], event[1] + event[2]))
            missing.update(range(VERTICES, VERTICES + 16))
            for address in sorted(missing):
                changed = dict(memory)
                del changed[address]
                models = []
                for words in (self.words, self.retail):
                    model = RibbonAccessOracle(words, changed, phase=phase)
                    with self.assertRaisesRegex(AssertionError, 'unmapped read|unmapped store'):
                        model.run()
                    models.append(model)
                self.assertEqual(self.public_events(models[0]), self.public_events(models[1]))
                self.assertEqual((external(models[0].memory), models[0].calls),
                    (external(models[1].memory), models[1].calls))
                pairs += 1
        self.receipt('entry-prefixes', dict(ordinary_whole_entry_public_prefix_cases=cases,
            pre_vertex_read_and_first_vertex_store_byte_fault_pairs=pairs, fault_executions=pairs * 2,
            complete_private_memory_equal_at_completed_exit_cases=complete_private_memory_equal,
            private_fault_state_and_store_prefix=False, hardware_or_portable_C_fault_semantics=False))

    def test_remaining_difference_partition_does_not_prove_register_mapping(self):
        groups = operand_partition(self.words, self.retail)
        counts = {k: len(v) for k, v in groups.items()}
        self.assertEqual(counts, dict(GP_fields_only=176, FP_fields_only=0, combined_operand_fields=0, other=9))
        self.assertEqual(groups['other'], [0x14, 0x34, 0x278, 0x280, 0x284, 0x288, 0x290, 0x294, 0x298])
        self.receipt('operand-partition', dict(groups=groups, counts=counts, raw_differences=185,
            syntactic_partition_only=True, consistent_register_mapping_proven=False,
            guards_or_normalized_body=False, byte_match=False))

    def test_mode_load_order_negative_passes_outputs_but_changes_required_fault_prefix(self):
        bad = self.body.replace('D_800A4AC8[2] | D_800A4AC8[3]', 'D_800A4AC8[3] | D_800A4AC8[2]')
        self.assertNotEqual(bad, self.body)
        record, words = screen.compile_candidate(self.root, self.out, 'negative-mode-load-order', bad)
        witnesses = 0
        for flags, offset in itertools.product((0, 2, 8, 10), range(4)):
            memory = fixture(flags=flags)
            self.compare(memory, words=words)
            del memory[screen.SYMBOLS['D_800A4AC8'] + 12 + offset]
            models = []
            for body in (self.words, words, self.retail):
                model = RibbonAccessOracle(body, memory)
                with self.assertRaisesRegex(AssertionError, 'unmapped read'):
                    model.run()
                models.append(model)
            self.assertEqual(self.public_events(models[0]), self.public_events(models[2]))
            self.assertNotEqual(self.public_events(models[1]), self.public_events(models[2]))
            self.assertEqual((external(models[0].memory), models[0].calls),
                (external(models[1].memory), models[1].calls))
            witnesses += 1
        self.receipt('mode-order-negative', dict(ordinary_output_equivalent_cases=witnesses,
            effective_read_prefix_witnesses=witnesses, measurement=record,
            no_timeout_or_unsupported_instruction_witness=True))


NATIVE_TYPES = r'''typedef unsigned char u8;typedef signed char s8;typedef short s16;
typedef unsigned short u16;typedef int s32;typedef unsigned int u32;typedef float f32;
typedef struct {struct {s16 ob[3];u16 flag;s16 tc[2];u8 cn[4];} v;} Vtx;
typedef struct {struct {u32 w0,w1;} words;} Gfx;
#define NULL ((void *)0)
#define gSPVertex(p,v,n,k) do {Gfx *q=(p);q->words.w0=0x01000000|((n)<<12)|(((k)+(n))<<1);q->words.w1=(u32)(v);}while(0)
#define gSP1Triangle(p,a,b,c,f) do {Gfx *q=(p);q->words.w0=0x05000000|((a)<<17)|((b)<<9)|((c)<<1);q->words.w1=0;}while(0)
void *memcpy(void *,const void *,u32);
'''

NATIVE_FIXTURE = r'''
Gfx *func_151D80C4(u8 *,Gfx *,s16);
u8 D_80090CD4[16];u32 D_800D2C9C,D_800A4AC8[4];f32 D_800DD1E8[4],D_800DD1D8[4];
static union {u32 align;u8 bytes[65536];} storage,wanted;
#define OWN 256
#define REC 4096
#define PAY 768
#define ALT 12288
#define VERT 24576
#define OUT 43008
static int mutation,failed,error,used,total,copies;
static s16 expectedView;static u32 logArgs[260][12];
static u32 load(u8 *b,int a){return *(u32 *)(b+a);}
static f32 number(u8 *b,int a){return *(f32 *)(b+a);}
static void value(u8 *b,int a,f32 v){*(f32 *)(b+a)=v;}
static f32 plus(f32 a,f32 b){volatile f32 v=a+b;return v;}
static f32 times(f32 a,f32 b){volatile f32 v=a*b;return v;}
static int signbyte(u8 v){return (signed char)v;}
static void effect(u8 *b,int kind,int copy){
 if(kind==4){
  if(mutation==1)*(u32 *)(b+OWN+148)=(u32)(storage.bytes+ALT);
  if(mutation==2)*(u32 *)(b+OWN+152)=(u32)(storage.bytes+ALT);
  if(mutation==3)b[OWN+46]=1;
  if(mutation==4)*(u16 *)(b+OWN+30)=10;
  if(mutation==5)*(s16 *)(b+OWN+28)=-32768;
  if(mutation==6)b[OWN+44]=0;
 }
 if(kind==5&&!copy){
  if(mutation==7)*(u32 *)(b+OWN+148)=(u32)(storage.bytes+ALT);
  if(mutation==8)b[OWN+45]=1;
  if(mutation==9){*(u16 *)(b+OWN+30)=0;*(s16 *)(b+OWN+28)=0;}
  if(mutation==10&&b==storage.bytes)D_800DD1E8[0]=100;
  if(mutation==11)value(b,REC+28+24,15000);
 }
}
static void record(int kind,u32 *args,int count){
 int i;if(total>=260){error=1;return;}logArgs[total][0]=kind;
 for(i=0;i<count;i++){logArgs[total][i+1]=args[i];}total++;
}
static void accept(int kind,u32 *args,int count){
 int i;if(used>=total||logArgs[used][0]!=(u32)kind){error=2;return;}
 for(i=0;i<count;i++)if(logArgs[used][i+1]!=args[i])error=3;
 used++;
}
void func_151D5D60(void *slots,s16 view,s32 size,Vtx **cursor,u8 *fresh){
 u32 a[5]={(u32)slots,(u32)(s32)view,(u32)size,0,0};
 if(fresh||view!=expectedView){error=4;}accept(0,a,5);*cursor=failed?NULL:(Vtx *)(storage.bytes+VERT);
}
Gfx *func_15142E24(Gfx *p,void *source,s32 a,s32 b,s32 c,s32 d,s32 index,u8 kind,u8 *attachment,u8 *sync,s32 flags){
 u32 v[11]={(u32)p,(u32)source,(u32)a,(u32)b,(u32)c,(u32)d,(u32)index,kind,(u32)attachment,0,(u32)flags};
 if(*sync!=1){error=5;}*sync=0;accept(1,v,11);return p+1;
}
Gfx *func_15142B7C(Gfx *p,u32 a,u32 b){u32 v[3]={(u32)p,a,b};accept(2,v,3);return p+1;}
Gfx *func_1513F4E4(Gfx *p,u8 kind,u8 *sync){u32 v[3]={(u32)p,kind,0};if(*sync)error=6;accept(3,v,3);return p+1;}
Gfx *func_15142FBC(Gfx *p,u32 a,u32 b,u8 *sync){u32 v[4]={(u32)p,a,b,0};if(*sync)error=7;accept(4,v,4);effect(storage.bytes,4,0);return p+1;}
void *memcpy(void *d,const void *s,u32 n){
 u32 i,v[3]={(u32)d,(u32)s,n};accept(5,v,3);
 for(i=0;i<n;i++)((u8 *)d)[i]=((const u8 *)s)[i];
 effect(storage.bytes,5,copies++);return d;
}
static void pair(u8 *b,int *at,f32 *xyz,f32 phase,int alpha,int factor,f32 x,f32 z){
 int side,i;for(side=1;side>=-1;side-=2){int p=*at;
  *(s16 *)(b+p)=(s32)plus(xyz[0],times(x,(f32)side));
  *(s16 *)(b+p+2)=(s32)xyz[1];*(s16 *)(b+p+4)=(s32)plus(xyz[2],-times(z,(f32)side));
  *(s16 *)(b+p+8)=(s32)phase;*(s16 *)(b+p+10)=side>0?2048:0;
  for(i=0;i<3;i++){b[p+12+i]=255;}b[p+15]=(u8)(alpha*factor/256);*(u16 *)(b+p+6)=0;*at+=16;
 }
}
static int back(u8 *b,int i){return i<0?b[OWN+37]-1:i;}
static int reference(void){
 u8 *b=wanted.bytes;int rec,payload,index,prior,point,at=VERT,out=OUT,alpha,factor,i,limit=0,copy=0;
 f32 previous[3],current[3],before,phase,x,z;u32 a[11];
 if(signbyte(b[OWN+44])<2)return OUT;
 rec=load(b,OWN+148)-(u32)storage.bytes;payload=load(b,OWN+152)-(u32)storage.bytes;
 a[0]=(u32)(storage.bytes+OWN+132);a[1]=(u32)(s32)expectedView;a[2]=b[OWN+37]*32+160;a[3]=a[4]=0;record(0,a,5);
 if(failed)return OUT;
 a[0]=(u32)(storage.bytes+out);a[1]=(u32)D_80090CD4;a[2]=a[3]=a[4]=a[5]=0;a[6]=31;a[7]=a[8]=a[9]=0;a[10]=62;record(1,a,11);out+=8;
 a[0]=(u32)(storage.bytes+out);a[1]=0x200005;a[2]=0x1F0600;record(2,a,3);out+=8;
 a[0]=(u32)(storage.bytes+out);a[1]=0x4C;a[2]=0;record(3,a,3);out+=8;
 a[0]=(u32)(storage.bytes+out);a[1]=D_800D2C9C|0x82CA0;a[2]=D_800A4AC8[3]|D_800A4AC8[2];a[3]=0;record(4,a,4);out+=8;effect(b,4,0);
 index=back(b,signbyte(b[OWN+46])-1);
 if(*(u16 *)(b+OWN+30)&2){for(i=0;i<3;i++)previous[i]=number(b,OWN+16+i*4);alpha=0;before=number(b,payload+24);}
 else{prior=index;index=back(b,index-1);for(i=0;i<3;i++)previous[i]=number(b,rec+prior*28+i*4);alpha=b[rec+prior*28+20];before=number(b,rec+prior*28+24);}
 point=rec+index*28;for(i=0;i<3;i++)current[i]=number(b,point+i*4);
 x=times(D_800DD1E8[expectedView],5.5f);z=times(D_800DD1D8[expectedView],5.5f);
 factor=(*(u16 *)(b+OWN+30)&8)?(*(s16 *)(b+OWN+28)*12)&255:255;
 pair(b,&at,previous,before,alpha,factor,x,z);alpha=b[point+20];phase=number(b,point+24);
 do{
  if(++limit>256){error=8;return 0;}pair(b,&at,current,phase,alpha,factor,x,z);
  *(u32 *)(b+out)=0x01004008;*(u32 *)(b+out+4)=(u32)(storage.bytes+at-64);out+=8;
  *(u32 *)(b+out)=0x05000204;*(u32 *)(b+out+4)=0;out+=8;
  *(u32 *)(b+out)=0x05020604;*(u32 *)(b+out+4)=0;out+=8;
  if(phase<before){
   a[0]=(u32)(storage.bytes+at);a[1]=(u32)(storage.bytes+at-32);a[2]=32;record(5,a,3);
   for(i=0;i<32;i++){b[at+i]=b[at-32+i];}effect(b,5,copy++);
   *(s16 *)(b+at-24)-=32768;*(s16 *)(b+at-8)-=32768;at+=32;
  }
  prior=index;index--;point-=28;if(index<0){index=b[OWN+37]-1;point=rec+index*28;}
  for(i=0;i<3;i++){current[i]=number(b,point+i*4);}alpha=b[point+20];before=number(b,rec+prior*28+24);phase=number(b,point+24);
 }while(prior!=signbyte(b[OWN+45]));return out;
}
static int check(int state,int current,int goal,int count,int flags,int opacity,int view,int pattern,int mode,int success){
 int i,j,k,result;Gfx *actual;u8 *b=storage.bytes;
 for(i=0;i<65536;i++)b[i]=(u8)(i*17+13);
 for(k=0;k<2;k++)for(j=-1;j<256;j++){int p=(k?ALT:REC)+j*28;
  value(b,p,j*3.25f-100+(k?10:0));value(b,p+4,-2.75f+(k?10:0));value(b,p+8,j*-4.5f+50+(k?10:0));
  b[p+20]=(u8)(j*61+255);value(b,p+24,pattern==0?j*2500.25f-10000:pattern==1?-j*1000.5f:0);
 }
 value(b,OWN+16,12.75f);value(b,OWN+20,-3.5f);value(b,OWN+24,-22.25f);value(b,PAY+24,12500.5f);
 *(u32 *)(b+OWN+148)=(u32)(b+REC);*(u32 *)(b+OWN+152)=(u32)(b+PAY);
 b[OWN+44]=(u8)state;b[OWN+46]=(u8)current;b[OWN+45]=(u8)goal;b[OWN+37]=(u8)count;
 *(u16 *)(b+OWN+30)=(u16)flags;*(s16 *)(b+OWN+28)=(s16)opacity;
 for(i=0;i<4;i++){D_800DD1E8[i]=0.25f;D_800DD1D8[i]=-0.75f;}
 D_800D2C9C=0xAA551234;D_800A4AC8[2]=0x00112233;D_800A4AC8[3]=0x44008800;
 for(i=0;i<65536;i++)wanted.bytes[i]=b[i];
 failed=!success;expectedView=(s16)view;mutation=mode;used=total=copies=error=0;result=reference();
 {Gfx *(*volatile call)(u8 *,Gfx *,s16)=func_151D80C4;actual=call(b+OWN,(Gfx *)(b+OUT),(s16)view);}
 if(error||used!=total||(u32)actual!=(u32)(b+result))return 1;
 if(mode==10&&success&&D_800DD1E8[0]!=100)return 3;
 for(i=0;i<65536;i++){if(b[i]!=wanted.bytes[i])return 2;}return 0;
}
'''
