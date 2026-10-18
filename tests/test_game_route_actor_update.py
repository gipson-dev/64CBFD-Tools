"""Complete route caller contracts; private candidates do not receive matching credit."""
import itertools
import csv
import json
import math
from pathlib import Path
import struct
import unittest

from tools.tests import game_view_point_projection_oracle as base
from tools.tests.test_game_record_heading_setter import SetterOracle
from tools.experiments import game_route_actor_update as source
from tools.tests import test_game_actor_route_snap as snap
from tools.tests import test_game_route_vector_builder as vector
from tools.tests import test_game_record_progress_lap as lap

ENTRY, ROM, WORDS = 0x15087350, 0xB4800, 604
TABLE, ACTORS, RECORDS, OBJECTS = 0x800872A0, 0x800CC2D0, 0x50000, 0x60000
COUNT, EVENT, TICKS, MASK = 0x800D2398, 0x800D2390, 0x800BE9E4, 0x800D18A0
VECTOR, CUBIC, DERIVATIVE, ADVANCE = 0x15088F30, 0x150497E0, 0x150498A4, 0x15088A08
SELECT, COPY, FINALIZE, SIN, COS = 0x15042D78, 0x10023A10, 0x1508802C, 0x15047D60, 0x15047C00
NEIGHBOR, ROUTES = 0x150888A8, 0x70000
HELPERS = {VECTOR: 83, CUBIC: 49, DERIVATIVE: 62, ADVANCE: 212, NEIGHBOR: 88}
STATIC_BYTES = {}
put, read, bits, floating, STACK = base.put, base.read, base.bits, base.floating, base.STACK


def signed(value, width=32):
    return ((value & ((1 << width) - 1)) ^ (1 << (width - 1))) - (1 << (width - 1))


def public(memory):
    return {a: v for a, v in memory.items() if not STACK - 0x1000 <= a < STACK + 0x400}


def divide(left, right):
    a, b = floating(left), floating(right)
    return bits(a / b if b else math.nan if not a else math.copysign(math.inf, a * math.copysign(1., b)))


def selection_effect(memory, row, effect):
    if effect in (1, 2, 3):
        put(memory, EVENT, effect, 1)
    elif effect == 4:
        put(memory, row + 0x30, 2, 1)
        put(memory, OBJECTS + 0x140 + 0x84, 0, 1)
    elif effect == 5:
        put(memory, TICKS, 7)
        put(memory, row + 0x33, 251, 1)


