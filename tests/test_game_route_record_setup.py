"""Three-word ABI, closed routes, allocation effects and non-installable C model."""
import csv
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_route_record_setup as source
from tools.tests import test_game_route_vector_builder as base
from tools.tests import test_game_record_neighbor_selector as neighbor
from tools.tests.test_game_record_progress_lap import LapOracle

put, read, STACK = base.put, base.read, base.STACK
ROUTES, ARENA, OTHER, ALIAS = 0x30000, 0x50000, 0x60000, 0x3F000000
TABLE, COUNT, ROUTE_TABLE = 0x800872A0, 0x80087290, 0x800D2350
MODE, PLAYERS, EXTRAS, READY, MASK, HUMAN = 0x800D23A8, 0x800D2398, 0x800D2399, 0x800D239A, 0x800D2394, 0x8008FD90
LOOKUP, SELECTOR, INITIALIZE, ALLOCATE = 0x15086D48, 0x150888A8, 0x15088824, 0x10003C40
HELPERS = {LOOKUP: 19, SELECTOR: 88, INITIALIZE: 33}
CONSTRUCTOR = ((0x2B, 0, 1), (0x2C, 0, 1), (0x2D, 0, 1), (0x2E, 0, 1), (0x28, 0, 1),
    (0x1C, 0, 4), (0x18, 0, 4), (0x20, 0xFFFFFFFF, 4), (0x2F, 0, 1), (8, 0, 4),
    (0, 0x3F000000, 4), (4, 0x3F000000, 4), (0x24, 0, 2), (0x26, 0, 1), (0x27, 0, 1),
    (0x31, 0, 1), (0xC, 0, 4), (0x14, 0, 4), (0x33, 2, 1), (0x30, 0, 1),
    (0x2A, 127, 1), (0x49, 0, 1), (0x10, 0x3F800000, 4))


def signed(value, bits=32):
    return ((value & ((1 << bits) - 1)) ^ (1 << (bits - 1))) - (1 << (bits - 1))


def public(memory):
    return {at: value for at, value in memory.items() if not STACK - 0x400 <= at < STACK + 0x400}


def allocation_effect(memory, mode):
    if mode == 1:
        put(memory, PLAYERS, 255, 1)
        put(memory, HUMAN, 128, 1)
    if mode == 4:
        put(memory, MASK, 0xCAFEBABE)
        put(memory, EXTRAS, 0x7E, 1)
        put(memory, READY, 0x5A, 1)
    return {2: OTHER, 3: PLAYERS - 0x30, 5: TABLE, 6: 0}.get(mode, ARENA)


def fixture(length=3, mode=0, players=2, extras=1, key=7, gate=0, allocation=0, first=0, human=4):
    total = signed(players + extras)
    if total > 260:
        raise ValueError('Fixture has an unbounded positive allocation')
    capacity = max(1, total) * 132 + 16
    m = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x400, 0x400)}
    for at, size in ((ROUTES, 8192), (ARENA, capacity), (OTHER, capacity), (ALIAS, capacity),
                     (0x80087280, 128), (0x800D2300, 1024), (0x8008FD80, 32)):
        m.update({at + i: 0xA5 for i in range(size)})
    for i in range(512):
        put(m, ROUTES + i * 16 + 7, (key + 1) & 255, 1)
        for j in range(5):
            put(m, ROUTES + i * 16 + 9 + j, 255, 1)
        put(m, ROUTES + i * 16 + 14, 0, 1)
        put(m, ROUTES + i * 16 + 15, 0, 1)
    start = first & 255
    ids = [(start + i) % 255 for i in range(length)]
    for index, node in enumerate(ids):
        put(m, ROUTES + node * 16 + 9, ids[(index + 1) % length], 1)
        put(m, ROUTES + node * 16 + 10, ids[index - 1], 1)
    put(m, ROUTES + ids[1 % length] * 16 + 15, 1, 1)
    if gate != 1:
        put(m, ROUTES + first * 16 + 7, key & 255, 1)
    if gate == 2:
        for node in ids:
            put(m, ROUTES + node * 16 + 14, 1, 1)
    if gate in (3, 4):
        for node in ids:
            for j in range(5):
                put(m, ROUTES + node * 16 + 9 + j, 255, 1)
        put(m, ROUTES + ids[0] * 16 + 9, ids[1], 1)
        if gate == 4:
            put(m, ROUTES + ids[1] * 16 + 9, ids[2], 1)
            put(m, ROUTES + ids[2] * 16 + 9, ids[0], 1)
    put(m, COUNT, 0 if gate == 5 else 0xFFFF if gate == 6 else max(first + 1, length), 2)
    for at, value, size in ((TABLE, 0xA5A5A5A5, 4), (ROUTE_TABLE, ROUTES, 4), (MODE, mode, 1),
                             (PLAYERS, 0xA5, 1), (EXTRAS, 0xA5, 1), (READY, 0xA5, 1),
                             (MASK, 0x5AA55AA5, 4), (HUMAN, human, 1)):
        put(m, at, value, size)
    return m, tuple(value & 0xFFFFFFFF for value in (key, players, extras)), allocation


