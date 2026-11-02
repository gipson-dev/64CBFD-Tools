from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import json
import struct

from tools.tests import game_point_effect_payload_oracle as old
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset


ENTRY = 0x15152F70
INPUT = 0x22000
STACK = old.STACK
MARK = old.MARK
WORDS = 202
SIZE = WORDS * 4


@dataclass(frozen=True)
class Case:
    seed: int = 0
    mode: int = 0
    mutation: int = 0
    phase: int = 0


def u32(value):
    return value & 0xFFFFFFFF


def signed(value, bits):
    sign = 1 << (bits - 1)
    return ((value & ((1 << bits) - 1)) ^ sign) - sign


def put(memory, address, value, size=4):
    old.put(memory, address, value, size)


def get(memory, address, size=4):
    return old.read(memory, address, size)


def data(memory, address, size):
    return bytes(memory[address + index] for index in range(size))


def set_fields(memory, case, late=False):
    seed = case.seed
    values = {
        0x00: (old.bits(-8.0 if late else 1.25 + seed), 4),
        0x04: (old.bits(9.0 if late else -2.5 - seed), 4),
        0x08: (old.bits(-10.0 if late else 3.75 + seed * 0.5), 4),
        0x0C: (old.bits(4.0 if late else -1.5), 4),
        0x10: (old.bits(2.0 if late else 3.0), 4),
        0x14: (old.bits(-3.0 if late else 2.25), 4),
        0x18: (old.bits(5.0 if late else 1.5), 4),
        0x1C: (old.bits(7.0 if late else 0.75), 4),
        0x20: (old.bits(6.0 if late else 2.5), 4),
        0x24: (1 if late else (0 if seed % 4 == 0 else 1), 2),
        0x26: (2, 2),
        0x28: (-120 if late else -30, 2),
        0x2A: (25 if late else 60, 2),
        0x2C: (70 if late else 15, 2),
        0x2E: (31 if late else 45, 2),
        0x30: (17 if late else 7, 2),
        0x32: (10 if late else 15, 2),
        0x34: (-200 if late else -20, 2),
        0x36: (50 if late else 100, 2),
        0x38: (0xA8 if late else 0x18, 1),
        0x39: (0xB9 if late else 0x29, 1),
        0x3C: (0x12345678 if late else 0x89ABCDEF, 4),
        0x40: (0x23456789 if late else 0x76543210, 4),
        0x44: (0x3456789A if late else 0x6543210F, 4),
        0x48: (0x456789AB if late else 0x543210FE, 4),
        0x4C: (0x56789ABC if late else 0x43210FED, 4),
        0x50: (0x6789ABCD if late else 0x3210FEDC, 4),
        0x54: (0xC4 if late else 0x34, 1),
        0x55: (0xD5 if late else 0x45, 1),
    }
    for offset, (value, size) in values.items():
        put(memory, INPUT + offset, value, size)


def fixture(case):
    home = STACK + case.phase
    memory = {home + index: 0xCD for index in range(-4096, 1024)}
    for index in range(88):
        memory[INPUT + index] = (index * 29 + case.seed * 11 + 101) & 255
    for index in range(1024):
        memory[MARK + index] = (index * 7 + 0x5A) & 255
    set_fields(memory, case)
    return memory


def mutate_input(memory, case, late=False):
    mask = 2 if late else 1
    if case.mutation & mask:
        set_fields(memory, case, True)


def trig_value(index, angle, case):
    table = (
        old.bits(0.0),
        old.bits(0.25),
        old.bits(-0.5),
        old.bits(0.75),
        old.bits(-1.0),
        old.bits(1.5),
    )
    return table[(index + angle + case.seed) % len(table)]


def private_tails_are_untouched(descriptor, motion, header):
    return (
        all(descriptor[index] == 0xCD for index in range(30, 36))
        and all(motion[index] == 0xCD for index in (*range(20, 24), *range(28, 32)))
        and header[20] == 0xCD
        and header[22] == 0xCD
        and header[23] == 0xCD
    )


