"""Pending-row protocol with bounded projection callback effects."""
import itertools

from tools.experiments import game_view_pending_queue as source
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_animation_timeline_oracle import bits, signed
from tools.tests.test_game_point_transform_match import put, read
from tools.tests import game_view_projection_family_oracle as family

COUNT, ROWS, DIRTY, COMMAND = 0x80082FA0, 0x800D9AC0, 0x800D9AF0, 0x1510B128
BANKS = ((COUNT - 8, 0x20), (ROWS - 16, 0x80))
FLOATS = (bits(-1), 0, 0x80000000, bits(0.5), bits(-2), 0x7F800000,
    0xFF800000, 0x7FC12345, 0x7F810000, 1, 0x80000001, bits(1024))
COUNTS = (-0x80000000, -2, -1, 0, 1, 3, 5)


def fixture(count=3, pattern=0, skip=0):
    memory = {machine.STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x600, 0x180)}
    for base, size in BANKS:
        memory.update({base + i: (i * 13 + 0xA5) & 255 for i in range(size)})
    for index in range(6):
        for field in range(3):
            put(memory, ROWS + index * 12 + field * 4, FLOATS[(pattern + index + field * 3) % 12])
        if skip >> index & 1:
            put(memory, ROWS + index * 12, bits(-1))
    put(memory, COUNT, count & 0xFFFFFFFF)
    memory[DIRTY] = 0xA5
    return memory


def effects(memory, packet, mode, ordinal):
    index = packet[0]
    if mode == 1:
        put(memory, COUNT, 0xFFFFFFFF)
    elif mode == 2 and ordinal == 1:
        put(memory, COUNT, 5)
    elif mode == 3:
        put(memory, ROWS + index * 12, bits(9))
        if index < 5:
            for field, value in enumerate((bits(0.5), 0x7FCAB123, 0x80000000)):
                put(memory, ROWS + (index + 1) * 12 + field * 4, value)
    elif mode == 4:
        put(memory, COUNT, 0)
        memory[DIRTY] = 0xFE
        put(memory, ROWS + index * 12 + 4, 0x12345678)
    elif mode == 5 and index < 5:
        put(memory, ROWS + (index + 1) * 12, bits(-1))
    elif mode == 6:
        put(memory, COUNT, min(index + 1, 5))


def reference(memory, mode=0):
    memory, packets = dict(memory), []
    count, index = signed(read(memory, COUNT)), 0
    while index <= count:
        assert index < 6, 'Outside bounded row domain'
        row = ROWS + index * 12
        scale = read(memory, row)
        if scale != bits(-1):
            packet = (index, read(memory, row + 4), read(memory, row + 8), scale, 0)
            packets.append((COMMAND, packet))
            effects(memory, packet, mode, len(packets))
            put(memory, row, bits(-1))
            count = signed(read(memory, COUNT))
        index += 1
    memory[DIRTY] = 0
    return memory, packets


def cases():
    for count, pattern, skip, mode in itertools.product(COUNTS, range(12), (0, 0x15, 0x2A, 0x3F), range(7)):
        yield dict(memory=fixture(count, pattern, skip), mode=mode)


class QueueOracle(machine.BurstOracle):
    def __init__(self, words, memory, mode=0, phase=0, fault=None, connected=None):
        super().__init__(words, memory, phase=phase, entry=source.ENTRY,
            arguments=(0x12345678,), connected=connected, fault=fault)
        self.code = faults.TrackedCode(self.code, self)
        self.current_pc, self.delay_of = source.ENTRY, None
        self.fault, self.accesses, self.mode = fault, 0, mode

    def access(self):
        if self.own_instruction and source.ENTRY <= self.current_pc < source.ENTRY + 168:
            if self.accesses == self.fault:
                raise faults.AccessBoundary
            self.accesses += 1

    def record_call(self, target):
        assert target == COMMAND, hex(target)
        packet = self.arguments(5)
        self.calls.append((target, packet))
        self.events.append(('CALL', target, packet))

    def hook(self, target):
        assert target == COMMAND
        effects(self.memory, self.calls[-1][1], self.mode, len(self.calls))
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0xAABB1234


def connected_reference(memory, sdk_mode=0):
    memory, calls, commands = dict(memory), [], []
    index, count = 0, signed(read(memory, COUNT))
    while index <= count:
        row = ROWS + index * 12
        scale = read(memory, row)
        if scale != bits(-1):
            packet = (index, read(memory, row+4), read(memory, row+8), scale, 0)
            commands.append(packet)
            memory, child_calls = family.reference(memory, packet, sdk_mode=sdk_mode)
            calls.extend(child_calls)
            put(memory, row, bits(-1))
            count = signed(read(memory, COUNT))
        index += 1
    memory[DIRTY] = 0
    return memory, calls, commands


class ConnectedQueueOracle(family.FamilyOracle):
    def __init__(self, words, memory, connected, sdk_mode=0, phase=0):
        super().__init__(words, memory, (0, 0, 0, 0, 0), sdk_mode=sdk_mode,
            phase=phase, root=source.ENTRY, connected=connected)

    def record_call(self, target):
        if target == COMMAND:
            packet = self.arguments(5)
            self.index = packet[0]
            self.command_calls.append(packet)
        else:
            super().record_call(target)