class NonTerminatingRoute(Exception):
    pass


def reference(initial, args, allocation):
    memory = dict(initial)
    calls, trace = [], []

    def get(at, n=4):
        value = read(memory, at, n)
        trace.append(('R', at, n, value))
        return value

    def store(at, value, n=4):
        put(memory, at, value, n)
        trace.append(('W', at, n, value & ((1 << (8 * n)) - 1)))

    def select(excluded, node):
        call = (excluded & 255, node & 255, 0)
        calls.append((SELECTOR, call))
        result, reads = neighbor.reference(memory, call, ROUTE_TABLE)
        trace.extend(('R', at, n, value) for at, n, value in reads)
        return result & 255

    store(TABLE, 0)
    calls.append((LOOKUP, args[:1]))
    size = signed(get(COUNT, 2), 16)
    first = 255
    if size > 0:
        bank = get(ROUTE_TABLE)
        for i in range(size):
            if get(bank + i * 16 + 7, 1) == args[0]:
                first = i & 255
                break
    if first == 255:
        return memory, calls, trace
    mode = signed(get(MODE, 1), 8)
    bank = get(ROUTE_TABLE)
    best = mode * 255 & 255
    chosen = 255
    for i in range(5):
        candidate = get(bank + first * 16 + i + 9, 1)
        if candidate != 255 and get(bank + candidate * 16 + 14, 1) == 0:
            kind = get(bank + candidate * 16 + 15, 1)
            if kind >= best if mode == 0 else kind <= best:
                best, chosen = kind, candidate
    if chosen == 255:
        return memory, calls, trace
    after = select(first, chosen)
    previous = select(chosen, first)
    if previous == 255 or after == 255:
        return memory, calls, trace
    old, current, length, seen = chosen, after, 0, set()
    while True:
        if (old, current) in seen:
            raise NonTerminatingRoute((old, current))
        seen.add((old, current))
        following = select(old, current)
        length += 1
        if old == first:
            break
        old, current = current, following
    store(EXTRAS, args[2], 1)
    store(PLAYERS, args[1], 1)
    total = signed(args[1] + args[2])
    store(MASK, 0)
    snapshot = (read(memory, TABLE), read(memory, PLAYERS, 1), read(memory, EXTRAS, 1), read(memory, MASK), read(memory, READY, 1))
    calls.append((ALLOCATE, ((total * 132) & 0xFFFFFFFF, 1, 0, 0), snapshot))
    result = allocation_effect(memory, allocation)
    store(TABLE, result)
    for index in range(max(total, 0)):
        record = (get(TABLE) + index * 132) & 0xFFFFFFFF
        calls.append((INITIALIZE, (record,)))
        for offset, value, n in CONSTRUCTOR:
            store((record + offset) & 0xFFFFFFFF, value, n)
        for offset, value in ((0x2B, previous), (0x2D, chosen), (0x2E, after), (0x2C, first)):
            store((record + offset) & 0xFFFFFFFF, value, 1)
        if index < signed(get(PLAYERS, 1), 8):
            store((record + 0x31) & 0xFFFFFFFF, index, 1)
        human = signed(get(HUMAN, 1), 8)
        store((record + 0x26) & 0xFFFFFFFF, length, 1)
        store((record + 0x30) & 0xFFFFFFFF, index >= human, 1)
    store(READY, 1, 1)
    return memory, calls, trace


