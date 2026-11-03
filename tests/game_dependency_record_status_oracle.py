"""Guest semantics and live-record reload proof for func_1509D08C."""

from dataclasses import dataclass

from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read


ENTRY = 0x1509D08C
BASE_GLOBAL = 0x800D2FB0
BITS_GLOBAL = 0x800D2E4C
BASE = 0x22000
RECORD = 0x30000
ALT_FIRST = 0x4000
ALT_SECOND = 0x5000
SECOND = 0x34000
LIST = 0x36000
ALT_SECOND_VALUE = 0x37000
ALT_FIRST_LIST = 0x38000
ALT_SECOND_LIST = 0x39000
OUT_FIRST = 0x3A000
OUT_SECOND = 0x3B000
BITS = 0x3C000
u32 = lambda value: value & 0xFFFFFFFF


@dataclass(frozen=True)
class Case:
    ids: tuple = ()
    inactive: int = -1
    outputs: int = 3
    base_null: bool = False
    record_null: bool = False
    alias: int = 0
    index: int = 1
    arg0: int = -7
    phase: int = 0
    seed: int = 0


def signed16(value):
    return ((value & 0xFFFF) ^ 0x8000) - 0x8000


def cases():
    rows = []
    for outputs in range(4):
        rows.extend((Case(outputs=outputs, base_null=True),
                     Case(outputs=outputs, record_null=True),
                     Case(outputs=outputs),
                     Case(ids=(0,), outputs=outputs),
                     Case(ids=(7, 8, 31), outputs=outputs)))
    ids = (-9, -1, 0, 1, 7, 8, 15, 31, 127)
    rows.append(Case(ids=ids))
    for inactive in range(len(ids)):
        rows.append(Case(ids=ids, inactive=inactive))
    rows.extend((Case(ids=(0, 7), alias=1), Case(ids=(1, 8), alias=2),
                 Case(ids=(15,), phase=8, seed=1, index=2, arg0=0x12345678),
                 Case(ids=(31, 63), phase=0, seed=2, outputs=1)))
    return tuple(dict.fromkeys(rows))


def fill(memory, base, size, seed):
    memory.update({base + index: (index * 29 + seed * 11 + 0x5A) & 0xFF
                   for index in range(size)})


def record(memory, address, second, dependencies, ids):
    put(memory, address, second)
    put(memory, address + 8, dependencies)
    put(memory, address + 12, len(ids))
    for index, value in enumerate(ids):
        put(memory, dependencies + index * 2, value, 2)


def fixture(case):
    memory = {STACK + case.phase + index:
              (index * 17 + case.seed * 13 + 0xA5) & 0xFF
              for index in range(-512, 768)}
    for base, size in ((BASE_GLOBAL, 4), (BITS_GLOBAL, 4), (BASE, 0x80),
                       (RECORD, 0x20), (ALT_FIRST, 0x20), (ALT_SECOND, 0x20),
                       (SECOND, 4), (LIST, 0x80), (ALT_SECOND_VALUE, 4),
                       (ALT_FIRST_LIST, 0x80), (ALT_SECOND_LIST, 0x80),
                       (OUT_FIRST, 4), (OUT_SECOND, 4), (BITS - 0x40, 0x80)):
        fill(memory, base, size, case.seed)
    put(memory, BASE_GLOBAL, 0 if case.base_null else BASE)
    put(memory, BITS_GLOBAL, BITS)
    entry = BASE + case.index * 8
    put(memory, entry + 8, 0 if case.record_null else RECORD)
    put(memory, SECOND, 0xFFFF, 2)
    record(memory, RECORD, SECOND, LIST, case.ids)

    if case.alias == 1:
        put(memory, LIST, ALT_FIRST, 2)
        put(memory, ALT_SECOND_VALUE, 0xFFFE, 2)
        record(memory, ALT_FIRST, ALT_SECOND_VALUE, ALT_FIRST_LIST, case.ids)
        for index, value in enumerate(case.ids):
            put(memory, ALT_FIRST_LIST + index * 2, value, 2)
    elif case.alias == 2:
        put(memory, SECOND, ALT_SECOND, 2)
        put(memory, ALT_SECOND_VALUE, 0xFFFD, 2)
        record(memory, ALT_SECOND, ALT_SECOND_VALUE, ALT_SECOND_LIST, case.ids)
        for index, value in enumerate(case.ids):
            put(memory, ALT_SECOND_LIST + index * 2, value, 2)

    for position, resource in enumerate(case.ids):
        address = BITS + (resource >> 3)
        memory[address] = memory.get(address, 0) | 1 << (resource & 7)
        if position == case.inactive:
            memory[address] &= ~(1 << (resource & 7))
    return memory


def pointers(case):
    entry = BASE + case.index * 8
    first = entry + 8 if case.alias == 1 else OUT_FIRST
    second = entry + 8 if case.alias == 2 else OUT_SECOND
    return (first if case.outputs & 1 else 0,
            second if case.outputs & 2 else 0)


def reference(initial, case):
    memory = dict(initial)
    first, second = pointers(case)
    put(memory, STACK + case.phase, case.arg0)
    base = read(memory, BASE_GLOBAL)
    entry = u32(base + case.index * 8)
    if base == 0:
        if first:
            put(memory, first, 0xBF)
        if second:
            put(memory, second, 0)
        return memory, 0
    current = read(memory, entry + 8)
    if current == 0:
        if first:
            put(memory, first, 0xBF)
        if second:
            put(memory, second, 0)
        return memory, 0
    if first:
        put(memory, first, signed16(read(memory, read(memory, current + 8), 2)))
        current = read(memory, entry + 8)
    if second:
        put(memory, second, signed16(read(memory, read(memory, current), 2)))
        current = read(memory, entry + 8)
    count = read(memory, current + 12)
    dependency = read(memory, current + 8)
    for position in range(count):
        resource = signed16(read(memory, dependency + position * 2, 2))
        if not (memory[BITS + (resource >> 3)] & 1 << (resource & 7)):
            return memory, 0
    return memory, 1


class StatusOracle(FactoryOracle):
    def __init__(self, words, memory, case):
        first, second = pointers(case)
        super().__init__(words, memory, case, entry=ENTRY,
                         s={"D_800D2FB0": BASE_GLOBAL,
                            "D_800D2E4C": BITS_GLOBAL},
                         arguments=tuple(map(u32, (case.arg0, case.index, first, second))))
        self.before_registers = self.r[:]
        self.before_floats = self.f[:]


def semantic_state(machine):
    return (machine.memory, machine.r[2], machine.trace, machine.events,
            tuple(sorted(machine.visits)))


def qualify(programs):
    rows = cases()
    covered = set()
    executions = 0
    for case in rows:
        initial = fixture(case)
        expected_memory, expected_return = reference(initial, case)
        machines = []
        for words in programs:
            machine = StatusOracle(words, initial, case)
            machine.run()
            assert machine.memory == expected_memory, case
            assert machine.r[2] == expected_return, case
            assert machine.r[29] == machine.before_registers[29]
            assert machine.r[16:24] == machine.before_registers[16:24]
            assert machine.r[28] == machine.before_registers[28]
            assert machine.f == machine.before_floats
            assert not machine.calls
            machines.append(machine)
            executions += 1
        states = [semantic_state(machine) for machine in machines]
        assert states[0] == states[1] == states[2], case
        covered.update(machines[0].visits)
    expected = set(range(ENTRY, ENTRY + len(programs[0]) * 4, 4))
    assert covered == expected, sorted(expected - covered)
    return {"cases": len(rows), "executions": executions,
            "covered_words": len(covered), "live_reload_cases": 2}
