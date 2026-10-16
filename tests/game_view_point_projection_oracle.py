"""Ordered float32 projection reference and actual 58-word matrix/tail execution."""
import itertools
import math

from tools.experiments import game_view_point_projection as source
from tools.tests.game_view_render_pass_oracle import RenderOracle, STACK, put, read
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests import test_game_actor_burst_consumer_match as faults

BASE, PAGE, MATRICES = 0x800BE628, 0x800BE9C0, 0x800D9D10
VIEWS, OTHER, OUTPUT = 0x30000, 0x40000, 0x20000
MATRIX, TAIL, CONTINUATION = 0x150A7960, 0x150A7A00, 0x150A7A14


def half(v): return ((v & 65535) ^ 32768) - 32768
def add(a, b): return bits(floating(a) + floating(b))
def sub(a, b): return bits(floating(a) - floating(b))
def mul(a, b): return bits(floating(a) * floating(b))


def reciprocal(v):
    f = floating(v)
    return bits(1.0 / f if f else math.copysign(math.inf, f))


def public(memory):
    return {a:v for a, v in memory.items() if not STACK - 0x400 <= a < STACK + 0x100}


def transformed(memory, args):
    matrix = (MATRICES + half(args[0]) * 64) & 0xFFFFFFFF
    result = []
    for axis in range(4):
        values = [read(memory, matrix + i * 4 + axis * 4) for i in (0, 4, 8, 12)]
        result.append(add(add(mul(values[0], args[1]), mul(values[1], args[2])),
            add(mul(values[2], args[3]), values[3])))
    return tuple(result)


def reference(initial, args):
    memory = dict(initial)
    x, y, z, w = transformed(memory, args)
    inv = reciprocal(w)
    offset = half(args[0]) * 384
    row = (read(memory, BASE) + offset) & 0xFFFFFFFF
    px = add(mul(mul(add(read(memory, row + 12), bits(5.0)), x), inv), read(memory, row + 52))
    put(memory, args[4], px)
    row = (read(memory, BASE) + offset) & 0xFFFFFFFF
    py = sub(read(memory, row + 56), mul(mul(add(read(memory, row + 16), bits(5.0)), y), inv))
    put(memory, args[5], py)
    row = (read(memory, BASE) + offset + memory[PAGE] * 16) & 0xFFFFFFFF
    scale, translation = (half(read(memory, row + p, 2)) for p in (0x44, 0x4C))
    pz = mul(add(mul(mul(z, inv), bits(float(scale))), bits(float(translation))), bits(32.0))
    put(memory, args[6], pz)
    return memory, (x, y, z, w)