class SetupOracle(LapOracle):
    def __init__(self, words, memory, args, helpers, allocation=0, phase=0, entry=source.ENTRY):
        self.allocation = allocation
        super().__init__(words, memory, args, [], phase, entry, connected=helpers)

    def record_call(self, target):
        count = {LOOKUP: 1, SELECTOR: 3, INITIALIZE: 1, ALLOCATE: 4}[target]
        args = self.arguments(count)
        if target == ALLOCATE:
            snapshot = (read(self.memory, TABLE), read(self.memory, PLAYERS, 1), read(self.memory, EXTRAS, 1),
                        read(self.memory, MASK), read(self.memory, READY, 1))
            self.calls.append((target, args, snapshot))
        else:
            self.calls.append((target, args))

    def hook(self, target):
        if target != ALLOCATE:
            raise AssertionError('Only the allocator may be an opaque provider')
        result = allocation_effect(self.memory, self.allocation)
        for i in range(4):
            put(self.memory, self.r[29] + i * 4, 0xB5000000 + i)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result


class FullTraceOracle(SetupOracle):
    def __init__(self, *args, **kwargs):
        self.complete_trace = []
        super().__init__(*args, **kwargs)

    def get(self, at, n):
        value = super().get(at, n)
        self.complete_trace.append(('R', at, n, value))
        return value

    def put(self, at, value, n):
        super().put(at, value, n)
        self.complete_trace.append(('W', at, n, value & ((1 << (8 * n)) - 1)))


class WindowStop(Exception):
    pass


class CallerOracle(SetupOracle):
    def record_call(self, target):
        if target == source.ENTRY:
            self.forwarded.append(self.arguments(3))
            self.caller_saved = ([self.r[i] for i in (*range(16, 24), 28, 29, 30)], self.f[20:])
            return
        super().record_call(target)

    def execute(self, word):
        if self.current_pc == 0x1509E1C0:
            if self.caller_saved != ([self.r[i] for i in (*range(16, 24), 28, 29, 30)], self.f[20:]):
                raise AssertionError('Setup did not restore the real caller saved ABI')
        if self.current_pc == 0x1509E3C8:
            self.stopped = True
            raise WindowStop
        return super().execute(word)


def corpus():
    for length, mode, players, extras, human in itertools.product(
            (3, 4, 7), (0, 1, 2, 128, 255), (0, 1, 3), (0, 1, 2), (0, 2, 128)):
        yield (length, mode, players, extras, 7, 0, 0, 0, human)
    for gate, key, mode in itertools.product(range(1, 7), (0, 7, 128, 255, -1, 256), (0, 1)):
        yield (3, mode, 2, 1, key, gate, 0, 0, 4)
    for allocation, mode, phase in itertools.product(range(1, 6), (0, 1, 255), (0, 1)):
        yield (3, mode, 2 + phase, 1, 7, 0, allocation, 0, 4)
    for first in (127, 128, 254, 255, 256, 511):
        yield (3, 0, 2, 1, 7, 0, 0, first, 4)
    for players, extras in ((127, 1), (128, 0), (255, 1), (256, 0), (-129, 130),
                            (-1, 2), (0x7FFFFFFF, 1), (0x80000000, 0),
                            (0x80000000, 0x80000000), (0x7FFFFFFF, 0x80000002), (-1, 1)):
        yield (3, 0, players, extras, 7, 0, 6 if signed(players + extras) <= 0 else 0, 0, 4)
    for length, mode in itertools.product((128, 254, 255), (0, 1)):
        yield (length, mode, 1, 1, 7, 0, 0, 0, 4)


