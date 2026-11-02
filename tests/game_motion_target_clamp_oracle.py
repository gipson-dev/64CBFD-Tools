"""Guest semantics, aliases, and the real object-update callback window."""

from dataclasses import dataclass
import ctypes
import itertools
import struct

from tools.experiments import game_motion_target_clamp_guard_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary


STATE = 0x30000
PARENT = 0x15113E54
PARENT_END = 0x15113F00
PARENT_ROM = 0x141304
TABLE_ROM = 0x22D96C
DISPATCH_GLOBALS = {
    "D_800DBEF0": 0x800DBEF0,
    "D_800DBEF4": 0x800DBEF4,
    "D_800DBF98": 0x800DBF98,
}
POSITIONS = (
    0xC1200000, 0x00000000, 0x80000000, 0x412FFFFF, 0x41300000,
    0x41300001, 0x425BFFFF, 0x425C0000, 0x425C0001, 0x42C80000,
    0x7F800000, 0xFF800000, 0x7FC12345,
)
VELOCITIES = (
    0xBF800000, 0xBDCCCCCD, 0x80000000, 0, 0x3DCCCCCD,
    0x3F800000, 0x7F800000, 0xFF800000, 0x7FC54321,
)
TARGETS = (
    0xC0000000, 0xBF000000, 0x80000000, 0, 0x3F000000,
    0x40000000, 0x7F800000, 0x7FC23456,
)
TICKS = (-0x80000000, -100, -1, 0, 1, 2, 100, 0x7FFFFFFF)
CONSTANTS = (
    (0x3F0CCCCD, 0x3F0CCCCD, 0x3D4CCCCD, 0x3D4CCCCD),
    (0x3F400000, 0x3E800000, 0x3E000000, 0x3D000000),
    (0x80000000, 0, 0x3F000000, 0x3E800000),
)


def u32(value):
    return value & 0xFFFFFFFF


def signed(value):
    value &= 0xFFFFFFFF
    return (value & 0x7FFFFFFF) - (value & 0x80000000)


def floating(word):
    return struct.unpack(">f", struct.pack(">I", word & 0xFFFFFFFF))[0]


def bits(value):
    rounded = ctypes.c_float(value).value
    return struct.unpack(">I", struct.pack(">f", rounded))[0]


def add(left, right):
    return bits(floating(left) + floating(right))


def multiply(left, right):
    return bits(floating(left) * floating(right))


def integer_float(value):
    return bits(float(signed(value)))


def less(left, right):
    return floating(left) < floating(right)


def is_nan(word):
    return (word & 0x7F800000) == 0x7F800000 and (word & 0x7FFFFF) != 0


@dataclass(frozen=True)
class Case:
    position: int = 0x41200000
    velocity: int = 0x3F000000
    target: int = 0
    ticks: int = 1
    constants: tuple = CONSTANTS[0]
    state: int = STATE
    seed: int = 0
    phase: int = 0


def cases():
    rows = []
    for index, (position, velocity, ticks) in enumerate(
            itertools.product(POSITIONS, VELOCITIES, TICKS)):
        rows.append(Case(position, velocity, TARGETS[index % len(TARGETS)], ticks,
                         CONSTANTS[index % len(CONSTANTS)], seed=index & 3,
                         phase=(index & 1) * 8))
    for index, (region, velocity, target) in enumerate(itertools.product(
            (0x41200000, 0x41A00000, 0x42800000), VELOCITIES, TARGETS)):
        rows.append(Case(region, velocity, target, (0, 1, 2)[index % 3],
                         CONSTANTS[index % len(CONSTANTS)], seed=index & 3,
                         phase=(index & 1) * 8))
    # Exercise every live field against every external input address. These
    # cases preserve the retail load/store order instead of assuming no alias.
    aliases = []
    for address in (*source.SYMBOLS.values(),):
        for offset in (4, 0x64, 0x7C):
            aliases.append(u32(address - offset))
    for index, state in enumerate(aliases):
        rows.append(Case(POSITIONS[index % len(POSITIONS)],
                         VELOCITIES[(index * 3) % len(VELOCITIES)],
                         TARGETS[(index * 5) % len(TARGETS)],
                         TICKS[index % len(TICKS)], CONSTANTS[index % len(CONSTANTS)],
                         state=state, seed=index & 3, phase=(index & 1) * 8))
    return rows


