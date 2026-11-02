"""Guest semantic oracle for the randomized directional-effect factory."""
from dataclasses import dataclass
from pathlib import Path
import json
import struct

from tools.tests import game_localized_trail_factory_oracle as base
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset


ENTRY = 0x15154684
ROM = 0x181B34
WORDS = 128
SIZE = WORDS * 4
INPUT = 0x22000
STACK = base.STACK
MARK = base.MARK


@dataclass(frozen=True)
class Case:
    seed: int = 0
    mutation: int = 0
    phase: int = 0
    channel: int = 0

    @property
    def arg1(self):
        return u32(self.channel * 0x01010101)

    @property
    def arg2(self):
        return u32(0xD4000000 | self.seed * 0x101)


def u32(value):
    return value & 0xFFFFFFFF


def signed(value, bits):
    sign = 1 << (bits - 1)
    return ((value & ((1 << bits) - 1)) ^ sign) - sign


def put(memory, address, value, size=4):
    base.put(memory, address, value, size)


def get(memory, address, size=4):
    return base.get(memory, address, size)


def data(memory, address, size):
    return bytes(memory[address + index] for index in range(size))


def rng_value(index, case):
    values = (0, 1, 2, 5, 17, 255, 0xFFFFFFFF, 3)
    return values[(index + case.seed) % len(values)]


def float_value(index, case):
    values = (0.0, 0.25, 0.5, 0.75, -0.5, 1.25, -1.5, 2.0)
    return base.old.bits(values[(index + case.seed) % len(values)])


def set_fields(memory, case, late=False):
    fields = {
        0x00: (1 if late else 0, 2),
        0x02: (1 if late else 2, 2),
        0x04: (0x44004000 if late else 0x44000000, 4),
        0x08: (0xC1 if late else 0x81, 1),
        0x09: (0xC2 if late else 0x82, 1),
        0x0A: (-37 if late else 11, 2),
        0x0C: (-1234 if late else 2345, 2),
        0x0E: (3 if late else 9, 2),
        0x10: (base.old.bits(4.0 if late else 0.5), 4),
        0x14: (base.old.bits(1.5 if late else 0.25), 4),
        0x18: (base.old.bits(5.0 if late else -1.25), 4),
        0x1C: (base.old.bits(-0.5 if late else 2.0), 4),
        0x20: (0x33003000 if late else 0x33000000, 4),
        0x24: (0x91 if late else 0x44, 1),
        0x25: (1 if late else 3, 1),
        0x26: (-70 if late else 20, 2),
        0x28: (2 if late else 4, 2),
        0x2A: (0xD1 if late else 0xA1, 1),
        0x2B: (0xD2 if late else 0xA2, 1),
        0x2C: (base.old.bits(-2.0 if late else 1.5), 4),
        0x30: (base.old.bits(1.25 if late else 0.75), 4),
        0x34: (base.old.bits(0.6 if late else 0.4), 4),
        0x38: (0x87654321 if late else 0x12345678, 4),
    }
    for offset, (value, size) in fields.items():
        put(memory, INPUT + offset, value, size)


def fixture(case, symbols):
    del symbols
    home = STACK + case.phase
    memory = {home + index: (index * 17 + 0xCD) & 255 for index in range(-4096, 1024)}
    for base_address, size in ((INPUT, 60), (MARK, 1024)):
        for index in range(size):
            memory[base_address + index] = (index * 29 + case.seed * 11 + 0x65) & 255
    set_fields(memory, case)
    return memory


def mutate(memory, case, mask):
    if case.mutation & mask:
        set_fields(memory, case, True)


def write_direction(memory, first, second, radius, pointer):
    put(memory, pointer + 0, u32(first))
    put(memory, pointer + 4, u32(second))
    put(memory, pointer + 8, radius)