NATIVE = r'''
#include <ultra64.h>
typedef union {u32 alignment; u8 b[132 * 260 + 16];} Bank;
static Bank arena, other;
static u8 routes[8192], originalRoutes[8192];
u8 *D_800872A0, *D_800D2350;
s16 D_80087290;
s8 D_800D23A8, D_800D2398, D_800D2399, D_800D239A, D_8008FD90;
s32 D_800D2394;
static u32 calls[1024][10], callCount, allocationMode;
static void stop(u32 code) { __asm__ volatile("int $0x80"::"a"(1),"b"(code)); __builtin_unreachable(); }
static u32 canonicalPointer(u8 *p) {
    u32 a = (u32)p - (u32)arena.b, b = (u32)p - (u32)other.b;
    if (!p) return 0;
    if (a < sizeof(arena.b)) return 0x50000u + a;
    if (b < sizeof(other.b)) return 0x60000u + b;
    return (u32)p;
}
static u32 *call(u32 id) {
    u32 *row;
    if (callCount == 1024) stop(23);
    row = calls[callCount++]; row[0] = id; return row;
}
s32 func_15086D48_body(s32);
s32 func_150888A8_body(u8, u8, s8);
void func_15088824_body(u8 *);
s32 func_15086D48(s32 key) {
    call(1)[1] = key; return func_15086D48_body(key);
}
s32 func_150888A8(u8 a, u8 b, s8 c) {
    u32 *row = call(2); row[1] = a; row[2] = b; row[3] = (s32)c;
    return func_150888A8_body(a, b, c);
}
void func_15088824(u8 *p) {
    call(3)[1] = canonicalPointer(p); func_15088824_body(p);
}
void *allocate_memory(u32 size, s32 a, s32 b, s32 c) {
    u32 *row = call(4); row[1] = size; row[2] = a; row[3] = b; row[4] = c;
    row[5] = canonicalPointer(D_800872A0); row[6] = (u8)D_800D2398;
    row[7] = (u8)D_800D2399; row[8] = D_800D2394; row[9] = (u8)D_800D239A;
    if (allocationMode == 1) {D_800D2398 = -1; D_8008FD90 = -128;}
    if (allocationMode == 4) {D_800D2394 = (s32)0xCAFEBABE; D_800D2399 = 0x7E; D_800D239A = 0x5A;}
    return allocationMode == 6 ? 0 : allocationMode == 2 ? other.b : arena.b;
}
void func_150870D0(s32, s32, s32);
HELPER_BODIES
TARGET_BODY
static const u8 templates[][132] = {TEMPLATES};
static const u32 expectedCalls[][10] = {CALLS};
static const u32 expectedRecords[] = {RECORDS};
typedef struct {u32 p[9], globals[7], records, callAt, callCount;} Case;
static const Case cases[] = {CASES};
static u8 canonicalByte(u8 *p, u32 at) {
    u32 start, n = 0, value;
    if (at < 0x24) {start = at & ~3u; n = 4;}
    else if (at < 0x26) {start = 0x24; n = 2;}
    else return p[at];
    value = n == 4 ? *(u32 *)(p + start) : *(u16 *)(p + start);
    return value >> ((n - 1 - (at - start)) * 8);
}
static void setup(const Case *c) {
    u32 i, j, start = c->p[7] & 255u, length = c->p[0];
    for (i = 0; i < sizeof(arena.b); i++) arena.b[i] = other.b[i] = 0xA5;
    for (i = 0; i < sizeof(routes); i++) routes[i] = 0xA5;
    for (i = 0; i < 512; i++) {
        routes[i * 16 + 7] = c->p[4] + 1;
        for (j = 0; j < 5; j++) routes[i * 16 + 9 + j] = 255;
        routes[i * 16 + 14] = routes[i * 16 + 15] = 0;
    }
    for (i = 0; i < length; i++) {
        u32 node = (start + i) % 255;
        routes[node * 16 + 9] = (start + (i + 1) % length) % 255;
        routes[node * 16 + 10] = (start + (i + length - 1) % length) % 255;
    }
    routes[((start + 1 % length) % 255) * 16 + 15] = 1;
    if (c->p[5] != 1) routes[c->p[7] * 16 + 7] = c->p[4];
    if (c->p[5] == 2) for (i = 0; i < length; i++) routes[((start + i) % 255) * 16 + 14] = 1;
    if (c->p[5] == 3 || c->p[5] == 4) {
        for (i = 0; i < length; i++) for (j = 0; j < 5; j++) routes[((start + i) % 255) * 16 + 9 + j] = 255;
        routes[start * 16 + 9] = (start + 1) % 255;
        if (c->p[5] == 4) {
            routes[((start + 1) % 255) * 16 + 9] = (start + 2) % 255;
            routes[((start + 2) % 255) * 16 + 9] = start;
        }
    }
    D_80087290 = c->p[5] == 5 ? 0 : c->p[5] == 6 ? -1 :
        (s32)(c->p[7] + 1 > length ? c->p[7] + 1 : length);
    for (i = 0; i < sizeof(routes); i++) originalRoutes[i] = routes[i];
    D_800872A0 = (u8 *)0xA5A5A5A5u; D_800D2350 = routes;
    D_800D23A8 = c->p[1]; D_8008FD90 = c->p[8];
    D_800D2398 = D_800D2399 = D_800D239A = (s8)0xA5;
    D_800D2394 = 0x5AA55AA5; allocationMode = c->p[6]; callCount = 0;
    for (i = 0; i < 1024; i++) for (j = 0; j < 10; j++) calls[i][j] = 0;
}
void _start(void) {
    u32 ci, i, j, bank, at, rows;
    for (ci = 0; ci < sizeof(cases) / sizeof(cases[0]); ci++) {
        const Case *c = &cases[ci];
        setup(c); func_150870D0(c->p[4], c->p[2], c->p[3]);
        if (canonicalPointer(D_800872A0) != c->globals[0] || (u8)D_800D2398 != c->globals[1] ||
            (u8)D_800D2399 != c->globals[2] || (u8)D_800D239A != c->globals[3] ||
            (u32)D_800D2394 != c->globals[4] || (u8)D_8008FD90 != c->globals[5] ||
            (u16)D_80087290 != c->globals[6] || D_800D2350 != routes || (u8)D_800D23A8 != (u8)c->p[1]) stop(23);
        if (callCount != c->callCount) stop(23);
        for (i = 0; i < callCount; i++) for (j = 0; j < 10; j++)
            if (calls[i][j] != expectedCalls[c->callAt + i][j]) stop(23);
        rows = (s32)(c->p[2] + c->p[3]) > 0 ? c->p[2] + c->p[3] : 1;
        for (bank = 0; bank < 2; bank++) {
            u8 *p = bank ? other.b : arena.b;
            for (i = 0; i < rows; i++) for (at = 0; at < 132; at++) {
                const u8 *want = templates[expectedRecords[c->records + bank * rows + i]];
                if (canonicalByte(p + i * 132, at) != want[at]) stop(23);
            }
            for (at = rows * 132; at < sizeof(arena.b); at++) if (p[at] != 0xA5) stop(23);
        }
        for (i = 0; i < sizeof(routes); i++) if (routes[i] != originalRoutes[i]) stop(23);
    }
    stop(0);
}
'''


