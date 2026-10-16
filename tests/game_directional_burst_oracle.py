"""Reuse the qualified guest runner for the burst's signed DIV and NEG.S."""
from tools.experiments import game_directional_burst as source
from tools.tests import test_game_quad_edge_emitter as edge

bits, floating, rounded, read, put, signed = edge.bits, edge.floating, edge.rounded, edge.read, edge.put, edge.signed
STACK, state, public, AccessFault = edge.STACK, edge.state, edge.public, edge.AccessFault


def remainder(word):
    value = signed(word)
    quotient = abs(value) // 50
    return value - (-quotient if value < 0 else quotient) * 50


def provider(target, angle):
    return bits(((angle & 255) - 128) / (128.0 if target == source.COSINE else 64.0))


def fixture(compact=0, angle=0x12345680, flags=0xABCDEF81, pattern=0, default=0xABCD):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-1024, 512)}
    put(memory, source.DEFAULT_ANGLE, default, 2)
    points = ((0, 1, -1), (-32768, 32767, -123), (0xABCD8000, 0x12347FFF, 0xFEDCFFFE))
    return memory, (*points[pattern], angle, compact, flags, 0x87654321)


def reference(memory, args, random_word, phase=0, mode=0, trig=provider):
    memory, homes, calls = dict(memory), list(args), []
    if homes[4] == 0:
        homes[3] = read(memory, source.DEFAULT_ANGLE, 2)
    calls.append((source.RANDOM,))
    if mode == 1:
        put(memory, source.DEFAULT_ANGLE, 0x4321, 2)
    elif mode == 2:
        homes[:4] = [0x12348001, 0xABCD7FFF, 0xFFFF8000, 0xFEDC0181]
    yaw, polar = homes[3] & 255, remainder(random_word) & 255
    calls.append((source.COSINE, yaw))
    c = floating(trig(source.COSINE, yaw))
    calls.append((source.SINE, yaw))
    n = floating(trig(source.SINE, yaw))
    calls.append((source.COSINE, polar))
    p = floating(trig(source.COSINE, polar))
    if mode == 3:
        homes[4] = 0 if homes[4] else 0x12340100
    vx, vz = rounded(c * p), rounded(-n * p)
    vx, vz = rounded(vx + vx), rounded(vz + vz)
    fx, fz = edge.signed(edge.trunc(rounded(vx * 256.0))), edge.signed(edge.trunc(rounded(vz * 256.0)))
    count = 31 if homes[4] else 49
    packet = [0] * count
    for i in range(3):
        packet[i] = edge.short(homes[i]) & 0xFFFFFFFF
    for i, value in ((3, 42), (5, 255), (6, 255), (7, 255), (12, 6),
            (13, fx >> 8), (14, fx & 255), (15, fz >> 8), (16, fz & 255)):
        packet[i] = value & 0xFFFFFFFF
    tail = ((22, 1), (23, 512), (24, 358), (25, 255), (26, -50), (29, homes[5] & 255), (30, homes[6])) if count == 31 else (
        (27, 512), (28, 358), (31, 20), (34, 255), (35, 255), (36, -50),
        (37, 200), (38, 9), (39, 1), (41, 1), (42, 50), (43, 20), (47, homes[5] & 255), (48, homes[6]))
    for i, value in tail:
        packet[i] = value & 0xFFFFFFFF
    calls.append((source.SMALL if count == 31 else source.LARGE, *packet))
    return public(memory), calls, tuple(packet)


class BurstOracle(edge.EdgeOracle):
    def __init__(self, words, memory, args, random_word=0, phase=0, mode=0,
            fault=None, connected=None, entry=source.ENTRY, allocation_fail=False):
        super().__init__(words, memory, args, phase=phase, mode=mode, fault=fault,
            connected=connected, entry=entry, allocation_fail=allocation_fail)
        self.random_word, self.trig_count = random_word, 0

    def execute(self, word):
        op, rs, rt, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word & 63
        if op == 0 and fn == 26:
            numerator, denominator = signed(self.r[rs]), signed(self.r[rt])
            if denominator != 50:
                raise AssertionError('Burst signed DIV is qualified only for divisor 50')
            quotient = abs(numerator) // 50
            if numerator < 0:
                quotient = -quotient
            self.lo, self.hi = quotient & 0xFFFFFFFF, (numerator - quotient * 50) & 0xFFFFFFFF
        elif op == 17 and word >> 21 & 31 == 16 and fn == 7:
            self.f[word >> 6 & 31] = self.f[word >> 11 & 31] ^ 0x80000000
        else:
            super().execute(word)

    def record_call(self, target):
        if target == source.ENTRY:
            self.entry_args = self.arguments(7)
            raise edge.CallBoundary
        count = {source.RANDOM: 0, source.COSINE: 1, source.SINE: 1, source.SMALL: 31, source.LARGE: 49}.get(target)
        if count is None:
            return super().record_call(target)
        args = self.arguments(count)
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))
        if target in (source.SMALL, source.LARGE):
            self.factory_count += 1
            self.packets.append(args)

    def hook(self, target):
        if target not in (source.RANDOM, source.COSINE, source.SINE, source.SMALL, source.LARGE):
            super().hook(target)
            if self.allocation_fail and target == edge.factory.HEAP:
                self.r[2] = 0
            return
        result = None
        value = self.random_word if target == source.RANDOM else 0xABCD0123
        if target == source.RANDOM:
            self.random_count += 1
            if self.mode == 1:
                self.put(source.DEFAULT_ANGLE, 0x4321, 2)
            elif self.mode == 2:
                for i, data in enumerate((0x12348001, 0xABCD7FFF, 0xFFFF8000, 0xFEDC0181)):
                    self.put(self.incoming + i * 4, data, 4)
        if target in (source.COSINE, source.SINE):
            self.trig_count += 1
            result = provider(target, self.r[4])
            if self.mode == 3 and self.trig_count == 3:
                self.put(self.incoming + 16, 0 if self.input_args[4] else 0x12340100, 4)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for i in (*range(1, 16), 24, 25):
            self.r[i] = 0xA5000000 + i
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = value & 0xFFFFFFFF
        if result is not None:
            self.f[0] = result