def fixture(view=0, page=0, xyz=(1.25, -2.5, 3.75), pattern=0, alias=0):
    memory = {STACK + i:(i * 17 + 0xA5) & 255 for i in range(-0x400, 0x100)}
    for base, length in ((OUTPUT, 64), (BASE - 8, 32), (PAGE - 8, 32)):
        memory.update({base + i:0xA5 for i in range(length)})
    put(memory, BASE, VIEWS)
    memory[PAGE] = page
    matrix = (MATRICES + half(view) * 64) & 0xFFFFFFFF
    values = [bits(v) for v in (1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 3.25, -4.5, 5.75, 2.)]
    if pattern == 1:
        values = [bits(v) for v in (0.25, -2., 3., 0.5, -4., 5., 0.125, 0.25, 6., 0.25, -7., -0.5, -8., 9., 10., 3.)]
    elif pattern == 2:
        values[15] = bits(0.0)
    elif pattern == 3:
        for i in (3, 7, 11, 15): values[i] = bits(-0.0)
    elif pattern == 4:
        values[15] = 0x7FC12345
    elif pattern == 5:
        values[15] = bits(math.inf)
    elif pattern == 6:
        values[15] = 0x00800000
    elif pattern == 7:
        values[15] = bits(-2.0)
    elif pattern == 8:
        values[0] = bits(16777216.)
        values[4] = bits(-16777216.)
        values[12] = bits(1.)
    for i, value in enumerate(values): put(memory, matrix + i * 4, value)
    for bank in (VIEWS, OTHER):
        row = (bank + half(view) * 384) & 0xFFFFFFFF
        memory.update({row + i:0xA5 for i in range(384)})
        for p, value in ((12, 141.5), (16, 103.25), (52, 146.), (56, 108.)):
            put(memory, row + p, bits(value + (5 if bank == OTHER else 0)))
        for frame in set((0, 1, 2, 128, 255, page)):
            at = row + frame * 16
            for p, value in ((0x44, (-32768, 32767, -12345)[frame % 3]), (0x4C, (32767, -32768, 23456)[frame % 3])):
                if bank == OTHER: value += 1 if p == 0x44 else -3
                put(memory, at + p, value & 65535, 2)
    row = (VIEWS + half(view) * 384) & 0xFFFFFFFF
    outputs = [OUTPUT + 16, OUTPUT + 20, OUTPUT + 24]
    if alias == 1: outputs[1] = outputs[0]
    elif alias == 2: outputs[2] = outputs[0]
    elif alias == 3: outputs[0] = row + 16
    elif alias == 4: outputs[0] = row + 56
    elif alias == 5: outputs[1] = row + page * 16 + 0x44
    elif alias == 6: outputs[1] = PAGE
    elif alias in (7, 8):
        outputs[alias - 7] = BASE
        for i in range(12): put(memory, matrix + i * 4, 0)
        put(memory, matrix + 48, 0); put(memory, matrix + 52, 0)
        put(memory, matrix + 60, bits(1.0))
        put(memory, row + (52 if alias == 7 else 56), OTHER)
    elif alias == 9:
        outputs[0] = PAGE
        for i in range(12): put(memory, matrix + i * 4, 0)
        put(memory, matrix + 48, 0); put(memory, matrix + 60, bits(1.0))
        put(memory, row + 52, 0x01000000)
    for address in outputs:
        for i in range(4): memory.setdefault(address + i, 0xA5)
    args = (view & 0xFFFFFFFF, *(v if isinstance(v, int) else bits(v) for v in xyz), *outputs)
    return memory, args


def corpus():
    for view, page, xyz, pattern in itertools.product((0, 1, -1, 3, 32767, 0x8000, 0x10001, 0x1FFFF),
            (0, 1, 255), ((1.25, -2.5, 3.75), (-0., 0., -1.), (1., 1., 1.)), range(9)):
        yield fixture(view, page, xyz, pattern)
    for view, page, alias in itertools.product((0, 1, -1), (0, 1, 128, 255), range(1, 10)):
        memory, args = fixture(view, page, alias=alias)
        try: reference(memory, args)
        except KeyError: continue
        yield memory, args


class PointProjectionOracle(RenderOracle):
    def __init__(self, words, memory, args, helper, phase=0, entry=source.ENTRY, connected=None):
        self.all_accesses, self.access_fault = 0, None
        code = {MATRIX + i * 4:w for i, w in enumerate(helper)}
        code.update(connected or {})
        super().__init__(words, memory, phase=phase, entry=entry, arguments=args, connected=code)

    def access(self):
        if self.own_instruction:
            if self.all_accesses == self.access_fault: raise faults.AccessBoundary
            self.all_accesses += 1
        super().access()

    def record_call(self, target):
        if target == TAIL:
            args = self.arguments(8)
            self.calls.append((target, args))
            self.observations.append((self.f[12], self.f[14]))
            assert self.observations[-1] == args[1:3]
        elif target == source.ENTRY:
            self.calls.append((target, self.arguments(7)))
        else: raise AssertionError('Unexpected point-projection provider ' + hex(target))

    def hook(self, target): raise AssertionError('Point-projection helper must be connected')


def state(m):
    return m.memory, m.r, m.f, m.events, m.calls, m.observations, m.current_pc, m.delay_of, m.all_accesses
