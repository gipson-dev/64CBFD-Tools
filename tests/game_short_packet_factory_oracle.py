from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import json
import struct

from tools.tests import game_point_effect_payload_oracle as old
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset


ENTRY = 0x15153298
INPUT = 0x22000
STACK = old.STACK
MARK = old.MARK
WORDS = 231
SIZE = WORDS * 4
OWNER = 0x13579BDF
PRIVATE = (*range(4, 12), 26, 27, 43, 51, 54, 55)


@dataclass(frozen=True)
class Case:
    seed: int = 0
    mode: int = 0
    mutation: int = 0
    phase: int = 0
    owner: int = OWNER


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


def rng_value(index, case):
    values = (0, 1, 2, 5, 17, 255, 0xFFFFFFFF, 3)
    return values[(index + case.seed) % len(values)]


def float_value(index, case):
    values = (0.0, 0.25, 0.5, 0.75, -0.5, 1.25, -1.5, 2.0)
    return old.bits(values[(index + case.seed) % len(values)])


def trunc(value, bits):
    return signed(int(old.floating(value)), bits)


def set_fields(memory, case, late=False):
    seed = case.seed
    values = {
        0x00: (old.bits(-8.0 if late else 1.25 + seed), 4),
        0x04: (old.bits(9.0 if late else -2.5 - seed), 4),
        0x08: (old.bits(-10.0 if late else 3.75 + seed * 0.5), 4),
        0x0C: (0, 2),
        0x0E: (2, 2),
        0x10: (-70 if late else -20, 2),
        0x12: (40 if late else 30, 2),
        0x14: (55 if late else 15, 2),
        0x16: (35 if late else 25, 2),
        0x18: (old.bits(-2.0 if late else 1.5), 4),
        0x1C: (old.bits(1.25 if late else 0.75), 4),
        0x20: (-30 if late else 5, 2),
        0x22: (20 if late else 10, 2),
        0x24: (80 if late else -10, 2),
        0x26: (30 if late else 20, 2),
        0x28: (-33 if late else -7, 1),
        0x29: (0x91 if late else 0x44, 1),
        0x2A: (30 if late else -5, 2),
        0x2C: (25 if late else 15, 2),
        0x2E: (-1234 if late else 0x1234, 2),
        0x30: (-200 if late else 100, 2),
        0x32: (50 if late else 20, 2),
        0x34: (200 if late else -100, 2),
        0x36: (45 if late else 25, 2),
        0x38: (0x89ABCDEF if late else 0x12345678, 4),
        0x3C: (0x19 if late else 0xAA, 1),
        0x3D: (0x27 if late else 0xBB, 1),
    }
    for offset, (value, size) in values.items():
        put(memory, INPUT + offset, value, size)


def fixture(case):
    home = STACK + case.phase
    memory = {home + index: 0xCD for index in range(-4096, 1024)}
    for index in range(62):
        memory[INPUT + index] = (index * 29 + case.seed * 11 + 101) & 255
    for index in range(1024):
        memory[MARK + index] = (index * 7 + 0x5A) & 255
    set_fields(memory, case)
    return memory


def mutate_input(memory, case, after_submit=False):
    mask = 2 if after_submit else 1
    if case.mutation & mask:
        set_fields(memory, case, True)


def trig_value(index, angle, case):
    table = (
        old.bits(0.0), old.bits(0.25), old.bits(-0.5),
        old.bits(0.75), old.bits(-1.0), old.bits(1.5),
    )
    return table[(index + angle + case.seed) % len(table)]


def private_bytes_untouched(packet):
    return all(packet[index] == 0xCD for index in PRIVATE)


