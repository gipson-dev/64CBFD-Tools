"""Guest semantics and live-helper mutation proof for the cleanup callback pair."""

from dataclasses import dataclass
import struct

from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read


OWNER = 0x30000
RELEASE = 0x1516972C
UNREGISTER = 0x1000FD38
CALLBACK = 0x151C87AC
FUNCTIONS = {
    "func_151C94D4": (0x151C94D4, 0x1513CA6C),
    "func_151C95D8": (0x151C95D8, 0x1513CAA0),
}
OFFSETS = (0x13C, 0x144, 0x148, 0x14C, 0x150, 0x154, 0x158, 0x15C, 0x160)
RESOURCES = tuple(0x50000 + index * 0x100 for index in range(len(OFFSETS)))
u32 = lambda value: value & 0xFFFFFFFF


@dataclass(frozen=True)
class Case:
    pattern: int = 0
    mutation_slot: int = -1
    mutation_call: int = -1
    replacement: int = 0
    phase: int = 0
    seed: int = 0


def cases():
    rows = [Case(pattern=pattern) for pattern in range(1 << len(OFFSETS))]
    for slot in range(len(OFFSETS)):
        for call in (0, 1, 2, 4, 8):
            for replacement in (0, slot + 1):
                rows.append(Case((1 << len(OFFSETS)) - 1, slot, call, replacement))
    for pattern in (0, 1, 0x100, 0x1FF):
        rows.append(Case(pattern=pattern, phase=8))
        rows.append(Case(pattern=pattern, phase=8, seed=1))
        for seed in (1, 2):
            rows.append(Case(pattern=pattern, seed=seed))
    return tuple(dict.fromkeys(rows))


def fixture(case):
    memory = {STACK + case.phase + index: (index * 17 + case.seed * 13 + 0xA5) & 0xFF
              for index in range(-512, 768)}
    memory.update({OWNER - 32 + index: (index * 29 + case.seed * 11 + 0x5A) & 0xFF
                   for index in range(0x220)})
    for index, offset in enumerate(OFFSETS):
        put(memory, OWNER + offset, RESOURCES[index] if case.pattern & (1 << index) else 0)
    return memory


def apply_effect(memory, case, ordinal):
    if ordinal == case.mutation_call and case.mutation_slot >= 0:
        value = (RESOURCES[case.replacement - 1] if case.replacement else 0)
        put(memory, OWNER + OFFSETS[case.mutation_slot], value)


def reference(initial, case, finalizer):
    memory = dict(initial)
    calls = []

    first = read(memory, OWNER + OFFSETS[0])
    if first:
        calls.append((RELEASE, (first,)))
        apply_effect(memory, case, len(calls) - 1)
        calls.append((UNREGISTER, (CALLBACK, OWNER + 0x110, 0)))
        apply_effect(memory, case, len(calls) - 1)

    for offset in OFFSETS[1:]:
        resource = read(memory, OWNER + offset)
        if resource:
            calls.append((RELEASE, (resource,)))
            apply_effect(memory, case, len(calls) - 1)

    calls.append((finalizer, (OWNER,)))
    apply_effect(memory, case, len(calls) - 1)
    return memory, calls


def public(memory, case):
    low = STACK + case.phase - 512
    high = STACK + case.phase + 768
    return {address: value for address, value in memory.items()
            if not low <= address < high}


class CleanupOracle(FactoryOracle):
    def __init__(self, words, memory, case, entry, finalizer):
        self.finalizer = finalizer
        super().__init__(words, memory, case, entry=entry, s={}, arguments=(OWNER,))
        self.before_registers = self.r[:]
        self.before_floats = self.f[:]

    def record_call(self, target):
        counts = {RELEASE: 1, UNREGISTER: 3, self.finalizer: 1}
        assert target in counts, hex(target)
        arguments = tuple(map(u32, self.arguments(counts[target])))
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))

    def hook(self, target):
        apply_effect(self.memory, self.case, len(self.calls) - 1)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011
        self.r[2] = 0xDEADBEEF


def verify(machine, initial, case, finalizer):
    expected_memory, expected_calls = reference(initial, case, finalizer)
    assert public(machine.memory, case) == public(expected_memory, case), case
    assert machine.calls == expected_calls, (case, machine.calls, expected_calls)
    assert machine.r[29] == machine.before_registers[29]
    assert machine.r[16:24] == machine.before_registers[16:24]
    assert machine.r[28] == machine.before_registers[28]
    assert machine.f[20:] == machine.before_floats[20:]


def semantic_state(machine, case):
    return (public(machine.memory, case), machine.calls, machine.trace,
            machine.events, tuple(sorted(machine.visits)))


def qualify(programs):
    rows = cases()
    covered = {name: set() for name in FUNCTIONS}
    executions = 0
    for name, (entry, finalizer) in FUNCTIONS.items():
        variants = programs[name]
        for case in rows:
            initial = fixture(case)
            machines = []
            for words in variants:
                machine = CleanupOracle(words, initial, case, entry, finalizer)
                machine.run()
                verify(machine, initial, case, finalizer)
                machines.append(machine)
                executions += 1
            states = [semantic_state(machine, case) for machine in machines]
            assert states[0] == states[1] == states[2], (name, case)
            covered[name].update(machines[0].visits)

    for name, (entry, _) in FUNCTIONS.items():
        expected = set(range(entry, entry + len(programs[name][0]) * 4, 4))
        assert covered[name] == expected, (name, expected - covered[name])
    return {
        "cases_per_function": len(rows),
        "functions": len(FUNCTIONS),
        "executions": executions,
        "covered_words_per_function": 65,
        "null_patterns": 512,
        "live_helper_mutation_cases": 90,
        "stack_phase_and_seed_cases": len(rows) - 602,
    }
