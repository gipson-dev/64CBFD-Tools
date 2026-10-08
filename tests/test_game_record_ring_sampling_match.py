"""Live sampling state, fractional interpolation and closed scheduling guards."""

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

from tools.experiments import game_record_ring_sampling_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_record_ring_update_match as ring
from tools.tests import test_game_record_velocity_match as velocity
from tools.tests import test_game_random_curve_record as native
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK

OWNER, PAYLOAD, ACTOR, RECORDS = 0x20000, 0x21000, 0x22000, 0x28000
ALT_PAYLOAD, ALT_RECORDS = 0x23000, 0x30000
DISPATCHER, RELEASE, TABLE = 0x15147740, 0x1516972C, 0x8008A23C
SOURCE = 'conker/src/game/generated_204660.c'
INSERT = screen.DECLARATIONS.replace('extern f32 D_800BE9A4;\nvoid func_151D8718(f32 *, f32 *, f32);\n', '') + '\ns32 func_151D7A38(u8 *owner);\n\n'
MARKER = 's32 func_151D792C(u8 *owner);\n\n'


def source_shapes(root):
    source = (root / SOURCE).read_text()
    baseline = source.replace(screen.SELECTED, screen.ORIGINAL)
    assert baseline.count(screen.ORIGINAL) == 1
    if INSERT in baseline:
        assert baseline.count(INSERT) == 1
        selected = baseline.replace(screen.ORIGINAL, screen.SELECTED)
        baseline = baseline.replace(INSERT, '')
    else:
        assert baseline.count(MARKER) == 1
        selected = baseline.replace(MARKER, MARKER + INSERT).replace(screen.ORIGINAL, screen.SELECTED)
    return baseline, selected


def rounded(operation, a, b):
    return bits({'add': lambda: floating(a) + floating(b), 'sub': lambda: floating(a) - floating(b),
                 'mul': lambda: floating(a) * floating(b), 'div': lambda: floating(a) / floating(b)}[operation]())


def fixture(flag=1, progress=2.25, current=0, goal=0, count=4, state=0, delta=1.0, layout=0, symbols=None):
    symbols = symbols or screen.SYMBOLS
    memory = {STACK + i: 0xA5 for i in range(-0x400, 0x100)}
    for base, length in ((OWNER, 0xB0), (PAYLOAD, 0x40), (ACTOR, 0x100), (ALT_PAYLOAD, 0x40)):
        memory.update({base + i: (i * 17 + 0xA5) & 255 for i in range(-16, length)})
    indices = set(range(8)) | set(range(-128, -118)) | set(range(120, 128))
    indices.update(range(ring.byte_signed(current) - 1, min(128, ring.byte_signed(current) + 8)))
    for base in (RECORDS, ALT_RECORDS):
        for index in indices:
            memory.update({base + index * 28 + offset: (index + offset * 17 + 0xA5) & 255 for offset in range(28)})
    records = (RECORDS, ACTOR + 0x30, PAYLOAD + 4)[layout]
    for a, value, width in ((OWNER + 0x98, PAYLOAD, 4), (OWNER + 0x94, records, 4),
            (PAYLOAD, ACTOR, 4), (ALT_PAYLOAD, ACTOR, 4), (ACTOR + 0x2D, flag, 1),
            (OWNER + 0x2E, current, 1), (OWNER + 0x2D, goal, 1), (OWNER + 0x25, count, 1),
            (OWNER + 0x2C, state, 1), (PAYLOAD + 0x14, bits(progress), 4),
            (ALT_PAYLOAD + 0x14, bits(1.0), 4), (PAYLOAD + 0x10, bits(2.0), 4),
            (symbols['D_800BE9A4'], bits(delta), 4)):
        put(memory, a, value, width)
    for axis, (old, new) in enumerate(zip((1.0, -2.0, 4.0), (5.0, 6.0, -8.0))):
        put(memory, PAYLOAD + 4 + axis * 4, bits(old))
        put(memory, ACTOR + 0x30 + axis * 4, bits(new))
    for name, value in zip(('D_800AB2EC', 'D_800AB2F0'), (0x3E6F9DB3, 0x3DEF9DB3)):
        put(memory, velocity.screen.SYMBOLS[name], value)
    return memory