def reference(initial, args, effect=0):
    """Ordered binary32 algorithm, independent of the caller's MIPS control flow."""
    m, calls = dict(initial), []
    get = lambda at, n=4: read(m, at & 0xFFFFFFFF, n)
    store = lambda at, value, n=4: put(m, at & 0xFFFFFFFF, value, n)
    index, active, look = args
    if not get(TABLE):
        return m, calls
    offset = index * 0x84 & 0xFFFFFFFF
    row = get(TABLE) + offset & 0xFFFFFFFF
    actor = ACTORS + signed(get(row + 0x31, 1), 8) * 0x32C
    px, pz = get(actor + 0x14), get(actor + 0x1C)
    store(EVENT, 0, 1)
    if signed(get(row + 0x30, 1), 8):
        step = base.mul(base.sub(get(row + 4), get(row)), bits(.125))
        if floating(get(0x8009D9E0)) < floating(step):
            step = get(0x8009D9E0)
        if floating(step) < floating(get(0x8009D9E4)):
            step = get(0x8009D9E4)
        store(row, base.add(get(row), step))
    else:
        store(row, bits(.5))
    arrays = [STACK - 0xF00 + axis * 16 for axis in range(3)]
    scratch = STACK - 0xE00

    def vectors(record):
        nonlocal m
        calls.append((VECTOR, 'record' if record == row else 'copy', get(record), get(record + 8)))
        m, _ = vector.reference(m, (record, *arrays))

    def cubic(axis, record, derivative=False):
        values = [get(arrays[axis] + j * 4) for j in range(4)]
        t = get(record + 8)
        calls.append((DERIVATIVE if derivative else CUBIC, axis, 0, t))
        return snap.spline(values, t, derivative)

    def advance(record, delta):
        nonlocal m
        calls.append((ADVANCE, 'record' if record == row else 'copy', delta))
        m, result, _, nested = lap.reference(m, (record, delta))
        calls.extend((NEIGHBOR, values) for _, values in nested)
        return signed(result, 8)

    length, refresh, gain, prior_error = 0, 1, bits(.75), get(0x8009D9E8)
    for iteration in range(11):
        if refresh:
            vectors(row)
            dx, dz = (base.sub(get(arrays[a] + 8), get(arrays[a] + 4)) for a in (0, 2))
            length = bits(math.sqrt(floating(base.add(base.mul(dx, dx), base.mul(dz, dz)))))
        x, dx = cubic(0, row, True)
        z, dz = cubic(2, row, True)
        inv = divide(bits(-1.), bits(math.sqrt(floating(base.add(base.mul(dx, dx), base.mul(dz, dz))))))
        dx, dz = base.mul(dx, inv), base.mul(dz, inv)
        store(row + 0xC, dx)
        store(row + 0x10, dz)
        intercept = base.add(base.mul(x, dx), base.mul(z, dz)) ^ 0x80000000
        error = base.add(base.add(base.mul(dx, px), base.mul(dz, pz)), intercept)
        if not (floating(error) < -50. or 50. < floating(error)):
            break
        absolute = error ^ 0x80000000 if floating(error) < 0. else error
        if floating(prior_error) < floating(absolute):
            gain = base.mul(gain, bits(.5))
        prior_error = absolute
        step = divide(base.mul(error, gain), length)
        if floating(step) < -.5:
            step = bits(-.5)
        if .5 < floating(step):
            step = bits(.5)
        refresh = advance(row, step ^ 0x80000000)
    calls.append((SELECT, (128,)))
    selection_effect(m, row, effect)
    store(row + 0x32, get(row + 0x33, 1), 1)
    store(row + 0x33, get(TICKS), 1)
    numerator = base.mul(base.sub(base.add(base.add(base.mul(get(actor + 0x2C), dx),
        base.mul(get(actor + 0x34), dz)), intercept), error), bits(4.))
    store(row + 0x14, divide(numerator, bits(float(signed(get(row + 0x32, 1), 8)))))
    if signed(get(row + 0x30, 1), 8):
        calls.append((COPY, 132))
        m.update({scratch + i: m[row + i] for i in range(132)})
        advance(scratch, base.add(look, look))
        vectors(scratch)
        for axis, output in enumerate((0x800D239C, 0x800D23A0, 0x800D23A4)):
            store(output, cubic(axis, scratch))
        if signed(index) < signed(get(COUNT, 1), 8):
            if not active:
                constant = struct.unpack('>d', struct.pack('>Q', get(0x8009D9F0, 8)))[0]
                angle = bits(floating(get(0x800CC310)) * constant)
                calls.append((SIN, angle))
                store(0x800D239C, base.add(base.mul(bits(math.sin(floating(angle))), bits(300.)), get(actor + 0x14)))
                store(0x800D23A0, get(actor + 0x18))
                calls.append((COS, angle))
                store(0x800D23A4, base.add(base.mul(bits(math.cos(floating(angle))), bits(300.)), get(actor + 0x1C)))
            for axis, output in enumerate((0x800D239C, 0x800D23A0, 0x800D23A4)):
                value = floating(get(output))
                if not math.isfinite(value) or not -2147483648. <= value < 2147483648.:
                    raise ValueError('Outside qualified float-to-s32 domain')
                destination = get(get(0x800D2104) + get(actor + 0x13F, 1) * 4)
                store(destination + 8 + axis * 2, math.trunc(value), 2)
            store(actor + 0x44, bits(float(signed(active))))
            event = signed(get(EVENT, 1), 8)
            if event in (1, 2, 3):
                store(actor + 0x20, bits((75., 55., 65.)[event - 1]))
            store(actor + 0x21E, 0, 1)
    else:
        store(row, 0)
        vectors(row)
        start_x, start_z = cubic(0, row), cubic(2, row)
        store(row, bits(1.))
        vectors(row)
        dx, dz = base.sub(cubic(0, row), start_x), base.sub(cubic(2, row), start_z)
        length = bits(math.sqrt(floating(base.add(base.mul(dx, dx), base.mul(dz, dz)))))
        value = 0
        if 1. < floating(length):
            inv = divide(bits(1.), length)
            dx, dz = base.mul(dx, inv), base.mul(dz, inv)
            value = base.mul(base.sub(base.add(base.mul(dx, px), base.mul(dz, pz)),
                base.add(base.mul(dx, start_x), base.mul(dz, start_z))), inv)
        store(row, value)
    store(row + 0x48, active, 1)
    store(0x800D23A9, 1, 1)
    if not signed(get(row + 0x30, 1), 8) and get(row + 0x48, 1) and not (
            get(MASK, 2) & (1 << (get(row + 0x31, 1) & 31))):
        store(row + 0x1C, get(row + 0x1C) + get(TICKS))
    if signed(get(row + 0x30, 1), 8) >= 2 and not get(get(actor + 0x31C) + 0x84, 1):
        calls.append((FINALIZE, (row, actor, 13)))
    if offset == 0:
        scores = []
        for i in range(max(0, signed(get(COUNT, 1), 8))):
            current = get(TABLE) + i * 132
            value = base.add(get(current + 8), bits(float(signed(get(current + 0x24, 2), 16))))
            lap_value = signed(get(current + 0x2A, 1), 8)
            if lap_value != 127:
                value = base.add(value, base.sub(get(0x8009D9F8), base.mul(bits(float(lap_value)), bits(1000.))))
            if get(MASK, 2) & 1 << (get(current + 0x31, 1) & 31):
                value = base.sub(value, get(0x8009D9FC))
            scores.append((i, floating(value)))
        if any(math.isnan(value) for _, value in scores):
            raise ValueError('Independent ranking requires ordered finite scores')
        for rank, (slot, _) in enumerate(sorted(scores, key=lambda v: v[1], reverse=True), 1):
            store(get(TABLE) + slot * 132 + 0x29, rank, 1)
    return m, calls


