"""Full 96-byte debris packets and retained-provider observations, not just initialized bytes."""
from tools.tests import game_six_piece_debris_oracle as previous
from tools.experiments import game_six_piece_debris_match as source

STACK, bits, floating = previous.STACK, previous.bits, previous.floating
put, read, public, AccessFault = previous.put, previous.read, previous.edge.public, previous.edge.AccessFault
HOLES = previous.HOLES
ALLOCATOR, HEAP, REGISTER, COPY = 0x15167A68, 0x10003C6C, 0x15168A4C, 0x10023A10


def reference(memory, args, mode=0, rotation=0, phase=0):
    calls, packets, known_holes, result = previous.reference(memory, args, mode, rotation)
    holes = bytes(memory[STACK + phase - 0x120 + 0xBC + i] for i in HOLES)
    full = []
    for packet, known in zip(packets, known_holes):
        if known is not None:
            holes = known
        values, h, data = iter(packet), iter(holes), []
        for i in range(96):
            data.append(next(h) if i in HOLES else next(values))
        full.append(bytes(data))
    return calls, full, result


class DebrisMatchOracle(previous.DebrisOracle):
    def __init__(self, words, memory, args, phase=0, mode=0, rotation=0, fault=None,
            connected=None, fail=False, entry=source.ENTRY, bindings=None):
        super().__init__(words, memory, args, phase, mode, rotation, fault)
        self.entry = entry
        self.code = {entry + i * 4: w for i, w in enumerate(words)}
        self.code.update(connected or {})
        self.full_packets, self.observed, self.lower_calls, self.copies = [], [], [], []
        self.fail = fail
        self.bindings = bindings or {source.LOOKUP: source.LOOKUP, source.RANDOM: source.RANDOM,
            source.SUBMIT: source.SUBMIT, source.RING: source.RING}

    def record_call(self, target):
        canonical = self.bindings.get(target, target)
        if canonical in (source.LOOKUP, source.RANDOM, source.SUBMIT, source.RING):
            super().record_call(canonical)
            if canonical == source.SUBMIT:
                self.full_packets.append(bytes(self.peek(self.packet_pointer + i, 1) for i in range(96)))
            if self.packet_pointer is not None:
                self.observed.append((canonical, bytes(self.peek(self.packet_pointer + i, 1) for i in range(96))))
        else:
            count = {ALLOCATOR: 6, HEAP: 5, REGISTER: 2, COPY: 3}[target]
            self.lower_calls.append((target, *self.arguments(count)))

    def hook(self, target):
        canonical = self.bindings.get(target, target)
        if canonical in (source.LOOKUP, source.RANDOM, source.SUBMIT, source.RING):
            if self.packet_pointer is not None:
                if self.mode == 5 and canonical == source.RANDOM:
                    self.put(self.packet_pointer + 0x18, bits(123.25 + self.random_count), 4)
                elif self.mode == 6 and canonical == source.LOOKUP:
                    self.put(self.packet_pointer + 0x3C, 700 + self.lookup_count, 4)
            return super().hook(canonical)
        value = 0xABCD0123
        if target == HEAP:
            value = 0 if self.fail and len(self.full_packets) % 3 == 0 else 0x30000 + (len(self.full_packets) - 1) * 0x100
        elif target == REGISTER:
            self.put(self.r[4], self.r[5], 1)
        elif target == COPY:
            src, dest, length = self.arguments(3)
            assert length == 96
            packet = bytes(self.get(src + i, 1) for i in range(length))
            for i, b in enumerate(packet):
                self.put(dest + i, b, 1)
            self.copies.append((dest, packet))
        else:
            raise AssertionError(('unknown connected debris provider', hex(target)))
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for i in (*range(1, 16), 24, 25):
            self.r[i] = 0xA5000000 + i
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = value


def literal(model):
    return (model.memory, model.r, model.f, model.hi, model.lo, model.condition, model.events,
        model.calls, model.full_packets, model.observed, model.lower_calls, model.copies, model.accesses)
