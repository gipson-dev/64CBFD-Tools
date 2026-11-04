"""Independent guest model for func_15075938's wrapped path condition."""

from dataclasses import dataclass

from tools.experiments import game_path_offset_condition_match as match
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read


ACTOR_POINTER = 0x800D154C
COMMAND = 0x800D1890
TARGET = 0x800D1891
MODE = 0x800D1892
PATH_COUNTS_POINTER = 0x800D2108
HELPER = 0x15075400
ACTOR = 0x24000
PATH_COUNTS = 0x26000
ACTOR_REGION = (ACTOR - 0x20, 0x280)
TABLE_REGION = (PATH_COUNTS - 0x10, 0x120)


def s8(value):
    value &= 0xFF
    return value - 0x100 if value & 0x80 else value


@dataclass(frozen=True)
class Case:
    path_count: int
    current: int
    offset: int
    target: int
    mode: int
    command: int
    path_index: int
    phase: int = 0


def fixture(case):
    memory = {
        STACK + offset: (offset * 17 + case.command * 29 + 0xA5) & 0xFF
        for offset in range(-0x400, 0x180)
    }
    for start, length in (ACTOR_REGION, TABLE_REGION):
        memory.update({
            start + offset: (offset * 13 + case.path_index * 7 + 0x5A) & 0xFF
            for offset in range(length)
        })
    for address in (ACTOR_POINTER, COMMAND, TARGET, MODE, PATH_COUNTS_POINTER):
        memory.update({address + offset: 0xA5 for offset in range(4)})

    put(memory, ACTOR_POINTER, ACTOR, 4)
    put(memory, PATH_COUNTS_POINTER, PATH_COUNTS, 4)
    put(memory, COMMAND, case.command, 1)
    put(memory, TARGET, case.target, 1)
    put(memory, MODE, case.mode, 1)
    put(memory, ACTOR + 0x13F, case.path_index, 1)
    put(memory, ACTOR + 0x21E, case.current, 1)
    put(memory, ACTOR + 0x221, case.offset, 1)
    put(memory, PATH_COUNTS + case.path_index, case.path_count, 1)
    return memory


def reference(initial, case):
    memory = dict(initial)
    current = case.current - s8(case.offset)
    wrap = case.path_count - 1
    if current < 0:
        current += wrap
    elif current >= wrap:
        current -= wrap

    target = case.path_count - 2 if case.target == 0xFF else case.target
    if case.mode == 0:
        changed = target == current
    elif case.mode == 1:
        changed = target != current
    elif case.mode == 2:
        changed = target < current
    else:
        changed = target > current
    calls = [(HELPER, (case.command,))] if changed else []
    return memory, calls


def public(memory):
    return {
        address: value for address, value in memory.items()
        if not STACK - 0x400 <= address < STACK + 0x180
    }


class PathOffsetConditionOracle(TimingOracle):
    def __init__(self, words, memory, case):
        super().__init__(words, memory, phase=case.phase, entry=match.ENTRY,
                         arguments=(0xDEADBEEF,))

    def record_call(self, target):
        if target != HELPER:
            raise AssertionError("Unexpected path-condition call %08X" % target)
        arguments = self.arguments(1)
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))

    def hook(self, target):
        if target != HELPER:
            raise AssertionError("Unexpected path-condition hook %08X" % target)
        for offset in range(4):
            self.put(self.r[29] + offset * 4, 0xC7000000 + offset, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xC5000000 + register
        self.f[:20] = [0xC6000000 + index for index in range(20)]
        self.lo, self.hi = 0xC5000010, 0xC5000011

    def execute(self, word):
        if word >> 26 == 32:  # lb
            rs = word >> 21 & 31
            rt = word >> 16 & 31
            immediate = word & 0xFFFF
            if immediate & 0x8000:
                immediate -= 0x10000
            address = (self.r[rs] + immediate) & 0xFFFFFFFF
            self.r[rt] = s8(self.get(address, 1)) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)