def fixture(case):
    memory = {STACK + index: (index * 17 + case.seed * 13 + 0xA5) & 0xFF
              for index in range(-1024, 1024)}
    for index in range(-16, 0x100):
        memory[u32(case.state + index)] = (index * 29 + case.seed * 11 + 0x5A) & 0xFF
    values = (case.ticks, *case.constants)
    for address, value in zip((source.SYMBOLS["D_800BE9E4"],
                               source.SYMBOLS["D_800A0FA0"],
                               source.SYMBOLS["D_800A0FA4"],
                               source.SYMBOLS["D_800A0FA8"],
                               source.SYMBOLS["D_800A0FAC"]), values):
        put(memory, address, value)
    # Write state fields last so aliased fixtures have one unambiguous initial
    # byte image; the reference then performs the retail access sequence.
    put(memory, u32(case.state + 4), case.position)
    put(memory, u32(case.state + 0x64), case.velocity)
    put(memory, u32(case.state + 0x7C), case.target)
    return memory


def reference(initial, case):
    memory = dict(initial)
    state = case.state
    tick = read(memory, source.SYMBOLS["D_800BE9E4"])
    velocity = read(memory, u32(state + 0x64))
    position = read(memory, u32(state + 4))
    position = add(position, multiply(velocity, integer_float(tick)))
    put(memory, u32(state + 4), position)
    position = read(memory, u32(state + 4))
    if less(position, 0x41300000):
        target = read(memory, source.SYMBOLS["D_800A0FA0"])
        velocity = read(memory, u32(state + 0x64))
        put(memory, u32(state + 0x7C), target)
    elif less(0x425C0000, position):
        target = read(memory, source.SYMBOLS["D_800A0FA4"]) ^ 0x80000000
        velocity = read(memory, u32(state + 0x64))
        put(memory, u32(state + 0x7C), target)
    else:
        target = read(memory, u32(state + 0x7C))
    if less(velocity, target):
        value = add(velocity, read(memory, source.SYMBOLS["D_800A0FA8"]))
        put(memory, u32(state + 0x64), value)
        value = read(memory, u32(state + 0x64))
        if less(target, value):
            put(memory, u32(state + 0x64), target)
    elif less(target, velocity):
        value = add(velocity, read(memory, source.SYMBOLS["D_800A0FAC"]) ^ 0x80000000)
        put(memory, u32(state + 0x64), value)
        value = read(memory, u32(state + 0x64))
        if less(value, target):
            put(memory, u32(state + 0x64), target)
    return memory


class MotionOracle(FactoryOracle):
    def __init__(self, words, memory, case, entry=source.ENTRY, connected=None):
        super().__init__(words, memory, case, entry=entry, s={}, connected=connected,
                         arguments=(case.state,))

    def execute(self, word):
        op = word >> 26
        fmt = word >> 21 & 31
        fn = word & 63
        if op == 17 and fmt == 16 and fn == 7:
            self.f[word >> 6 & 31] = self.f[word >> 11 & 31] ^ 0x80000000
            return
        super().execute(word)

    def record_call(self, target):
        if target == source.ENTRY:
            args = tuple(self.arguments(1))
            self.calls.append((target, args))
            self.events.append(("CALL", target, args))
            return
        raise AssertionError(("Unexpected call", hex(target)))

    def hook(self, target):
        raise AssertionError(("Unexpected hook", hex(target)))


def result_words(memory, case):
    return tuple(read(memory, u32(case.state + offset)) for offset in (4, 0x64, 0x7C))


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 1024 <= address < STACK + 1024}


