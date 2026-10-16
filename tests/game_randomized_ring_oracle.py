"""Whole randomized ring packets; empty paths and incoming-home probes are explicit."""
from tools.experiments import game_randomized_ring_emitter as source
from tools.tests import test_game_quad_edge_emitter as edge
from tools.tests.test_game_table_fade_callback import TableFadeOracle
from tools.tests.test_game_table_range_loader import RangeOracle

STACK, bits, floating, rounded = edge.STACK, edge.bits, edge.floating, edge.rounded
put, read, signed, short, public, AccessFault = edge.put, edge.read, edge.signed, edge.short, edge.public, edge.AccessFault
RANDOMS = ((0, 0xFFFFFFFF, 0x80000000), (0xFFFF0000, 0x1234FFFF, 0x80010001),
    (0x12345678, 0x87654321, 0xFEDCBA98))


def trig(table, sine, angle):
    angle = (angle - 64) & 255 if sine else angle & 255
    folded = angle if angle <= 64 else 128 - angle if angle <= 128 else angle - 128 if angle <= 192 else 256 - angle
    return table[folded] ^ (0x80000000 if 64 < angle <= 192 else 0)


def fixture(colors, count=4, pattern=0, flags=0xABCDEF81, palette=0, colors_address=source.COLORS):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-2048, 768)}
    memory.update({colors_address + i: b for i, b in enumerate(colors)})
    xyz = ((12.25, -34.75, 56.5), (-32768.75, 32767.5, -123.25),
        (50000.75, -60000.25, 32768.5))[pattern % 3]
    args = (*map(bits, xyz), bits((70.0, -125.25, 0.0)[pattern % 3]),
        (500, -32768, 50000)[pattern % 3], bits((0.00457763671875, -0.125, 0.0)[pattern % 3]),
        palette & 0xFFFFFFFF, count & 0xFFFFFFFF, flags, 0x87654321)
    return memory, args


def changes(role, number, args, mode, incoming, colors):
    if mode == 1 and role == 'random' and number == 1:
        return tuple((incoming + i * 4, value, 4) for i, value in (
            (0, bits(111.25)), (1, bits(-999.0)), (2, bits(-222.5)), (3, bits(999.0)),
            (4, 1234), (5, bits(0.125)), (6, 1), (7, min(signed(args[7]), 3)),
            (8, 0x55), (9, 0x12345678)))
    if mode == 2 and role in ('sine', 'random', 'factory'):
        return ((colors, 0xF0 - (number & 15), 1), (colors + 1, number & 255, 1),
            (colors + 2, number ^ 0xA5, 1))
    if mode == 3 and role == 'factory' and number == 1:
        return ((incoming + 28, 1, 4), (incoming + 36, 0x10203040, 4))
    return ()


