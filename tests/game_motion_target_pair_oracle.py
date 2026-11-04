"""Independent guest model for the split motion-target callback pair."""

from dataclasses import dataclass

from tools.experiments import game_motion_target_pair_match as match
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read


TABLE_GLOBAL = 0x800BE4E0
TABLE = 0x28000
HELPER = 0x150CDB6C
RANDOM = 0x150ADA20
ADVANCE = 0x150C8350


@dataclass(frozen=True)
class Case:
    intensity: int
    present: bool
    pattern: int
    phase: int = 0


def random_value(case, ordinal):
    values = (
        0,
        1,
        0x7FFFFFFF,
        0x80000000,
        0xFFFFFFFF,
        0xA5A50000 | ((case.pattern * 37 + ordinal * 19) & 0xFFFF),
    )
    return values[(case.pattern + ordinal) % len(values)]


def fixture(case):
    memory = {STACK + offset: (offset * 17 + case.pattern * 29 + 0xA5) & 0xFF
              for offset in range(-0x400, 0x180)}
    for address in range(TABLE_GLOBAL - 8, TABLE_GLOBAL + 12):
        memory[address] = 0xA5
    for offset in range(-8, 116):
        memory[TABLE + offset] = (offset * 13 + case.pattern * 31 + 0x63) & 0xFF
    put(memory, TABLE_GLOBAL, TABLE if case.present else 0, 4)
    return memory


def signed(value):
    return value - 0x100000000 if value & 0x80000000 else value


def reference(initial, case):
    memory = dict(initial)
    calls = []
    if not case.present:
        return memory, calls
    calls.append((HELPER, (case.intensity & 0xFFFFFFFF,)))
    base = (case.intensity * 300) >> 8
    span = ((case.intensity * 50) >> 8) + 50
    for ordinal, offset in enumerate(range(0, 100, 10)):
        calls.append((RANDOM, ()))
        target = base + (random_value(case, ordinal) % span)
        put(memory, TABLE + offset + 8, target & 0xFFFF, 2)
    return memory, calls


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x400 <= address < STACK + 0x180}


class InitializerOracle(TimingOracle):
    def __init__(self, words, memory, case):
        super().__init__(words, memory, phase=case.phase,
                         entry=match.INITIALIZER_ENTRY,
                         arguments=(case.intensity & 0xFFFFFFFF,))
        self.case = case
        self.random_calls = 0

    def record_call(self, target):
        widths = {HELPER: 1, RANDOM: 0}
        if target not in widths:
            raise AssertionError("Unexpected motion-target call %08X" % target)
        arguments = self.arguments(widths[target])
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))

    def hook(self, target):
        returned = 0xC5000002
        if target == RANDOM:
            returned = random_value(self.case, self.random_calls)
            self.random_calls += 1
        for offset in range(4):
            self.put(self.r[29] + offset * 4, 0xC7000000 + offset, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xC5000000 + register
        self.f[:20] = [0xC6000000 + index for index in range(20)]
        self.lo, self.hi = 0xC5000010, 0xC5000011
        self.r[2] = returned & 0xFFFFFFFF


class WrapperOracle(TimingOracle):
    def __init__(self, words, memory, view, phase):
        super().__init__(words, memory, phase=phase, entry=match.WRAPPER_ENTRY,
                         arguments=(view & 0xFFFFFFFF,))

    def record_call(self, target):
        if target != ADVANCE:
            raise AssertionError("Unexpected frame-layer call %08X" % target)
        self.calls.append((target, ()))
        self.events.append(("CALL", target, ()))

    def hook(self, target):
        for offset in range(4):
            self.put(self.r[29] + offset * 4, 0xD7000000 + offset, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xD5000000 + register
        self.r[2] = 0xD5000002
