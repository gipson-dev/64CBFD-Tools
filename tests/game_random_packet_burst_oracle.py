"""Independent packet arithmetic and bounded providers for the random burst."""
import math

from tools.tests import game_table_debris_oracle as prior
from tools.experiments import game_random_packet_burst as source

STACK, put, read = prior.STACK, prior.put, prior.read
bits, floating, rounded, HOLES = prior.bits, prior.floating, prior.rounded, prior.HOLES
RANDOMS = (0x8000FFFF, 0x7FFF0000, 0xFFFF8000, 0x00000001, 0x1234ABCD,
    0xFEDC4321, 0x80000000, 0x7FFFFFFF, 0x0000FFFF, 0xFFFFFFFF, 0, 0x87654321)


def signed(n):
    return n if n < 0x80000000 else n - 0x100000000


def fixture(rom, count=3, kind=0x89ABCDCB, minimum=0.5, maximum=1.0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-2048, 768)}
    memory.update({0x800A6FA4 + i: b for i, b in enumerate(rom[0x24BA64:0x24BA80])})
    args = (count & 0xFFFFFFFF, kind, bits(123.25), bits(-45.5), bits(8.125), bits(6.0),
        bits(minimum), bits(maximum), bits(60.0), 0xABCD0105, 0x87654321, bits(-0.7), 0xABCDEF81, 0xFEDCBA98)
    return memory, args


def effects(memory, packet, incoming, role, number, mode):
    if mode == 1 and role == 'random':
        for axis in range(3):
            put(memory, incoming + 8 + axis * 4, bits(number * (axis + 1) * -1.25))
    if mode == 5 and role == 'random':
        put(memory, incoming + 20, bits(number * 0.75))
        for i in (24, 28, 32, 36, 40, 44, 48, 52):
            put(memory, incoming + i, bits(99.0))
    if packet is None:
        return
    if role == 'submit' and mode in (2, 3, 4):
        for i in HOLES:
            packet[i] = (number * 19 + i) & 255
        put(packet, 0x0C, bits(number * 1.25))
        put(packet, 0x48, bits(number * 1.25))
        put(packet, 0x3C, number * 101)
        packet[0x55] = number & 255
    if mode == 3 and role == 'random' and number % 12 == 0:
        put(packet, 0x30, bits(number * 0.25))
        put(packet, 0x34, bits(number * 0.5))
    if mode == 4 and role == 'random':
        put(packet, 0x40, 0x13570000 + number)


def duration_word(value):
    if not math.isfinite(value) or value < 0 or value >= 4294967296.0:
        return 0xFFFFFFFF
    return math.trunc(value)


