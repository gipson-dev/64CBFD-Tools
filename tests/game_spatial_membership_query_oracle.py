"""Independent guest model for func_1503F800's relative spatial tree."""

from dataclasses import dataclass

from tools.experiments import game_spatial_membership_query_match as match
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read


HEAD = 0x800DBE48
INITIALIZE = 0x1510F800
BASE = 0x24000
A, B, C, D, ALTERNATE = (
    BASE + 0x80,
    BASE + 0xC0,
    BASE + 0x40,
    BASE + 0x100,
    BASE + 0x180,
)
NODE_REGION = (BASE - 0x100, 0x400)


def u32(value):
    return value & 0xFFFFFFFF


def s16(value):
    return ((value & 0xFFFF) ^ 0x8000) - 0x8000


def put16(memory, address, value):
    put(memory, address, value & 0xFFFF, 2)


def get16(memory, address):
    return s16(read(memory, address, 2))


def set_node(memory, address, mask, sibling, radius, center_x, center_z, child):
    put16(memory, address + 0, 0x6A5A)
    put16(memory, address + 2, mask)
    put16(memory, address + 4, sibling)
    put16(memory, address + 6, radius)
    put16(memory, address + 8, center_x)
    put16(memory, address + 10, center_z)
    put16(memory, address + 12, child)


@dataclass(frozen=True)
class Case:
    kind: int
    x: int = 0x12340064
    z: int = 0xABCDFFCE
    category: int = 7
    mode: int = 0
    phase: int = 0
    fifth: int = 0


def fixture(case):
    memory = {
        STACK + offset: (offset * 17 + case.kind * 29 + 0xA5) & 0xFF
        for offset in range(-0x400, 0x180)
    }
    start, length = NODE_REGION
    memory.update({start + offset: (offset * 13 + 0x5A) & 0xFF
                   for offset in range(length)})
    for offset in range(-8, 12):
        memory[HEAD + offset] = 0xA5

    x, z = s16(case.x), s16(case.z)
    bit = 1 << case.category
    radius = 9
    set_node(memory, A, bit, 0, radius, x, z, 0)
    set_node(memory, B, bit, 0, radius, x, z, 0)
    set_node(memory, C, bit, 0, radius, x, z, 0)
    set_node(memory, D, bit, 0, 0xFFFF, x, z, 0)
    set_node(memory, ALTERNATE, bit, 0, radius, x, z, 0)
    put(memory, HEAD, A, 4)

    if case.kind == 0:  # Empty tree.
        put(memory, HEAD, 0, 4)
    elif case.kind == 1:  # Accepted leaf.
        pass
    elif case.kind == 2:  # In bounds but wrong category: reject immediately.
        set_node(memory, A, 0, B - A, radius, x, z, 0)
    elif case.kind == 3:  # Out of bounds, then a positive sibling offset.
        set_node(memory, A, bit, B - A, radius, x + radius + 1, z, 0)
    elif case.kind == 4:  # Out of bounds, then a negative sibling offset.
        put(memory, HEAD, B, 4)
        set_node(memory, B, bit, C - B, radius, x + radius + 1, z, 0)
    elif case.kind == 5:  # Selected parent, then a positive child offset.
        set_node(memory, A, bit, 0, radius, x, z, B - A)
    elif case.kind == 6:  # Selected parent, then a negative child offset.
        put(memory, HEAD, B, 4)
        set_node(memory, B, bit, 0, radius, x, z, C - B)
    elif case.kind == 7:  # Exhaust a zero sibling offset.
        set_node(memory, A, bit, 0, radius, x + radius + 1, z, 0)
    elif case.kind == 8:  # Inclusive positive X edge.
        set_node(memory, A, bit, 0, radius, x - radius, z, 0)
    elif case.kind == 9:  # Inclusive negative X edge.
        set_node(memory, A, bit, 0, radius, x + radius, z, 0)
    elif case.kind == 10:  # One beyond the positive Z edge.
        set_node(memory, A, bit, 0, radius, x, z - radius - 1, 0)
    elif case.kind == 11:  # Zero-radius exact point.
        set_node(memory, A, bit, 0, 0, x, z, 0)
    elif case.kind == 12:  # Maximum unsigned radius remains unsigned.
        set_node(memory, A, bit, 0, 0xFFFF, x + 123, z - 321, 0)
    elif case.kind == 13:  # One beyond the negative Z edge.
        set_node(memory, A, bit, 0, radius, x, z + radius + 1, 0)
    else:
        raise ValueError("Unknown spatial-membership fixture")
    return memory


def initialize_effect(memory, mode):
    if mode == 1:
        put(memory, HEAD, ALTERNATE, 4)
    elif mode == 2:
        put(memory, HEAD, 0, 4)
    elif mode == 3:
        put16(memory, read(memory, HEAD) + 2, 0)


def reference(initial, case):
    memory = dict(initial)
    initialize_effect(memory, case.mode)
    x, z = s16(case.x), s16(case.z)
    node = read(memory, HEAD)
    while node:
        center_x = get16(memory, node + 8)
        radius = read(memory, node + 6, 2)
        if center_x - radius <= x <= center_x + radius:
            center_z = get16(memory, node + 10)
            if center_z - radius <= z <= center_z + radius:
                mask = get16(memory, node + 2)
                if not (mask & (1 << case.category)):
                    return memory, 1, [(INITIALIZE, (0,))]
                offset = get16(memory, node + 12)
                if not offset:
                    return memory, 0, [(INITIALIZE, (0,))]
            else:
                offset = get16(memory, node + 4)
        else:
            offset = get16(memory, node + 4)
        node = u32(node + offset) if offset else 0
    return memory, 1, [(INITIALIZE, (0,))]


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x400 <= address < STACK + 0x180}


class SpatialMembershipOracle(TimingOracle):
    def __init__(self, words, memory, case):
        arguments = (0x34567890, case.x, case.z, case.category, case.fifth)
        super().__init__(words, memory, phase=case.phase, entry=match.ENTRY,
                         arguments=arguments)
        self.case = case

    def record_call(self, target):
        if target != INITIALIZE:
            raise AssertionError("Unexpected spatial-membership call %08X" % target)
        arguments = self.arguments(1)
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))

    def hook(self, target):
        if target != INITIALIZE:
            raise AssertionError("Unexpected spatial-membership hook %08X" % target)
        initialize_effect(self.memory, self.case.mode)
        for offset in range(4):
            self.put(self.r[29] + offset * 4, 0xC7000000 + offset, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xC5000000 + register
        self.f[:20] = [0xC6000000 + index for index in range(20)]
        self.lo, self.hi = 0xC5000010, 0xC5000011

