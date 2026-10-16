"""Independent typed-table contract and bounded MIPS packet observations."""
from tools.tests import test_game_quad_edge_emitter as edge
from tools.tests import game_six_piece_debris_match_oracle as prior
from tools.experiments import game_table_debris as source

STACK, bits, floating, rounded = edge.STACK, edge.bits, edge.floating, edge.rounded
put, read, short, public = edge.put, edge.read, edge.short, edge.public
ACTOR, HOLES = 0x20000, prior.HOLES
RANDOMS = (0.0, 1.0 / 65536.0, 0.25, 0.5, 0.75, 65535.0 / 65536.0)


def initialized(packet):
    return bytes(value for i, value in enumerate(packet) if i not in HOLES)


def fixture(rom, pattern=0, flags=0xABCDEF81, context=0x87654321):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-2048, 768)}
    memory.update({ACTOR + i: 0xA5 for i in range(128)})
    for i, value in enumerate(((0, 1, -1), (-32768, 32767, -123), (123, -456, 789))[pattern % 3]):
        put(memory, ACTOR + 16 + i * 2, value, 2)
    memory.update({source.TABLE + i: b for i, b in enumerate(rom[0x24B998:0x24BA40])})
    memory.update({0x800A6F98 + i: b for i, b in enumerate(rom[0x24BA58:0x24BA70])})
    if pattern:
        for index in range(6):
            at = source.TABLE + index * 28
            put(memory, at, (0x8000 + 257 * index) if pattern == 1 else 65535 - index, 2)
            put(memory, at + 2, 0xABCD, 2)
            for field in range(6):
                value = ((index + 1) * (field + 1) * 3.25) * (-1 if field % 2 else 1)
                put(memory, at + 4 + field * 4, bits(value))
    return memory, (ACTOR, flags & 0xFFFFFFFF, context & 0xFFFFFFFF)