def fixture(index=0, mode=0, active=1, count=3, position=(20., 10.), fraction=.2, real=False):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x1000, 0x400)}
    for bank, length in ((RECORDS, 32 * 0x84), (ACTORS - 0x32C, 6 * 0x32C),
                         (OBJECTS, 0x200), (0x800D2000, 0x500)):
        memory.update({bank + i: 0xA5 for i in range(length)})
    put(memory, TABLE, RECORDS)
    put(memory, COUNT, count, 1)
    put(memory, TICKS, 4)
    put(memory, MASK, 0, 2)
    put(memory, 0x800D2104, OBJECTS)
    put(memory, OBJECTS, OBJECTS + 0x100)
    put(memory, 0x800CC310, bits(0.))
    for i in range(17):
        row = RECORDS + i * 0x84
        for off, value in ((0, bits(.3)), (4, bits(.4)), (8, bits(fraction + i * .1)),
                           (0x18, 13), (0x1C, 27), (0x24, 0)):
            put(memory, row + off, value, 2 if off == 0x24 else 4)
        for off, value in ((0x29, 0), (0x2A, 127), (0x30, mode if i == index else 1),
                           (0x31, i % 3), (0x32, 2), (0x33, 4)):
            put(memory, row + off, value, 1)
    row = RECORDS + index * 0x84
    actor = ACTORS + (index % 3) * 0x32C
    for off, value in ((0x14, position[0]), (0x18, 5.), (0x1C, position[1]),
                       (0x2C, 1.), (0x34, 2.)):
        put(memory, actor + off, bits(value))
    put(memory, actor + 0x13F, 0, 1)
    put(memory, actor + 0x31C, OBJECTS + 0x140)
    put(memory, OBJECTS + 0x140 + 0x84, 1, 1)
    for address, value in ((0x8009D9E0, .05), (0x8009D9E4, -.05),
                           (0x8009D9E8, 1.e9), (0x8009D9F8, 100000.), (0x8009D9FC, 200000.)):
        put(memory, address, bits(value))
    put(memory, 0x8009D9F0, struct.unpack('>Q', struct.pack('>d', .01))[0], 8)
    if real:
        memory.update(STATIC_BYTES)
        memory.update({ROUTES + i: 0xA5 for i in range(4096)})
        for i in range(8):
            for node, x, y, z in ((i, (i - 1) * 100, i * 10, (i - 1) * 50),
                                  (128 + i, (i - 1) * 100 + 40, i * 10, (i - 1) * 50 - 20)):
                for axis, value in enumerate((x, y, z)):
                    put(memory, ROUTES + node * 16 + axis * 2, value, 2)
                for slot, value in enumerate(((i - 1) % 8, (i + 1) % 8, 128 + i, 255, 255)):
                    put(memory, ROUTES + node * 16 + 9 + slot, value, 1)
                put(memory, ROUTES + node * 16 + 14, 4 if node >= 128 else 0, 1)
                put(memory, ROUTES + node * 16 + 15, 0, 1)
        for i in range(17):
            for off, value in ((0x26, 8), (0x27, 0), (0x28, 0), (0x2B, 0),
                               (0x2C, 1), (0x2D, 2), (0x2E, 3), (0x2F, 0)):
                put(memory, RECORDS + i * 0x84 + off, value, 1)
        put(memory, 0x800D2350, ROUTES)
        for name, value in (('D_800E0BE7', 2), ('D_800BE616', 0), ('D_8008FD90', 3), ('D_800D23A8', 0)):
            put(memory, lap.ANCHORS[name], value, 1)
        for i in range(4):
            put(memory, lap.ANCHORS['D_800E0C10'] + i * 2, 300, 2)
            put(memory, lap.ANCHORS['D_800E0C18'] + i * 4, 1000)
    return memory, (index, active, bits(.125))


