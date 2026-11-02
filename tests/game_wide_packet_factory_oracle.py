from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import json
import struct

from tools.tests import game_point_effect_payload_oracle as old
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset


ENTRY = 0x151539B4
ROM = 0x180E64
INPUT = 0x22000
STACK = old.STACK
MARK = old.MARK
WORDS = 180
SIZE = WORDS * 4
PRIVATE = (0x29, 0x2E, 0x2F, 0x35, 0x3A, 0x3B)


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


def rng_value(index, case):
    values = (0, 1, 2, 5, 17, 255, 0xFFFFFFFF, 3)
    return values[(index + case.seed) % len(values)]


def float_value(index, case):
    values = (0.0, 0.25, 0.5, 0.75, -0.5, 1.25, -1.5, 2.0)
    return old.bits(values[(index + case.seed) % len(values)])


def set_fields(memory, case, late=False):
    seed = case.seed
    values = {
        0x00: (0 if not late else 1, 2),
        0x02: (2 if not late else 1, 2),
        0x04: (old.bits(-8.0 if late else 1.25 + seed), 4),
        0x08: (old.bits(9.0 if late else -2.5 - seed), 4),
        0x0C: (old.bits(-10.0 if late else 3.75 + seed * 0.5), 4),
        0x10: (-70 if late else -20, 2),
        0x12: (40 if late else 30, 2),
        0x14: (55 if late else 15, 2),
        0x16: (35 if late else 25, 2),
        0x18: (old.bits(-2.0 if late else 1.5), 4),
        0x1C: (old.bits(1.25 if late else 0.75), 4),
        0x20: (old.bits(5.0 if late else -1.25), 4),
        0x24: (old.bits(-0.5 if late else 2.0), 4),
        0x28: (0x91 if late else 0x44, 1),
        0x29: (0x92 if late else 0x45, 1),
        0x2A: (0x93 if late else 0x46, 1),
        0x2B: (0x94 if late else 0x47, 1),
        0x2C: (0x95 if late else 0x48, 1),
        0x2D: (0x96 if late else 0x49, 1),
        0x2E: (0x97 if late else 0x4A, 1),
        0x2F: (0x98 if late else 0x4B, 1),
        0x30: (0x99 if late else 0x4C, 1),
        0x32: (-30 if late else 5, 2),
        0x34: (20 if late else 10, 2),
        0x36: (0xABCD if late else 0x1234, 2),
        0x38: (old.bits(-3.0 if late else 2.5), 4),
        0x3C: (old.bits(1.75 if late else 0.5), 4),
        0x40: (9 if late else 3, 1),
        0x41: (7 if late else 4, 1),
        0x42: (-1234 if late else 0x1234, 2),
        0x44: (2345 if late else -4321, 2),
        0x46: (0xA5 if late else 0x5A, 1),
    }
    for offset, (value, size) in values.items():
        put(memory, INPUT + offset, value, size)


def fixture(case):
    home = STACK + case.phase
    memory = {home + index: 0xCD for index in range(-4096, 1024)}
    for index in range(72):
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
    packet = home - 60
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

    remaining = integer() % u32(signed(get(memory, INPUT + 2, 2), 16) + 1)
    put(memory, packet + 0x00, get(memory, INPUT + 0x04))
    put(memory, packet + 0x04, get(memory, INPUT + 0x08))
    put(memory, packet + 0x08, get(memory, INPUT + 0x0C))
    remaining = u32(remaining + signed(get(memory, INPUT + 0x00, 2), 16))
    for index in range(9):
        put(memory, packet + 0x20 + index, get(memory, INPUT + 0x28 + index, 1), 1)
    put(memory, packet + 0x2C, get(memory, INPUT + 0x36, 2), 2)
    put(memory, packet + 0x36, get(memory, INPUT + 0x42, 2), 2)
    put(memory, packet + 0x38, get(memory, INPUT + 0x44, 2), 2)
    while remaining != 0:
        first_angle = signed(
            integer() % u32(signed(get(memory, INPUT + 0x14, 2), 16) + 1)
            + signed(get(memory, INPUT + 0x10, 2), 16), 16,
        )
        second_angle = signed(
            integer() % u32(signed(get(memory, INPUT + 0x16, 2), 16) + 1)
            + signed(get(memory, INPUT + 0x12, 2), 16), 16,
        )
        second_primary = trig(second_angle)
        second_quarter = trig(second_angle - 0x40)
        first_primary = trig(first_angle)
        first_quarter = trig(first_angle - 0x40)
        direction_scale = old.fm(old.bits(10.0), second_primary)
        put(memory, packet + 0x0C, old.fm(direction_scale, first_quarter))
        put(memory, packet + 0x10, old.fm(old.bits(-10.0), second_quarter))
        put(memory, packet + 0x14, old.fm(direction_scale, first_primary))
        put(memory, packet + 0x18, old.fa(old.fm(real(), get(memory, INPUT + 0x1C)), get(memory, INPUT + 0x18)))
        put(memory, packet + 0x1C, old.fa(old.fm(real(), get(memory, INPUT + 0x24)), get(memory, INPUT + 0x20)))
        value = integer() % u32(signed(get(memory, INPUT + 0x34, 2), 16) + 1)
        put(memory, packet + 0x2A, value + signed(get(memory, INPUT + 0x32, 2), 16), 2)
        put(memory, packet + 0x30, old.fa(old.fm(real(), get(memory, INPUT + 0x3C)), get(memory, INPUT + 0x38)))
        value = integer() % (get(memory, INPUT + 0x41, 1) + 1)
        put(memory, packet + 0x34, value + get(memory, INPUT + 0x40, 1), 1)
        arguments = (packet, get(memory, INPUT + 0x46, 1), 0, case.mode & 255, 0)
        calls.append((symbols["func_15156190"], tuple(map(u32, arguments))))
        snapshot = data(memory, packet, 60)
        assert private_bytes_untouched(snapshot)
        payloads.append((snapshot, tuple(map(u32, arguments))))
        put(memory, MARK + 4 * submits, submits + 1)
        submits += 1
        mutate_input(memory, case, True)
        remaining = u32(remaining - 1)
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
            arguments=(INPUT, case.mode),
        )

    @property
    def packet(self):
        return self.home - 60

    def record_call(self, target):
        counts = {
            self.target: 2,
            self.providers["func_150ADA20"]: 0,
            self.providers["func_150ADA68"]: 0,
            self.providers["func_151423D8"]: 1,
            self.providers["func_15156190"]: 5,
        }
        assert target in counts, hex(target)
        arguments = tuple(u32(value) for value in self.arguments(counts[target]))
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))
        if target == self.providers["func_15156190"]:
            assert arguments == (
                self.packet, get(self.memory, INPUT + 0x46, 1), 0,
                self.case.mode & 255, 0,
            )
            snapshot = data(self.memory, self.packet, 60)
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
            assert target == self.providers["func_15156190"]
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
    receipt = json.loads((output / "private-layout-v2.json").read_text())
    row = receipt["layouts"][layout]
    entry = row["entry"]
    result = []
    for label in ("original", "C", "raw"):
        image = (output / ("layout-{}-{}.elf".format(layout, label))).read_bytes()
        at = elf_slot_offset(image, entry, SIZE)
        result.append(struct.unpack_from(">180I", image, at))
    assert result[0] == result[1]
    assert sum(left != right for left, right in zip(result[0], result[2])) == 25
    return entry, row["symbols"], result


