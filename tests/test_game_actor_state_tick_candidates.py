"""Bounded semantic screen, not installation acceptance for the actor-state tick."""

import hashlib
import itertools
import json
import struct
import unittest
from pathlib import Path

from tools.experiments import game_actor_state_tick_candidates as screen
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle, put
from tools.tests.test_game_record_neighbor_visit_match import read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.game_animation_timeline_oracle import bits, floating, signed


ROOT = Path(__file__).resolve().parents[2]
GLOBAL, ACTORS, EVENT_BYTES, DELTA, DIFFICULTY = 0x800D23B0, 0x800CC2D0, 0x800E0BB8, 0x800BE9E4, 0x800E0BD0
LIMIT, PERIOD, IDLE_PERIOD, CHANCE, SCALE = 0x800872C4, 0x800872D0, 0x800872E0, 0x800872E8, 0x800872F8
VIEWPORTS, LAST_PLAYER, FORMAT = 0x800BE628, 0x80082FA0, 0x8009DA20
STATE, ALT_STATE, ATTACHED, VIEWS = 0x20000, 0x24000, 0x90000, 0x70000
STATUS, BAND, SIGNAL, TRANSITION, ACTION, STEER, RANDOM, ZONES, COLOR, TEXT = (
    0x150859AC, 0x15085DA8, 0x1508EC5C, 0x1508DAEC, 0x1508EBF8,
    0x1508CAD8, 0x150ADA68, 0x1508B3F8, 0x1504332C, 0x15042D94)
ARITY = {STATUS: 2, SIGNAL: 2, TRANSITION: 2, ACTION: 2, STEER: 6,
         RANDOM: 0, ZONES: 0, COLOR: 4, TEXT: 5}


def s8(value):
    return value if value < 128 else value - 256


def s16(value):
    return value if value < 32768 else value - 65536


def f32(value):
    return floating(bits(value))


def private(address):
    return STACK - 0x2000 <= address < STACK + 0x100


def fixture(count=4, category=0xB7, delta=1, seed=0, active=0xFFFF, seen=0, action=0):
    memory = {STACK + i: 0xA5 for i in range(-0x2000, 0x100)}
    for base, size in ((STATE, 0x1900), (ALT_STATE, 0x1900), (ACTORS, 16 * 0x32C),
                       (ATTACHED, 16 * 0x200), (VIEWS, 16 * 0x180)):
        memory.update({base + i: 0xA5 for i in range(size)})
    for address, value, size in ((GLOBAL, STATE, 4), (DELTA, delta, 4), (DIFFICULTY, seed % 4, 1),
                                (VIEWPORTS, VIEWS, 4), (LAST_PLAYER, 3, 4)):
        put(memory, address, value, size)
    for i in range(4):
        for base, value, size in ((LIMIT, (-1, 0, 30, 31)[i], 2), (PERIOD, (-1, 0, 8, 30)[i], 1),
                                 (IDLE_PERIOD, (0, 1, 50, -128)[i], 1), (CHANCE, (-1, 0, 49, 99)[i], 1),
                                 (SCALE, bits(1.25 + i), 4)):
            put(memory, base + i * size, value, size)
    for base in (STATE, ALT_STATE):
        for offset, value, size in ((0x10, count, 4), (0x14, active, 4), (0x18, seen, 4),
                                    (0x16BC, category, 2)):
            put(memory, base + offset, value, size)
        for i in range(16):
            for offset, value in ((0x1C, 99), (0x5C, 0), (0x9C, 99), (0x11C, 7),
                    (0x19C, (seed + i) % 4), (0x21C, (seed * 7 + i * 11) % 32),
                    (0x25C, (seed + i * 13) % 64), (0x29C, (seed + i) % 12 - 5),
                    (0x31C, action), (0x35C, (seed + i) % 2), (0x39C, 99), (0x3DC, 99),
                    (0x41C, (seed + i) % 3), (0x4DC, 99), (0x59C, 99), (0xDDC, 20),
                    (0xE64, i % 4), (0xFF0, 17), (0x1574, (seed + i) * 59 - 2)):
                put(memory, base + offset + i * 4, value)
            for offset, value in ((0x1705, 127 - i), (0x1715, i - 128),
                                  (0x1725, i * 7 - 90), (0x1735, 80 - i * 11)):
                put(memory, base + offset + i, value, 1)
    for i in range(16):
        actor = ACTORS + i * 0x32C
        attached = ATTACHED + i * 0x200
        for offset, value, size in ((0x14, bits(i * 17.25), 4), (0x18, bits(i * 3.5), 4),
                (0x1C, bits(-i * 12.75), 4), (0x128, (seed + i) % 2, 1),
                (0x1E4, 0xA5, 1), (0x20F, (0xFF, 0, 7, 128)[(seed + i) % 4], 1),
                (0x222, 0xA5, 1), (0x22C, (0xA1FF, 0xA3FF)[(seed + i) % 2], 2),
                (0x232, (0, 4, 5, 255)[(seed + i) % 4], 1), (0x2FD, (seed + i) % 2, 1),
                (0x31C, attached, 4)):
            put(memory, actor + offset, value, size)
        put(memory, attached + 0x19A, (seed + i * 17) & 255, 1)
        put(memory, attached + 0x1AC, (seed + i) % 2, 1)
        put(memory, EVENT_BYTES + i, ((i + 1) % max(count, 1)) | (0x80 if (seed + i) % 2 else 0), 1)
        for offset, value in ((0x24, 20.75 + i), (0x2C, 4.75 + i), (0x30, 101.25 + i)):
            put(memory, VIEWS + i * 0x180 + offset, bits(value))
    return memory


