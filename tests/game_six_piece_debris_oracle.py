"""Bounded debris model: initialized packet bytes, opaque calls, and live globals."""
import struct

from tools.experiments import game_six_piece_debris as source
from tools.tests import test_game_quad_edge_emitter as edge

STACK, bits, floating, rounded = edge.STACK, edge.bits, edge.floating, edge.rounded
put, read, signed, short = edge.put, edge.read, edge.signed, edge.short
ACTOR, VECTORS, KINDS = 0x20000, 0x800A6E90, 0x800A6F80
HOLES = (0x44, 0x45, 0x46, 0x47, 0x5E, 0x5F)
RANDOMS = (0, 0x7FFFFFFF, 0x80000000, 0xFFFF0000, 0x12345678, 0xFEDCBA98)


def fixture(rom, options=0, kind=1, variant=0x12345678, flags=0xABCDEF81, pattern=0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-2048, 768)}
    memory.update({ACTOR + i: 0xA5 for i in range(0x80)})
    for i, value in enumerate(((0, 1, -1), (-32768, 32767, -123), (123, -456, 789))[pattern % 3]):
        put(memory, ACTOR + 0x10 + 2 * i, value, 2)
    memory.update({VECTORS + i: b for i, b in enumerate(rom[0x24B950:0x24B998])})
    memory.update({KINDS + i: b for i, b in enumerate(rom[0x24BA40:0x24BA58])})
    return memory, (ACTOR, kind & 0xFFFFFFFF, variant, options & 0xFFFFFFFF, flags, 0x87654321)


def effects(memory, role, number, mode, packet=None):
    if mode in (1, 3) and role == 'lookup':
        put(memory, VECTORS + (number - 1) * 12, bits(number * -31.25))
        put(memory, KINDS + number % 6, 0x70 + number, 1)
        put(memory, ACTOR + 0x10, 12345, 2)
        put(memory, 0x800A6F94, bits(99.0))
        put(memory, 0x800A6F88, bits(11.0))
    if mode == 3 and role == 'random':
        put(memory, VECTORS + ((number // 6) % 6) * 12 + 4, bits(number * -2.5))
    if mode in (2, 3) and role == 'submit':
        # Providers may retain and alter the escaped object between iterations.
        for i in HOLES:
            put(packet, i, (number * 19 + i) & 255, 1)
        for i in (0x0C, 0x30, 0x48):
            put(packet, i, bits(number * 1.25))
        put(packet, 0x3C, number * 101)
        put(packet, 0x55, number, 1)


def initialized(packet):
    return bytes(value for i, value in enumerate(packet) if i not in HOLES)


def reference(memory, args, mode=0, rotation=0):
    memory, packet = dict(memory), {i: 0 for i in range(96)}
    origins = [float(short(read(memory, args[0] + 16 + i * 2, 2))) for i in range(3)]
    coefficient = floating(read(memory, 0x800A6F94))
    for i in (0x30, 0x34, 0x38):
        put(packet, i, bits(1.0))
    put(packet, 0x3C, 60)
    for i in range(3):
        put(packet, 0x48 + i * 4, read(memory, 0x800A6F88 + i * 4))
    for i, value in ((0x54, 2), (0x55, 255), (0x59, 60), (0x5B, args[2] & 255)):
        put(packet, i, value, 1)
    calls, packets, holes, random_count = [], [], [], 0
    for index in range(6):
        kind = read(memory, KINDS + index, 1) if args[3] & 2 else (args[1] + (index if args[3] & 1 else 0)) & 0xFFFFFFFF
        calls.append(('lookup', kind))
        asset = 0 if mode == 4 and index % 2 == 0 else 0xABCD0000 + index + 1
        effects(memory, 'lookup', index + 1, mode)
        vector = [floating(read(memory, VECTORS + index * 12 + i * 4)) for i in range(3)]
        for i, value in enumerate(vector):
            put(packet, i * 4, bits(rounded(value + origins[i])))
            velocity = rounded(abs(value) * coefficient) if i == 1 else rounded(value * coefficient)
            if i == 1:
                velocity = rounded(velocity + 7.0)
            put(packet, 0x18 + i * 4, bits(velocity))
        put(packet, 0x5A, kind & 255, 1)
        for i in range(6):
            calls.append(('random',))
            value = RANDOMS[(random_count + rotation) % len(RANDOMS)]
            random_count += 1
            effects(memory, 'random', random_count, mode)
            offset = (0x18 if i < 3 else 0x24) + i % 3 * 4
            value = rounded(float(signed(value) >> 16) * (2.0 ** -14 if i < 3 else 5.0 / 65536.0))
            if i < 3:
                value = rounded(floating(read(packet, offset)) + value)
            put(packet, offset, bits(value))
        put(packet, 0x40, asset)
        calls.append(('submit', args[4] & 255, args[5]))
        packets.append(initialized(bytes(packet.values())))
        holes.append(None if index == 0 or mode not in (2, 3) else bytes(packet[i] for i in HOLES))
        effects(memory, 'submit', index + 1, mode, packet)
    ring = (bits(origins[0]), bits(rounded(origins[1] - 80.0)), bits(origins[2]), bits(70.0),
        500, 0x3B960000, 0, 10, args[4] & 255, args[5])
    calls.append(('ring', *ring))
    put(memory, args[0] + 0x6E, 1, 1)
    return calls, packets, holes, edge.public(memory)


class DebrisOracle(edge.EdgeOracle):
    def __init__(self, words, memory, args, phase=0, mode=0, rotation=0, fault=None):
        super().__init__(words, memory, args, phase=phase, mode=mode, fault=fault, entry=source.ENTRY)
        self.lookup_count, self.packet_pointer, self.holes, self.rotation = 0, None, [], rotation

    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 5:
            self.f[word >> 6 & 31] = self.f[word >> 11 & 31] & 0x7FFFFFFF
        else:
            super().execute(word)

    def record_call(self, target):
        if target == source.LOOKUP:
            self.lookup_count += 1
            self.calls.append(('lookup', self.r[4]))
        elif target == source.RANDOM:
            self.calls.append(('random',))
        elif target == source.SUBMIT:
            self.packet_pointer = self.r[4]
            packet = bytes(self.peek(self.packet_pointer + i, 1) for i in range(96))
            self.packets.append(initialized(packet))
            self.holes.append(bytes(packet[i] for i in HOLES))
            self.calls.append(('submit', self.r[5], self.r[6]))
        elif target == source.RING:
            self.calls.append(('ring', self.f[12], self.f[14], *self.r[6:8], *self.arguments(10)[4:]))
        else:
            raise AssertionError(('unknown debris target', hex(target)))

    def hook(self, target):
        value = 0xABCD0000 + self.lookup_count
        if target == source.LOOKUP:
            effects(self.memory, 'lookup', self.lookup_count, self.mode)
            if self.mode == 4 and self.lookup_count % 2:
                value = 0
        elif target == source.RANDOM:
            value = RANDOMS[(self.random_count + self.rotation) % len(RANDOMS)]
            self.random_count += 1
            effects(self.memory, 'random', self.random_count, self.mode)
        elif target == source.SUBMIT:
            packet = {i: self.peek(self.packet_pointer + i, 1) for i in range(96)}
            effects(self.memory, 'submit', len(self.packets), self.mode, packet)
            for i, b in packet.items():
                self.put(self.packet_pointer + i, b, 1)
        for i in range(10 if target == source.RING else 4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for i in (*range(1, 16), 24, 25):
            self.r[i] = 0xA5000000 + i
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = value