def public(memory, case):
    home = STACK + case.phase
    return {address: value for address, value in memory.items() if not home - 4096 <= address < home + 1024}


def role_trace(machine):
    result = []
    for event in machine.trace:
        operation, address, size, value = event
        if INPUT <= address and address + size <= INPUT + 72:
            result.append((operation, "input", address - INPUT, size, value))
        elif machine.packet <= address and address + size <= machine.packet + 60:
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
        public(machine.memory, machine.case), data(machine.memory, machine.packet, 60),
        [machine.r[index] for index in (*range(16, 24), 28, 29, 30, 31)],
        machine.f[20:], machine.calls, machine.payloads,
        machine.hi, machine.lo, machine.current_pc, machine.delay_of,
        machine.rng_i, machine.rng_f, machine.trig_i, machine.submits,
    )


def traces_match_with_anchor(retail, raw):
    retail = Counter(retail)
    raw = Counter(raw)
    anchors = [event for event, count in (raw - retail).items() for _ in range(count)]
    return anchors == [("R", "input", 0x28, 1, raw_anchor_value(raw))]


def raw_anchor_value(raw):
    values = [event[4] for event in raw if event[:4] == ("R", "input", 0x28, 1)]
    assert len(values) == 1
    return values[0]


def qualify(root, output):
    cases = [
        Case(seed=index % 8, mode=index, mutation=(index // 8) % 4, phase=(index % 2) * 8)
        for index in range(256)
    ]
    executions = 0
    seen = set()
    modes = set()
    packet_counts = set()
    role_trace_events = 0
    anchor_reads = 0
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
            delta = Counter(raw_trace) - Counter(retail_trace)
            assert sum(delta.values()) == 1, (layout, case, delta)
            event, count = next(iter(delta.items()))
            assert count == 1 and event[:4] == ("R", "input", 0x28, 1), (layout, case, event)
            anchor_reads += 1
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
    retail = struct.unpack_from(">180I", rom, ROM)
    traps = {ENTRY + 4 * index for index, word in enumerate(retail) if word & 0xFC00003F == 13}
    assert len(traps) == 5
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
        "input_live_extent_bytes": 71,
        "input_natural_bytes": 72,
        "packet_visible_bytes": 54,
        "packet_live_extent_bytes": 58,
        "packet_natural_bytes": 60,
        "all_six_private_bytes_untouched": True,
        "original_and_normalized_full_state_trace_equal": True,
        "raw_C_callee_preserved_register_and_FP_state_equal": True,
        "raw_C_public_memory_calls_complete_payloads_equal": True,
        "raw_C_has_only_one_documented_duplicate_input_read_per_execution": True,
        "documented_anchor_reads": anchor_reads,
        "role_trace_events_compared": role_trace_events,
        "normalized_access_prefix_pairs": prefixes,
        "independent_reference": True,
    }
    (output / "private-guest-v3.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(qualify(Path.cwd(), Path(__file__).parent), flush=True)