def native_cases():
    yield from (p for p in corpus() if p[6] not in (3, 5))
    for field in (1, 2, 8):
        for byte in range(256):
            p = [3, 0, 2, 1, 7, 0, 0, 0, 4]
            p[field] = byte
            yield tuple(p)


def native_text(owner, body):
    templates, template_ids, records, calls, cases = [], {}, [], [], []
    for p in native_cases():
        memory, args, mode = fixture(*p)
        result, expected, _ = reference(memory, args, mode)
        start, call_at = len(records), len(calls)
        for address in (ARENA, OTHER):
            for i in range(max(1, signed(args[1] + args[2]))):
                record = bytes(result[address + i * 132 + j] for j in range(132))
                if record not in template_ids:
                    template_ids[record] = len(templates)
                    templates.append(record)
                records.append(template_ids[record])
        for target, parameters, *snapshot in expected:
            row = [{LOOKUP: 1, SELECTOR: 2, INITIALIZE: 3, ALLOCATE: 4}[target], *parameters]
            if snapshot:
                row.extend(snapshot[0])
            calls.append(row + [0] * (10 - len(row)))
        globals_ = [read(result, at, n) for at, n in ((TABLE, 4), (PLAYERS, 1), (EXTRAS, 1),
            (READY, 1), (MASK, 4), (HUMAN, 1), (COUNT, 2))]
        cases.append([p, globals_, start, call_at, len(expected)])
    bodies = []
    for name in ('func_15086D48', 'func_150888A8', 'func_15088824'):
        lo, hi = source.function_span(owner, name)
        bodies.append(owner[lo:hi].replace(name + '(', name + '_body(', 1))
    array = lambda row: '{' + ','.join('0x%Xu' % (v & 0xFFFFFFFF) for v in row) + '}'
    text = NATIVE.replace('HELPER_BODIES', '\n'.join(bodies)).replace('TARGET_BODY', body)
    text = text.replace('TEMPLATES', ',\n'.join(array(row) for row in templates))
    text = text.replace('CALLS', ',\n'.join(array(row) for row in calls))
    text = text.replace('RECORDS', ','.join(map(str, records)))
    text = text.replace('CASES', ',\n'.join('{' + array(p) + ',' + array(g) + ',%d,%d,%d}' % (r, c, n)
        for p, g, r, c, n in cases))
    return text, len(cases)


class RouteRecordSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.values = source.freeze(cls.root, cls.out)
        cls.truth = list(struct.unpack_from('>160I', cls.values['conker/conker.us.bin'], source.ROM))
        image = cls.values['conker/build/conker.us.elf']
        cls.helpers = {}
        for entry, count in HELPERS.items():
            at = source.installed.prior.elf_slot_offset(image, entry, count * 4)
            body = image[at:at + count * 4]
            if body != cls.values['conker/conker.us.bin'][entry - 0x14FD2B50:entry - 0x14FD2B50 + count * 4]:
                raise ValueError('Changed real route-record helper')
            cls.helpers.update(zip(range(entry, entry + count * 4, 4), struct.unpack('>%dI' % count, body)))

    def receipt(self, name, **values):
        values.update(production_installed=False, matching_credit=0)
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_full_semantic_cases_real_helpers_and_saved_ABI(self):
        count = 0
        for case, parameters in enumerate(corpus()):
            memory, args, allocation = fixture(*parameters)
            expected, calls, trace = reference(memory, args, allocation)
            machines = []
            for body in (self.words, self.truth):
                m = SetupOracle(body, memory, args, self.helpers, allocation, (case & 1) * 8).run()
                self.assertEqual((public(m.memory), m.calls, m.trace), (public(expected), calls, trace), parameters)
                self.assertEqual(m.f[20:], m.saved_f)
                for register in (*range(16, 24), 28, 29, 30, 31):
                    self.assertEqual(m.r[register], m.before[register])
                machines.append(m)
            self.assertEqual(machines[0].memory, machines[1].memory, parameters)
            count += 1
        self.receipt('guest', cases=count, real_helper_words=140,
                     allocator_only_opaque=True, complete_ordinary_memory_public_order_and_calls_equal=True,
                     both_stack_phases=True, native_aliases_or_hardware_traps_not_claimed=True)

    def test_02_native32_and_effective_controls(self):
        body = source.selected()
        controls = {
            'hardcoded-key': body.replace('func_15086D48(key)', 'func_15086D48(0)'),
            'narrow-total': body.replace('(s32)((u32)playerCount + (u32)extraCount)',
                                       '(u8)((u32)playerCount + (u32)extraCount)'),
            'unsigned-human': body.replace('humanLimit = D_8008FD90;', 'humanLimit = (u8)D_8008FD90;'),
            'wrong-slot-limit': body.replace('i < D_800D2398', 'i < playerCount'),
            'wrong-stride': body.replace('offset += 0x84;', 'offset += 0x80;'),
        }
        exits = {}
        text, count = native_text(self.values['conker/src/game/generated_B3020.c'].decode(), body)
        for label, candidate, opt in [('O0', body, '-O0'), ('O2', body, '-O2')] + [
                (name, candidate, '-O2') for name, candidate in controls.items()]:
            self.assertTrue(candidate == body if label in ('O0', 'O2') else candidate != body, label)
            unit = self.out / ('native-' + label + '.c')
            unit.write_text(text.replace(body, candidate, 1))
            command = [*base.native_command(opt), '-fno-strict-aliasing', '-mstackrealign',
                       str(unit), '-o', str(unit.with_suffix(''))]
            compiled = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
            self.assertEqual((compiled.returncode, compiled.stdout, compiled.stderr), (0, '', ''), label)
            result = subprocess.run([str(unit.with_suffix(''))], capture_output=True, text=True, timeout=30)
            self.assertEqual((result.returncode, result.stdout, result.stderr),
                             (0 if label in ('O0', 'O2') else 23, '', ''), label)
            exits[label] = result.returncode
        self.receipt('native32', cases_per_profile=count, profiles=['O0+UBSAN', 'O2+UBSAN'],
                     exits=exits, real_C_helpers=3, complete_banks_and_routes_and_calls_equal=True,
                     all_mode_player_and_human_bytes=True, guest_aliases_3_and_5_excluded=True,
                     positive_null_allocations_and_universal_C_or_hardware_proof_not_claimed=True)

    def test_03_fired_private_prefix_boundary_still_rejects_matching(self):
        fixtures = [tuple(p) for p in ((3, 0, 2, 1, 7, 0, 0, 0, 4),
                    (4, 1, 0, 0, 7, 0, 0, 0, 128),
                    (3, 0, 2, 1, 7, 1, 0, 0, 4),
                    (3, 0, 2, 1, 7, 2, 0, 0, 4))]
        exact, rejected, first, extents = 0, 0, None, []
        for parameters in fixtures:
            memory, args, allocation = fixture(*parameters)
            full = [FullTraceOracle(words, memory, args, self.helpers, allocation).run()
                    for words in (self.words, self.truth)]
            extents.append([m.all_accesses for m in full])
            for cut in range(min(m.all_accesses for m in full)):
                results = []
                for words in (self.words, self.truth):
                    m = FullTraceOracle(words, memory, args, self.helpers, allocation)
                    m.access_fault = cut
                    with self.assertRaises(base.base.faults.AccessBoundary):
                        m.run()
                    results.append(m)
                a, b = results
                if (a.memory, a.complete_trace) == (b.memory, b.complete_trace):
                    exact += 1
                else:
                    rejected += 1
                    if first is None:
                        changed = [at for at in sorted(set(a.memory) | set(b.memory))
                                   if a.memory.get(at) != b.memory.get(at)]
                        first = dict(parameters=parameters, cut=cut, raw_PC=a.current_pc,
                                     retail_PC=b.current_pc, differing_memory=changed,
                                     raw_last_accesses=a.complete_trace[-4:],
                                     retail_last_accesses=b.complete_trace[-4:])
        self.assertGreater(exact, 0)
        self.assertGreater(rejected, 0)
        self.assertIsNotNone(first)
        self.receipt('private-boundary', fired_cuts=exact + rejected, equal_memory_prefixes=exact,
                     rejected_memory_prefixes=rejected, first=first,
                     raw_and_retail_access_counts=extents,
                     complete_private_order_equal=False, installation_permitted=False,
                     synthetic_access_cuts_not_hardware_traps_or_universal_GPR_proof=True)

    def test_04_raw_bindings_and_frozen_inputs_fail_closed(self):
        text, functions, rel = source.parse_object(self.obj)
        definition = functions[source.FUNCTION]
        offset = definition['value']
        count = 0
        for i in range(160):
            damaged = bytearray(text)
            damaged[offset + i * 4] ^= 1
            with patch.object(source, 'parse_object', return_value=(bytes(damaged), functions, rel)), \
                    self.assertRaises(ValueError):
                source.checked(self.obj)
            count += 1
        for at in source.BINDINGS:
            damaged = dict(rel)
            damaged[offset + at] = []
            with patch.object(source, 'parse_object', return_value=(text, functions, damaged)), \
                    self.assertRaises(ValueError):
                source.checked(self.obj)
            count += 1
        original = Path.read_bytes
        frozen = 0
        for index, name in enumerate(source.INPUTS):
            for target in (self.root / name, self.out / ('before-%02d' % index)):
                def corrupt(path, *args, **kwargs):
                    data = original(path, *args, **kwargs)
                    return data + b'\0' if path == target else data
                with patch.object(Path, 'read_bytes', corrupt), self.assertRaises(ValueError):
                    source.freeze(self.root, self.out)
                frozen += 1
        self.receipt('corruptions', raw_and_binding_controls=count, live_and_snapshot_controls=frozen,
                     all_inputs_unchanged=source.freeze(self.root, self.out).keys() == self.values.keys())

    def test_05_whole_Game_call_scan_and_three_argument_window(self):
        rom = self.values['conker/conker.us.bin']
        opcode = (3 << 26) | ((source.ENTRY >> 2) & 0x3FFFFFF)
        found = []
        with (self.root / 'conker/retail_layout.us.txt').open() as stream:
            for row in csv.DictReader(stream):
                if row['section'] != 'game':
                    continue
                for at in range(int(row['address'], 0), int(row['end'], 0), 4):
                    if struct.unpack_from('>I', rom, at - 0x14FD2B50)[0] == opcode:
                        found.append((row['function'], at))
        self.assertEqual([at for _, at in found], [0x1509E1B8])
        entry = 0x1509E1B0
        window = list(struct.unpack_from('>6I', rom, entry - 0x14FD2B50))
        cases = 0
        for parameters in list(corpus())[::13]:
            memory, args, allocation = fixture(*parameters)
            stream = 0x70000
            for i, value in enumerate(args):
                put(memory, stream + 8 + i * 4, value)
            results = []
            for body in (self.words, self.truth):
                helpers = dict(self.helpers)
                helpers.update(zip(range(source.ENTRY, source.ENTRY + 640, 4), body))
                m = CallerOracle(window, memory, (), helpers, allocation, (cases & 1) * 8, entry)
                m.code[0x1509E3C8] = 0
                m.r[16] = stream
                m.stopped = False
                expected, calls, trace = reference(memory, args, allocation)
                with self.assertRaises(WindowStop):
                    m.run()
                self.assertTrue(m.stopped)
                self.assertEqual(m.forwarded, [args])
                self.assertEqual(m.r[2], 0)
                # Three script argument reads belong to the real caller, not the setup reference.
                self.assertEqual((public(m.memory), m.calls, m.trace[3:]), (public(expected), calls, trace))
                results.append(m)
            self.assertEqual(results[0].memory, results[1].memory)
            cases += 1
        self.receipt('caller', whole_Game_direct_sites=found, fired_retail_only_windows=cases,
                     real_delay_argument_and_return_zero=True, three_full_width_arguments=True,
                     complete_unrecovered_caller_and_unknown_indirect_interfaces_not_claimed=True)

    def test_06_five_neighbor_slots_and_unsigned_classes(self):
        count = 0
        for pattern, mode in itertools.product(range(3 ** 5), (0, 1, 128)):
            memory, args, allocation = fixture(mode=mode)
            for i in range(5):
                put(memory, ROUTES + 9 + i, (255, 1, 2)[pattern // (3 ** i) % 3], 1)
            # Covers equality/tie selection, high-bit unsigned classes, and rejection.
            for node in (1, 2):
                put(memory, ROUTES + node * 16 + 14, 1 if pattern % 7 == node else 0, 1)
                put(memory, ROUTES + node * 16 + 15,
                    (0, 1, 2, 127, 128, 254, 255)[(pattern + node) % 7], 1)
            expected, calls, trace = reference(memory, args, allocation)
            machines = []
            for body in (self.words, self.truth):
                m = SetupOracle(body, memory, args, self.helpers, allocation, (count & 1) * 8).run()
                self.assertEqual((public(m.memory), m.calls, m.trace), (public(expected), calls, trace),
                                 (pattern, mode))
                machines.append(m)
            self.assertEqual(machines[0].memory, machines[1].memory)
            count += 1
        self.receipt('five-neighbors', cases=count, all_243_five_slot_patterns=True,
                     unsigned_classes_and_disabled_types_and_last_ties=True,
                     complete_ordinary_memory_public_order_and_calls_equal=True)


if __name__ == '__main__':
    unittest.main()
