"""Guest oracle for the direct-exact effect-record factory."""

from dataclasses import dataclass
import json
import struct
import subprocess

from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object


DESCRIPTOR = 0x30000
PAIR = 0x31000
RECORD = 0x32000


@dataclass(frozen=True)
class Case:
    index: int
    pair: int
    count: int
    helper_reject: int
    allocate: int
    mutation: int
    callback: int
    slot: int
    extra: int
    context: int
    flags: int


def symbols(layout):
    return {
        "func_151555AC": (0x151555AC, 0x17110000, 0x1F110000)[layout],
        "func_15167A68": (0x15167A68, 0x17220000, 0x1F220000)[layout],
        "memcpy": (0x15022EC0, 0x17330000, 0x1F330000)[layout],
    }


def link(obj, output, source, layout, label):
    syms = symbols(layout)
    entry = (source.ENTRY, 0x17038000, 0x1F00FFFC)[layout]
    text, functions, relocations = parse_object(obj)
    assembly, unknown = emit_function(text, functions[source.FUNCTION], relocations,
                                      source.FUNCTION, syms)
    assert not unknown
    path = output / ("record-layout-%d-%s" % (layout, label))
    path.with_suffix(".s").write_text(assembly)
    path.with_suffix(".ld").write_text(
        "SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n" % entry
        + "\n".join("%s = 0x%X;" % item for item in syms.items()))
    subprocess.run(["mips-linux-gnu-as", "-EB", "-march=vr4300", "-o",
                    str(path.with_suffix(".o")), str(path.with_suffix(".s"))], check=True)
    subprocess.run(["mips-linux-gnu-ld", "-m", "elf32btsmip", "-T",
                    str(path.with_suffix(".ld")), "-e", source.FUNCTION, "-o",
                    str(path.with_suffix(".elf")), str(path.with_suffix(".o"))], check=True)
    raw = sections(path.with_suffix(".elf"))[".text"][1][:source.SIZE]
    return entry, syms, list(struct.unpack(">%dI" % source.WORDS, raw))


def cases():
    result = []
    for index in range(256):
        branch = index & 3
        result.append(Case(
            index=index,
            pair=0 if branch == 0 else PAIR,
            count=(-1, 0, 1, 3)[branch],
            helper_reject=1 if branch == 3 and index & 4 else 0,
            allocate=0 if index % 7 == 0 else 1,
            mutation=(index >> 3) & 3,
            callback=index,
            slot=index,
            extra=(index * 0x01020305) & 0xFFFFFFFF,
            context=(0x76540000 | index),
            flags=0x20 if index & 1 else 0,
        ))
    return result


def fixture(case):
    memory = {STACK + i: (i * 17 + case.index * 11 + 0xA5) & 0xFF
              for i in range(-512, 256)}
    for base, length in ((DESCRIPTOR, 0x58), (PAIR, 16), (RECORD, 0xE0)):
        memory.update({base + i: (i * 29 + case.index * 7 + base) & 0xFF
                       for i in range(length)})
    put(memory, DESCRIPTOR + 8, 0x3F800000 + case.index)
    put(memory, DESCRIPTOR + 0xC, 0xBF000000 + case.index)
    put(memory, DESCRIPTOR + 0x14, case.flags, 2)
    put(memory, STACK + 0x10, case.extra)
    put(memory, STACK + 0x14, case.slot)
    put(memory, STACK + 0x18, case.context)
    return memory


def mutate_helper(memory, case):
    if case.mutation & 1:
        put(memory, DESCRIPTOR + 0x14, case.flags ^ 0x20, 2)
        memory[DESCRIPTOR + 2] ^= 0x5A


def mutate_allocator(memory, case):
    if case.mutation & 2:
        memory[DESCRIPTOR + 3] ^= 0xA5


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 512 <= address < STACK + 256}


