"""Semantic, caller, owner and strict-image gates for func_15158BD0."""

from dataclasses import dataclass
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_owner_effect_record_factory_candidates as candidate
from tools.experiments import game_owner_effect_record_factory_match as match
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_frame_timing_oracle import STACK, TimingOracle
from tools.tests.test_game_point_transform_match import put, read


ROOT = Path(__file__).resolve().parents[2]
OWNER, RECORD = 0x22000, 0x24000
ALLOCATE, CLASSIFY, RELEASE = 0x15167A68, 0x15159370, 0x1516979C
PATTERNS = (
    0x00000000, 0x80000000, 0x3F800000, 0xBF400000,
    0x7F800000, 0xFF800000, 0x7FC12345, 0xC2480000,
)


def u32(value):
    return value & 0xFFFFFFFF


@dataclass(frozen=True)
class Case:
    owner_present: bool = True
    allocated: bool = True
    classified: bool = True
    enabled: int = 1
    extra_bytes: int = 0
    classification: int = 0x6D
    phase: int = 0
    seed: int = 0


def fixture(case=Case()):
    memory = {
        STACK + index: (index * 17 + case.seed * 23 + 0xA5) & 0xFF
        for index in range(-0x500, 0x180)
    }
    for base, size, salt in ((OWNER, 0x100, 11), (RECORD, 0x100, 19)):
        memory.update({
            base + index: (index * salt + case.seed * 29 + 0x57) & 0xFF
            for index in range(size)
        })
    for index in range(3):
        put(memory, OWNER + 0x14 + index * 4,
            PATTERNS[(case.seed + index * 3) & 7])
    memory[OWNER + 0x3B] = (case.seed * 37 + 0x63) & 0xFF
    return memory


def reference(initial, case=Case()):
    memory = dict(initial)
    owner = OWNER if case.owner_present else 0
    calls = []
    if owner == 0:
        return memory, calls, 0
    calls.append((ALLOCATE, (
        0x2E, 0, u32(case.extra_bytes + 0x58), 1, 0xFF, 1,
    )))
    if not case.allocated:
        return memory, calls, 0
    put(memory, RECORD + 0x18, OWNER)
    for offset, value in ((0x2C, 2), (0x2D, 2), (0x2E, 2),
                          (0x2F, 3), (0x30, 0)):
        memory[RECORD + offset] = value
    memory[RECORD + 0x1C] = initial[OWNER + 0x3B]
    for index in range(3):
        put(memory, RECORD + 0x20 + index * 4,
            read(initial, OWNER + 0x14 + index * 4))
    memory[RECORD + 0x31] = 1 if (case.enabled & 0xFF) != 0 else 0
    put(memory, RECORD + 0x10, 1)
    put(memory, RECORD + 0x14, 0)
    calls.append((CLASSIFY, (OWNER, RECORD + 0x1D, RECORD)))
    memory[RECORD + 0x1D] = case.classification & 0xFF
    if not case.classified:
        calls.append((RELEASE, (RECORD,)))
        return memory, calls, 0
    memory[RECORD + 0x50] = 0
    return memory, calls, RECORD


def public(memory):
    return {
        address: value for address, value in memory.items()
        if not STACK - 0x500 <= address < STACK + 0x180
    }


class FactoryOracle(TimingOracle):
    def __init__(self, words, memory, case=Case(), fault=None):
        super().__init__(
            words, memory, phase=case.phase, entry=match.ENTRY,
            arguments=(
                OWNER if case.owner_present else 0,
                case.enabled,
                case.extra_bytes,
            ),
        )
        self.case = case
        self.root_fault = fault

    def record_call(self, target):
        widths = {ALLOCATE: 6, CLASSIFY: 3, RELEASE: 1}
        if target not in widths:
            raise AssertionError("Unexpected owner-effect helper %08X" % target)
        arguments = tuple(u32(value) for value in self.arguments(widths[target]))
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))

    def hook(self, target):
        if target == ALLOCATE:
            result = RECORD if self.case.allocated else 0
        elif target == CLASSIFY:
            self.put(self.calls[-1][1][1], self.case.classification, 1)
            result = 1 if self.case.classified else 0
        elif target == RELEASE:
            result = 0
        else:
            raise AssertionError("Unbounded owner-effect helper %08X" % target)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678
        self.r[2] = u32(result)