class Providers:
    """Shared bounded opaque provider contract; the state machine is independent."""

    def __init__(self, status=1, steering=0, randoms=(0.0, 0.25, 0.5, 0.75, 1.0), actions=None):
        self.status, self.steering = status, steering
        self.randoms, self.random_index = randoms, 0
        self.actions, self.calls, self.occurrences = actions or {}, [], {}

    def call(self, target, arguments, store):
        self.calls.append((target, *arguments))
        occurrence = self.occurrences.get(target, 0)
        self.occurrences[target] = occurrence + 1
        for address, value, size in self.actions.get((target, occurrence), ()):
            store(address, value, size)
        if target == STATUS:
            return self.status
        if target == BAND:
            return 3
        if target == STEER:
            return self.steering
        if target == RANDOM:
            value = bits(self.randoms[self.random_index % len(self.randoms)])
            self.random_index += 1
            return value
        return 0x12345678


class TickOracle(TriangleOracle):
    def __init__(self, words, memory, phase=0, **providers):
        super().__init__(words, memory, phase=phase, entry=screen.ENTRY, arguments=())
        self.provider = Providers(**providers)

    def record_call(self, target):
        arguments = (self.f[12],) if target == BAND else self.arguments(ARITY[target])
        self.calls.append((target, *arguments))

    def hook(self, target):
        arguments = (self.f[12],) if target == BAND else self.arguments(ARITY[target])
        result = self.provider.call(target, arguments, self.put)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        if target == RANDOM:
            self.f[0] = result
        else:
            self.r[2] = result

    def execute(self, word):
        if word >> 26 == 32:
            rs, rt, immediate = word >> 21 & 31, word >> 16 & 31, word & 65535
            address = (self.r[rs] + s16(immediate)) & 0xFFFFFFFF
            self.r[rt] = s8(self.get(address, 1)) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)


