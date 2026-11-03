"""Guest semantic corpus for the selected menu record submitter."""

from dataclasses import dataclass

from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put


ENTRY = 0x151E2404
SUBMIT = 0x150076A0
SOURCE = 0x800E0BE0
STATE_GLOBAL = 0x8008FDD4
INDEX_TABLE = 0x800AB690
RECORD_GLOBAL = 0x80082BBC
JUMP_TABLE = 0x800AB9BC
STATE = 0x30000
RECORDS = 0x60000
TARGETS = (0x151E2490, 0x151E249C, 0x151E249C, 0x151E24CC, 0x151E24CC,
           0x151E24B0, 0x151E24CC, 0x151E24B0, 0x151E24BC, 0x151E24BC)


@dataclass(frozen=True)
class Case:
    index: int
    category: int = 0
    seed: int = 0
    phase: int = 0


def cases():
    return tuple(Case(index, category, seed, phase)
                 for index in (-2, -1, *range(12))
                 for category, seed, phase in ((0, 0, 0), (2, 1, 8)))


def fixture(case):
    memory = {STACK + case.phase + offset: (offset * 17 + case.seed * 13 + 0xA5) & 0xFF
              for offset in range(-512, 768)}
    for base, size in ((SOURCE, 28), (STATE, 0x80), (INDEX_TABLE, 0x80),
                       (RECORDS - 0x40, 0x120), (JUMP_TABLE, 40)):
        memory.update({base + offset: (offset * 29 + case.seed * 11 + 0x5A) & 0xFF
                       for offset in range(size)})
    put(memory, STATE_GLOBAL, STATE)
    put(memory, RECORD_GLOBAL, RECORDS)
    memory[STATE + 0x42] = case.category
    memory[INDEX_TABLE + case.category * 10] = case.index & 0xFF
    for position, target in enumerate(TARGETS):
        put(memory, JUMP_TABLE + position * 4, target)
    return memory


def reference(initial, case):
    memory = dict(initial)
    record = (RECORDS + case.index * 10) & 0xFFFFFFFF
    source = lambda offset: memory[SOURCE + offset]
    memory[record] = 0
    memory[record + 1] = source(2)
    memory[record + 2] = source(3)
    memory[record + 3] = source(0x10)
    memory[record + 4] = source(0x11)
    if case.index == 0:
        memory[record + 5] = source(4)
    elif case.index in (1, 2):
        memory[record + 5] = source(0xD)
        memory[record + 6] = source(0xE)
    elif case.index in (5, 7):
        memory[record + 5] = source(0x12)
    elif case.index in (8, 9):
        memory[record + 5] = source(7)
        memory[record + 6] = source(0x13)
    memory[record + 8] = source(0x16)
    memory[record + 9] = source(6)
    return memory, [(SUBMIT, ())]


def public(memory, case):
    low, high = STACK + case.phase - 512, STACK + case.phase + 768
    return {address: value for address, value in memory.items()
            if not low <= address < high}


class MenuRecordOracle(FactoryOracle):
    def __init__(self, words, memory, case):
        super().__init__(words, memory, case, entry=ENTRY, s={}, arguments=())
        self.before_registers = self.r[:]
        self.before_floats = self.f[:]

    def execute(self, word):
        op = word >> 26
        if op == 11:  # sltiu
            source, target = word >> 21 & 31, word >> 16 & 31
            immediate = word & 0xFFFF
            if immediate & 0x8000:
                immediate |= 0xFFFF0000
            self.r[target] = int((self.r[source] & 0xFFFFFFFF) < immediate)
            self.r[0] = 0
            return
        super().execute(word)

    def record_call(self, target):
        assert target == SUBMIT, hex(target)
        self.calls.append((target, ()))
        self.events.append(("CALL", target, ()))

    def hook(self, target):
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011


def qualify(programs):
    covered = set()
    executions = 0
    for case in cases():
        initial = fixture(case)
        expected_memory, expected_calls = reference(initial, case)
        states = []
        for program_index, words in enumerate(programs):
            machine = MenuRecordOracle(words, initial, case)
            try:
                machine.run()
            except Exception as error:
                raise AssertionError((case, program_index, error, machine.r,
                                      sorted(machine.visits))) from error
            assert public(machine.memory, case) == public(expected_memory, case), case
            assert machine.calls == expected_calls, case
            assert machine.r[29] == machine.before_registers[29]
            assert machine.r[16:24] == machine.before_registers[16:24]
            assert machine.r[28] == machine.before_registers[28]
            assert machine.f[20:] == machine.before_floats[20:]
            states.append((public(machine.memory, case), machine.calls,
                           machine.trace, machine.events, tuple(sorted(machine.visits))))
            executions += 1
        assert states[0] == states[1] == states[2], case
        covered.update(machine.visits)
    expected = set(range(ENTRY, ENTRY + len(programs[0]) * 4, 4))
    assert covered == expected, sorted(expected - covered)
    return {"cases": len(cases()), "executions": executions,
            "covered_words": len(covered), "switch_cases": 10}