def controls():
    body = candidate.SELECTED
    variants = {
        "wrong-kind": body.replace("(0x2E, 0,", "(0x2D, 0,", 1),
        "wrong-size": body.replace("extraBytes + 0x58", "extraBytes + 0x54", 1),
        "wrong-owner": body.replace("record->owner = owner", "record->owner = owner + 1", 1),
        "wrong-class0": body.replace("record->class0 = 2", "record->class0 = 1", 1),
        "wrong-class3": body.replace("record->class3 = 3", "record->class3 = 2", 1),
        "wrong-owner-id": body.replace("owner[0x3B]", "owner[0x3A]", 1),
        "wrong-x": body.replace("owner + 0x14", "owner + 0x10", 1),
        "wrong-z": body.replace("owner + 0x1C", "owner + 0x20", 1),
        "wrong-enable": body.replace("record->enabled = 1", "record->enabled = 2", 1),
        "wrong-active": body.replace("record->active = 1", "record->active = 2", 1),
        "wrong-state": body.replace("record->state = 0", "record->state = 1", 1),
        "wrong-classifier-output": body.replace(
            "&record->classification", "&record->ownerId", 1),
        "wrong-release": body.replace(
            "func_1516979C(record)", "func_1516979C((u8 *)record + 1)", 1),
        "wrong-tail": body.replace("record->tail = 0", "record->tail = 1", 1),
    }
    if len(variants) != 14 or any(value == body for value in variants.values()):
        raise AssertionError("An owner-effect factory control did not alter source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef signed int s32;
typedef unsigned int u32;
typedef float f32;
#define NULL ((void *)0)
''' + candidate.DECLARATIONS + r'''
static u32 ownerWords[0x40], recordWords[0x40], expectedWords[0x40];
static u32 allocateCalls, classifyCalls, releaseCalls, failed;
static u32 allowAllocation, allowClassification, wantedSize;
static u8 wantedClassification;
static void store32(void *pointer, u32 value) { *(u32 *)pointer = value; }
static u32 load32(const void *pointer) { return *(const u32 *)pointer; }
void *func_15167A68(s32 kind, s32 context, s32 bytes, s32 active,
                    s32 slot, s32 pool) {
    allocateCalls++;
    if (kind != 0x2E || context != 0 || (u32)bytes != wantedSize ||
        active != 1 || slot != 0xFF || pool != 1) failed = 1;
    return allowAllocation ? recordWords : NULL;
}
s32 func_15159370(u8 *owner, u8 *classification,
                  OwnerEffectRecord15158BD0 *record) {
    classifyCalls++;
    if (owner != (u8 *)ownerWords || classification != (u8 *)recordWords + 0x1D ||
        record != (OwnerEffectRecord15158BD0 *)recordWords) failed = 2;
    *classification = wantedClassification;
    return allowClassification;
}
void func_1516979C(void *record) {
    releaseCalls++;
    if (record != recordWords) failed = 3;
}
''' + body + r'''
static int one(u32 seed) {
    static const u32 patterns[8] = {0,0x80000000u,0x3F800000u,0xBF400000u,
        0x7F800000u,0xFF800000u,0x7FC12345u,0xC2480000u};
    u8 *owner = (u8 *)ownerWords;
    u8 *record = (u8 *)recordWords;
    u8 *expected = (u8 *)expectedWords;
    OwnerEffectRecord15158BD0 *result;
    u32 index, ownerPresent = seed & 1u;
    u8 enabled = (u8)(seed * 0x25u);
    s32 extra = (s32)((seed * 7u) & 0x3FFu);
    for (index = 0; index < sizeof(ownerWords); index++)
        owner[index] = (u8)(seed * 11u + index * 7u + 0x31u);
    for (index = 0; index < sizeof(recordWords); index++) {
        record[index] = (u8)(seed * 13u + index * 5u + 0x59u);
        expected[index] = record[index];
    }
    for (index = 0; index < 3; index++)
        store32(owner + 0x14 + index * 4, patterns[(seed + index * 3u) & 7u]);
    owner[0x3B] = (u8)(seed * 37u + 0x63u);
    allowAllocation = (seed >> 1) & 1u;
    allowClassification = (seed >> 2) & 1u;
    wantedClassification = (u8)(seed * 41u + 0x6Du);
    wantedSize = (u32)extra + 0x58u;
    allocateCalls = classifyCalls = releaseCalls = failed = 0;
    result = func_15158BD0(ownerPresent ? owner : NULL, enabled, extra);
    if (!ownerPresent) {
        if (result != NULL || allocateCalls || classifyCalls || releaseCalls) return 10;
    } else if (!allowAllocation) {
        if (result != NULL || allocateCalls != 1 || classifyCalls || releaseCalls) return 11;
    } else {
        store32(expected + 0x10, 1); store32(expected + 0x14, 0);
        store32(expected + 0x18, (u32)owner);
        expected[0x1C] = owner[0x3B]; expected[0x1D] = wantedClassification;
        for (index = 0; index < 3; index++)
            store32(expected + 0x20 + index * 4, load32(owner + 0x14 + index * 4));
        expected[0x2C] = 2; expected[0x2D] = 2; expected[0x2E] = 2;
        expected[0x2F] = 3; expected[0x30] = 0; expected[0x31] = enabled ? 1 : 0;
        if (allowClassification) expected[0x50] = 0;
        if (result != (allowClassification ? (OwnerEffectRecord15158BD0 *)recordWords : NULL) ||
            allocateCalls != 1 || classifyCalls != 1 ||
            releaseCalls != (allowClassification ? 0u : 1u)) return 12;
        for (index = 0; index < sizeof(recordWords); index++)
            if (record[index] != expected[index]) return 13;
    }
    return failed ? (int)(20u + failed) : 0;
}
static int run(void) {
    u32 seed;
    if (sizeof(void *) != 4 || sizeof(OwnerEffectRecord15158BD0) != 0x58 ||
        __builtin_offsetof(OwnerEffectRecord15158BD0, owner) != 0x18 ||
        __builtin_offsetof(OwnerEffectRecord15158BD0, classification) != 0x1D ||
        __builtin_offsetof(OwnerEffectRecord15158BD0, x) != 0x20 ||
        __builtin_offsetof(OwnerEffectRecord15158BD0, enabled) != 0x31 ||
        __builtin_offsetof(OwnerEffectRecord15158BD0, tail) != 0x50) return 9;
    for (seed = 0; seed < 4096; seed++) {
        s32 code = one(seed);
        if (code) return code;
    }
    return 0;
}
void _start(void) {
    s32 code = run();
    __asm__ volatile("int $0x80"::"a"(1),"b"(code));
    __builtin_unreachable();
}
'''


def run_native(label, body, optimization, should_pass):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / (label + ".elf")
    source.write_text(native_source(body))
    command = [
        "gcc", "-m32", "-std=c99", optimization, "-fno-pie", "-no-pie",
        "-ffreestanding", "-fno-strict-aliasing", "-fno-stack-protector",
        "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
        "-Wall", "-Wextra", "-Werror", "-nostdlib",
        str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if should_pass and executed.returncode != 0:
        raise AssertionError((label, executed.returncode, executed.stderr))
    if not should_pass and executed.returncode == 0:
        raise AssertionError((label, "semantic control passed"))


class GameOwnerEffectRecordFactoryMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.prepared = match.prepare(ROOT)
        cls.retail = list(struct.unpack_from(
            ">%dI" % match.WORDS,
            (ROOT / match.ROM_IMAGE).read_bytes(), match.ROM,
        ))
        selected = candidate.compare(
            "test-selected", candidate.SELECTED, ("-O2", "-g3")
        )
        cls.selected = selected
        compact = ROOT / candidate.BUILD / "test-selected.o"
        linked, functions = link_owner(ROOT, cls.output, compact, candidate.OWNER)
        info = functions[match.FUNCTION]
        cls.natural = list(struct.unpack_from(
            ">%dI" % match.WORDS, linked, info["value"]
        ))

    def receipt(self, name, data):
        (self.output / (name + ".json")).write_text(
            json.dumps(data, indent=2) + "\n"
        )

    def test_01_guarded_profile_owner_neighbors_and_strict_image(self):
        self.assertEqual(
            (self.selected["words"], self.selected["frame"],
             self.selected["differences"]),
            (65, 0x30, 23),
        )
        self.assertEqual(self.selected["object_raw_sha256"], match.RAW_SHA256)
        report = self.prepared["report"]
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(
            (report["guards"], report["neighbors"], report["strict_exclusions"]),
            (23, 36, 0),
        )
        self.assertTrue(report["all_addresses_fixed"])
        self.assertTrue(report["game_data"]["exact"])
        self.assertEqual(report["functions"], 6052)

    def test_02_guest_all_paths_record_bytes_and_all_words(self):
        cases = []
        for seed, values in enumerate(itertools.product(
                (False, True), (False, True), (False, True),
                (0, 1, 0xFF, 0x12345678), (0, 0x24, 0x400), (0, 8))):
            present, allocated, classified, enabled, extra, phase = values
            cases.append(Case(
                present, allocated, classified, enabled, extra,
                seed * 43 + 0x6D, phase, seed,
            ))
        coverage = [set(), set()]
        for case in cases:
            initial = fixture(case)
            wanted, calls, result = reference(initial, case)
            for index, words in enumerate((self.retail, self.natural)):
                model = FactoryOracle(words, initial, case).run()
                self.assertEqual((public(model.memory), model.calls, model.r[2]),
                                 (public(wanted), calls, result), case)
                coverage[index].update(model.visits)
        full = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4))
        self.assertEqual(coverage[0], full)
        self.assertEqual(coverage[1], full)
        self.receipt("guest-contract", {
            "cases_per_body": len(cases),
            "retail_words": len(coverage[0]),
            "natural_C_words": len(coverage[1]),
            "reserved_ranges_preserved": ["0x1E..0x1F", "0x32..0x4F", "0x51..0x57"],
            "paths": ["null-owner", "allocation-failure", "classification-failure", "success"],
        })

    def test_03_native_profiles_and_effective_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED,
                       optimization, True)
        variants = controls()
        for label, body in variants.items():
            run_native("control-" + label, body, "-O2", False)
        self.receipt("native-contract", {
            "profiles": ["O0", "O2", "O3"],
            "cases_per_profile": 4096,
            "controls": sorted(variants),
            "actual_32_bit_C": True,
        })

    def test_04_callers_and_fault_boundaries(self):
        evidence = match.registry_evidence(ROOT)
        self.assertEqual(evidence["direct_jal_calls"], [
            "0x9a268", "0x9a2ec", "0xa08a4", "0x17ae64",
            "0x17af14", "0x17af80", "0x17afdc",
        ])
        self.assertEqual(evidence["aligned_pointer_literals"], [])
        states = []
        for words in (self.retail, self.natural):
            for classified in (False, True):
                case = Case(True, True, classified, 0x12345678, 0x24,
                            0xA7, 8, 19)
                initial = fixture(case)
                baseline = FactoryOracle(words, initial, case).run()
                for cut in range(baseline.root_accesses):
                    model = FactoryOracle(words, initial, case, fault=cut)
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.root_accesses, cut)
                    states.append((model.current_pc, model.delay_of, cut))
        self.assertGreater(len(states), 80)
        self.receipt("callers-and-faults", {
            "direct_callers": len(evidence["direct_jal_calls"]),
            "fault_observations": len(states),
            "unique_boundaries": len(set(states)),
        })


if __name__ == "__main__":
    unittest.main()
