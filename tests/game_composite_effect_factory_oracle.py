"""Guest-MIPS full-state oracle for func_15152B38."""
from dataclasses import dataclass
from pathlib import Path
import json
import struct

from tools.tests import game_point_effect_payload_oracle as old
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset

ENTRY = 0x15152B38
INPUT = 0x22000
STACK = old.STACK
MARK = old.MARK
SUBMIT = 0x1515C2F0


@dataclass(frozen=True)
class Case:
    seed: int = 0
    mode: int = 0
    extra: int = 0
    mutation: int = 0
    phase: int = 0


def u32(value):
    return value & 0xFFFFFFFF


def put(memory, address, value, size=4):
    old.put(memory, address, value, size)


def get(memory, address, size=4):
    return old.read(memory, address, size)


def signed(value, bits):
    sign = 1 << (bits - 1)
    return ((value & ((1 << bits) - 1)) ^ sign) - sign


def data(memory, address, size):
    return bytes(memory[address + index] for index in range(size))


def set_fields(memory, seed, late=False):
    values = {
        0x00: (1 + ((seed + int(late)) & 1), 4),
        0x04: (1, 4),
        0x08: (old.bits(-8.0 if late else 1.25), 4),
        0x0C: (old.bits(9.0 if late else -2.5), 4),
        0x10: (old.bits(-10.0 if late else 3.75), 4),
        0x14: (old.bits(1.0 if late else 2.0), 4),
        0x18: (old.bits(2.0 if late else 4.0), 4),
        0x1C: (old.bits(3.0 if late else 0.75), 4),
        0x20: (old.bits(5.0 if late else 3.0), 4),
        0x24: (old.bits(6.0 if late else 1.5), 4),
        0x28: (old.bits(7.0 if late else 2.5), 4),
        0x2C: (-12 if late else -30, 2),
        0x2E: (20 if late else 60, 2),
        0x30: (6 if late else 15, 2),
        0x32: (18 if late else 45, 2),
        0x34: (17 if late else 7, 4),
        0x38: (3 if late else 5, 4),
        0x3C: (-9 if late else 20, 2),
        0x3E: (7 if late else 8, 2),
        0x40: (0xB123 if late else 0x8123, 2),
        0x42: (0x31 if late else 0x11, 1),
        0x43: (0x42 if late else 0x22, 1),
        0x44: (0x53 if late else 0x33, 1),
        0x57: (0x64 if late else 0x44, 1),
        0x58: (0x75 if late else 0x55, 1),
        0x5C: (0x12345678 if late else 0x89ABCDEF, 4),
        0x60: (0x23456789 if late else 0x76543210, 4),
        0x64: (-1234 if late else 1234, 2),
        0x66: (2345 if late else -2345, 2),
        0x68: (-3456 if late else 3456, 2),
        0x6A: (0x9A if late else 0x6A, 1),
        0x6C: (old.bits(8.0 if late else 4.5), 4),
        0x70: (-17 if late else 17, 1),
        0x71: (29 if late else -29, 1),
    }
    for index in range(4):
        values[0x45 + index] = (20 + index + (30 if late else 0), 1)
        values[0x49 + index] = (3 + index, 1)
        values[0x4D + index] = (80 + index + (20 if late else 0), 1)
        values[0x51 + index] = (4 + index, 1)
    values[0x55] = (120 if late else 100, 1)
    values[0x56] = (9, 1)
    for offset, (value, size) in values.items():
        put(memory, INPUT + offset, value, size)


def fixture(case):
    home = STACK + case.phase
    memory = {home + index: (index * 19 + case.seed * 17 + 73) & 255 for index in range(-2048, 1024)}
    for index in range(0x74):
        memory[INPUT + index] = (index * 29 + case.seed * 11 + 101) & 255
    set_fields(memory, case.seed, False)
    return memory


def mutate_input(memory, case, late=False):
    mask = 2 if late else 1
    if case.mutation & mask:
        set_fields(memory, case.seed, True)