class UpdateOracle(SetterOracle):
    """Execute every caller instruction, with declared opaque numeric providers."""
    def __init__(self, words, memory, args, phase=0, helpers=None, effect=0, steps=(100., 10., 50.)):
        super().__init__(words, memory, args, 0, phase=phase, table=TABLE, entry=ENTRY)
        self.trace, self.vector_outputs, self.provider_calls = [], {}, []
        self.code.update(helpers or {})
        self.effect = effect
        self.steps = steps

    def get(self, address, size):
        value = super().get(address, size)
        if getattr(self, 'trace', None) is not None and self.own_instruction:
            self.trace.append(('R', address, size, value))
        return value

    def put(self, address, value, size):
        super().put(address, value, size)
        if getattr(self, 'trace', None) is not None and self.own_instruction:
            self.trace.append(('W', address, size, value & ((1 << (size * 8)) - 1)))

    def execute(self, word):
        op, fmt, ft, fs, fd, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        if op == 17 and fmt == 16 and fn in (4, 7, 33):
            x = floating(self.f[fs])
            if fn == 4:
                self.f[fd] = bits(math.sqrt(x))
            elif fn == 7:
                self.f[fd] = self.f[fs] ^ 0x80000000
            else:
                pair = struct.unpack('>Q', struct.pack('>d', x))[0]
                self.f[fd], self.f[fd + 1] = pair & 0xFFFFFFFF, pair >> 32
        elif op == 17 and fmt == 17 and fn in (2, 32):
            def double(r):
                return struct.unpack('>d', struct.pack('>Q', self.f[r + 1] << 32 | self.f[r]))[0]
            x = double(fs)
            if fn == 32:
                self.f[fd] = bits(x)
            else:
                value = struct.unpack('>Q', struct.pack('>d', x * double(ft)))[0]
                self.f[fd], self.f[fd + 1] = value & 0xFFFFFFFF, value >> 32
        else:
            super().execute(word)

    def record_call(self, target):
        if target == ENTRY:
            raise AssertionError('Unexpected recursive update')
        if target not in (VECTOR, CUBIC, DERIVATIVE, ADVANCE, SELECT, COPY, FINALIZE, SIN, COS, NEIGHBOR):
            raise AssertionError('Unknown route update provider ' + hex(target))
        self.calls.append((target, self.arguments({VECTOR: 4, CUBIC: 3, DERIVATIVE: 4,
            ADVANCE: 2, SELECT: 1, COPY: 3, FINALIZE: 3, SIN: 0, COS: 0, NEIGHBOR: 3}[target])))
        args = self.calls[-1][1]
        if target in self.code:
            if target == VECTOR:
                for axis, output in enumerate(args[1:]):
                    self.vector_outputs[output] = axis
                self.provider_calls.append((target, 'record' if args[0] == self.row else 'copy',
                    read(self.memory, args[0]), read(self.memory, args[0] + 8)))
            elif target in (CUBIC, DERIVATIVE):
                self.provider_calls.append((target, self.vector_outputs[args[0]], args[1], args[2]))
            elif target == ADVANCE:
                self.provider_calls.append((target, 'record' if args[0] == self.row else 'copy', args[1]))
            else:
                self.provider_calls.append((target, args))

    def hook(self, target):
        args = self.calls[-1][1]
        result, float_result = 0, 0
        if target == VECTOR:
            for axis, output in enumerate(args[1:]):
                self.vector_outputs[output] = axis
                for j in range(4):
                    put(self.memory, output + j * 4, bits((j - 1) * self.steps[axis]))
            self.provider_calls.append((target, read(self.memory, args[0] + 8)))
        elif target in (CUBIC, DERIVATIVE):
            axis = self.vector_outputs[args[0]]
            step = bits(self.steps[axis])
            float_result = base.mul(args[2], step)
            if target == DERIVATIVE:
                put(self.memory, args[3], step)
            self.provider_calls.append((target, axis, args[1], args[2]))
        elif target == ADVANCE:
            put(self.memory, args[0] + 8, base.add(read(self.memory, args[0] + 8), args[1]))
            result = 0
            self.provider_calls.append((target, args[1]))
        elif target == COPY:
            data = [self.memory[args[0] + i] for i in range(args[2])]
            self.memory.update({args[1] + i: value for i, value in enumerate(data)})
            self.provider_calls.append((target, args[2]))
        elif target in (SIN, COS):
            x = floating(self.f[12])
            float_result = bits(math.sin(x) if target == SIN else math.cos(x))
            self.provider_calls.append((target, self.f[12]))
        else:
            self.provider_calls.append((target, args))
        if target == SELECT:
            selection_effect(self.memory, self.row, self.effect)
        for i in range(4):
            put(self.memory, self.r[29] + i * 4, 0xB5000000 + i)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2], self.f[0] = result, float_result