def actions(mode, index, symbols):
    if index:
        return []
    return {0: [], 1: [(OWNER + 0x2E, 3, 1)], 2: [(OWNER + 0x25, 2, 1)],
        3: [(OWNER + 0x2D, 0, 1)], 4: [(OWNER + 0x2C, 255, 1)],
        5: [(OWNER + 0x94, ALT_RECORDS, 4)], 6: [(OWNER + 0x98, ALT_PAYLOAD, 4)],
        7: [(PAYLOAD + 0x14, bits(1.25), 4)], 8: [(symbols['D_800BE9A4'], bits(8.0), 4)],
        9: [(ACTOR + 0x30, bits(128.0), 4), (PAYLOAD + 4, bits(64.0), 4)]}[mode]


class SamplingReference(ring.RingReference):
    def call(self, position, delta):
        args = position, position + 12, delta
        index = len(self.calls)
        self.calls.append(args)
        self.events.append(('CALL', self.symbols['func_151D8718'], args))
        if self.actual:
            self.memory, events = velocity.reference(self.memory, *args)
            self.events.extend(events)
        else:
            height, speed = self.get(position + 4), self.get(position + 12)
            self.put(position + 4, height ^ delta)
            self.put(position + 12, speed ^ 0x01010101)
        for address, value, width in actions(self.mode, index, self.symbols):
            self.put(address, value, width)

    def run(self):
        payload, records = self.get(OWNER + 0x98), self.get(OWNER + 0x94)
        actor = self.get(payload)
        if not self.get(actor + 0x2D, 1) & 1:
            self.result = 0
            return self
        current = [self.get(actor + 0x30 + axis * 4) for axis in range(3)]
        for axis, value in enumerate(current):
            self.put(OWNER + 0x10 + axis * 4, value)
        delta = self.get(self.symbols['D_800BE9A4'])
        self.put(payload + 0x14, rounded('add', self.get(payload + 0x14), rounded('mul', bits(0.25), delta)))
        progress = self.get(payload + 0x14)
        if floating(progress) > 1.0:
            fraction = rounded('div', bits(1.0), progress)
            point = [self.get(payload + 4)]
            time = rounded('add', self.get(payload + 0x10), self.get(self.symbols['D_800BE9A4']))
            point.extend(self.get(payload + 4 + axis * 4) for axis in (1, 2))
            differences = [rounded('sub', current[axis], self.get(payload + 4 + axis * 4)) for axis in range(3)]
            time_step = rounded('mul', time, fraction)
            steps = [rounded('mul', difference, fraction) for difference in differences]
            for _ in range(64):
                record = (records + ring.byte_signed(self.get(OWNER + 0x2E, 1)) * 28) & 0xFFFFFFFF
                self.put(record, point[0])
                self.put(record + 4, point[1])
                for offset in (12, 16):
                    self.put(record + offset, 0)
                self.put(record + 20, 0, 1)
                self.put(record + 24, 0)
                self.put(record + 8, point[2])
                self.call(record, time)
                cursor, count = ring.byte_signed(self.get(OWNER + 0x2E, 1)), self.get(OWNER + 0x25, 1)
                self.put(OWNER + 0x2E, cursor + 1, 1)
                cursor = ring.byte_signed(self.get(OWNER + 0x2E, 1))
                time = rounded('sub', time, time_step)
                if cursor == count:
                    self.put(OWNER + 0x2E, 0, 1)
                    cursor = ring.byte_signed(self.get(OWNER + 0x2E, 1))
                state, goal = ring.byte_signed(self.get(OWNER + 0x2C, 1)), ring.byte_signed(self.get(OWNER + 0x2D, 1))
                self.put(OWNER + 0x2C, state + 1, 1)
                if goal == cursor:
                    self.put(OWNER + 0x2D, goal + 1, 1)
                    goal, count = ring.byte_signed(self.get(OWNER + 0x2D, 1)), self.get(OWNER + 0x25, 1)
                    if goal == count:
                        self.put(OWNER + 0x2D, 0, 1)
                    self.put(OWNER + 0x2C, ring.byte_signed(self.get(OWNER + 0x2C, 1)) - 1, 1)
                point = [rounded('add', value, step) for value, step in zip(point, steps)]
                self.put(payload + 0x14, rounded('sub', self.get(payload + 0x14), bits(1.0)))
                if not floating(self.get(payload + 0x14)) > 1.0:
                    break
            else:
                raise AssertionError('sampling reference domain does not terminate')
            for axis, value in enumerate(point):
                self.put(payload + 4 + axis * 4, value)
            self.put(payload + 0x10, time)
        self.result = 1
        return self