def reference(initial, case, symbols):
    memory = dict(initial)
    home = STACK + case.phase
    descriptor = home - 96
    motion = home - 60
    header = home - 28
    calls = []
    payloads = []
    integer_index = 0
    float_index = 0
    trig_index = 0
    submits = 0

    def integer():
        nonlocal integer_index
        calls.append((symbols["func_150ADA20"], ()))
        value = old.ri(integer_index, old.Case(seed=case.seed))
        integer_index += 1
        if integer_index == 1:
            mutate_input(memory, case, False)
        return value

    def real():
        nonlocal float_index
        calls.append((symbols["func_150ADA68"], ()))
        value = old.rf(float_index, old.Case(seed=case.seed))
        float_index += 1
        return value

    def trig(angle):
        nonlocal trig_index
        angle &= 255
        calls.append((symbols["func_151423D8"], (angle,)))
        value = trig_value(trig_index, angle, case)
        trig_index += 1
        return value

    put(memory, header + 0x10, 1)
    put(memory, header + 0x0E, 1, 2)
    put(memory, motion + 0x19, get(memory, INPUT + 0x38, 1), 1)
    put(memory, motion + 0x1A, get(memory, INPUT + 0x54, 1), 1)
    put(memory, motion + 0x18, get(memory, INPUT + 0x39, 1), 1)
    put(memory, motion + 0x1B, get(memory, INPUT + 0x55, 1), 1)
    for offset in range(0, 12, 4):
        put(memory, header + offset, get(memory, INPUT + offset))
    for offset, value, size in (
        (0x00, 0, 4),
        (0x04, 1, 4),
        (0x08, 0x160600, 4),
        (0x0C, 3, 4),
        (0x10, 0x10, 4),
        (0x14, 0x80, 4),
        (0x18, 0x20, 4),
        (0x1C, 0, 1),
        (0x1D, 9, 1),
    ):
        put(memory, descriptor + offset, value, size)

    remaining = integer() % (signed(get(memory, INPUT + 0x26, 2), 16) + 1) + signed(
        get(memory, INPUT + 0x24, 2), 16
    )
    while remaining != 0:
        first_angle = signed(
            integer() % (signed(get(memory, INPUT + 0x2A, 2), 16) + 1)
            + signed(get(memory, INPUT + 0x28, 2), 16),
            16,
        )
        second_angle = signed(
            integer() % (signed(get(memory, INPUT + 0x2E, 2), 16) + 1)
            + signed(get(memory, INPUT + 0x2C, 2), 16),
            16,
        )
        second_primary = trig(second_angle)
        second_quarter = trig(second_angle - 0x40)
        first_primary = trig(first_angle)
        first_quarter = trig(first_angle - 0x40)
        speed = old.fa(old.fm(real(), get(memory, INPUT + 0x20)), get(memory, INPUT + 0x1C))
        byte_value = integer() % (signed(get(memory, INPUT + 0x32, 2), 16) + 1)
        byte_value += signed(get(memory, INPUT + 0x30, 2), 16)
        put(memory, header + 0x15, byte_value, 1)
        short_value = integer() % (signed(get(memory, INPUT + 0x36, 2), 16) + 1)
        short_value += signed(get(memory, INPUT + 0x34, 2), 16)
        put(memory, header + 0x0C, short_value, 2)
        put(
            memory,
            motion,
            old.fa(old.fm(real(), get(memory, INPUT + 0x10)), get(memory, INPUT + 0x0C)),
        )
        product = old.fm(speed, second_primary)
        put(
            memory,
            motion + 0x10,
            old.fa(old.fm(real(), get(memory, INPUT + 0x18)), get(memory, INPUT + 0x14)),
        )
        put(memory, motion + 0x04, old.fm(product, first_quarter))
        put(memory, motion + 0x08, old.fm(speed ^ 0x80000000, second_quarter))
        put(memory, motion + 0x0C, old.fm(product, first_primary))
        args = (
            header,
            motion,
            0,
            get(memory, INPUT + 0x3C),
            get(memory, INPUT + 0x40),
            get(memory, INPUT + 0x44),
            get(memory, INPUT + 0x48),
            get(memory, INPUT + 0x4C),
            get(memory, INPUT + 0x50),
            0,
            0,
            descriptor,
            0,
            case.mode & 255,
            1,
        )
        calls.append((symbols["func_15147DA0"], tuple(map(u32, args))))
        snapshot = (
            data(memory, descriptor, 36),
            data(memory, motion, 32),
            data(memory, header, 24),
            tuple(map(u32, args)),
        )
        assert private_tails_are_untouched(*snapshot[:3])
        payloads.append(snapshot)
        put(memory, MARK + 4 * submits, submits + 1)
        submits += 1
        mutate_input(memory, case, True)
        remaining -= 1
    return memory, calls, payloads, integer_index, float_index, trig_index, submits