def reference(initial, case, symbols):
    memory = dict(initial)
    home = STACK + case.phase
    scratch = home - 16
    calls, payloads = [], []
    integer_index = real_index = submits = 0

    def integer():
        nonlocal integer_index
        calls.append((symbols["func_150ADA20"], ()))
        value = rng_value(integer_index, case)
        integer_index += 1
        if integer_index == 1:
            mutate(memory, case, 1)
        return value

    def real():
        nonlocal real_index
        calls.append((symbols["func_150ADA68"], ()))
        value = float_value(real_index, case)
        real_index += 1
        return value

    remaining = integer() % u32(signed(get(memory, INPUT + 2, 2), 16) + 1)
    remaining = u32(remaining + signed(get(memory, INPUT, 2), 16))
    while signed(remaining, 32) > 0:
        first_random, second_random, radius_random = integer(), integer(), real()
        first = signed(first_random & 0xFF, 16)
        second = signed(second_random % u32(signed(get(memory, INPUT + 0x0E, 2), 16) + 1)
                        + signed(get(memory, INPUT + 0x0A, 2), 16), 16)
        radius = base.old.fa(base.old.fm(radius_random, get(memory, INPUT + 0x14)),
                             get(memory, INPUT + 0x10))
        calls.append((symbols["func_15143794"], (u32(first), u32(second), radius, scratch)))
        write_direction(memory, first, second, radius, scratch)
        mutate(memory, case, 2)
        scale_random = real()
        selector_random, duration_random = integer(), integer()
        time_random, chance_random = real(), real()
        selector = u32(selector_random % (get(memory, INPUT + 0x25, 1) + 1)
                       + get(memory, INPUT + 0x24, 1))
        duration = u32(duration_random % u32(signed(get(memory, INPUT + 0x28, 2), 16) + 1)
                       + signed(get(memory, INPUT + 0x26, 2), 16))
        scale = base.old.fa(base.old.fm(scale_random, get(memory, INPUT + 0x1C)),
                            get(memory, INPUT + 0x18))
        time = base.old.fa(base.old.fm(time_random, get(memory, INPUT + 0x30)),
                           get(memory, INPUT + 0x2C))
        opaque = int(base.old.floating(chance_random) <
                     base.old.floating(get(memory, INPUT + 0x34)))
        arguments = tuple(map(u32, (
            get(memory, INPUT + 0x04), scratch, scale, get(memory, INPUT + 0x20),
            selector, duration, time, opaque, get(memory, INPUT + 0x38),
            case.channel, case.arg2,
        )))
        calls.append((symbols["func_151C5F44"], arguments))
        payloads.append((data(memory, INPUT, 60), data(memory, scratch, 12), arguments))
        put(memory, MARK + 4 * submits, submits + 1)
        submits += 1
        mutate(memory, case, 4)
        remaining = u32(remaining - 1)
    return memory, calls, payloads, integer_index, real_index, submits