def reference(initial, case):
    memory = dict(initial)
    home = STACK + case.phase
    stack = home - 176
    packet = stack + 0x58
    header = stack + 0x94
    calls = []
    payloads = []
    integer_index = 0
    float_index = 0

    def integer():
        nonlocal integer_index
        calls.append((old.INTEGER, ()))
        value = old.ri(integer_index, old.Case(seed=case.seed))
        integer_index += 1
        if integer_index == 1:
            mutate_input(memory, case, False)
        return value

    def real():
        nonlocal float_index
        calls.append((old.FLOAT, ()))
        value = old.rf(float_index, old.Case(seed=case.seed))
        float_index += 1
        return value

    first = integer()
    remaining = first % (get(memory, INPUT + 4) + 1) + get(memory, INPUT)
    for offset in range(0, 12, 4):
        put(memory, header + offset, get(memory, INPUT + 8 + offset))
    put(memory, header + 0x0E, get(memory, INPUT + 0x40, 2), 2)
    put(memory, header + 0x10, 10)
    for target, source in ((0x14, 0x42), (0x15, 0x43), (0x16, 0x44), (0x20, 0x57), (0x21, 0x58)):
        put(memory, packet + target, get(memory, INPUT + source, 1), 1)
    for target, source, size in (
        (0x24, 0x5C, 4),
        (0x28, 0x60, 4),
        (0x2C, 0x64, 2),
        (0x2E, 0x66, 2),
        (0x30, 0x68, 2),
        (0x32, 0x6A, 1),
        (0x34, 0x6C, 4),
        (0x38, 0x70, 1),
        (0x39, 0x71, 1),
    ):
        put(memory, packet + target, get(memory, INPUT + source, size), size)
    count = 0
    while remaining:
        first = integer()
        put(memory, header + 0x15, first % (get(memory, INPUT + 0x38) + 1) + get(memory, INPUT + 0x34), 1)
        first = integer()
        short_range = signed(get(memory, INPUT + 0x3E, 2), 16)
        short_base = signed(get(memory, INPUT + 0x3C, 2), 16)
        put(memory, header + 0x0C, first % (short_range + 1) + short_base, 2)
        put(memory, packet, old.fa(old.fm(real(), get(memory, INPUT + 0x18)), get(memory, INPUT + 0x14)))
        put(memory, packet + 0x10, old.fa(old.fm(real(), get(memory, INPUT + 0x20)), get(memory, INPUT + 0x1C)))
        first = integer()
        second = integer()
        sample = real()
        first_angle = signed(first % (signed(get(memory, INPUT + 0x2E, 2), 16) + 1) + signed(get(memory, INPUT + 0x2C, 2), 16), 16)
        second_angle = signed(second % (signed(get(memory, INPUT + 0x32, 2), 16) + 1) + signed(get(memory, INPUT + 0x30, 2), 16), 16)
        radius = old.fa(old.fm(sample, get(memory, INPUT + 0x28)), get(memory, INPUT + 0x24))
        calls.append((old.VECTOR, (u32(first_angle), u32(second_angle), radius, packet + 4)))
        for index, value in enumerate((old.bits(first_angle * 0.125), old.bits(second_angle * 0.25), old.fm(radius, old.bits(0.5)))):
            put(memory, packet + 4 + 4 * index, value)
        pairs = [
            (0x17, 0x45, 0x49),
            (0x18, 0x46, 0x4A),
            (0x19, 0x47, 0x4B),
            (0x1A, 0x48, 0x4C),
            (0x1B, 0x4D, 0x51),
            (0x1C, 0x4E, 0x52),
            (0x1D, 0x4F, 0x53),
            (0x1E, 0x50, 0x54),
            (0x1F, 0x55, 0x56),
        ]
        for target, base, range_offset in pairs:
            first = integer()
            put(memory, packet + target, first % (get(memory, INPUT + range_offset, 1) + 1) + get(memory, INPUT + base, 1), 1)
        call = (SUBMIT, (header, 0, packet, 0, case.mode & 255, u32(case.extra)))
        calls.append(call)
        payloads.append((header, data(memory, header, 24), packet, data(memory, packet, 60)))
        put(memory, MARK + 4 * count, count + 1)
        mutate_input(memory, case, True)
        count += 1
        remaining -= 1
    return memory, calls, payloads, integer_index, float_index


