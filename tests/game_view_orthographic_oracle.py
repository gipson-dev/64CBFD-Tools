"""Bounded setup protocol and finite, exactly representable orthographic cases."""
import itertools
import struct

from tools.experiments import game_view_orthographic_setup as source
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import bits, floating, signed

ORTHO, ORTHO_FLOAT, IDENTITY, CONVERTER = 0x151EF954, 0x151EF800, 0x151EFE00, 0x151EFD00
BASE, NEAR, FAR, DERIVED, COEFFICIENT = 0x800BE628, 0x800D9B20, 0x800D9B1C, 0x800D3670, 0x800A2C20
CONFIG_NEAR, CONFIG_FAR, MATRIX, VIEWS, ALTERNATE = 0x800DD2F2, 0x800DD2F4, 0x800D9B28, 0x24000, 0x28000
BANKS = ((VIEWS, 0x180), (ALTERNATE, 0x180), (0x800D9B10, 0x80), (0x800D3660, 0x40), (0x800A2C10, 0x40))
CONFIG_BANK, CONFIG_SIZE = 0x800DD2E0, 0x40
SHORTS = (0, 1, -1, 32767, -32768, 0x1234)
FLOATS = (bits(160), bits(-120), 0, 0x80000000, 0x7F800000, 0xFF800000,
    0x7FC12345, 0x7F810000, 1, 0x80000001, bits(0.5), bits(1024))
VIEW_CHOICES = (VIEWS, MATRIX - 0xC, FAR - 0xC, DERIVED - 0xC, COEFFICIENT - 0xC, DERIVED - 0x10, NEAR - 0xC)


def signed16(value):
    return value if value < 32768 else value - 65536


def fixture(near=0, far=1, pattern=0, view=0):
    memory = {machine.STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x600, 0x180)}
    for base, size in (*BANKS, (CONFIG_BANK, CONFIG_SIZE), (BASE, 4)):
        memory.update({base + i: (i * 13 + 0xA5) & 255 for i in range(size)})
    put(memory, CONFIG_NEAR, near & 65535, 2)
    put(memory, CONFIG_FAR, far & 65535, 2)
    for address, value in ((NEAR, bits(-7)), (FAR, bits(31)), (DERIVED, bits(77)), (COEFFICIENT, FLOATS[(pattern + 3) % 12])):
        put(memory, address, value)
    for bank in (VIEWS, ALTERNATE):
        put(memory, bank + 0xC, FLOATS[pattern % 12])
        put(memory, bank + 0x10, FLOATS[(pattern + 5) % 12])
    put(memory, BASE, VIEW_CHOICES[view])
    return memory


def helper_effect(memory, packet, mode=0):
    if mode:
        for address, value in ((BASE, ALTERNATE), (NEAR, bits(9)), (FAR, bits(-11)),
                (DERIVED, bits(13)), (COEFFICIENT, bits(-8)), (ALTERNATE + 0xC, bits(7)), (ALTERNATE + 0x10, bits(-3))):
            put(memory, address, value)
        put(memory, CONFIG_NEAR, 0x8001, 2)
        put(memory, CONFIG_FAR, 0x7FFE, 2)
    for i in range(16):
        put(memory, packet[0] + i * 4, (0x11223300 ^ packet[1 + i % 7] ^ (i * 0x01010101)) & 0xFFFFFFFF)


def packet_and_defaults(memory):
    memory = dict(memory)
    near, far = signed16(read(memory, CONFIG_NEAR, 2)), signed16(read(memory, CONFIG_FAR, 2))
    put(memory, NEAR, bits(near))
    put(memory, FAR, bits(far))
    put(memory, DERIVED, bits(100.0 - floating(read(memory, FAR))))
    view = read(memory, BASE)
    x, y = read(memory, view + 0xC), read(memory, view + 0x10)
    return memory, (MATRIX, x ^ 0x80000000, x, y ^ 0x80000000, y, bits(1), read(memory, COEFFICIENT), bits(1))


def reference(memory, mode=0):
    memory, packet = packet_and_defaults(memory)
    helper_effect(memory, packet, mode)
    return memory, packet


def finite_sdk_fixture(width, height, coefficient, near=-32768, far=32767):
    memory = fixture(near, far)
    put(memory, VIEWS + 0xC, bits(width))
    put(memory, VIEWS + 0x10, bits(height))
    put(memory, COEFFICIENT, bits(coefficient))
    return memory


def sdk_reference(memory):
    memory, packet = packet_and_defaults(memory)
    width, height, far = map(floating, (packet[2], packet[4], packet[6]))
    values = [0.0] * 16
    values[0], values[5] = 1.0 / width, 1.0 / height
    values[10], values[14], values[15] = -2.0 / (far - 1), -(far + 1) / (far - 1), 1.0
    integers = []
    for value in values:
        scaled = value * 65536
        assert scaled == int(scaled) and -0x80000000 <= scaled <= 0x7FFFFFFF
        integers.append(int(scaled) & 0xFFFFFFFF)
    payload = struct.pack('>32H', *(word >> 16 for word in integers), *(word & 65535 for word in integers))
    for i, value in enumerate(payload):
        memory[MATRIX + i] = value
    return memory, packet


def mock_cases():
    for n, (pair, pattern, view, mode) in enumerate(itertools.product(range(6), range(12), range(7), range(2))):
        yield dict(memory=fixture(SHORTS[pair], SHORTS[(pair + 3) % 6], pattern, view), mode=mode,
            unused=(0, 0x80000000, 0xFFFFFFFF, 0x12345678)[n % 4], view=view)


class SetupOracle(machine.BurstOracle):
    def __init__(self, words, memory, unused=0, mode=0, phase=0, connected=None, fault=None, entry=source.ENTRY):
        super().__init__(words, memory, phase=phase, entry=entry, arguments=(unused,), connected=connected, fault=fault)
        self.code = faults.TrackedCode(self.code, self)
        self.current_pc, self.delay_of = entry, None
        self.mode, self.fault, self.accesses = mode, fault, 0

    def access(self):
        if self.own_instruction and source.ENTRY <= self.current_pc < source.ENTRY + 184:
            if self.accesses == self.fault:
                raise faults.AccessBoundary
            self.accesses += 1

    def record_call(self, target):
        widths = {ORTHO: 8, ORTHO_FLOAT: 8, IDENTITY: 1, CONVERTER: 2}
        assert target in widths, hex(target)
        packet = self.arguments(widths[target])
        self.calls.append((target, packet))
        self.events.append(('CALL', target, packet))

    def hook(self, target):
        assert target == ORTHO
        helper_effect(self.memory, self.calls[-1][1], self.mode)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0xAABB1234