def reference(initial, case, syms):
    memory = dict(initial)
    calls = []
    probe = ()
    if case.pair and case.count > 0:
        local = STACK - 56 + 0x2C
        put(memory, local, read(memory, DESCRIPTOR + 8))
        put(memory, local + 4, read(memory, DESCRIPTOR + 0xC))
        calls.append((syms["func_151555AC"], (DESCRIPTOR, local, case.pair, case.count)))
        probe = (read(memory, local), read(memory, local + 4))
        mutate_helper(memory, case)
        if case.helper_reject:
            return memory, calls, probe, 0
    flags = read(memory, DESCRIPTOR + 0x14, 2)
    category = 0x57 if flags & 0x20 else 0x5D
    calls.append((syms["func_15167A68"],
                  (category, case.context, (case.extra + 0x70) & 0xFFFFFFFF,
                   1, case.slot, 1)))
    mutate_allocator(memory, case)
    if not case.allocate:
        return memory, calls, probe, 0
    calls.append((syms["memcpy"], (RECORD + 0x10, DESCRIPTOR, 0x58)))
    for offset in range(0x58):
        memory[RECORD + 0x10 + offset] = memory[DESCRIPTOR + offset]
    memory[RECORD + 0x68] = 0
    memory[RECORD + 0x68] |= case.callback & 0xFF
    return memory, calls, probe, RECORD


class Oracle(AreaOracle):
    def __init__(self, words, memory, case, entry, syms):
        self.case = case
        self.syms = syms
        self.probe = ()
        super().__init__(words, memory,
            (DESCRIPTOR, case.callback, case.pair, case.count), entry=entry)

    def record_call(self, target):
        counts = {self.syms["func_151555AC"]: 4,
                  self.syms["func_15167A68"]: 6,
                  self.syms["memcpy"]: 3}
        assert target in counts, hex(target)
        self.calls.append((target, tuple(self.arguments(counts[target]))))

    def hook(self, target):
        case = self.case
        if target == self.syms["func_151555AC"]:
            local = self.calls[-1][1][1]
            self.probe = (read(self.memory, local), read(self.memory, local + 4))
            mutate_helper(self.memory, case)
            result = case.helper_reject
        elif target == self.syms["func_15167A68"]:
            mutate_allocator(self.memory, case)
            result = RECORD if case.allocate else 0
        else:
            destination, source, count = self.calls[-1][1]
            for offset in range(count):
                self.memory[destination + offset] = self.memory[source + offset]
            result = destination
        for register in (1, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.r[2] = result & 0xFFFFFFFF


def qualify(root, output, source):
    programs = []
    for layout in range(3):
        entry, syms, original = link(root / source.OBJECT, output, source, layout, "original")
        _, _, candidate = link(output / "selected-final.o", output, source, layout, "C")
        assert original == candidate
        programs.append((entry, syms, original))
    covered = set()
    executions = 0
    branches = set()
    for entry, syms, words in programs:
        for case in cases():
            initial = fixture(case)
            expected, calls, probe, result = reference(initial, case, syms)
            machine = Oracle(words, initial, case, entry, syms).run()
            assert (public(machine.memory), machine.calls, machine.probe, machine.r[2]) == (
                public(expected), calls, probe, result)
            covered.update(pc - entry for pc in machine.visits if entry <= pc < entry + source.SIZE)
            branches.add((bool(case.pair), case.count > 0, bool(case.helper_reject), bool(case.allocate)))
            executions += 1
    missing = sorted(set(range(0, source.SIZE, 4)) - covered)
    assert len(covered) == source.WORDS - 1 and missing == [0x50]
    report = {
        "success": True, "private_only": True, "matching_credit": 0,
        "cases_per_layout": 256, "independent_links": 3,
        "executions": executions, "words": source.WORDS,
        "covered_words": len(covered), "all_reachable_words_reached": True,
        "unreachable_duplicate_load_words": 1,
        "all256_callback_and_slot_bytes": True,
        "overlap_disabled_zero_positive_and_reject_paths": True,
        "allocation_success_and_failure_paths": True,
        "both_category_flags": True,
        "live_descriptor_mutations_after_helper_and_allocator": True,
        "complete_88_byte_copy_checked": True,
        "original_and_raw_C_words_equal": True,
        "branch_combinations": len(branches),
    }
    (output / "private-guest-v1.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