class Machine(FactoryOracle):
    def __init__(self, words, memory, case, entry=ENTRY):
        self.case = case
        self.home = STACK + case.phase
        self.rng_i = 0
        self.rng_f = 0
        self.submits = 0
        self.payloads = []
        super().__init__(words, memory, case, entry=entry, s={}, connected=None, arguments=(INPUT, case.mode, case.extra))

    def record_call(self, target):
        counts = {ENTRY: 3, old.INTEGER: 0, old.FLOAT: 0, old.VECTOR: 4, SUBMIT: 6}
        assert target in counts, hex(target)
        arguments = tuple(u32(value) for value in self.arguments(counts[target]))
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))
        if target == SUBMIT:
            self.payloads.append((arguments[0], data(self.memory, arguments[0], 24), arguments[2], data(self.memory, arguments[2], 60)))

    def hook(self, target):
        case = self.case
        arguments = self.calls[-1][1]
        value = 0
        float_value = None
        if target == old.INTEGER:
            value = old.ri(self.rng_i, old.Case(seed=case.seed))
            self.rng_i += 1
            if self.rng_i == 1:
                mutate_input(self.memory, case, False)
        elif target == old.FLOAT:
            float_value = old.rf(self.rng_f, old.Case(seed=case.seed))
            self.rng_f += 1
        elif target == old.VECTOR:
            vector = (
                old.bits(signed(arguments[0], 16) * 0.125),
                old.bits(signed(arguments[1], 16) * 0.25),
                old.fm(arguments[2], old.bits(0.5)),
            )
            for index, component in enumerate(vector):
                put(self.memory, arguments[3] + 4 * index, component)
        else:
            assert target == SUBMIT
            put(self.memory, MARK + 4 * self.submits, self.submits + 1)
            self.submits += 1
            mutate_input(self.memory, case, True)
        for index in range(4):
            self.put(self.r[29] + 4 * index, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011
        self.r[2] = u32(value)
        if float_value is not None:
            self.f[0] = float_value


def programs(output, layout=0):
    receipt = json.loads((output / "private-layout-v5.json").read_text())
    entry = receipt["layouts"][layout]["entry"]
    result = []
    for label in ("original", "C"):
        image = (output / ("layout-{}-{}.elf".format(layout, label))).read_bytes()
        at = elf_slot_offset(image, entry, 1080)
        result.append(struct.unpack_from(">270I", image, at))
    assert result[0] == result[1]
    return entry, result


def state(machine):
    return (
        machine.memory,
        machine.r,
        machine.f,
        machine.trace,
        machine.calls,
        machine.payloads,
        machine.hi,
        machine.lo,
        machine.current_pc,
        machine.delay_of,
        machine.all_accesses,
        machine.rng_i,
        machine.rng_f,
        machine.submits,
    )


def qualify(root, output):
    cases = [
        Case(
            seed=index % 4,
            mode=index,
            extra=(index * 0x87654321) & 0xFFFFFFFF,
            mutation=(0, 1, 2, 3)[index % 4],
            phase=(index % 2) * 8,
        )
        for index in range(256)
    ]
    total = 0
    seen = set()
    modes = set()
    extras = set()
    layouts = json.loads((output / "private-layout-v5.json").read_text())["layouts"]
    assert len(layouts) == 3
    entry, words = programs(output)
    for case in cases:
        initial = fixture(case)
        expected, calls, payloads, integers, reals = reference(initial, case)
        models = [Machine(code, initial, case, entry).run() for code in words]
        assert state(models[0]) == state(models[1])
        machine = models[0]
        assert (
            old.public(machine.memory, old.Case(phase=case.phase)),
            machine.calls,
            machine.payloads,
            machine.rng_i,
            machine.rng_f,
        ) == (
            old.public(expected, old.Case(phase=case.phase)),
            calls,
            payloads,
            integers,
            reals,
        )
        seen.update(value for model in models for value in model.visits)
        modes.add(case.mode & 255)
        extras.add(u32(case.extra))
        total += 1
    prefixes = 0
    for case in (Case(), Case(seed=3, mode=255, extra=0xFFFFFFFF, mutation=3, phase=8)):
        initial = fixture(case)
        full = Machine(words[0], initial, case, entry).run()
        for cut in range(full.all_accesses):
            models = []
            for code in words:
                machine = Machine(code, initial, case, entry)
                machine.cut = cut
                try:
                    machine.run()
                except old.faults.AccessBoundary:
                    pass
                else:
                    raise AssertionError("Access prefix did not fire")
                models.append(machine)
            assert state(models[0]) == state(models[1])
            prefixes += 1
    rom = (root / "conker/conker.us.bin").read_bytes()
    retail = struct.unpack_from(">270I", rom, 0x17FFE8)
    traps = {ENTRY + 4 * index for index, word in enumerate(retail) if word & 0xFC00003F == 13}
    assert len(traps) == 14
    assert set(range(ENTRY, ENTRY + 1080, 4)) - traps <= seen
    assert not (traps & seen)
    assert modes == set(range(256)) and len(extras) == 256
    report = dict(
        success=True,
        cases=total,
        executions=total * 2,
        semantic_layouts=1,
        independent_GNU_links=len(layouts),
        root_words=270,
        covered_nontrap_words=256,
        unreachable_divisor_traps=14,
        all256_mode_bytes=True,
        full_32bit_extra_values=True,
        live_input_after_first_RNG_and_after_submit=True,
        input_bytes=116,
        packet_visible_bytes=58,
        packet_private_extent=60,
        header_visible_bytes=22,
        header_private_extent=24,
        complete_scratch_bytes=88,
        private_tail_bytes_untouched=6,
        access_prefix_pairs=prefixes,
        original_and_C_full_state_calls_payloads_and_traces_equal=True,
        independent_reference=True,
    )
    (output / "private-guest-v6.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    root = Path.cwd()
    output = Path(__file__).parent
    print(qualify(root, output), flush=True)
