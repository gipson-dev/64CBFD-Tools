"""Semantic, caller, owner and strict-image gates for func_15195984."""

from dataclasses import dataclass
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_packed_layout_record_allocator_candidates as candidate
from tools.experiments import game_packed_layout_record_allocator_match as match
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_frame_timing_oracle import STACK, TimingOracle
from tools.tests.test_game_point_transform_match import put, read


ROOT = Path(__file__).resolve().parents[2]
RECORD = 0x22000
ALLOCATE = 0x151957B0
HEAD = 0x800E08E8
TAIL = 0x800E08EC


@dataclass(frozen=True)
class Case:
    key: int = 0x12345678
    packed_size: int = 0x3456789A
    packed_scale: int = 0xABCDEF01
    double_size: int = 0
    allocate: bool = True
    phase: int = 0
    seed: int = 0


def fixture(case=Case()):
    memory = {STACK + index: (index * 17 + case.seed + 0xA5) & 0xFF
              for index in range(-0x300, 0x100)}
    memory.update({RECORD - 0x20 + index:
                   (index * 13 + case.seed * 19 + 0x59) & 0xFF
                   for index in range(0x80)})
    return memory


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x300 <= address < STACK + 0x100}


def reference(initial, case):
    memory = dict(initial)
    result = RECORD if case.allocate else 0
    if result:
        put(memory, RECORD + 0x18, 0)
        for index in range(5):
            put(memory, RECORD + 0x1C + index * 2, 0xFFFF, 2)
            put(memory, RECORD + 0x26 + index * 2, 0xFFFF, 2)
        put(memory, RECORD + 0x08, case.key, 2)
        width = ((case.packed_size >> 12) & 0xFFF) + 2
        height = (case.packed_size & 0xFFF) + 2
        if case.double_size:
            width *= 2
            height *= 2
        put(memory, RECORD + 0x0A, width, 2)
        put(memory, RECORD + 0x0C, height, 2)
        put(memory, RECORD + 0x0E,
            ((case.packed_scale >> 12) & 0xFFF) * 8, 2)
        put(memory, RECORD + 0x10, (case.packed_scale & 0xFFF) * 8, 2)
        memory[RECORD + 0x14] = 1
    return memory, result, [(ALLOCATE, (0x3C, HEAD, TAIL))]