def reference(initial, args, mode=0, rotation=0, phase=0):
    memory, incoming = dict(initial), STACK + phase
    for i, a in enumerate(args):
        put(memory, incoming + i * 4, a)
    packet = {i: memory[incoming - 224 + 124 + i] if i in HOLES else 0 for i in range(96)}
    scale_range = rounded(floating(args[7]) - floating(args[6]))
    minimum, spread = floating(args[6]), rounded(floating(args[8]) / 65536.0)
    vertical_spread = rounded(floating(args[5]) * floating(0x36CCCCCD))
    for i, value in ((0x48, rounded(floating(args[11]) * -0.75)), (0x4C, floating(args[11])), (0x50, floating(0xBE4CCCCD))):
        put(packet, i, bits(value))
    put(packet, 0x3C, args[10])
    for i, value in ((0x54, 2), (0x55, 255), (0x5A, args[1]), (0x5B, args[9]), (0x5C, 1), (0x5D, 1)):
        put(packet, i, value, 1)
    calls, packets, draws = [], [], 0
    if signed(args[0]) <= 0:
        return calls, packets
    put(memory, incoming + 20, bits(rounded(floating(args[5]) * floating(0x3F4CCCCD))))
    flags, context = args[12] & 255, args[13]

    def draw():
        nonlocal draws
        value = RANDOMS[(draws + rotation) % len(RANDOMS)]
        draws += 1
        calls.append(('random',))
        effects(memory, packet if packets else None, incoming, 'random', draws, mode)
        return value

    for index in range(signed(args[0])):
        for axis in range(3):
            high = signed(draw()) >> 16
            put(packet, axis * 4, bits(rounded(rounded(high * spread) + floating(read(memory, incoming + 8 + axis * 4)))))
        calls.append(('lookup', args[1]))
        effects(memory, packet if packets else None, incoming, 'lookup', index + 1, mode)
        put(packet, 0x40, 0 if mode in (4, 6) else 0xABCD0000 + index + 1)
        put(packet, 0x18, bits(rounded((signed(draw()) >> 16) * (15.0 / 65536.0))))
        low = draw() & 65535
        put(packet, 0x1C, bits(rounded(rounded(low * vertical_spread) + floating(read(memory, incoming + 20)))))
        put(packet, 0x20, bits(rounded((signed(draw()) >> 16) * (15.0 / 65536.0))))
        for axis in range(3):
            put(packet, 0x24 + axis * 4, bits(rounded((signed(draw()) >> 16) * (10.0 / 65536.0))))
        for axis in range(3):
            low = draw() & 65535
            value = rounded(rounded(rounded(low / 65536.0) * scale_range) + minimum)
            if axis < 2:
                put(packet, 0x30 + axis * 4, bits(value))
            else:
                third = value
        total = rounded(rounded(floating(read(packet, 0x30)) + floating(read(packet, 0x34))) + third)
        duration = rounded(rounded(total * floating(0x40D55556)) + 20.0)
        packet[0x59] = duration_word(duration) & 255
        put(packet, 0x38, bits(third))
        calls.append(('submit', flags, context))
        packets.append(bytes(packet.values()))
        effects(memory, packet, incoming, 'submit', index + 1, mode)
    return calls, packets


class BurstOracle(prior.TableDebrisOracle):
    def __init__(self, words, memory, args, phase=0, mode=0, rotation=0, fcsr=0, **kwargs):
        kwargs.setdefault('entry', source.ENTRY)
        kwargs.setdefault('bindings', {a: a for a in (source.RANDOM, source.LOOKUP, source.SUBMIT)})
        super().__init__(words, memory, args, phase=phase, mode=mode, rotation=rotation, **kwargs)
        self.fcsr = self.initial_fcsr = fcsr

    def record_call(self, target):
        assert self.fcsr == self.initial_fcsr, 'duration conversion leaked FCSR state'
        canonical = self.bindings.get(target, target)
        if canonical == source.RANDOM:
            self.calls.append(('random',))
        elif canonical == source.LOOKUP:
            self.lookup_count += 1
            self.calls.append(('lookup', self.r[4]))
        elif canonical == source.SUBMIT:
            self.packet_pointer = self.r[4]
            packet = bytes(self.peek(self.packet_pointer + i, 1) for i in range(96))
            self.full_packets.append(packet)
            self.packets.append(prior.initialized(packet))
            self.calls.append(('submit', self.r[5], self.r[6]))
        else:
            return super().record_call(target)
        if self.packet_pointer is not None:
            self.observed.append((canonical, bytes(self.peek(self.packet_pointer + i, 1) for i in range(96))))

    def hook(self, target):
        canonical = self.bindings.get(target, target)
        if canonical not in (source.LOOKUP, source.RANDOM, source.SUBMIT):
            return super().hook(target)
        packet = None if self.packet_pointer is None else {
            i: self.peek(self.packet_pointer + i, 1) for i in range(96)}
        if canonical == source.RANDOM:
            value = RANDOMS[(self.random_count + self.rotation) % len(RANDOMS)]
            self.random_count += 1
            role, number = 'random', self.random_count
        elif canonical == source.LOOKUP:
            value = 0 if self.mode in (4, 6) else 0xABCD0000 + self.lookup_count
            role, number = 'lookup', self.lookup_count
        else:
            value, role, number = 0, 'submit', len(self.full_packets)
        effects(self.memory, packet, self.incoming, role, number, self.mode)
        if packet is not None:
            for i, byte in packet.items():
                self.put(self.packet_pointer + i, byte, 1)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for i in (*range(1, 16), 24, 25):
            self.r[i] = 0xA5000000 + i
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = value

    def run(self):
        result = super().run()
        assert self.fcsr == self.initial_fcsr
        return result