class WindowStop(Exception):
    pass


class CallerWindow(UpdateOracle):
    def __init__(self, body, memory, args, helpers, window, site, stop, source_words, phase, poison, actor):
        super().__init__([0], memory, args, phase, helpers)
        code = dict(helpers)
        code.update(zip(range(ENTRY, ENTRY + len(body) * 4, 4), body))
        code.update(zip(range(window, window + len(source_words) * 4, 4), source_words))
        code[stop] = 0
        self.code = base.faults.TrackedCode(code, self)
        self.entry, self.site, self.stop, self.poison = window, site, stop, poison
        self.r[16] = actor
        self.r[2] = args[0]
        self.f[16] = args[2]
        self.call_state, self.forwarded_args, self.stopped, self.returned = None, None, False, False

    def record_call(self, target):
        if target == ENTRY:
            self.forwarded_args = self.arguments(3)
            self.call_state = ([self.r[r] for r in (*range(16, 24), 28, 29, 30, 31)], self.f[20:].copy())
        else:
            super().record_call(target)

    def execute(self, word):
        # The dispatcher returns to an unconditional branch; execution dispatches
        # its delay word, while the actor caller dispatches the ordinary load.
        if self.current_pc in (self.site + 8, self.site + 12) and not self.returned:
            actual = ([self.r[r] for r in (*range(16, 24), 28, 29, 30, 31)], self.f[20:].copy())
            if actual != self.call_state:
                raise AssertionError('Route update did not restore caller state')
            self.r[2] = self.poison
            self.returned = True
        if self.current_pc == self.stop:
            self.stopped = True
            raise WindowStop
        super().execute(word)


class RouteActorUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>604I', cls.rom, ROM))
        cls.source = source
        cls.out = cls.root / source.BUILD
        cls.obj, cls.candidate, cls.row = source.qualify(cls.root, cls.out)
        cls.values = source.freeze(cls.root, cls.out)
        cls.helpers = {}
        image = cls.values['conker/build/conker.us.elf']
        for address, n in ((0x8009D9E0, 4), (0x8009D9E4, 4), (0x8009D9E8, 4),
                           (0x8009D9F0, 8), (0x8009D9F8, 4), (0x8009D9FC, 4)):
            at = source.prior.elf_slot_offset(image, address, n)
            STATIC_BYTES.update({address + i: image[at + i] for i in range(n)})
        for entry, n in HELPERS.items():
            at = source.prior.elf_slot_offset(image, entry, n * 4)
            body = list(struct.unpack_from('>%dI' % n, image, at))
            if body != list(struct.unpack_from('>%dI' % n, cls.rom, entry - 0x14FD2B50)):
                raise ValueError('Changed real route helper: ' + hex(entry))
            cls.helpers.update(zip(range(entry, entry + n * 4, 4), body))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, args, phase=0, real=True, effect=0, bodies=None, steps=(100., 10., 50.)):
        pair = [UpdateOracle(body, memory, args, phase, self.helpers if real else None, effect, steps).run()
                for body in (bodies or (self.retail, self.candidate))]
        self.assertEqual(public(pair[0].memory), public(pair[1].memory))
        self.assertEqual(pair[0].provider_calls, pair[1].provider_calls)
        if real:
            expected, calls = reference(memory, args, effect)
            self.assertEqual(public(pair[0].memory), public(expected))
            self.assertEqual(pair[0].provider_calls, calls)
        for model in pair:
            self.assertEqual(model.f[20:], model.saved_f)
        return pair

    def test_01_complete_nonmoving_projection_and_rank_outputs(self):
        memory, args = fixture()
        expected = UpdateOracle(self.retail, memory, args).run()
        actual = UpdateOracle(self.candidate, memory, args).run()
        self.assertEqual(public(actual.memory), public(expected.memory))
        self.assertEqual(actual.provider_calls, expected.provider_calls)
        self.assertEqual(read(expected.memory, RECORDS + 8), bits(.2))
        self.assertEqual([read(expected.memory, RECORDS + i * 0x84 + 0x29, 1) for i in range(3)], [3, 2, 1])

    def test_02_complete_caller_with_494_real_helper_words(self):
        count = 0
        self.seen = set()
        for index, mode, active, position, phase in itertools.product((0, 1, 3), (0, 1, 2, 128),
                (0, 1, 256), ((20., 10.), (-300., 100.), (1600., -250.)), (0, 8)):
            memory, args = fixture(index=index, mode=mode, active=active, position=position, real=True)
            pair = self.compare(memory, args, phase)
            self.seen.update(pair[0].visits)
            count += 1
        self.receipt('real-helpers', cases=count, real_helper_words=sum(HELPERS.values()),
            caller_words=604, raw_candidate_words=len(self.candidate),
            complete_public_memory_and_canonical_call_contracts_equal=True,
            private_frame_and_hardware_fault_equivalence_not_claimed=True,
            retail_caller_words_reached=sum(ENTRY <= at < ENTRY + WORDS * 4 for at in self.seen))

    def test_03_effectful_selection_event_and_signed_tick_refresh(self):
        count = 0
        for effect, mode, active, phase in itertools.product(range(1, 6), (0, 1, 2, 255), (0, 1), (0, 8)):
            memory, args = fixture(mode=mode, active=active, real=True)
            self.compare(memory, args, phase, effect=effect)
            count += 1
        self.receipt('provider-effects', cases=count, effects=5, real_route_helpers=True)

    def test_04_frozen_production_inputs_and_no_matching_credit(self):
        self.assertEqual(self.row['neighbors'], 72)
        self.assertEqual(self.row['diagnostics'], '')
        self.assertFalse(self.row['installed'])
        self.assertEqual(self.row['matching_credit'], 0)
        source.freeze(self.root, self.out)
        owner = self.values['conker/src/game/generated_B3020.c'].decode()
        lo, hi = source.function_span(owner, source.FUNCTION)
        self.assertEqual(owner[lo:hi], 's32 func_15087350() {\n    return 0;\n}')

    def test_05_signed_lap_scores_stable_ties_and_all_17_slots(self):
        cases = 0
        for lap_value in range(256):
            memory, args = fixture(mode=1, count=3, real=True)
            put(memory, RECORDS + 132 + 0x2A, lap_value, 1)
            self.compare(memory, args)
            cases += 1
        for count, mask, pattern in itertools.product((-128, -1, 0, 1, 2, 16, 17), (0, 1, 7), range(3)):
            memory, args = fixture(mode=1, count=count, real=True)
            put(memory, MASK, mask, 2)
            for i in range(17):
                put(memory, RECORDS + i * 132 + 8, bits(.2 if pattern == 0 else ((i * 7) % 17) * .03125))
                put(memory, RECORDS + i * 132 + 0x24, (-32768, 0, 32767)[(i if pattern == 2 else 1) % 3], 2)
            self.compare(memory, args)
            cases += 1
        self.receipt('ranking', cases=cases, all_256_lap_bytes=True, signed_16_tick_extremes=True,
            counts=[-128, -1, 0, 1, 2, 16, 17], stable_equal_scores=True, masked_players=True,
            independent_stable_sorted_reference=True, larger_positive_counts_not_qualified=True)

    def test_06_null_table_modular_index_and_signed_actor(self):
        cases = 0
        for index in (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
            memory, args = fixture(real=True)
            put(memory, TABLE, 0)
            self.compare(memory, (index, 0xFFFFFFFF, bits(.125)))
            cases += 1
        for index in (0, 0x40000000, 0x80000000, 0xC0000000, 0xFFFFFFFF):
            memory, args = fixture(mode=1, real=True)
            if index == 0xFFFFFFFF:
                memory.update({RECORDS - 132 + i: memory[RECORDS + i] for i in range(132)})
            self.compare(memory, (index, args[1], args[2]))
            cases += 1
        for actor_id in (-128, -1, 0, 31, 32, 127):
            memory, args = fixture(mode=1, real=True)
            actor = ACTORS + actor_id * 0x32C
            memory.update({actor + i: memory[ACTORS + i] for i in range(0x32C)})
            put(memory, RECORDS + 0x31, actor_id, 1)
            self.compare(memory, args)
            cases += 1
        self.receipt('index-actor', cases=cases, full_32_bit_modular_record_offsets=True,
            null_table_dereference_gate=True, signed_actor_bytes=[-128, -1, 0, 31, 32, 127],
            shifts_use_low_five_bits=True, arbitrary_invalid_pointers_not_qualified=True)

    def test_07_full_width_active_and_signed_tick_divisor(self):
        cases = 0
        for active, old_tick, mode in itertools.product((0, 1, 128, 255, 256, 0x10001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF),
                (1, 127, 128, 255), (0, 1)):
            memory, args = fixture(mode=mode, active=active, real=True)
            put(memory, RECORDS + 0x33, old_tick, 1)
            put(memory, RECORDS + 0x1C, 0x7FFFFFFE)
            self.compare(memory, args)
            cases += 1
        self.receipt('active-ticks', cases=cases, active_values=9, signed_tick_bytes=[1, 127, 128, 255],
            modular_timer_overflow=True, full_width_zero_test_and_float_conversion=True,
            stored_active_byte_and_unsigned_retest=True, zero_divisor_native_domain_not_claimed=True)

    def test_08_exact_error_limits_and_eleven_iteration_stop(self):
        cases = 0
        for position, iterations in ((-34., 1), (66., 1), (-34.00000762939453, 2),
                                     (66.00000762939453, 2), (-4096., 11), (4096., 11)):
            memory, args = fixture(index=1, mode=1, position=(position, 0.), fraction=.15)
            put(memory, RECORDS + 132 + 8, bits(.25))
            pair = self.compare(memory, args, real=False, steps=(64., 10., 0.))
            for model in pair:
                actual_iterations = sum(target == DERIVATIVE for target, _ in model.calls) // 2
                self.assertEqual(actual_iterations, iterations)
            cases += 1
        self.receipt('limits', cases=cases, exact_inclusive_error_bounds=[-50, 50],
            adjacent_representable_outside_values=True, stop_after_11_iterations=True,
            axis_aligned_bounded_numeric_providers=True)

    def test_09_effective_compiled_semantic_negatives(self):
        b = source.SELECTED
        forms = {
            'upper-inclusive': b.replace('50.0f < error', '50.0f <= error'),
            'ten-iterations': b.replace('iterations >= 11', 'iterations >= 10'),
            'unsigned-old-tick': b.replace('(f32)(s8)record[0x32]', '(f32)record[0x32]'),
            'byte-active-test': b.replace('if (active == 0)', 'if ((u8)active == 0)'),
            'half-lookahead': b.replace('lookAhead + lookAhead', 'lookAhead'),
            'unsigned-lap': b.replace('(f32)(s8)cursor[0x2A]', '(f32)cursor[0x2A]'),
            'ascending-rank': b.replace('scores[i] < scores[i + 1]', 'scores[i] > scores[i + 1]'),
        }
        for name, body in forms.items():
            _, wrong, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            if name in ('upper-inclusive', 'ten-iterations'):
                memory, args = fixture(index=1, mode=1, position=(-34. if name == 'upper-inclusive' else -4096., 0.))
                put(memory, RECORDS + 132 + 8, bits(.25))
                models = [UpdateOracle(w, memory, args, steps=(64., 10., 0.)).run() for w in (self.retail, wrong)]
            else:
                memory, args = fixture(mode=1, active=256 if name == 'byte-active-test' else 1, real=True)
                put(memory, RECORDS + 0x33, 255, 1)
                put(memory, RECORDS + 132 + 0x2A, 255, 1)
                models = [UpdateOracle(w, memory, args, helpers=self.helpers).run() for w in (self.retail, wrong)]
            self.assertNotEqual((public(models[0].memory), models[0].provider_calls),
                                (public(models[1].memory), models[1].provider_calls), name)
        self.receipt('semantic-controls', controls=len(forms), ordinary_wrong_results_only=True,
            crashes_timeouts_or_budget_exhaustion_not_credited=True)

    def test_10_current_frame_is_rejected_by_observed_private_stores(self):
        memory, args = fixture(real=True)
        pair = self.compare(memory, args)
        first = [next(event for event in model.trace if event[0] == 'W') for model in pair]
        self.assertEqual(first[0], ('W', STACK - 0x1C8 + 0x44, 4, 0xDEAD0000))
        self.assertEqual(first[1], ('W', STACK - 0x1E0 + 0x3C, 4, 0xDEAD0000))
        self.assertNotEqual(pair[0].memory, pair[1].memory)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (588, 480, 599))
        self.receipt('private-boundary', first_retail_write=first[0], first_raw_C_write=first[1],
            full_private_memory_equal=False, production_installation_allowed=False,
            emitted_word_and_store_evidence=True, no_hardware_fault_or_matching_credit=True)

    def test_11_whole_Game_direct_scan_and_both_actual_caller_windows(self):
        opcode = 3 << 26 | (ENTRY >> 2 & 0x3FFFFFF)
        sites = []
        with (self.root / 'conker/retail_layout.us.txt').open() as stream:
            for row in csv.DictReader(stream):
                if row['section'] != 'game':
                    continue
                for at in range(int(row['address'], 0), int(row['end'], 0), 4):
                    if struct.unpack_from('>I', self.rom, at - 0x14FD2B50)[0] == opcode:
                        sites.append((row['function'], at))
        self.assertEqual(sites, [('func_150538CC', 0x150539C0), ('func_1509DFC4', 0x1509E1D4)])
        count = 0
        for dispatcher, index, phase, poison in itertools.product((False, True), (0, 1), (0, 8), (0, 0xDEADCAFE)):
            memory, args = fixture(index=index, mode=1, active=256 if dispatcher else 0, real=True)
            if dispatcher:
                start, site, stop = 0x1509E1C8, 0x1509E1D4, 0x1509E3C8
                actor = 0x90000
                put(memory, actor + 8, index)
                put(memory, actor + 12, args[1])
                args = args[:2] + (0x3DCCCCCD,)
                length = 7
            else:
                start, site, stop = 0x150539B8, 0x150539C0, 0x150539CC
                actor = ACTORS + (index % 3) * 0x32C
                put(memory, actor + 0x221, 254, 1)
                args = args[:2] + (0,)
                length = 5
            source_words = list(struct.unpack_from('>%dI' % length, self.rom, start - 0x14FD2B50))
            expected, calls = reference(memory, args)
            pair = []
            for body in (self.retail, self.candidate):
                model = CallerWindow(body, memory, args, self.helpers, start, site, stop,
                    source_words, phase, poison, actor)
                with self.assertRaises(WindowStop):
                    model.run()
                self.assertTrue(model.stopped and model.returned)
                self.assertEqual(model.forwarded_args, args)
                self.assertEqual(model.provider_calls, calls)
                self.assertEqual(public(model.memory), public(expected))
                self.assertEqual(model.r[2], 0 if dispatcher else 0xFFFFFFFE)
                pair.append(model)
            self.assertEqual(pair[0].provider_calls, pair[1].provider_calls)
            count += 1
        self.receipt('callers', whole_Game_direct_sites=sites, window_cases=count,
            actual_delay_instructions_and_argument_bits=True, caller_saved_state_restored=True,
            both_return_consumers_ignore_callee_V0=True, unknown_indirect_and_whole_callers_not_claimed=True,
            bcopy_static_JAL_alias=hex(COPY), bcopy_runtime_address_not_rebased_or_executed=True)

    def test_12_source_profile_bank_and_fingerprint_controls(self):
        expected = [(588, 480, 599), (590, 488, 479), (588, 472, 538),
                    (578, 480, 600), (580, 480, 571), (578, 472, 566),
                    (622, 480, 616), (624, 472, 619), (622, 472, 612),
                    (613, 472, 609), (615, 472, 608), (613, 464, 606)]
        rows = json.loads((self.out / 'screens.json').read_text())
        self.assertEqual([(r['words'], r['frame'], r['differences']) for r in rows], expected)
        self.assertEqual(len(rows), 12)
        cases = 0
        for normal, (label, body) in itertools.product((False, True), list(source.forms())):
            name = label + ('-normal' if normal else '-no-unroll')
            self.assertEqual((self.out / (name + '.c')).read_text(), source.recovered_owner(
                self.values['conker/src/game/generated_B3020.c'].decode(), body))
            command = json.loads((self.out / (name + '-command.json')).read_text())
            self.assertEqual(command.count('-Wo,-loopunroll,0'), 0 if normal else 1)
            data, functions = source.prior.link_owner(self.root, self.out, self.out / (name + '.o'), source.OWNER)
            f = functions[source.FUNCTION]
            words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
            row = next(r for r in rows if r['name'] == name)
            self.assertEqual((row['neighbors'], row['diagnostics']), (72, ''))
            for index, mode, phase in itertools.product((0, 1), (0, 1, 128), (0, 8)):
                memory, args = fixture(index=index, mode=mode, real=True)
                self.compare(memory, args, phase, bodies=(self.retail, words))
                cases += 1
        raw, bindings = source.checked(self.obj)
        for i in range(len(raw) // 4):
            damaged = bytearray(raw)
            damaged[i * 4] ^= 1
            with self.assertRaises(ValueError):
                source.check_payload(bytes(damaged), bindings)
        for at in bindings:
            wrong = dict(bindings)
            wrong[at] = [('R_MIPS_26', 'wrong')]
            with self.assertRaises(ValueError):
                source.check_payload(raw, wrong)
        self.receipt('source-profiles', forms=6, profiles=2, guest_cases=cases,
            all72_neighbors_and_pools_preserved_per_screen=True, raw_word_controls=588,
            binding_controls=len(bindings), none_is_an_installable_word_frame_match=True)


if __name__ == '__main__':
    unittest.main()