def reference(initial, case, symbols):
    memory = dict(initial)
    home = STACK + case.phase
    packet = home - 56
    calls = []
    payloads = []
    integer_index = 0
    real_index = 0
    trig_index = 0
    submits = 0

    def integer():
        nonlocal integer_index
        calls.append((symbols["func_150ADA20"], ()))
        value = rng_value(integer_index, case)
        integer_index += 1
        if integer_index == 1:
            mutate_input(memory, case, False)
        return value

    def real():
        nonlocal real_index
        calls.append((symbols["func_150ADA68"], ()))
        value = float_value(real_index, case)
        real_index += 1
        return value

    def trig(angle):
        nonlocal trig_index
        angle &= 255
        calls.append((symbols["func_151423D8"], (angle,)))
        value = trig_value(trig_index, angle, case)
        trig_index += 1
        return value

    put(memory, packet + 0x10, trunc(get(memory, INPUT), 16), 2)
    put(memory, packet + 0x12, trunc(get(memory, INPUT + 4), 16), 2)
    put(memory, packet + 0x14, trunc(get(memory, INPUT + 8), 16), 2)
    scale = old.bits(256.0)
    put(memory, packet + 0x1C, trunc(old.fm(get(memory, INPUT), scale), 8), 1)
    put(memory, packet + 0x1D, trunc(old.fm(get(memory, INPUT + 4), scale), 8), 1)
    put(memory, packet + 0x1E, trunc(old.fm(get(memory, INPUT + 8), scale), 8), 1)
    put(memory, packet + 0x2C, get(memory, INPUT + 0x3C, 1), 1)
    put(memory, packet + 0x2D, get(memory, INPUT + 0x3C, 1), 1)
    put(memory, packet + 0x30, 0, 1)
    put(memory, packet + 0x31, 0, 1)
    put(memory, packet + 0x32, 0, 1)
    put(memory, packet + 0x2E, get(memory, INPUT + 0x3C, 1), 1)
    put(memory, packet + 0x2F, get(memory, INPUT + 0x3D, 1), 1)
    put(memory, packet + 0x1F, get(memory, INPUT + 0x28, 1), 1)
    put(memory, packet + 0x0C, 0, 2)
    put(memory, packet + 0x34, get(memory, INPUT + 0x29, 1), 2)
    put(memory, packet + 0x0E, get(memory, INPUT + 0x2E, 2), 2)
    put(memory, packet, get(memory, INPUT + 0x38))

    remaining = integer() % (signed(get(memory, INPUT + 0x0E, 2), 16) + 1)
    remaining += signed(get(memory, INPUT + 0x0C, 2), 16)
    while remaining != 0:
        first_angle = signed(
            integer() % (signed(get(memory, INPUT + 0x12, 2), 16) + 1)
            + signed(get(memory, INPUT + 0x10, 2), 16), 16,
        )
        second_angle = signed(
            integer() % (signed(get(memory, INPUT + 0x16, 2), 16) + 1)
            + signed(get(memory, INPUT + 0x14, 2), 16), 16,
        )
        second_primary = trig(second_angle)
        second_quarter = trig(second_angle - 0x40)
        first_primary = trig(first_angle)
        first_quarter = trig(first_angle - 0x40)
        speed = old.fa(old.fm(real(), get(memory, INPUT + 0x1C)), get(memory, INPUT + 0x18))
        product = old.fm(speed, second_primary)
        value = integer() % (signed(get(memory, INPUT + 0x22, 2), 16) + 1)
        put(memory, packet + 0x28, value + signed(get(memory, INPUT + 0x20, 2), 16), 2)
        put(memory, packet + 0x16, trunc(old.fm(product, first_quarter), 16), 2)
        put(memory, packet + 0x20, trunc(old.fm(speed ^ 0x80000000, second_quarter), 16), 2)
        put(memory, packet + 0x18, trunc(old.fm(product, first_primary), 16), 2)
        value = integer() % (signed(get(memory, INPUT + 0x26, 2), 16) + 1)
        put(memory, packet + 0x22, value + signed(get(memory, INPUT + 0x24, 2), 16), 2)
        value = integer() % (signed(get(memory, INPUT + 0x2C, 2), 16) + 1)
        put(memory, packet + 0x2A, value + signed(get(memory, INPUT + 0x2A, 2), 16), 1)
        value = integer() % (signed(get(memory, INPUT + 0x32, 2), 16) + 1)
        put(memory, packet + 0x24, value + signed(get(memory, INPUT + 0x30, 2), 16), 2)
        value = integer() % (signed(get(memory, INPUT + 0x36, 2), 16) + 1)
        put(memory, packet + 0x26, value + signed(get(memory, INPUT + 0x34, 2), 16), 2)
        arguments = (packet, 0, 0, 0xFFFFFFFF, case.mode & 255, case.owner)
        calls.append((symbols["func_15167D84"], tuple(map(u32, arguments))))
        snapshot = data(memory, packet, 56)
        assert private_bytes_untouched(snapshot)
        payloads.append((snapshot, tuple(map(u32, arguments))))
        put(memory, MARK + 4 * submits, submits + 1)
        submits += 1
        mutate_input(memory, case, True)
        remaining -= 1
    return memory, calls, payloads, integer_index, real_index, trig_index, submits


class Machine(FactoryOracle):
    def __init__(self, words, memory, case, entry, symbols):
        self.case = case
        self.home = STACK + case.phase
        self.target = entry
        self.providers = symbols
        self.rng_i = 0
        self.rng_f = 0
        self.trig_i = 0
        self.submits = 0
        self.payloads = []
        super().__init__(
            words, memory, case, entry=entry, s={}, connected=None,
            arguments=(INPUT, case.mode, case.owner),
        )

    @property
    def packet(self):
        return self.home - 56

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
            self.target: 3,
            self.providers["func_150ADA20"]: 0,
            self.providers["func_150ADA68"]: 0,
            self.providers["func_151423D8"]: 1,
            self.providers["func_15167D84"]: 6,
        }
        assert target in counts, hex(target)
        arguments = tuple(u32(value) for value in self.arguments(counts[target]))
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))
        if target == self.providers["func_15167D84"]:
            assert arguments == (self.packet, 0, 0, 0xFFFFFFFF, self.case.mode & 255, self.case.owner)
            snapshot = data(self.memory, self.packet, 56)
            assert private_bytes_untouched(snapshot)
            self.payloads.append((snapshot, arguments))

    def hook(self, target):
        value = 0x76543210
        float_result = None
        if target == self.providers["func_150ADA20"]:
            value = rng_value(self.rng_i, self.case)
            self.rng_i += 1
            if self.rng_i == 1:
                mutate_input(self.memory, self.case, False)
        elif target == self.providers["func_150ADA68"]:
            float_result = float_value(self.rng_f, self.case)
            self.rng_f += 1
        elif target == self.providers["func_151423D8"]:
            angle = self.calls[-1][1][0] & 255
            float_result = trig_value(self.trig_i, angle, self.case)
            self.trig_i += 1
        else:
            assert target == self.providers["func_15167D84"]
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
        if float_result is not None:
            self.f[0] = float_result


