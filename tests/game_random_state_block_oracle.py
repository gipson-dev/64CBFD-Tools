"""Independent guest model for func_1509C120's state-block replacement."""

from dataclasses import dataclass

from tools.experiments import game_random_state_block_match as match
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read


ACTIVE = 0x800D2E4C
RANDOM = 0x150ADA20
ALLOCATE = 0x10003C40
RELEASE = 0x10004074
BCOPY = 0x10023A10
OLD_BASE = 0x24000
ALLOC_BASE = 0x28000
POISON = 0x2F000
BLOCK_SIZE = 0x1B


@dataclass(frozen=True)
class Case:
    choice: int
    old_present: bool
    gate: int
    pattern: int
    phase: int = 0


def old_address(case):
    return OLD_BASE + case.pattern * 0x100


def allocation_address(case, ordinal):
    return ALLOC_BASE + case.pattern * 0x1000 + ordinal * 0x100


def random_value(case, ordinal):
    if ordinal == 0:
        return ((case.pattern * 0x125A5A5) & 0xFFFFFFFC) | case.choice
    return ((case.pattern * 0x243137) & 0xFFFFFFFB) | case.gate


def fixture(case):
    memory = {
        STACK + offset: (offset * 17 + case.pattern * 29 + 0xA5) & 0xFF
        for offset in range(-0x400, 0x180)
    }
    for address in range(ACTIVE - 8, ACTIVE + 12):
        memory[address] = 0xA5
    for base in (old_address(case), POISON):
        for offset in range(-8, BLOCK_SIZE + 8):
            memory[base + offset] = (
                offset * 13 + case.pattern * 31 + base // 0x100 + 0x5A
            ) & 0xFF
    for ordinal in range(4):
        base = allocation_address(case, ordinal)
        for offset in range(-8, BLOCK_SIZE + 8):
            memory[base + offset] = (
                offset * 19 + ordinal * 37 + case.pattern * 11 + 0x63
            ) & 0xFF
    put(memory, ACTIVE, old_address(case) if case.old_present else 0, 4)
    return memory


def copy_bytes(memory, source, destination, length):
    values = [memory[source + offset] for offset in range(length)]
    for offset, value in enumerate(values):
        memory[destination + offset] = value


def reference(initial, case):
    memory = dict(initial)
    calls = [(RANDOM, ())]
    old = old_address(case) if case.old_present else 0
    proceed = not case.old_present
    if case.old_present:
        calls.append((RANDOM, ()))
        proceed = case.gate == 4
    if not proceed:
        return memory, calls

    blocks = []
    for ordinal in range(case.choice + 1):
        address = allocation_address(case, ordinal)
        blocks.append(address)
        calls.append((ALLOCATE, (BLOCK_SIZE, 0xFF, 2, 0)))
    for ordinal in range(case.choice):
        calls.append((RELEASE, (blocks[ordinal],)))

    selected = blocks[case.choice]
    put(memory, ACTIVE, selected, 4)
    if old:
        calls.append((BCOPY, (old, selected, BLOCK_SIZE)))
        copy_bytes(memory, old, selected, BLOCK_SIZE)
        calls.append((RELEASE, (old,)))
    return memory, calls


def public(memory):
    return {
        address: value for address, value in memory.items()
        if not STACK - 0x400 <= address < STACK + 0x180
    }


class RandomStateBlockOracle(TimingOracle):
    def __init__(self, words, memory, case):
        super().__init__(
            words,
            memory,
            phase=case.phase,
            entry=match.ENTRY,
            arguments=(0xDEADBEEF,),
        )
        self.case = case
        self.random_calls = 0
        self.allocate_calls = 0

    def record_call(self, target):
        widths = {
            RANDOM: 0,
            ALLOCATE: 4,
            RELEASE: 1,
            BCOPY: 3,
        }
        if target not in widths:
            raise AssertionError("Unexpected state-block call %08X" % target)
        arguments = self.arguments(widths[target])
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))

    def hook(self, target):
        arguments = self.calls[-1][1]
        returned = 0xC5000002
        if target == RANDOM:
            returned = random_value(self.case, self.random_calls)
            self.random_calls += 1
        elif target == ALLOCATE:
            if arguments != (BLOCK_SIZE, 0xFF, 2, 0):
                raise AssertionError("Unexpected allocation arguments")
            returned = allocation_address(self.case, self.allocate_calls)
            self.allocate_calls += 1
        elif target == BCOPY:
            source, destination, length = arguments
            copy_bytes(self.memory, source, destination, length)
        elif target != RELEASE:
            raise AssertionError("Unexpected state-block hook %08X" % target)

        for offset in range(4):
            self.put(self.r[29] + offset * 4, 0xC7000000 + offset, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xC5000000 + register
        self.f[:20] = [0xC6000000 + index for index in range(20)]
        self.lo, self.hi = 0xC5000010, 0xC5000011
        self.r[2] = returned & 0xFFFFFFFF