def effects(memory, role, number, mode, packet=None):
    if mode in (1, 3) and role == 'lookup':
        at = source.TABLE + (number - 1) * 28
        put(memory, at, 0xDC80 + number, 2)
        put(memory, at + 4, bits(number * -31.25))
        put(memory, at + 8, bits(number * -7.5))
        put(memory, at + 16, bits(number * 19.25))
        put(memory, ACTOR + 16, 12345, 2)
        for address in range(0x800A6F98, 0x800A6FB0, 4):
            put(memory, address, bits(99.0))
    if mode == 5 and role == 'random':
        put(memory, source.TABLE + ((number - 1) // 2) * 28 + 4, bits(number * 17.25))
    if mode in (2, 3) and role == 'submit':
        for i in HOLES:
            put(packet, i, (number * 19 + i) & 255, 1)
        for i in (0x0C, 0x30, 0x48):
            put(packet, i, bits(number * 1.25))
        put(packet, 0x3C, number * 101)
        put(packet, 0x55, number, 1)


def reference(memory, args, mode=0, rotation=0, phase=0, frame=0xE8, home=0x84):
    memory, packet = dict(memory), {i: 0 for i in range(96)}
    for i in HOLES:
        packet[i] = memory[STACK + phase - frame + home + i]
    origins = [float(short(read(memory, args[0] + 16 + 2 * i, 2))) for i in range(3)]
    horizontal, vertical, rotation_scale = [floating(read(memory, at)) for at in (0x800A6FAC, 0x800A6FA8, 0x800A6FA4)]
    for i in (0x30, 0x34, 0x38):
        put(packet, i, bits(2.0))
    put(packet, 0x3C, 60)
    for i in range(3):
        put(packet, 0x48 + i * 4, read(memory, 0x800A6F98 + i * 4))
    for i, value in ((0x54, 2), (0x55, 255), (0x5B, 6), (0x5C, 2), (0x5D, 1)):
        put(packet, i, value, 1)
    calls, packets, draws = [], [], 0
    for index in range(6):
        at = source.TABLE + index * 28
        calls.append(('lookup', read(memory, at, 2)))
        asset = 0 if mode == 4 and index % 2 == 0 else 0xABCD0000 + index + 1
        effects(memory, 'lookup', index + 1, mode)
        put(packet, 0x5A, read(memory, at, 2), 1)
        for axis in range(3):
            value = floating(read(memory, at + 4 + 4 * axis))
            put(packet, axis * 4, bits(rounded(value + origins[axis])))
            put(packet, 0x18 + axis * 4, bits(rounded((abs(value) if axis == 1 else value) * (vertical if axis == 1 else horizontal))))
            put(packet, 0x0C + axis * 4, read(memory, at + 16 + axis * 4))
        put(packet, 0x24, bits(rounded(floating(read(packet, 0x0C)) * rotation_scale)))
        for offset, scale, center in ((0x28, 4.0, 2.0), (0x2C, 10.0, 5.0)):
            calls.append(('random',))
            value = RANDOMS[(draws + rotation) % len(RANDOMS)]
            draws += 1
            effects(memory, 'random', draws, mode)
            put(packet, offset, bits(rounded(rounded(value * scale) - center)))
        put(packet, 0x40, asset)
        calls.append(('submit', args[1] & 255, args[2]))
        packets.append(bytes(packet.values()))
        effects(memory, 'submit', index + 1, mode, packet)
    put(memory, args[0] + 0x6E, 1, 1)
    return calls, packets, public(memory)


class TableDebrisOracle(edge.EdgeOracle):
    def __init__(self, words, memory, args, phase=0, mode=0, rotation=0, fault=None,
            connected=None, fail=False, entry=source.ENTRY, bindings=None):
        super().__init__(words, memory, args, phase=phase, mode=mode, fault=fault, connected=connected, entry=entry)
        self.lookup_count, self.packet_pointer, self.rotation, self.fail = 0, None, rotation, fail
        self.full_packets, self.observed, self.lower_calls, self.copies = [], [], [], []
        self.bindings = bindings or {source.LOOKUP: source.LOOKUP, source.RANDOM: source.RANDOM, source.SUBMIT: source.SUBMIT}

    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 5:
            self.f[word >> 6 & 31] = self.f[word >> 11 & 31] & 0x7FFFFFFF
        else:
            super().execute(word)

    def record_call(self, target):
        canonical = self.bindings.get(target, target)
        if canonical == source.LOOKUP:
            self.lookup_count += 1
            self.calls.append(('lookup', self.r[4]))
        elif canonical == source.RANDOM:
            self.calls.append(('random',))
        elif canonical == source.SUBMIT:
            self.packet_pointer = self.r[4]
            packet = bytes(self.peek(self.packet_pointer + i, 1) for i in range(96))
            self.full_packets.append(packet)
            self.packets.append(initialized(packet))
            self.calls.append(('submit', self.r[5], self.r[6]))
        else:
            count = {prior.ALLOCATOR: 6, prior.HEAP: 5, prior.REGISTER: 2, prior.COPY: 3}[target]
            self.lower_calls.append((target, *self.arguments(count)))
        if self.packet_pointer is not None:
            self.observed.append((canonical, bytes(self.peek(self.packet_pointer + i, 1) for i in range(96))))

    def hook(self, target):
        canonical = self.bindings.get(target, target)
        value = 0xABCD0123
        returned = None
        if canonical == source.LOOKUP:
            effects(self.memory, 'lookup', self.lookup_count, self.mode)
            value = 0 if self.mode == 4 and self.lookup_count % 2 else 0xABCD0000 + self.lookup_count
        elif canonical == source.RANDOM:
            returned = bits(RANDOMS[(self.random_count + self.rotation) % len(RANDOMS)])
            self.random_count += 1
            effects(self.memory, 'random', self.random_count, self.mode)
        elif canonical == source.SUBMIT:
            packet = {i: self.peek(self.packet_pointer + i, 1) for i in range(96)}
            effects(self.memory, 'submit', len(self.full_packets), self.mode, packet)
            for i, byte in packet.items():
                self.put(self.packet_pointer + i, byte, 1)
        elif target == prior.HEAP:
            value = 0 if self.fail and len(self.full_packets) % 3 == 0 else 0x30000 + (len(self.full_packets) - 1) * 0x100
        elif target == prior.REGISTER:
            self.put(self.r[4], self.r[5], 1)
        elif target == prior.COPY:
            src, dest, size = self.arguments(3)
            assert size == 96
            packet = bytes(self.get(src + i, 1) for i in range(size))
            for i, byte in enumerate(packet):
                self.put(dest + i, byte, 1)
            self.copies.append((dest, packet))
        else:
            raise AssertionError(('unknown table-debris provider', hex(target)))
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for i in (*range(1, 16), 24, 25):
            self.r[i] = 0xA5000000 + i
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = value
        if returned is not None:
            self.f[0] = returned
