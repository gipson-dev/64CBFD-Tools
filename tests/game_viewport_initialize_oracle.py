"""Ordered initializer reference with explicit FOV/trig/projection contracts."""
import itertools
import math

from tools.experiments import game_viewport_initialize as source
from tools.tests.game_view_render_pass_oracle import RenderOracle, STACK, put, read
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests import test_game_actor_burst_consumer_match as faults

BASE, SCRATCH, PAGE, WIDTH, HEIGHT = 0x800BE628, 0x800BE62C, 0x800BE9C0, 0x800BE620, 0x800BE624
WIDTHS, HEIGHTS, ORIGINS, ASPECTS, SCALE, MARKS = 0x800BE638, 0x800BE650, 0x800BE668, 0x80082FA8, 0x800BE6B8, 0x800BE630
VIEWS, OTHER, THIRD, BUFFER = 0x70000, 0x80000, 0x90000, 0xA0000
TRANSFER, SINE, COSINE, BOUNDS, CLAMP, FINAL = 0x1501B0A0, 0x15047D60, 0x15047C00, 0x1501AE94, 0x1501AF44, 0x1510B32C
RETURNS = (bits(0.25), bits(1.0), bits(-0.5), bits(2.0), bits(0.125), bits(-0.25))
CONSTANTS = {0x800968E4:0x42CE0A3D, 0x800968E8:0x42726666, 0x800968EC:0x3C8EFA35, 0x800968F0:0x3C8EFA35}


class ConversionBoundary(Exception): pass
def half(v): return ((v & 65535) ^ 32768) - 32768
def add(a, b): return fp(a, b, 'add')
def sub(a, b): return fp(a, b, 'sub')
def mul(a, b): return fp(a, b, 'mul')
def div(a, b): return fp(a, b, 'div')
def public(memory): return {a:v for a, v in memory.items() if not STACK - 0x600 <= a < STACK + 0x180}
def answer(ordinal, seed): return RETURNS[(ordinal - 1 + seed) % len(RETURNS)]


def effects(memory, index, target, ordinal, mode):
    if mode == 1 and target == SINE and ordinal == 1: put(memory, BASE, OTHER)
    elif mode == 2 and target == COSINE and ordinal == 2: put(memory, BASE, THIRD)
    elif mode == 3 and target == COSINE and ordinal == 4: memory[PAGE] = 1
    elif mode == 4 and target == FINAL: put(memory, BASE, THIRD)
    elif mode == 5 and target == TRANSFER:
        row = read(memory, BASE) + index * 384
        put(memory, row + 0x6C, bits(75.0)); put(memory, row + 0x70, bits(35.0))
    else: return False
    return True