class Machine(FactoryOracle):
    def __init__(self, words, memory, case, entry, symbols, raw=False):
        self.case = case
        self.home = STACK + case.phase
        self.target = entry
        self.providers = symbols
        self.raw = raw
        self.rng_i = 0
        self.rng_f = 0
        self.trig_i = 0
        self.submits = 0
        self.payloads = []
        super().__init__(
            words,
            memory,
            case,
            entry=entry,
            s={},
            connected=None,
            arguments=(INPUT, case.mode),
        )

    @property
    def descriptor(self):
        return self.home - (92 if self.raw else 96)

    @property
    def motion(self):
        return self.home - (56 if self.raw else 60)

    @property
    def header(self):
        return self.home - (24 if self.raw else 28)

    def canonical_address(self, address):
        if self.raw and self.descriptor <= address < self.home:
            return address - 4
        return address

    def execute(self, word):
        operation = word >> 26
        fmt = word >> 21 & 31
        function = word & 63
        if operation == 17 and fmt == 16 and function == 7:
            source = word >> 11 & 31
            destination = word >> 6 & 31
            self.f[destination] = self.f[source] ^ 0x80000000
            return
        super().execute(word)

    def record_call(self, target):
        counts = {
            self.target: 2,
            self.providers["func_150ADA20"]: 0,
            self.providers["func_150ADA68"]: 0,
            self.providers["func_151423D8"]: 1,
            self.providers["func_15147DA0"]: 15,
        }
        assert target in counts, hex(target)
        arguments = tuple(u32(value) for value in self.arguments(counts[target]))
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))
        if target == self.providers["func_15147DA0"]:
            canonical = list(arguments)
            for index in (0, 1, 11):
                canonical[index] = self.canonical_address(canonical[index])
            snapshot = (
                data(self.memory, self.descriptor, 36),
                data(self.memory, self.motion, 32),
                data(self.memory, self.header, 24),
                tuple(canonical),
            )
            assert private_tails_are_untouched(*snapshot[:3])
            self.payloads.append(snapshot)

    def hook(self, target):
        value = 0x76543210
        float_value = None
        if target == self.providers["func_150ADA20"]:
            value = old.ri(self.rng_i, old.Case(seed=self.case.seed))
            self.rng_i += 1
            if self.rng_i == 1:
                mutate_input(self.memory, self.case, False)
        elif target == self.providers["func_150ADA68"]:
            float_value = old.rf(self.rng_f, old.Case(seed=self.case.seed))
            self.rng_f += 1
        elif target == self.providers["func_151423D8"]:
            angle = self.calls[-1][1][0] & 255
            float_value = trig_value(self.trig_i, angle, self.case)
            self.trig_i += 1
        else:
            assert target == self.providers["func_15147DA0"]
            put(self.memory, MARK + 4 * self.submits, self.submits + 1)
            self.submits += 1
            mutate_input(self.memory, self.case, True)
        for index in range(4):
            self.put(self.r[29] + 4 * index, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011
        self.r[2] = u32(value)
        if float_value is not None:
            self.f[0] = float_value


def programs(output, layout):
    receipt = json.loads((output / "private-layout-v6.json").read_text())
    row = receipt["layouts"][layout]
    entry = row["entry"]
    result = []
    for label in ("original", "C", "raw"):
        image = (output / ("layout-{}-{}.elf".format(layout, label))).read_bytes()
        at = elf_slot_offset(image, entry, SIZE)
        result.append(struct.unpack_from(">202I", image, at))
    assert result[0] == result[1]
    assert sum(left != right for left, right in zip(result[0], result[2])) == 37
    return entry, row["symbols"], result


def public(memory, case):
    home = STACK + case.phase
    return {
        address: value
        for address, value in memory.items()
        if not home - 4096 <= address < home + 1024
    }


def canonical_calls(machine):
    result = []
    for target, arguments in machine.calls:
        values = list(arguments)
        if target == machine.providers["func_15147DA0"]:
            for index in (0, 1, 11):
                values[index] = machine.canonical_address(values[index])
        result.append((target, tuple(values)))
    return result


def role_trace(machine):
    result = []
    roles = (
        ("descriptor", machine.descriptor, 36),
        ("motion", machine.motion, 32),
        ("header", machine.header, 24),
    )
    for event in machine.trace:
        operation, address, size, value = event
        if INPUT <= address and address + size <= INPUT + 88:
            result.append((operation, "input", address - INPUT, size, value))
            continue
        for name, base, extent in roles:
            if base <= address and address + size <= base + extent:
                result.append((operation, name, address - base, size, value))
                break
    return result


def semantic_memory(machine):
    return (
        public(machine.memory, machine.case),
        data(machine.memory, machine.descriptor, 36),
        data(machine.memory, machine.motion, 32),
        data(machine.memory, machine.header, 24),
    )


def full_state(machine):
    return (
        machine.memory,
        machine.r,
        machine.f,
        machine.trace,
        machine.calls,
        machine.payloads,
        machine.events,
        machine.hi,
        machine.lo,
        machine.current_pc,
        machine.delay_of,
        machine.all_accesses,
        machine.rng_i,
        machine.rng_f,
        machine.trig_i,
        machine.submits,
    )


def raw_semantic_state(machine):
    return (
        semantic_memory(machine),
        machine.r,
        machine.f,
        canonical_calls(machine),
        machine.payloads,
        machine.hi,
        machine.lo,
        machine.current_pc,
        machine.delay_of,
        machine.rng_i,
        machine.rng_f,
        machine.trig_i,
        machine.submits,
    )


def qualify(root, output):
    cases = [
        Case(seed=index % 8, mode=index, mutation=index % 4, phase=(index % 2) * 8)
        for index in range(256)
    ]
    executions = 0
    seen = set()
    modes = set()
    particle_counts = set()
    role_trace_events = 0
    for layout in range(3):
        entry, symbols, words = programs(output, layout)
        shift = entry - ENTRY
        for case in cases:
            initial = fixture(case)
            expected = reference(initial, case, symbols)
            models = [
                Machine(code, initial, case, entry, symbols, raw=(index == 2)).run()
                for index, code in enumerate(words)
            ]
            assert full_state(models[0]) == full_state(models[1]), (layout, case)
            assert raw_semantic_state(models[0]) == raw_semantic_state(models[2]), (layout, case)
            retail_trace = role_trace(models[0])
            raw_trace = role_trace(models[2])
            assert retail_trace == raw_trace, (layout, case, retail_trace, raw_trace)
            assert Counter(retail_trace) == Counter(raw_trace)
            role_trace_events += len(retail_trace)
            memory, calls, payloads, integers, reals, trig, submits = expected
            assert (
                public(models[0].memory, case),
                canonical_calls(models[0]),
                models[0].payloads,
                models[0].rng_i,
                models[0].rng_f,
                models[0].trig_i,
                models[0].submits,
            ) == (
                public(memory, case),
                calls,
                payloads,
                integers,
                reals,
                trig,
                submits,
            ), (layout, case)
            for model in models:
                seen.update(pc - shift for pc in model.visits)
            modes.add(case.mode & 255)
            particle_counts.add(submits)
            executions += len(models)

    prefixes = 0
    entry, symbols, words = programs(output, 0)
    for case in (Case(), Case(seed=7, mode=255, mutation=3, phase=8)):
        initial = fixture(case)
        full = Machine(words[0], initial, case, entry, symbols).run()
        for cut in range(full.all_accesses):
            models = []
            for code in words[:2]:
                machine = Machine(code, initial, case, entry, symbols)
                machine.cut = cut
                try:
                    machine.run()
                except old.faults.AccessBoundary:
                    pass
                else:
                    raise AssertionError("Access prefix did not fire")
                models.append(machine)
            assert full_state(models[0]) == full_state(models[1])
            prefixes += 1

    rom = (root / "conker/conker.us.bin").read_bytes()
    retail = struct.unpack_from(">202I", rom, 0x180420)
    traps = {ENTRY + 4 * index for index, word in enumerate(retail) if word & 0xFC00003F == 13}
    assert len(traps) == 5
    assert set(range(ENTRY, ENTRY + SIZE, 4)) - traps <= seen
    assert not (traps & seen)
    assert modes == set(range(256))
    assert particle_counts == {0, 1, 2}

    report = {
        "success": True,
        "private_only": True,
        "matching_credit": 0,
        "cases_per_layout": len(cases),
        "independent_GNU_links": 3,
        "executions": executions,
        "root_words": WORDS,
        "covered_nontrap_words": WORDS - len(traps),
        "unreachable_unsigned_divisor_traps": len(traps),
        "all256_mode_bytes": True,
        "particle_counts": sorted(particle_counts),
        "live_input_after_first_RNG_and_after_submit": True,
        "input_bytes": 88,
        "descriptor_visible_bytes": 30,
        "descriptor_private_extent": 36,
        "motion_visible_bytes": 28,
        "motion_private_extent": 32,
        "header_visible_bytes": 22,
        "header_private_extent": 24,
        "complete_private_scratch_bytes": 92,
        "all_private_tail_bytes_untouched": True,
        "original_and_normalized_full_state_trace_equal": True,
        "raw_C_full_register_and_FP_state_equal": True,
        "raw_C_public_memory_calls_complete_payloads_and_role_traces_equal": True,
        "role_trace_events_compared": role_trace_events,
        "normalized_access_prefix_pairs": prefixes,
        "independent_reference": True,
    }
    (output / "private-guest-v8.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(qualify(Path.cwd(), Path(__file__).parent), flush=True)