def reference(memory, **options):
    memory, stores = dict(memory), []
    providers = Providers(**options)

    def get(address, size=4):
        return read(memory, address, size)

    def store(address, value, size=4):
        put(memory, address, value, size)
        stores.append((address, size, value & ((1 << size * 8) - 1)))

    def context():
        return get(GLOBAL)

    def category():
        return s16(get(context() + 0x16BC, 2))

    def difficulty():
        return s8(get(DIFFICULTY, 1))

    def call(target, *args):
        return providers.call(target, tuple(a & 0xFFFFFFFF for a in args), store)

    def random():
        return floating(call(RANDOM))

    captured = context()
    active, seen, count = get(captured + 0x14), get(captured + 0x18), signed(get(captured + 0x10))
    changed = 0
    for slot in range(max(count, 0)):
        bit, offset = 1 << slot, slot * 4
        reset, status, band = (captured + b + offset for b in (0x1C, 0x39C, 0x9C))
        store(reset, 0)
        first = not active & bit and not seen & bit
        if not active & bit:
            seen |= bit
        if not (active & bit or first):
            store(status, 0)
            store(band, -1)
            continue
        actor = ACTORS + slot * 0x32C
        group = signed(get(captured + 0xE64 + offset))
        state, elapsed, cooldown, timer, action, latch, event, timeout, score = (
            captured + b + offset for b in (0x19C, 0x21C, 0x25C, 0x29C, 0x31C, 0x35C, 0x3DC, 0x41C, 0x1574))
        idle = True
        if group and category() == 0xB9:
            store(actor + 0x1E4, 1, 1)
        previous_timer = signed(get(timer))
        store(elapsed, get(elapsed) + get(DELTA))
        store(timer, get(timer) + get(DELTA))
        for address, inclusive in ((cooldown, True), (timeout, True), (score, False)):
            value = signed((get(address) - get(DELTA)) & 0xFFFFFFFF)
            store(address, value)
            if value < 0 or inclusive and value == 0:
                store(address, 0)
        if get(state) == 3 and get(cooldown) & 31 >= 29:
            call(SIGNAL, slot, 0x8000)
        store(event, get(EVENT_BYTES + slot, 1))
        store(EVENT_BYTES + slot, get(EVENT_BYTES + slot, 1) & 0x7F, 1)
        if context() != 0xFFFFFB24:
            store(context() + offset + 0x4DC, get(get(actor + 0x31C) + 0x19A, 1))
        store(status, call(STATUS, s16(slot & 65535), 4))
        store(band, call(BAND, get(actor + 0x18)))
        if get(status) == 0 or first or get(actor + 0x2FD, 1):
            if get(latch) == 0:
                value = get(actor + 0x20F, 1)
                store(context() + offset + 0x59C, value if value != 255 else -1)
                store(latch, 1)
                store(cooldown, 0)
                store(state, 0)
                store(context() + offset + 0x5C, 1)
                store(context() + offset + 0x11C, -1)
                address = captured + 0xDDC + group * 4
                store(address, get(address) - 1)
                value = get(event) & 127
                if value < count:
                    owner = signed(get(captured + 0xE64 + value * 4))
                    if owner != group:
                        address = captured + 0xDDC + owner * 4
                        store(address, get(address) + 1)
                if category() != 0xB9:
                    store(context() + offset + 0xFF0, 0)
                    call(TRANSITION, slot, 1)
                changed |= bit
        else:
            store(latch, 0)
        if get(action) != 0 and category() != 0xB8:
            if get(state) != 1 and signed(get(elapsed)) < 30:
                actor_action = get(actor + 0x232, 1)
                store(actor + 0x222, get(action) - 2, 1)
                if actor_action not in (4, 5):
                    call(ACTION, slot, 4)
                if actor_action == 4:
                    store(elapsed, 0)
                if actor_action == 5:
                    store(elapsed, 30)
                    store(context() + offset + 0x1868, get(SCALE + difficulty() * 4))
                    value = f32(f32(random() * 50.0) + floating(get(actor + 0x14)))
                    store(context() + offset + 0x17A8, bits(value))
                    store(context() + offset + 0x17E8, bits(f32(floating(get(actor + 0x18)) + 40.0)))
                    value = f32(f32(random() * 50.0) + floating(get(actor + 0x1C)))
                    store(context() + offset + 0x1828, bits(value))
                    value = signed(get(action))
                    if value - 2 >= 2:
                        other = ACTORS + value * 0x32C - 0x658
                        for dest, coordinate in ((0x17A8, 0x14), (0x1828, 0x1C)):
                            address = context() + offset + dest
                            difference = f32(floating(get(other + coordinate)) - floating(get(actor + coordinate)))
                            store(address, bits(f32(floating(get(address)) + f32(difference * 0.5))))
            idle = False
            if s8(get(PERIOD + difficulty(), 1)) < signed(get(timer)):
                store(timer, 0)
                previous_timer = -1
            started = signed(get(timer)) >= 0 and previous_timer < 0
            limit = s16(get(LIMIT + difficulty() * 2, 2))
            expired = limit != -1 and signed(get(elapsed)) >= limit
            for current, target in ((0x1725, 0x1705), (0x1735, 0x1715)):
                address = context() + slot
                value = s8(get(address + current, 1))
                store(address + current, value + ((s8(get(address + target, 1)) - value) >> 2), 1)
            row = context() + slot
            result = call(STEER, slot, get(action) - 2, int(started), int(expired),
                          s8(get(row + 0x1725, 1)), s8(get(row + 0x1735, 1)))
            if result and get(state) != 1:
                store(elapsed, 0)
            if get(timer) == 0:
                store(context() + slot + 0x1705, 0, 1)
                store(context() + slot + 0x1715, 0, 1)
                probability = int(f32(random() * 100.0))
                if s8(get(CHANCE + difficulty(), 1)) < probability:
                    store(context() + slot + 0x1705, -50 if random() > 0.5 else 50, 1)
                    store(context() + slot + 0x1715, 50 if random() > 0.5 else 0, 1)
        if idle and category() != 0xB8:
            store(timer, -s8(get(IDLE_PERIOD + difficulty(), 1)))
        flags = get(actor + 0x22C, 2)
        store(actor + 0x22C, flags & 0xFDFF, 2)
        if flags & 0x200 or get(event) & 0x80:
            store(state, 0)
            store(reset, 1)
        if get(get(actor + 0x31C) + 0x1AC, 1):
            store(cooldown, 20)
    store(context() + 0x18, seen)
    delta = signed(get(DELTA))
    store(context() + 0x16B4, bits(float(delta) if delta else 1.0))
    if context() != 0xFFFFFAA4:
        call(ZONES)
    if category() == 0xB9:
        views = get(VIEWPORTS)
        half_width = int(f32(floating(get(views + 0x30)) - floating(get(views + 0x2C)))) >> 1
        call(COLOR, 255, 255, 255, 255)
        index = 0
        while index <= signed(get(LAST_PLAYER)):
            if get(ACTORS + index * 0x32C + 0x128, 1) == 0:
                view = get(VIEWPORTS) + index * 0x180
                x = int(f32(floating(get(view + 0x2C)) + float(half_width)))
                y = int(f32(floating(get(view + 0x24)) + 6.0))
                score = signed(get(captured + 0x1574 + index * 4))
                quotient = abs(score) // 60 * (-1 if score < 0 else 1)
                call(TEXT, x, y, 1, FORMAT, quotient)
            index += 1
    return memory, providers.calls, stores, changed


class ActorStateTickCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ROOT
        cls.output = cls.root / screen.BUILD / 'test'
        screen.freeze(cls.root, cls.root / screen.BUILD)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.output, 'baseline')
        cls.retail = struct.unpack_from('>678I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM)
        cls.coverage, cls.completed = set(), 0

    @classmethod
    def tearDownClass(cls):
        result = dict(completed_pairs=cls.completed, retail_words_visited=len(cls.coverage),
                      retail_words=678, source_words=cls.record['body_words'], frame=cls.record['frame'],
                      installed=False, matching_credit=0,
                      boundary='Bounded semantic screen; no private-frame/access-fault/native/caller acceptance')
        (cls.output / 'semantic-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
        print('actor-state tick:', result)

    def compare(self, memory, phase=0, **providers):
        expected_memory, calls, stores, result = reference(memory, **providers)
        for (target, occurrence) in providers.get('actions', {}):
            self.assertGreater(sum(c[0] == target for c in calls), occurrence,
                               'Requested opaque-provider mutation did not fire')
        for label, words in (('retail', self.retail), ('candidate', self.words)):
            actual = TickOracle(words, memory, phase, **providers).run()
            self.assertEqual(actual.calls, calls, label)
            self.assertEqual([s for s in actual.stores if not private(s[0])], stores, label)
            self.assertEqual({a: b for a, b in actual.memory.items() if not private(a)},
                             {a: b for a, b in expected_memory.items() if not private(a)}, label)
            self.assertEqual(actual.r[2], result, label)
            if label == 'retail':
                type(self).coverage.update(actual.visits)
        type(self).completed += 1

    def test_complete_body_is_explicitly_not_a_match_or_installation(self):
        self.assertEqual(self.record['diagnostics'], '')
        self.assertEqual((self.record['body_words'], self.record['frame']), (658, 328))
        self.assertNotEqual(self.words, self.retail)
        self.assertFalse(self.record['installed'])
        self.assertEqual(self.record['matching_credit'], 0)

    def test_empty_inactive_first_seen_and_all_sixteen_slots(self):
        for count, phase, mask in itertools.product((-1, 0, 1, 4, 16), (0, 8),
                                                    ((0, 0), (0, 0xFFFF), (0xFFFF, 0), (5, 10))):
            self.compare(fixture(count=count, active=mask[0], seen=mask[1]), phase)

    def test_categories_timer_signs_states_actions_and_probability(self):
        for category, delta, action, seed in itertools.product((0xB7, 0xB8, 0xB9), (0, 1, 2, -1),
                                                              (0, 2, 4, 17), range(4)):
            with self.subTest(category=category, delta=delta, action=action, seed=seed):
                self.compare(fixture(category=category, delta=delta, action=action, seed=seed),
                             status=seed % 2, steering=seed // 2)

    def test_opaque_helpers_can_replace_global_and_mutate_captured_inputs(self):
        for target in (SIGNAL, STATUS, BAND, TRANSITION, ACTION, STEER, RANDOM, ZONES, COLOR, TEXT):
            memory = fixture(category=0xB7 if target == TRANSITION else 0xB9, action=5, seed=0)
            put(memory, STATE + 0x19C, 3)
            put(memory, STATE + 0x25C, 30)
            if target == TRANSITION:
                put(memory, ACTORS + 0x2FD, 1, 1)
            for changes in (((GLOBAL, ALT_STATE, 4),),
                            ((DELTA, 2, 4), (STATE + 0x10, 1, 4), (DIFFICULTY, 3, 1)),
                            ((STATE + 0x31C, 4, 4), (STATE + 0x14, 0, 4), (STATE + 0x18, 0xFFFF, 4))):
                with self.subTest(target=hex(target), changes=changes):
                    self.compare(memory, actions={(target, 0): changes})

    def test_effective_wrong_width_stride_and_predicate_controls(self):
        cases = (
            ('wide-actor-flag', screen.BASELINE.replace('actor[0x2FD] != 0', '*(u32 *)(actor + 0x2FC) != 0'),
             fixture(seed=0)),
            ('four-word-stride', screen.BASELINE.replace('            band++;', '            band += 4;'),
             fixture(active=0, seen=0xFFFF)),
            ('inclusive-random', screen.BASELINE.replace('func_150ADA68() > 0.5f', 'func_150ADA68() >= 0.5f'),
             fixture(action=5, seed=1)),
        )
        for name, body, memory in cases:
            with self.subTest(control=name):
                _, words = screen.compile_candidate(self.root, self.output, name, body)
                actual = TickOracle(words, memory, randoms=(0.5, 1.0)).run()
                expected, calls, stores, result = reference(memory, randoms=(0.5, 1.0))
                observed = ([s for s in actual.stores if not private(s[0])], actual.calls, actual.r[2])
                self.assertNotEqual(observed, (stores, calls, result), 'Ineffective semantic control')

    def test_stale_input_is_rejected_without_changing_production(self):
        from unittest.mock import patch
        wrong = dict(screen.INPUTS)
        wrong['conker/asm/B3020.s'] = '0' * 64
        with patch.object(screen, 'INPUTS', wrong):
            with self.assertRaisesRegex(ValueError, 'Actor tick input changed'):
                screen.freeze(self.root, self.output / 'stale-control')
        for name, digest in screen.INPUTS.items():
            self.assertEqual(hashlib.sha256((self.root / name).read_bytes()).hexdigest(), digest)

    def test_both_complete_owner_profiles_preserve_all_other_functions_and_pools(self):
        result = screen.owner_screen(self.root, self.output / 'owner')
        self.assertEqual([r['profile'] for r in result], ['primary', 'normal'])
        for row in result:
            self.assertEqual(row['preserved_neighbors'], 72)
            self.assertTrue(row['pools_unchanged'])
            self.assertTrue(row['isolated_words_and_bindings_equal'])
            self.assertEqual((row['body_words'], row['frame']), (658, 328))


if __name__ == '__main__':
    unittest.main()