def reference(initial, args, seed=0, mode=0):
    memory = dict(initial); index, layout, depth, transfer = args
    index, layout = signed(index), signed(layout)
    calls = []; ordinal = 0
    def row(): return (read(memory, BASE) + index * 384) & 0xFFFFFFFF
    def field(p): return read(memory, row() + p)
    def store(p, v, size=4): put(memory, row() + p, v, size)
    def call(target, packet):
        nonlocal ordinal
        packet = tuple(a & 0xFFFFFFFF for a in packet)
        calls.append((target, packet))
        if target in (SINE, COSINE): ordinal += 1
        effects(memory, index, target, ordinal, mode)
        return answer(ordinal, seed) if target in (SINE, COSINE) else 0
    def cast(v):
        f = floating(v)
        if not math.isfinite(f) or not -0x80000000 <= f < 0x80000000: raise ConversionBoundary
        return math.trunc(f) & 65535
    def vp(p, v): put(memory, (read(memory, SCRATCH) + index * 16 + p) & 0xFFFFFFFF, v, 2)
    def copy(source, target):
        for p in range(0, 16, 4): put(memory, target + p, read(memory, source + p))
    try:
        store(4, bits(float(signed(read(memory, WIDTHS + layout * 4)))))
        store(8, bits(float(signed(read(memory, HEIGHTS + layout * 4)))))
        if layout:
            store(4, sub(field(4), bits(2.0))); store(8, sub(field(8), bits(2.0)))
        store(0x64, read(memory, ASPECTS + layout * 4)); store(0x68, bits(2.0))
        if layout == 1:
            store(4, mul(field(4), read(memory, SCALE)))
            store(0x6C, mul(read(memory, 0x800968E4), read(memory, SCALE)))
        else: store(0x6C, read(memory, 0x800968E8))
        store(0x70, bits(50.0)); store(0x74, field(0x6C)); store(0x78, field(0x70))
        store(0x60, div(field(4), field(8)))
        store(12, mul(field(4), bits(0.5))); store(16, mul(field(8), bits(0.5)))
        origin = ORIGINS + layout * 20 + index * 4
        store(52, bits(float(half(read(memory, origin, 2)))))
        store(56, bits(float(half(read(memory, origin + 2, 2)))))
        store(44, sub(field(52), field(12))); store(36, sub(field(56), field(16)))
        store(48, add(field(12), field(52))); store(40, add(field(16), field(56)))
        if half(transfer): call(TRANSFER, (index, layout))
        else:
            w, h = (bits(float(signed(read(memory, p)))) for p in (WIDTHS, HEIGHTS))
            store(20, mul(div(field(4), w), div(div(w, h), div(field(4), field(8)))))
            store(24, div(field(8), bits(float(signed(read(memory, HEIGHTS))))))
        for fov, extent, constant, output in ((0x6C, 12, 0x800968EC, 0x7C), (0x70, 16, 0x800968F0, 0x80)):
            angle = mul(mul(field(fov), bits(0.5)), read(memory, constant))
            sine = call(SINE, (angle,)); cosine = call(COSINE, (angle,))
            store(output, div(sine, mul(field(extent), cosine)))
        value = add(field(4), bits(10.0)); vp(0, cast(add(value, value)))
        value = add(field(8), bits(10.0)); vp(2, cast(add(value, value)))
        depth = (signed(depth) >> 1) & 65535
        vp(4, depth); vp(6, 0); vp(8, cast(mul(field(52), bits(4.0)))); vp(10, cast(mul(field(56), bits(4.0))))
        vp(12, depth); vp(14, 0)
        copy(read(memory, SCRATCH) + index * 16, row() + 64 + memory[PAGE] * 16)
        record, page = row(), memory[PAGE]
        copy(record + 64 + page * 16, record + 64 + (0 if page else 1) * 16)
        store(0x84, bits(1.0))
        call(BOUNDS, (index,))
        max_x = sub(bits(float(signed(read(memory, WIDTH)))), bits(2.0))
        max_y = bits(float(signed(read(memory, HEIGHT))))
        inside = not (floating(field(44)) < 2.0 or floating(max_x) < floating(field(48)) or
            floating(field(36)) < 0.0 or floating(max_y) < floating(field(40)))
        store(1, int(inside), 1)
        record = row(); call(CLAMP, (record + 44, record + 36, record + 48, record + 40))
        for p, low, high in ((44, 2.0, max_x), (48, 2.0, max_x), (36, 0.0, max_y), (40, 0.0, max_y)):
            value = read(memory, record + p)
            if floating(value) < low: value = bits(low)
            elif floating(high) < floating(value): value = high
            put(memory, record + p, value)
        call(FINAL, (index, 0, 0, field(0x84)))
        put(memory, MARKS + index, index & 255, 1)
        return memory, calls, True
    except ConversionBoundary: return memory, calls, False