def semantic_equal(actual, expected, case):
    if actual.keys() != expected.keys():
        return False
    outputs = {u32(case.state + offset + byte)
               for offset in (4, 0x64, 0x7C) for byte in range(4)}
    for address in actual:
        if actual[address] == expected[address]:
            continue
        if address not in outputs:
            return False
        offset = next(offset for offset in (4, 0x64, 0x7C)
                      if address in {u32(case.state + offset + byte) for byte in range(4)})
        if not (is_nan(read(actual, u32(case.state + offset))) and
                is_nan(read(expected, u32(case.state + offset)))):
            return False
    return True


def qualify(root, programs):
    rows = cases()
    executions = 0
    visits = set()
    paths = {"low": 0, "middle": 0, "high": 0}
    aliases = 0
    for case in rows:
        initial = fixture(case)
        expected = reference(initial, case)
        machines = []
        for words in programs:
            machine = MotionOracle(words, initial, case).run()
            if not semantic_equal(machine.memory, expected, case):
                raise AssertionError((case, result_words(machine.memory, case),
                                      result_words(expected, case)))
            machines.append(machine)
            executions += 1
        first = machines[0]
        for machine in machines[1:]:
            if (machine.memory, machine.trace, machine.calls, machine.r[2]) != (
                    first.memory, first.trace, first.calls, first.r[2]):
                raise AssertionError(("program mismatch", case))
        visits.update(first.visits)
        position = floating(read(expected, u32(case.state + 4)))
        if position < 11.0:
            paths["low"] += 1
        elif 55.0 < position:
            paths["high"] += 1
        else:
            paths["middle"] += 1
        aliases += case.state != STATE

    rom = (root / "conker/conker.us.bin").read_bytes()
    if struct.unpack_from(">I", rom, TABLE_ROM)[0] != source.ENTRY:
        raise AssertionError("Motion callback table entry changed")
    parent_words = struct.unpack_from(">%dI" % ((PARENT_END - PARENT) // 4),
                                      rom, PARENT_ROM)
    caller_cases = 0
    for case in (Case(), Case(0x42800000, 0xBF000000, 0, 2, CONSTANTS[1]),
                 Case(0x412FFFFF, 0x3F000000, 0, -1, CONSTANTS[2], phase=8)):
        initial = fixture(case)
        put(initial, DISPATCH_GLOBALS["D_800DBEF0"], 1)
        put(initial, DISPATCH_GLOBALS["D_800DBF98"], 0)
        put(initial, DISPATCH_GLOBALS["D_800DBEF4"], case.state)
        initial[u32(case.state + 0x6F)] = 0x40
        initial[u32(case.state + 0x6E)] = 0
        put(initial, u32(case.state + 0x38), source.ENTRY)
        expected = reference(initial, case)
        pair = []
        for words in programs:
            connected = dict(zip(range(source.ENTRY, source.ENTRY + source.WORDS * 4, 4),
                                 words))
            machine = MotionOracle(parent_words, initial, case, entry=PARENT,
                                   connected=connected)
            machine.code = WindowCode(machine.code, machine)
            machine.code.ends = (PARENT_END,)
            try:
                machine.run()
            except WindowBoundary:
                pass
            else:
                raise AssertionError("Callback window did not reach boundary")
            if not semantic_equal(public(machine.memory), public(expected), case):
                raise AssertionError(("caller memory", case))
            if machine.calls != [(source.ENTRY, (case.state,))]:
                raise AssertionError(("caller ABI", machine.calls))
            pair.append(machine)
        for machine in pair[1:]:
            if pair[0].trace != machine.trace or pair[0].memory != machine.memory:
                raise AssertionError(("caller program mismatch", case))
        caller_cases += 1
    return {
        "cases": len(rows),
        "executions": executions,
        "covered_words": len(visits),
        "paths": paths,
        "alias_cases": aliases,
        "caller_cases": caller_cases,
        "callback_table_rom": "0x%X" % TABLE_ROM,
        "callback_field": "state+0x38",
        "callback_argument": "a0=state",
        "return_value_consumed": False,
    }