class Machine(FactoryOracle):
    def __init__(self, words, memory, case, entry, symbols):
        self.case, self.home, self.target, self.providers = case, STACK + case.phase, entry, symbols
        self.rng_i = self.rng_f = self.submits = 0
        self.payloads = []
        super().__init__(words, memory, case, entry=entry, s={}, connected=None,
                         arguments=(INPUT, case.arg1, case.arg2))

    def record_call(self, target):
        counts = {self.target: 3, self.providers["func_150ADA20"]: 0,
                  self.providers["func_150ADA68"]: 0, self.providers["func_15143794"]: 4,
                  self.providers["func_151C5F44"]: 11}
        assert target in counts, hex(target)
        arguments = tuple(u32(value) for value in self.arguments(counts[target]))
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))
        if target == self.providers["func_151C5F44"]:
            pointer = arguments[1]
            self.payloads.append((data(self.memory, INPUT, 60), data(self.memory, pointer, 12), arguments))

    def hook(self, target):
        value, float_result = 0x76543210, None
        if target == self.providers["func_150ADA20"]:
            value = rng_value(self.rng_i, self.case)
            self.rng_i += 1
            if self.rng_i == 1:
                mutate(self.memory, self.case, 1)
        elif target == self.providers["func_150ADA68"]:
            float_result = float_value(self.rng_f, self.case)
            self.rng_f += 1
        elif target == self.providers["func_15143794"]:
            first, second, radius, pointer = self.calls[-1][1]
            write_direction(self.memory, signed(first, 16), signed(second, 16), radius, pointer)
            mutate(self.memory, self.case, 2)
        else:
            assert target == self.providers["func_151C5F44"]
            put(self.memory, MARK + 4 * self.submits, self.submits + 1)
            self.submits += 1
            mutate(self.memory, self.case, 4)
        for index in range(4):
            self.put(self.r[29] + 4 * index, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011
        self.r[2] = u32(value)
        if float_result is not None:
            self.f[0] = float_result


def programs(output, layout):
    receipt = json.loads((output / "private-layout-v1.json").read_text())
    row, result = receipt["layouts"][layout], []
    entry = row["entry"]
    for label in ("original", "C", "raw"):
        image = (output / ("layout-{}-{}.elf".format(layout, label))).read_bytes()
        at = elf_slot_offset(image, entry, SIZE)
        result.append(struct.unpack_from(">128I", image, at))
    assert result[0] == result[1]
    assert sum(left != right for left, right in zip(result[0], result[2])) == 31
    return entry, row["symbols"], result


def public(memory, case):
    home = STACK + case.phase
    return {address: value for address, value in memory.items() if not home - 4096 <= address < home + 1024}


def normalize_calls(machine):
    result = []
    for target, arguments in machine.calls:
        values = list(arguments)
        if target == machine.providers["func_15143794"]:
            values[3] = 0x53524348
        elif target == machine.providers["func_151C5F44"]:
            values[1] = 0x53524348
        result.append((target, tuple(values)))
    return result


def normalize_expected(calls, symbols):
    result = []
    for target, arguments in calls:
        values = list(arguments)
        if target == symbols["func_15143794"]:
            values[3] = 0x53524348
        elif target == symbols["func_151C5F44"]:
            values[1] = 0x53524348
        result.append((target, tuple(values)))
    return result


def normalize_payloads(payloads):
    result = []
    for descriptor, scratch, arguments in payloads:
        values = list(arguments)
        values[1] = 0x53524348
        result.append((descriptor, scratch, tuple(values)))
    return result


def full_state(machine):
    return (machine.memory, machine.r, machine.f, machine.trace, machine.calls, machine.payloads,
            machine.events, machine.hi, machine.lo, machine.current_pc, machine.delay_of,
            machine.all_accesses, machine.rng_i, machine.rng_f, machine.submits)


def semantic_state(machine):
    return (public(machine.memory, machine.case),
            [machine.r[index] for index in (*range(16, 24), 28, 29, 30, 31)], machine.f[20:],
            normalize_calls(machine), normalize_payloads(machine.payloads), machine.hi, machine.lo,
            machine.current_pc, machine.delay_of, machine.rng_i, machine.rng_f, machine.submits)


def qualify(root, output):
    cases = [Case(seed=index % 8, mutation=(index // 8) % 8,
                  phase=(index % 2) * 8, channel=index) for index in range(256)]
    executions, payload_count = 0, 0
    seen, channels, request_counts = set(), set(), set()
    for layout in range(3):
        entry, symbols, words = programs(output, layout)
        shift = entry - ENTRY
        for case in cases:
            initial = fixture(case, symbols)
            expected = reference(initial, case, symbols)
            models = [Machine(code, initial, case, entry, symbols).run() for code in words]
            assert full_state(models[0]) == full_state(models[1]), (layout, case)
            assert semantic_state(models[0]) == semantic_state(models[2]), (layout, case)
            memory, calls, payloads, integers, reals, submits = expected
            assert public(models[0].memory, case) == public(memory, case), (layout, case)
            assert normalize_calls(models[0]) == normalize_expected(calls, symbols), (layout, case)
            assert normalize_payloads(models[0].payloads) == normalize_payloads(payloads), (layout, case)
            assert (models[0].rng_i, models[0].rng_f, models[0].submits) == (integers, reals, submits)
            # The raw C layout is intentionally not address-exact until the
            # guarded normalizations are applied; count retail-PC coverage
            # only from the original and normalized exact programs.
            for model in models[:2]:
                seen.update(pc - shift for pc in model.visits if entry <= pc < entry + SIZE)
            channels.add(case.channel)
            request_counts.add(submits)
            payload_count += submits
            executions += len(models)
    retail = struct.unpack_from(">128I", (root / "conker/conker.us.bin").read_bytes(), ROM)
    traps = {ENTRY + 4 * index for index, word in enumerate(retail) if word & 0xFC00003F == 13}
    assert len(traps) == 4
    missing = (set(range(ENTRY, ENTRY + SIZE, 4)) - traps) - seen
    assert not missing and not traps & seen, ([hex(value) for value in sorted(missing)],
                                               [hex(value) for value in sorted(traps & seen)])
    assert channels == set(range(256)) and request_counts == {0, 1, 2}
    report = {
        "success": True, "private_only": True, "matching_credit": 0,
        "cases_per_layout": len(cases), "independent_GNU_links": 3,
        "executions": executions, "root_words": WORDS,
        "covered_nontrap_words": WORDS - len(traps), "unreachable_unsigned_divisor_traps": len(traps),
        "all256_target_channel_bytes": True, "request_counts": sorted(request_counts),
        "provider_payloads_compared": payload_count, "input_natural_bytes": 60,
        "input_required_bytes": 54,
        "private_padding_bytes": ["0x08", "0x09", "0x0C", "0x0D", "0x2A", "0x2B"],
        "scratch_visible_bytes": 12,
        "all11_provider_arguments_and_complete_input_scratch_snapshots": True,
        "live_input_after_count_RNG_direction_and_provider": True,
        "original_and_normalized_full_state_trace_equal": True,
        "raw_C_callee_preserved_register_and_FP_state_equal": True,
        "raw_C_public_memory_calls_complete_payloads_equal": True,
        "independent_reference": True,
    }
    (output / "private-guest-v1.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(qualify(
        Path.cwd(), Path.cwd() / "conker/build/game-direction-effect-factory-15154684-match"
    ), indent=2))