def programs(output, layout):
    receipt = json.loads((output / "private-layout-v3.json").read_text())
    row = receipt["layouts"][layout]
    entry = row["entry"]
    result = []
    for label in ("original", "C", "raw"):
        image = (output / ("layout-{}-{}.elf".format(layout, label))).read_bytes()
        at = elf_slot_offset(image, entry, SIZE)
        result.append(struct.unpack_from(">231I", image, at))
    assert result[0] == result[1]
    assert sum(left != right for left, right in zip(result[0], result[2])) == 103
    return entry, row["symbols"], result


def public(memory, case):
    home = STACK + case.phase
    return {address: value for address, value in memory.items() if not home - 4096 <= address < home + 1024}


def role_trace(machine):
    result = []
    for event in machine.trace:
        operation, address, size, value = event
        if INPUT <= address and address + size <= INPUT + 62:
            result.append((operation, "input", address - INPUT, size, value))
        elif machine.packet <= address and address + size <= machine.packet + 56:
            result.append((operation, "packet", address - machine.packet, size, value))
    return result


def full_state(machine):
    return (
        machine.memory, machine.r, machine.f, machine.trace, machine.calls,
        machine.payloads, machine.events, machine.hi, machine.lo,
        machine.current_pc, machine.delay_of, machine.all_accesses,
        machine.rng_i, machine.rng_f, machine.trig_i, machine.submits,
    )


def semantic_state(machine):
    return (
        public(machine.memory, machine.case), data(machine.memory, machine.packet, 56),
        [machine.r[index] for index in (*range(16, 24), 28, 29, 30, 31)],
        machine.f[20:], machine.calls, machine.payloads,
        machine.hi, machine.lo, machine.current_pc, machine.delay_of,
        machine.rng_i, machine.rng_f, machine.trig_i, machine.submits,
    )


def qualify(root, output):
    cases = [
        Case(seed=index % 8, mode=index, mutation=index % 4, phase=(index % 2) * 8,
             owner=u32(OWNER + index * 0x10203))
        for index in range(256)
    ]
    executions = 0
    seen = set()
    modes = set()
    packet_counts = set()
    role_trace_events = 0
    for layout in range(3):
        entry, symbols, words = programs(output, layout)
        shift = entry - ENTRY
        for case in cases:
            initial = fixture(case)
            expected = reference(initial, case, symbols)
            models = [Machine(code, initial, case, entry, symbols).run() for code in words]
            assert full_state(models[0]) == full_state(models[1]), (layout, case)
            assert semantic_state(models[0]) == semantic_state(models[2]), (layout, case)
            retail_trace = role_trace(models[0])
            raw_trace = role_trace(models[2])
            assert Counter(retail_trace) == Counter(raw_trace), (layout, case)
            role_trace_events += len(retail_trace)
            memory, calls, payloads, integers, reals, trig, submits = expected
            assert (
                public(models[0].memory, case), models[0].calls, models[0].payloads,
                models[0].rng_i, models[0].rng_f, models[0].trig_i, models[0].submits,
            ) == (
                public(memory, case), calls, payloads, integers, reals, trig, submits,
            ), (layout, case)
            for model in models:
                seen.update(pc - shift for pc in model.visits)
            modes.add(case.mode & 255)
            packet_counts.add(submits)
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
    retail = struct.unpack_from(">231I", rom, 0x180748)
    traps = {ENTRY + 4 * index for index, word in enumerate(retail) if word & 0xFC00003F == 13}
    assert len(traps) == 8
    assert set(range(ENTRY, ENTRY + SIZE, 4)) - traps <= seen
    assert not (traps & seen)
    assert modes == set(range(256))
    assert packet_counts == {0, 1, 2}

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
        "packet_counts": sorted(packet_counts),
        "live_input_after_first_RNG_and_after_submit": True,
        "input_bytes": 62,
        "packet_visible_bytes": 42,
        "packet_private_extent": 56,
        "all_private_bytes_untouched": True,
        "original_and_normalized_full_state_trace_equal": True,
        "raw_C_callee_preserved_register_and_FP_state_equal": True,
        "raw_C_public_memory_calls_complete_payloads_and_role_trace_multiset_equal": True,
        "role_trace_events_compared": role_trace_events,
        "normalized_access_prefix_pairs": prefixes,
        "independent_reference": True,
    }
    (output / "private-guest-v4.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(qualify(Path.cwd(), Path(__file__).parent), flush=True)