class SamplingOracle(ring.RingOracle):
    def __init__(self, words, memory, mode=0, phase=0, entry=screen.ENTRY, symbols=None, connected=None):
        super().__init__(words, memory, mode, phase, entry, symbols or screen.SYMBOLS, connected)

    def record_call(self, target):
        if target == screen.ENTRY:
            self.callbacks.append(self.r[4])
        elif target == RELEASE:
            self.releases.append(self.r[4])
        else:
            assert target == self.symbols['func_151D8718']
            args = tuple(self.r[4:7])
            self.calls.append(args)
            self.events.append(('CALL', target, args))

    def hook(self, target):
        if target != RELEASE:
            assert target == self.symbols['func_151D8718']
            position, speed, delta = self.calls[-1]
            height, old = self.get(position + 4, 4), self.get(speed, 4)
            self.put(position + 4, height ^ delta, 4)
            self.put(speed, old ^ 0x01010101, 4)
            for address, value, width in actions(self.mode, len(self.calls) - 1, self.symbols):
                self.put(address, value, width)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]


class GameRecordRingSamplingTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-ring-sampling-test'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.normalized = screen.normalize(cls.words)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>166I', cls.rom, screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, mode=0, phase=0, words=None, entry=screen.ENTRY, symbols=None, trace=True):
        ref = SamplingReference(memory, mode, symbols)
        complete = ring.outcome(ref)
        models = []
        for body in ((self.words, self.normalized, self.retail) if words is None else (words, self.retail)):
            model = SamplingOracle(body, memory, mode, phase, entry, symbols)
            self.assertEqual(ring.outcome(model), complete)
            self.assertEqual((ring.public_memory(model), model.calls), (ring.public_memory(ref), ref.calls))
            if trace:
                self.assertEqual(ring.public_events(model), ref.events)
            if complete:
                self.assertEqual(model.r[2], ref.result)
            models.append(model)
        if words is None:
            self.assertEqual((models[1].r, models[1].f, models[1].memory, models[1].events),
                             (models[2].r, models[2].f, models[2].memory, models[2].events))
        return models, complete

    def test_01_complete_candidate_profiles_without_claiming_match(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), (166, 0xC8, 37))
        self.assertEqual((self.record['diagnostics'], self.record['pool_bytes']), ('', 0))
        self.assertNotEqual(self.words, self.retail)
        self.assertEqual(self.normalized, self.retail)
        for index in (0, *[int(row['offset'], 0) // 4 for row in screen.owner_guards()]):
            stale = self.words.copy()
            stale[index] ^= 1
            with self.assertRaises(AssertionError):
                screen.normalize(stale)
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, profile=p)[0] for p in ('o2g3', 'o2', 'o1g3', 'o1')]
        self.receipt('slot', dict(words=166, frame=0xC8, raw_differences=37, direct_words=129,
            guarded_words=37, no_insert_omit_or_relocation_changes=True,
            profiles=profiles, raw_difference_offsets=[i * 4 for i, (a, b) in enumerate(zip(self.words, self.retail)) if a != b]))

    def test_02_guest_bytes_interpolation_live_fields_aliases_and_retail_trace(self):
        count, seen = 0, set()
        for flag, progress, cur, goal, state, phase in itertools.product((0, 1), (0.0, 0.75, 1.0, 1.25, 2.25, 4.25), range(4), (0, 3), (0, 127, 255), (0, 8)):
            models, complete = self.compare(fixture(flag, progress, cur, goal, state=state), phase=phase)
            self.assertTrue(complete)
            seen.update(models[-1].visits)
            count += 1
        for byte in range(256):
            for memory in (fixture(flag=byte), fixture(current=byte), fixture(goal=byte), fixture(count=byte), fixture(state=byte)):
                self.assertTrue(self.compare(memory, phase=(byte & 1) * 8)[1])
                count += 1
        for mode, phase in itertools.product(range(10), (0, 8)):
            self.assertTrue(self.compare(fixture(), mode, phase)[1])
            count += 1
        for layout, phase in itertools.product((1, 2), (0, 8)):
            self.assertTrue(self.compare(fixture(layout=layout), phase=phase)[1])
            count += 1
        for delta in (-4.0, -1.0, 0.0, 0.5, 2.0, 4.0):
            self.assertTrue(self.compare(fixture(delta=delta))[1])
            count += 1
        for value in (0x80000000, 1, 0x7F800000, 0x7FC12345):
            memory = fixture()
            put(memory, PAYLOAD + 0x14, value)
            if value == 0x7F800000:
                continue
            self.assertTrue(self.compare(memory)[1])
            count += 1
        self.assertEqual(seen, set(range(screen.ENTRY, screen.ENTRY + 664, 4)) - {screen.ENTRY + 0x60})
        self.receipt('guest', dict(cases=count, all_256_actor_flag_current_goal_count_state_bytes=True,
            public_state_calls_return_and_access_trace=True, reachable_retail_words=165, compiler_dead_words=1,
            complete_normalized_GP_FP_private_state_and_trace=True, partial_overlap_not_portable_C=True,
            positive_infinite_progress_excluded_as_nonterminating=True))

    def test_03_lazy_gates_and_public_fault_prefixes(self):
        faults, lazy = 0, 0
        for flag, progress, phase in itertools.product((0, 1), (0.0, 2.25), (0, 8)):
            memory = fixture(flag=flag, progress=progress)
            ref = SamplingReference(memory).run()
            required = {event[1] + i for event in ref.events if event[0] != 'CALL' for i in range(event[2])}
            trimmed = {a: v for a, v in memory.items() if not ring.public(a) or a in required}
            self.assertTrue(self.compare(trimmed, phase=phase)[1])
            lazy += 1
        for mode, phase in itertools.product((0, 1, 5, 6, 7), (0, 8)):
            memory = fixture()
            ref = SamplingReference(memory, mode).run()
            for address, size in dict.fromkeys((event[1], event[2]) for event in ref.events if event[0] != 'CALL'):
                broken = dict(memory)
                del broken[address + size - 1]
                self.assertFalse(self.compare(broken, mode, phase)[1])
                faults += 1
        for field in (0x94, 0x98):
            memory = fixture()
            put(memory, OWNER + field, read(memory, OWNER + field) + 1)
            self.assertFalse(self.compare(memory)[1])
            faults += 1
        self.receipt('faults', dict(required_prefixes=faults, lazy_cases=lazy,
            public_prefix_and_partial_memory=True, normalized_complete_private_GP_FP_fault_state=True,
            portable_C_faults_and_CP0_not_modeled=True))

    def test_04_actual_native32_bytes_live_mutations_and_full_canaries(self):
        self.fixture = NATIVE_PREFIX + screen.DECLARATIONS + screen.SELECTED + NATIVE_CHECK
        self.run_host('unsigned cur,count,state,goal,flag,mode;\n'
            'for(cur=0;cur<256;cur++)for(count=0;count<256;count++){if(check(0,2.25f,cur,0,count,0,0))return 11;if(check(1,0.5f,cur,0,count,0,0))return 12;if(check(1,2.25f,cur,0,count,0,0))return 13;}\n'
            'for(state=0;state<256;state++)for(goal=0;goal<256;goal++)if(check(1,2.25f,3,goal,4,state,0))return 14;\n'
            'for(flag=0;flag<256;flag++)for(mode=0;mode<10;mode++)if(check(flag,2.25f,0,0,4,127,mode))return 15;')
        self.receipt('native', dict(executions=3 * 65536 + 65536 + 2560,
            actual_C_volatile_typed_call=True, full_current_count_pairs_and_state_goal_pairs=True,
            all_actor_flag_bytes_ten_mutations=True, canary_bytes=16384,
            independent_numeric_reference_calls_and_memory=True, prepared_native32_domain_only=True))

    def test_05_source_controls_and_effective_negative_mutations(self):
        samples = [(fixture(flag, progress, cur, goal, count), mode)
            for flag, progress, cur, goal, count, mode in ((0, 2.25, 0, 0, 4, 0),
                (1, 0.75, 0, 0, 4, 0), (1, 1.0, 0, 0, 4, 0),
                (1, 2.25, 3, 0, 4, 0), (1, 2.25, 127, 128, 128, 0),
                (1, 2.25, 255, 255, 4, 0))]
        samples += [(fixture(), mode) for mode in range(10)]
        records, ordinary, negatives = [], 0, 0
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, 'control-' + name, body)
            records.append(meta)
            equal = []
            for memory, mode in samples:
                ref, model = SamplingReference(memory, mode), SamplingOracle(words, memory, mode)
                expected, complete = ring.outcome(ref), ring.outcome(model)
                equal.append((complete, ring.public_memory(model), model.calls, model.r[2] if complete else None) ==
                    (expected, ring.public_memory(ref), ref.calls, ref.result if expected else None))
            if name.startswith('negative-'):
                self.assertFalse(all(equal), name)
                negatives += 1
            else:
                self.assertTrue(all(equal), name)
                ordinary += len(equal)
        self.receipt('controls', dict(forms=len(records), ordinary_executions=ordinary,
            effective_negatives=negatives, measurements=records))

    def test_06_complete_integrator_and_consuming_original_dispatcher(self):
        _, raw = velocity.screen.compile_candidate(self.root, self.out, 'velocity')
        helper = velocity.screen.normalize(raw)
        self.assertEqual(helper, list(struct.unpack_from('>19I', self.rom, velocity.screen.ROM)))
        dispatcher = list(struct.unpack_from('>100I', self.rom, 0x174BF0))
        count = 0
        for flag, progress, cur, goal, phase, parent in itertools.product((0, 1), (0.0, 0.75, 2.25), (0, 3), (0, 3), (0, 8), (False, True)):
            memory = fixture(flag, progress, cur, goal)
            put(memory, OWNER + 0x1E, 0, 2)
            put(memory, OWNER + 0x2F, 0, 1)
            put(memory, OWNER + 0x30, 16, 1)
            put(memory, TABLE + 16 * 4, screen.ENTRY)
            ref = SamplingReference(memory, actual=True).run()
            models = []
            for body in (self.words, self.normalized, self.retail):
                connected = dict(zip(range(velocity.screen.ENTRY, velocity.screen.ENTRY + 76, 4), helper))
                connected.update(zip(range(screen.ENTRY, screen.ENTRY + 664, 4), body))
                model = SamplingOracle(dispatcher if parent else body, memory, phase=phase,
                    entry=DISPATCHER if parent else screen.ENTRY, connected=connected).run()
                self.assertEqual((ring.public_memory(model), model.calls), (ring.public_memory(ref), ref.calls))
                if parent:
                    self.assertEqual(model.callbacks, [OWNER])
                    self.assertEqual(model.releases, [] if ref.result else [OWNER])
                else:
                    self.assertEqual((model.r[2], ring.public_events(model)), (ref.result, ref.events))
                models.append(model)
            self.assertEqual((models[1].r, models[1].f, models[1].memory, models[1].events),
                             (models[2].r, models[2].f, models[2].memory, models[2].events))
            count += 1
        self.receipt('connected', dict(cases=count, raw_normalized_retail_executions=count * 3, integrator_words=19,
            original_dispatcher_words=100, callback16_false_result_consumed=True,
            dispatcher_first_kind_zero_timer_flag_off_only=True, release_bounded_hook=True,
            linked_dispatcher_placeholder_not_restored=True, hardware_FCSR_gameplay_not_qualified=True))

    def test_07_copied_owners_real_padder_rebases_and_unchanged_link(self):
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
        self.assertEqual(text[target['value']:target['value'] + 664], isolated[:664])
        self.assertEqual({o - target['value']: r for o, r in rel.items() if target['value'] <= o < target['value'] + 664}, isolated_rel)
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            guards = list(csv.DictReader(stream))
        proposed = guards[:11168] + screen.owner_guards()
        assert_guard_history(self, proposed)
        for bad in (proposed[:-1], proposed + [dict(proposed[-1])], proposed[:11168] + list(reversed(screen.owner_guards()))):
            with self.assertRaises(AssertionError):
                assert_guard_history(self, bad)
        manifest = self.out / 'proposed.csv'
        with manifest.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=guards[0].keys())
            writer.writeheader()
            writer.writerows(proposed)
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
        self.assertEqual((functions[screen.FUNCTION]['size'], relocations), (664, isolated_rel))
        executions = 0
        for index, (entry, clock) in enumerate(zip((screen.ENTRY, 0x10007FFC, 0x7FFF8000, 0x80000000, 0x8FFF7FFC, 0x1FFF8000),
                (0x7FFC, 0x8000, 0xFFF8, 0x80007FFC, 0x80008000, 0xFFFF8000))):
            symbols = {'D_800BE9A4': clock, 'func_151D8718': (entry & 0xF0000000) + 0x108004}
            script, elf = self.out / 'padded.ld', self.out / ('rebased-%d.elf' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>166I', sections(elf)['.text'][1]))
            expected = list(self.retail)
            expected[0x6C // 4] = 0x3C040000 | (((clock + 0x8000) >> 16) & 65535)
            expected[0x78 // 4] = 0x24840000 | (clock & 65535)
            expected[0x188 // 4] = 0x0C000000 | ((symbols['func_151D8718'] >> 2) & 0x3FFFFFF)
            self.assertEqual(words, expected)
            for flag, mode, phase in itertools.product((0, 1), (0, 1, 5, 6, 7), (0, 8)):
                ref = SamplingReference(fixture(flag=flag, symbols=symbols), mode, symbols).run()
                model = SamplingOracle(words, fixture(flag=flag, symbols=symbols), mode, phase, entry, symbols).run()
                self.assertEqual((ring.public_memory(model), ring.public_events(model), model.calls, model.r[2]),
                    (ring.public_memory(ref), ref.events, ref.calls, ref.result))
                executions += 1
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        self.assertEqual((addresses[screen.FUNCTION], functions[screen.FUNCTION]), (screen.ENTRY, self.retail))
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            guards = list(csv.DictReader(stream))
        assert_guard_history(self, guards)
        self.assertIn(len(guards), (11168, 11205))
        source = (self.root / SOURCE).read_text()
        installed = screen.SELECTED in source
        self.assertIn(source, source_shapes(self.root))
        if not installed:
            self.assertEqual(hashlib.sha256((self.root / SOURCE).read_bytes()).hexdigest(),
                '7a21550c195ea94906d3c19c5521cb503786be0af2282916afa97fdf64f76245')
        self.assertEqual(guards[11168:], screen.owner_guards() if installed else [])
        found = [struct.unpack_from('>I', data, TABLE + 64 - address)[0] for address, data in
            sections(self.root / 'conker/build/conker.us.elf').values() if address <= TABLE + 64 < address + len(data)]
        self.assertEqual(found, [screen.ENTRY])
        self.receipt('owner-padder', dict(neighbors=len(current) - 1, unchanged_warning_count=len(diagnostics[0]),
            pools_relative_relocations_unchanged=True, padded_bytes=664, guards=37,
            independent_links=6, independently_expected_sites=3, executions=executions,
            live_source_installed=installed, live_linked_target_callback16_exact=True, guard_rows=len(guards)))


NATIVE_PREFIX = r'''
typedef signed char s8;typedef unsigned char u8;typedef int s32;typedef float f32;typedef unsigned int u32;
static u8 arena[16384] __attribute__((aligned(16))),expected[16384] __attribute__((aligned(16)));
f32 D_800BE9A4;static u32 expectedDelta,args[64][3];static unsigned used,total,error,mutation;
static u32 tobits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 frombits(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static int signbyte(unsigned value){return value<128?(int)value:(int)value-256;}
static f32 plus(f32 a,f32 b){volatile f32 value=a+b;return value;}
static f32 minus(f32 a,f32 b){volatile f32 value=a-b;return value;}
static f32 times(f32 a,f32 b){volatile f32 value=a*b;return value;}
static void effect(u8 *bytes,unsigned index,u32 *clock){
 if(index)return;
 if(mutation==1)bytes[32+0x2E]=3;
 if(mutation==2)bytes[32+0x25]=2;
 if(mutation==3)bytes[32+0x2D]=0;
 if(mutation==4)bytes[32+0x2C]=255;
 if(mutation==5)*(u8 **)(bytes+32+0x94)=arena+12288;
 if(mutation==6)*(u8 **)(bytes+32+0x98)=arena+384;
 if(mutation==7)*(f32 *)(bytes+224+0x14)=1.25f;
 if(mutation==8)*clock=tobits(8.0f);
 if(mutation==9){*(f32 *)(bytes+288+0x30)=128.0f;*(f32 *)(bytes+224+4)=64.0f;}
}
'''

NATIVE_CHECK = r'''
void func_151D8718(f32 *point,f32 *velocity,f32 time){
 u32 clock=tobits(D_800BE9A4);
 if(used>=total||(u32)point!=args[used][0]||(u32)velocity!=args[used][1]||tobits(time)!=args[used][2]){error=1;return;}
 *(u32 *)(point+1)^=tobits(time);*(u32 *)velocity^=0x01010101;
 effect(arena,used++,&clock);D_800BE9A4=frombits(clock);
}
static int check(unsigned flag,f32 progress,unsigned cursor,unsigned goal,unsigned count,unsigned state,unsigned mode){
 unsigned i,position,result=1;f32 point[3],current[3],step[3],fraction,time,timeStep;
 s32 (*volatile invoke)(u8 *)=func_151D7A38;u8 *owner=arena+32;
 if(sizeof(void*)!=4||sizeof(SamplingPayload151D7A38)!=24)return 1;
 for(i=0;i<16384;i++)arena[i]=(u8)(i*17+0xA5);
 *(u8 **)(owner+0x98)=arena+224;*(u8 **)(owner+0x94)=arena+4096;*(u8 **)(arena+224)=arena+288;
 *(u8 **)(arena+384)=arena+288;*(f32 *)(arena+384+0x14)=1.0f;
 owner[0x2E]=(u8)cursor;owner[0x2D]=(u8)goal;owner[0x25]=(u8)count;owner[0x2C]=(u8)state;arena[288+0x2D]=(u8)flag;
 *(f32 *)(arena+224+4)=1.0f;*(f32 *)(arena+224+8)=-2.0f;*(f32 *)(arena+224+12)=4.0f;
 *(f32 *)(arena+288+0x30)=5.0f;*(f32 *)(arena+288+0x34)=6.0f;*(f32 *)(arena+288+0x38)=-8.0f;
 *(f32 *)(arena+224+0x10)=2.0f;*(f32 *)(arena+224+0x14)=progress;
 D_800BE9A4=1.0f;expectedDelta=tobits(1.0f);mutation=mode;used=total=error=0;
 for(i=0;i<16384;i++)expected[i]=arena[i];
 if(!(flag&1))result=0;
 else{
  for(i=0;i<3;i++){current[i]=*(f32 *)(expected+288+0x30+i*4);*(f32 *)(expected+32+0x10+i*4)=current[i];}
  progress=plus(progress,0.25f);*(f32 *)(expected+224+0x14)=progress;
  if(progress>1.0f){
   fraction=1.0f/progress;time=plus(2.0f,1.0f);timeStep=times(time,fraction);
   for(i=0;i<3;i++){point[i]=*(f32 *)(expected+224+4+i*4);step[i]=times(minus(current[i],point[i]),fraction);}
   do{
    position=4096+(unsigned)(signbyte(expected[32+0x2E])*28);
    if(position+28>16384||total>=64)return 2;
    for(i=0;i<3;i++)*(f32 *)(expected+position+i*4)=point[i];
    *(u32 *)(expected+position+12)=0;*(u32 *)(expected+position+16)=0;expected[position+20]=0;*(u32 *)(expected+position+24)=0;
    args[total][0]=(u32)(arena+position);args[total][1]=(u32)(arena+position+12);args[total][2]=tobits(time);
    *(u32 *)(expected+position+4)^=tobits(time);*(u32 *)(expected+position+12)^=0x01010101;
    effect(expected,total++,&expectedDelta);
    expected[32+0x2E]=(u8)(expected[32+0x2E]+1);
    if(signbyte(expected[32+0x2E])==expected[32+0x25])expected[32+0x2E]=0;
    expected[32+0x2C]=(u8)(expected[32+0x2C]+1);
    if(expected[32+0x2D]==expected[32+0x2E]){
     expected[32+0x2D]=(u8)(expected[32+0x2D]+1);
     if(signbyte(expected[32+0x2D])==expected[32+0x25])expected[32+0x2D]=0;
     expected[32+0x2C]=(u8)(expected[32+0x2C]-1);
    }
    time=minus(time,timeStep);for(i=0;i<3;i++)point[i]=plus(point[i],step[i]);
    progress=minus(*(f32 *)(expected+224+0x14),1.0f);*(f32 *)(expected+224+0x14)=progress;
   }while(progress>1.0f);
   for(i=0;i<3;i++){*(f32 *)(expected+224+4+i*4)=point[i];}
   *(f32 *)(expected+224+0x10)=time;
  }
 }
 if((unsigned)invoke(owner)!=result||used!=total||error||tobits(D_800BE9A4)!=expectedDelta)return 3;
 for(i=0;i<16384;i++)if(arena[i]!=expected[i])return 4;
 return 0;
}
'''
