"""Whole spray loop and escaped output observations, using the bounded guest runner."""
from tools.experiments import game_scaled_random_spray as source
from tools.tests import test_game_quad_edge_emitter as edge

STACK, bits, floating, rounded = edge.STACK, edge.bits, edge.floating, edge.rounded
put, read, signed, short, public, AccessFault = edge.put, edge.read, edge.signed, edge.short, edge.public, edge.AccessFault
SAMPLES = ((0.25, -0.5, 1.5), (-1.75, 0.375, -0.0), (32767.25, -12345.5, -32768.5))


def fixture(count=3, scale=1.25, flags=0xABCDEF81, pattern=0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-2048, 768)}
    coords = ((0, 1, -1), (-32768, 32767, -123), (0xABCD8000, 0x12347FFF, 0xFEDCFFFE))[pattern]
    return memory, (*coords, count & 0xFFFFFFFF, bits(scale), flags, 0x87654321)


def vector(number, old, mode):
    values = list(SAMPLES[(number - 1) % 3])
    if mode in (1, 4) and number > 1:
        values[1:] = map(floating, old[1:])
    return tuple(bits(value) for value in values)


def poison(outputs):
    x, y, z = map(floating, outputs)
    return bits(rounded(x + 0.5)), bits(rounded(y - 0.25)), bits(-z)


def packet(args, outputs):
    fx, fy, fz = map(lambda value: signed(edge.trunc(floating(value))), outputs)
    words = [0] * 31
    words[:3] = [short(value) & 0xFFFFFFFF for value in args[:3]]
    for i, value in ((3, 47), (5, 255), (6, 255), (7, 255), (9, 255), (12, 7),
            (13, fx >> 8), (14, fx & 255), (15, fz >> 8), (16, fz & 255),
            (23, 512), (24, 512), (25, 40), (26, fy), (29, args[5] & 255), (30, args[6])):
        words[i] = value & 0xFFFFFFFF
    return tuple(words)


def reference(args, mode=0, provider=vector):
    count, scale = signed(args[3]), floating(args[4])
    calls, packets, observed, homes = [], [], [], (0, 0, 0)
    doubled = rounded(scale + scale) if count > 0 else 0.0
    for i in range(max(count, 0)):
        calls.append(('direction', 64))
        direction = provider(i + 1, homes, mode)
        outputs = tuple(bits(rounded(floating(value) * factor))
            for value, factor in zip(direction, (scale, doubled, scale)))
        p = packet(args, outputs)
        calls.append((source.FACTORY, *p))
        packets.append(p)
        observed.append(outputs)
        homes = poison(outputs) if mode in (3, 4) else outputs
    return calls, packets, observed


class SprayOracle(edge.EdgeOracle):
    def __init__(self, words, memory, args, phase=0, mode=0, fault=None, connected=None,
            entry=source.ENTRY, direction=source.DIRECTION, factory=source.FACTORY,
            allocation_fail=False, stop_entry=False):
        super().__init__(words, memory, args, phase=phase, mode=mode, fault=fault,
            connected=connected, entry=entry, allocation_fail=allocation_fail)
        self.direction, self.factory = direction, factory
        self.direction_count, self.output_pointers, self.observed = 0, None, []
        self.stop_spray_entry = stop_entry

    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 7:
            self.f[word >> 6 & 31] = self.f[word >> 11 & 31] ^ 0x80000000
        else:
            super().execute(word)

    def record_call(self, target):
        if target == source.ENTRY and self.stop_spray_entry:
            self.entry_args = self.arguments(7)
            raise edge.CallBoundary
        if target == self.direction:
            args = self.arguments(4)
            assert args[0] == 64 and len(set(args[1:])) == 3
            self.output_pointers = args[1:]
            self.direction_count += 1
            self.calls.append(('direction', args[0]))
        elif target == self.factory:
            args = self.arguments(31)
            self.calls.append((target, *args))
            self.packets.append(args)
            self.factory_count += 1
            self.observed.append(tuple(self.peek(at, 4) for at in self.output_pointers))
        elif target in (0x150489B0, 0x15048A40):
            self.calls.append((target, *self.arguments(1)))
            args = self.arguments(1)
        else:
            return super().record_call(target)
        self.events.append(('CALL', target, args))

    def hook(self, target):
        if target == self.direction:
            old = tuple(self.peek(at, 4) for at in self.output_pointers)
            values = vector(self.direction_count, old, self.mode)
            for at, value in zip(self.output_pointers, values):
                self.put(at, value, 4)
            if self.mode == 2 and self.direction_count == 1:
                for i, value in enumerate((1, 2, 3, 0xFFFFFFFF, bits(9.0), 0, 0)):
                    self.put(self.incoming + i * 4, value, 4)
        elif target == self.factory:
            if self.mode in (3, 4):
                for at, value in zip(self.output_pointers, poison(self.observed[-1])):
                    self.put(at, value, 4)
        else:
            super().hook(target)
            if self.allocation_fail and target == edge.factory.HEAP:
                self.r[2] = 0
            return
        for i in range(31 if target == self.factory else 4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for i in (*range(1, 16), 24, 25):
            self.r[i] = 0xA5000000 + i
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.hi, self.lo, self.r[2] = 0x87654321, 0x12345678, 0xABCD0123


def state(model):
    return (model.memory, model.r, model.f, model.hi, model.lo, model.condition, model.events, model.calls,
        model.accesses, model.observed, model.output_pointers)