def reference(memory, args, table, randoms=RANDOMS[0], phase=0, mode=0, limit=None, bindings=None):
    s = bindings or dict(sine=source.SINE, cosine=source.COSINE, random=source.RANDOM,
        factory=source.FACTORY, colors=source.COLORS)
    memory, homes, incoming = dict(memory), list(args), STACK + phase
    colors = [read(memory, s['colors'] + i, 1) for i in range(3)]
    calls, packets, random_count = [], [], 0

    def effect(role, number):
        for address, value, size in changes(role, number, args, mode, incoming, s['colors']):
            put(memory, address, value, size)
            if incoming <= address < incoming + 40:
                homes[(address - incoming) // 4] = value & 0xFFFFFFFF

    def draw():
        nonlocal random_count
        calls.append((s['random'],))
        value = randoms[random_count % len(randoms)]
        random_count += 1
        effect('random', random_count)
        return value

    count = signed(args[7])
    if count > 0:
        assert args[6] == 0, 'Only palette zero is within the native staged object'
        height, radius = short(edge.trunc(floating(args[1]))), floating(args[3])
        base_lifetime = rounded(float(signed(args[4])))
        step, angle_phase, index = 65535 // count, 0, 0
        while True:
            angle = angle_phase >> 8 & 255
            calls.append((s['sine'], angle))
            sine = floating(trig(table, True, angle))
            effect('sine', index + 1)
            calls.append((s['cosine'], angle))
            cosine = floating(trig(table, False, angle))
            position_z = rounded(rounded(radius * cosine) + floating(homes[2]))
            fixed_z = signed(edge.trunc(rounded(200.0 * cosine)))
            delay = rounded(rounded(float(draw() & 65535) * 2.0 ** -16) + 100.0)
            extent = signed(edge.trunc(rounded(rounded(float(draw() & 65535) * floating(homes[5])) + base_lifetime)))
            tail = draw()
            fixed_x = signed(edge.trunc(rounded(200.0 * sine)))
            position_x = rounded(rounded(radius * sine) + floating(homes[0]))
            p = [0] * 31
            p[:3] = [short(edge.trunc(position_x)) & 0xFFFFFFFF, height & 0xFFFFFFFF,
                short(edge.trunc(position_z)) & 0xFFFFFFFF]
            for at, value in ((3, 13), (5, colors[0]), (6, colors[1]), (7, colors[2]),
                    (12, 2), (13, fixed_x >> 8 & 255), (14, fixed_x & 255),
                    (15, fixed_z >> 8 & 255), (16, fixed_z & 255), (19, 5),
                    (23, short(extent)), (24, short(extent)), (25, (tail & 15) + 10),
                    (26, edge.trunc(delay)), (29, args[8] & 255), (30, homes[9])):
                p[at] = value & 0xFFFFFFFF
            p = tuple(p)
            packets.append(p)
            calls.append((s['factory'], *p))
            if limit is not None and len(packets) == limit:
                return calls, packets, public(memory)
            effect('factory', len(packets))
            index += 1
            angle_phase += step
            if index == signed(homes[7]):
                break
            assert index < 128, 'Unbounded reference input needs a declared prefix limit'
    return calls, packets, public(memory)


class RingOracle(edge.EdgeOracle):
    def __init__(self, words, memory, args, table, randoms=RANDOMS[0], phase=0, mode=0,
            fault=None, connected=None, limit=None, entry=source.ENTRY, bindings=None, stop_entry=False):
        super().__init__(words, memory, args, randoms=randoms, phase=phase, mode=mode,
            fault=fault, connected=connected, entry=entry)
        self.f[12], self.f[14] = args[:2]
        self.r[4:6] = [0xBAD00004, 0xBAD00005]
        self.table, self.limit, self.stop_entry = table, limit, stop_entry
        self.bindings = bindings or dict(sine=source.SINE, cosine=source.COSINE, random=source.RANDOM,
            factory=source.FACTORY, colors=source.COLORS)
        self.sine_count, self.cosine_count = 0, 0

    def execute(self, word):
        if word >> 26 in (38, 46):
            TableFadeOracle.execute(self, word)
        else:
            super().execute(word)

    def put(self, address, value, size):
        if size == 3:
            assert address % 4 == 0, 'SWR prefix must begin at its aligned word'
            if self.recording:
                self.access()
            RangeOracle.put(self, address, value, size)
        else:
            super().put(address, value, size)

    def record_call(self, target):
        s = self.bindings
        if target == source.ENTRY and self.stop_entry:
            self.entry_args = (self.f[12], self.f[14], *self.r[6:8], *self.arguments(10)[4:])
            raise edge.CallBoundary
        if target in (s['sine'], s['cosine']):
            self.calls.append((target, self.r[4]))
            if target == s['sine']:
                self.sine_count += 1
            else:
                self.cosine_count += 1
        elif target == s['random']:
            self.calls.append((target,))
        elif target == s['factory']:
            p = self.arguments(31)
            self.calls.append((target, *p))
            self.packets.append(p)
            self.factory_count += 1
            if self.limit is not None and len(self.packets) == self.limit:
                raise edge.CallBoundary
        else:
            return super().record_call(target)

    def hook(self, target):
        s, value, fp_value = self.bindings, 0xABCD0123, None
        if target == s['sine']:
            fp_value = trig(self.table, True, self.r[4])
            role, number = 'sine', self.sine_count
        elif target == s['cosine']:
            fp_value = trig(self.table, False, self.r[4])
            role, number = 'cosine', self.cosine_count
        elif target == s['random']:
            value = self.randoms[self.random_count % len(self.randoms)]
            self.random_count += 1
            role, number = 'random', self.random_count
        elif target == s['factory']:
            role, number = 'factory', len(self.packets)
        else:
            return super().hook(target)
        for address, data, size in changes(role, number, self.input_args, self.mode, self.incoming, s['colors']):
            self.put(address, data, size)
        for i in range(31 if target == s['factory'] else 4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for i in (*range(1, 16), 24, 25):
            self.r[i] = 0xA5000000 + i
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = value
        if fp_value is not None:
            self.f[0] = fp_value


def state(model):
    return (model.memory, model.r, model.f, model.hi, model.lo, model.condition, model.events,
        model.calls, model.packets, model.accesses)