def fixture(index=0, layout=0, depth=1023, transfer=0, page=0, pattern=0, alias=0):
    memory = {STACK + i:(i * 17 + 0xA5) & 255 for i in range(-0x600, 0x180)}
    for base, length in ((VIEWS, 0x2200), (OTHER, 0x2200), (THIRD, 0x2200), (BUFFER, 0x200),
            (0x800BE600, 0x440), (ASPECTS, 32)):
        memory.update({base + i:0xA5 for i in range(length)})
    for address, value in CONSTANTS.items(): put(memory, address, value)
    for n in range(6):
        w, h = ((292, 216), (292, 108), (146, 108), (146, 108), (320, 240), (320, 240))[n]
        if pattern == 1: w, h = -7, 3
        elif pattern == 2: w, h = 0x7FFFFFFF, -0x80000000
        elif pattern == 3: w, h = 1, 1
        put(memory, WIDTHS + n * 4, w & 0xFFFFFFFF); put(memory, HEIGHTS + n * 4, h & 0xFFFFFFFF)
        put(memory, ASPECTS + n * 4, bits((1.66, 0.83, 1.68, 1.68, 1.66, 0.0)[n]))
        for slot in range(5):
            for p, value in ((0, 146 + slot * 20), (2, 108 - slot * 10)):
                put(memory, ORIGINS + n * 20 + slot * 4 + p, value & 65535, 2)
    for base in (VIEWS, OTHER, THIRD):
        for slot in range(5):
            for p, value in ((4, 280.), (8, 200.), (12, 140.), (16, 100.), (52, 146.), (56, 108.), (0x6C, 65.), (0x70, 45.)):
                put(memory, base + slot * 384 + p, bits(value + (base - VIEWS) / 65536))
    scratch = BUFFER
    if alias: scratch = VIEWS + index * 384 + (0x34, 0x40, 0x50)[alias - 1] - index * 16
    for p, value in ((BASE, VIEWS), (SCRATCH, scratch), (WIDTH, 292), (HEIGHT, 216), (SCALE, bits(0.8))): put(memory, p, value)
    memory[PAGE] = page
    return memory, (index & 0xFFFFFFFF, layout & 0xFFFFFFFF, depth & 0xFFFFFFFF, transfer & 0xFFFFFFFF)


def corpus():
    for index, layout, depth, transfer, page in itertools.product((0, 1, 3), (0, 1, 2, 3, 5),
            (1023, -1, 0x80000001), (0, 1, 0x10000, 0x8000), (0, 1, 255)):
        yield fixture(index, layout, depth, transfer, page)
    for index, layout, alias in itertools.product((0, 1, 3), (0, 1, 2), (1, 2, 3)):
        yield fixture(index, layout, alias=alias)


class InitializeOracle(RenderOracle):
    def __init__(self, words, memory, args, helper, phase=0, seed=0, mode=0, entry=source.ENTRY):
        if set(range(entry, entry + len(words) * 4, 4)) & set(helper):
            raise ValueError('Initializer code overlaps a connected helper')
        self.all_accesses, self.access_fault = 0, None
        super().__init__(words, memory, phase=phase, entry=entry, arguments=args, connected=helper)
        self.seed, self.mode, self.trig_calls = seed, mode, 0
        self.index = signed(args[0]); self.code = faults.TrackedCode(self.code, self)

    def access(self):
        if self.own_instruction:
            if self.all_accesses == self.access_fault: raise faults.AccessBoundary
            self.all_accesses += 1
        super().access()

    def execute(self, word):
        if word >> 26 == 0 and word & 63 == 3:
            self.r[word >> 11 & 31] = signed(self.r[word >> 16 & 31]) >> (word >> 6 & 31) & 0xFFFFFFFF
        elif word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 13:
            f = floating(self.f[word >> 11 & 31])
            if not math.isfinite(f) or not -0x80000000 <= f < 0x80000000: raise ConversionBoundary
            self.f[word >> 6 & 31] = math.trunc(f) & 0xFFFFFFFF
        else: super().execute(word)

    def record_call(self, target):
        args = (self.f[12],) if target in (SINE, COSINE) else self.arguments({TRANSFER:2, BOUNDS:1, CLAMP:4, FINAL:4}[target])
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        if target in (SINE, COSINE): self.trig_calls += 1
        else: assert target in (TRANSFER, FINAL), hex(target)
        if effects(self.memory, self.index, target, self.trig_calls, self.mode):
            self.fired.append((target, self.trig_calls, self.mode))
        for i in range(4): self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for r in (1, 2, 3, *range(4, 16), 24, 25): self.r[r] = 0xA5000000 + r
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0x11223344
        self.f[0] = answer(self.trig_calls, self.seed)