class PackedLayoutAllocatorOracle(TimingOracle):
    def __init__(self, words, memory, case=Case(), fault=None):
        super().__init__(
            words, memory, phase=case.phase, entry=match.ENTRY,
            arguments=(case.key, case.packed_size,
                       case.packed_scale, case.double_size))
        self.case = case
        self.root_fault = fault

    def record_call(self, target):
        if target != ALLOCATE:
            raise AssertionError("Unexpected packed-layout helper %08X" % target)
        args = tuple(self.arguments(3))
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target != ALLOCATE:
            raise AssertionError("Unbounded packed-layout helper %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678
        self.r[2] = RECORD if self.case.allocate else 0


def controls():
    body = candidate.SELECTED
    variants = {
        "wrong-allocation-size": body.replace("0x3C,", "0x38,", 1),
        "wrong-list-head": body.replace(
            "(u8 *)&D_800E08E8, (u8 *)&D_800E08EC",
            "(u8 *)&D_800E08EC, (u8 *)&D_800E08EC", 1),
        "wrong-primary-count": body.replace("index < 5", "index < 4", 1),
        "wrong-secondary-sentinel": body.replace(
            "record->secondary2 = -1;", "record->secondary2 = 0;", 1),
        "wrong-key": body.replace("record->key = key;", "record->key = key + 1;", 1),
        "wrong-width-border": body.replace(
            "((packedSize >> 12) & 0xFFF) + 2",
            "((packedSize >> 12) & 0xFFF) + 1", 1),
        "wrong-double-gate": body.replace(
            "if (doubleSize != 0)", "if (doubleSize == 0)", 1),
        "wrong-scale": body.replace("record->scaledX *= 8;", "record->scaledX *= 7;", 1),
        "wrong-active": body.replace("record->active = 1;", "record->active = 2;", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("A packed-layout allocator control did not alter source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef signed short s16;
typedef signed int s32;
typedef unsigned int u32;
#define NULL ((void *)0)
''' + candidate.TYPES + r'''
static PackedLayoutRecord15195984 storage;
static u32 allocationCalls, returnNull, error;
s32 D_800E08E8;
s32 D_800E08EC;
s32 func_151957B0(s32 size, u8 *head, u8 *tail) {
    allocationCalls++;
    if (size != 0x3C || head != (u8 *)&D_800E08E8 ||
        tail != (u8 *)&D_800E08EC) error = 1;
    return returnNull ? 0 : (s32)&storage;
}
''' + body + r'''
static void write16(u8 *bytes, u32 offset, u32 value) {
    bytes[offset] = value;
    bytes[offset + 1] = value >> 8;
}
static int one(u32 seed) {
    u8 expected[sizeof(storage)];
    u8 *bytes = (u8 *)&storage;
    s32 key = (s32)(seed * 0x1020305u + 0x89ABCDEFu);
    s32 packedSize = (s32)(seed * 0x9E3779B9u + 0x3456789Au);
    s32 packedScale = (s32)(seed * 0x7F4A7C15u + 0xABCDEF01u);
    s32 doubleSize = (seed >> 1) & 1;
    u32 width, height, scaledX, scaledY, index;
    PackedLayoutRecord15195984 *result;
    for (index = 0; index < sizeof(storage); index++) {
        bytes[index] = (u8)(seed * 19u + index * 13u + 0x59u);
        expected[index] = bytes[index];
    }
    returnNull = (seed & 31u) == 0;
    allocationCalls = error = 0;
    if (!returnNull) {
        expected[0x18] = expected[0x19] = expected[0x1A] = expected[0x1B] = 0;
        for (index = 0; index < 5; index++) {
            write16(expected, 0x1C + index * 2, 0xFFFF);
            write16(expected, 0x26 + index * 2, 0xFFFF);
        }
        write16(expected, 0x08, (u32)key);
        width = (((u32)packedSize >> 12) & 0xFFF) + 2;
        height = ((u32)packedSize & 0xFFF) + 2;
        if (doubleSize) { width *= 2; height *= 2; }
        scaledX = (((u32)packedScale >> 12) & 0xFFF) * 8;
        scaledY = ((u32)packedScale & 0xFFF) * 8;
        write16(expected, 0x0A, width);
        write16(expected, 0x0C, height);
        write16(expected, 0x0E, scaledX);
        write16(expected, 0x10, scaledY);
        expected[0x14] = 1;
    }
    result = func_15195984(key, packedSize, packedScale, doubleSize);
    if (error || allocationCalls != 1 ||
        result != (returnNull ? NULL : &storage)) return 1;
    for (index = 0; index < sizeof(storage); index++)
        if (bytes[index] != expected[index]) return 2;
    return 0;
}
static int run(void) {
    u32 seed;
    if (sizeof(void *) != 4 || sizeof(s32) != 4 || sizeof(storage) != 0x3C ||
        __builtin_offsetof(PackedLayoutRecord15195984, key) != 0x08 ||
        __builtin_offsetof(PackedLayoutRecord15195984, link) != 0x18 ||
        __builtin_offsetof(PackedLayoutRecord15195984, primary) != 0x1C ||
        __builtin_offsetof(PackedLayoutRecord15195984, secondary0) != 0x26)
        return 9;
    for (seed = 0; seed < 4096; seed++) if (one(seed)) return 1;
    return 0;
}
void _start(void) {
    s32 code = run();
    __asm__ volatile("int $0x80"::"a"(1),"b"(code));
    __builtin_unreachable();
}
'''


def run_native(label, body, optimization, expected):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / (label + ".elf")
    source.write_text(native_source(body))
    command = [
        "gcc", "-m32", "-std=c99", optimization, "-fno-pie", "-no-pie",
        "-ffreestanding", "-fno-strict-aliasing", "-fno-stack-protector",
        "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
        "-Wall", "-Wextra", "-Werror", "-nostdlib", str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if executed.returncode != expected:
        raise AssertionError((label, executed.returncode, executed.stderr))


class GamePackedLayoutRecordAllocatorMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.retail = list(struct.unpack_from(
            ">64I", (ROOT / match.ROM_IMAGE).read_bytes(), match.ROM))

    def receipt(self, name, data):
        (self.output / (name + ".json")).write_text(
            json.dumps(data, indent=2) + "\n")

    def test_01_guarded_profile_owner_neighbors_and_strict_image(self):
        selected = candidate.compare(
            "test-selected", candidate.SELECTED, ("-O2", "-g3"))
        self.assertEqual(
            (selected["words"], selected["frame"], selected["differences"]),
            (64, 0x18, 46))
        self.assertEqual(selected["bindings"], {
            "0x018": [("R_MIPS_HI16", "D_800E08E8")],
            "0x01C": [("R_MIPS_HI16", "D_800E08EC")],
            "0x020": [("R_MIPS_LO16", "D_800E08EC")],
            "0x024": [("R_MIPS_LO16", "D_800E08E8")],
            "0x028": [("R_MIPS_26", "func_151957B0")],
        })
        plain = candidate.compare(
            "test-plain", candidate.SELECTED, ("-O2",))
        self.assertEqual(
            (plain["words"], plain["frame"], plain["differences"]),
            (64, 0x18, 56))
        report = match.prepare(ROOT)["report"]
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(
            (report["guards"], report["neighbors"], report["strict_exclusions"]),
            (46, 68, 0))
        self.assertTrue(report["all_addresses_fixed"])
        self.assertTrue(report["game_data"]["exact"])
        self.assertEqual(len({row["offset"] for row in match.PATCH_ROWS}), 46)

    def test_02_guest_packed_pairs_allocation_failure_and_all_words(self):
        cases = []
        for seed in range(512):
            for phase in (0, 8):
                cases.append(Case(
                    key=(seed * 0x1020305 + 0x89ABCDEF) & 0xFFFFFFFF,
                    packed_size=(seed * 0x9E3779B9 + 0x3456789A) & 0xFFFFFFFF,
                    packed_scale=(seed * 0x7F4A7C15 + 0xABCDEF01) & 0xFFFFFFFF,
                    double_size=(seed >> 1) & 1,
                    allocate=(seed & 31) != 0,
                    phase=phase, seed=seed))
        coverage = set()
        for case in cases:
            initial = fixture(case)
            wanted, result, calls = reference(initial, case)
            model = PackedLayoutAllocatorOracle(
                self.retail, initial, case).run()
            self.assertEqual(
                (public(model.memory), model.r[2], model.calls),
                (public(wanted), result, calls))
            coverage.update(model.visits)
        self.assertEqual(
            coverage, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.receipt("guest-contract", {
            "cases": len(cases), "words": len(coverage),
            "packed_values": 512, "stack_phases": 2,
            "allocation_failure_cases": sum(not case.allocate for case in cases),
            "callback_clobber": True,
        })

    def test_03_native_profiles_and_effective_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED,
                       optimization, 0)
        variants = controls()
        for label, body in variants.items():
            run_native("control-" + label, body, "-O2", 1)
        self.receipt("native-contract", {
            "profiles": ["O0", "O2", "O3"], "cases_per_profile": 4096,
            "controls": sorted(variants), "actual_32_bit_C": True,
        })

    def test_04_callers_abi_and_active_root_fault_boundaries(self):
        evidence = match.registry_evidence(ROOT)
        self.assertEqual(
            evidence["direct_jal_calls"], ["0x1c3038", "0x1c3394"])
        self.assertEqual(evidence["aligned_pointer_literals"], [])
        cases = (
            Case(0, 0, 0, 0, False),
            Case(0x7FFFFFFF, 0, 0xFFFFFFFF, 0, True),
            Case(0x80000000, 0xFFFFFFFF, 0, 1, True, phase=8),
            Case(0x12345678, 0x00FFF000, 0x00ABCDEF, 0, True),
            Case(0x89ABCDEF, 0x7FFFFFFF, 0x80000000, 1, True, phase=8),
        )
        states = []
        for case in cases:
            initial = fixture(case)
            baseline = PackedLayoutAllocatorOracle(
                self.retail, initial, case).run()
            for cut in range(baseline.root_accesses):
                model = PackedLayoutAllocatorOracle(
                    self.retail, initial, case, fault=cut)
                with self.assertRaises(faults.AccessBoundary):
                    model.run()
                states.append((model.current_pc, model.delay_of,
                               model.root_accesses))
        self.assertGreater(len(states), 20)
        self.receipt("callers-and-faults", {
            "direct_jal_calls": evidence["direct_jal_calls"],
            "callers": evidence["callers"],
            "root_access_faults": states,
        })


if __name__ == "__main__":
    unittest.main()
