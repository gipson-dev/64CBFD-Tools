"""Semantic, callback, owner and strict-image gates for func_151C86AC."""

from dataclasses import dataclass
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_owner_event_state_dispatch_candidates as candidate
from tools.experiments import game_owner_event_state_dispatch_match as match
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_frame_timing_oracle import STACK, TimingOracle
from tools.tests.test_game_point_transform_match import put, read


ROOT = Path(__file__).resolve().parents[2]
OWNER, EVENT = 0x22000, 0x23000
VALIDATE, ACTION = 0x151C87E0, 0x151C899C


def u32(value):
    return value & 0xFFFFFFFF


@dataclass(frozen=True)
class Case:
    code: int
    flags: int = 0
    owner_key: int = 0x12345678
    event_value: int = 0x12345678
    event_word4: int = 0x12345678
    validate: bool = False
    phase: int = 0
    seed: int = 0


def fixture(case):
    memory = {
        STACK + index: (index * 17 + case.seed * 23 + 0xA5) & 0xFF
        for index in range(-0x180, 0x100)
    }
    memory.update({
        OWNER + index: (index * 13 + case.seed * 19 + 0x59) & 0xFF
        for index in range(0x220)
    })
    memory.update({
        EVENT + index: (index * 29 + case.seed * 7 + 0x71) & 0xFF
        for index in range(8)
    })
    memory[OWNER + 0x196] = case.flags & 0xFF
    put(memory, OWNER + 0x138, case.owner_key)
    put(memory, EVENT, case.event_value)
    put(memory, EVENT + 4, case.event_word4)
    return memory


def reference(initial, case):
    memory, calls = dict(initial), []
    code = case.code & 0xFF
    if code == 0x20:
        if ((memory[OWNER + 0x196] & 0x10) and
                read(memory, OWNER + 0x138) == read(memory, EVENT + 4)):
            calls.append((VALIDATE, (read(memory, EVENT), OWNER)))
            if case.validate:
                calls.append((ACTION, (read(memory, EVENT), OWNER)))
    elif code == 0x3A and read(memory, OWNER + 0x138) == read(memory, EVENT):
        selector = memory[EVENT + 4]
        if selector == 0:
            memory[OWNER + 0x196] |= 2
        elif selector == 1:
            memory[OWNER + 0x196] &= 0xFD
        elif selector == 2:
            calls.append((ACTION, (0, OWNER)))
    return memory, calls


def public(memory):
    return {
        address: value for address, value in memory.items()
        if not STACK - 0x180 <= address < STACK + 0x100
    }


def cases():
    result, seed = [], 0
    for code, flags, equal, validate, phase in itertools.product(
            (0x20, 0x120), (0, 0x10, 0x12), (False, True),
            (False, True), (0, 8)):
        key = u32(0x10203040 + seed * 0x101)
        word4 = key if equal else key ^ 0x01000001
        result.append(Case(code, flags, key, 0xA0000000 + seed,
                           word4, validate, phase, seed))
        seed += 1
    for code, equal, selector, flags, phase in itertools.product(
            (0x3A, 0x13A), (False, True), (0, 1, 2, 3, 0xFF),
            (0, 2, 0xFD, 0xFF), (0, 8)):
        key = u32(0x50607080 + seed * 0x101)
        value = key if equal else key ^ 0x00010000
        word4 = (selector << 24) | (seed & 0x00FFFFFF)
        result.append(Case(code, flags, key, value, word4,
                           False, phase, seed))
        seed += 1
    for code, phase in itertools.product((0, 1, 0x1F, 0x21, 0x39, 0x3B, 0xFF), (0, 8)):
        result.append(Case(code, 0xFF, seed, seed, seed,
                           True, phase, seed))
        seed += 1
    return result


class DispatchOracle(TimingOracle):
    def __init__(self, words, memory, case, fault=None):
        super().__init__(words, memory, phase=case.phase, entry=match.ENTRY,
                         arguments=(OWNER, EVENT, case.code))
        self.case = case
        self.root_fault = fault

    def record_call(self, target):
        if target not in (VALIDATE, ACTION):
            raise AssertionError("Unexpected owner-event helper %08X" % target)
        arguments = tuple(u32(value) for value in self.arguments(2))
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))

    def hook(self, target):
        if target not in (VALIDATE, ACTION):
            raise AssertionError("Unexpected owner-event hook %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678
        self.r[2] = 1 if target == VALIDATE and self.case.validate else 0


def controls():
    body = candidate.SELECTED
    variants = {
        "wrong-event20": body.replace("case 0x20:", "case 0x21:", 1),
        "wrong-event3a": body.replace("case 0x3A:", "case 0x3B:", 1),
        "wrong-gate-bit": body.replace("& 0x10", "& 0x08", 1),
        "wrong-match-field": body.replace("state + 0x28", "state + 0x24", 1),
        "invert-validation": body.replace("!= 0", "== 0", 1),
        "wrong-first-action": body.replace(
            "func_151C899C(*(s32 *)event, *ownerHome);",
            "func_151C899C(0, *ownerHome);", 1),
        "wrong-owner-key": body.replace("state + 0x28", "state + 0x2C", 1),
        "wrong-set-bit": body.replace("|= 2", "|= 4", 1),
        "wrong-clear-bit": body.replace("0xFFFD", "0xFFFB", 1),
        "wrong-null-action": body.replace(
            "func_151C899C(NULL, *ownerHome);",
            "func_151C899C((void *)1, *ownerHome);", 1),
    }
    if len(variants) != 10 or any(value == body for value in variants.values()):
        raise AssertionError("An owner event-state control did not alter source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef signed int s32;
#define NULL ((void *)0)
''' + candidate.DECLARATIONS + "\n" + body + r'''
static u8 ownerData[0x220], eventData[8];
static s32 validateResult, validateCalls, actionCalls, failed;
static s32 expectedEvent, expectedAction;
static unsigned load32(const void *pointer) { return *(const unsigned *)pointer; }
static void store32(void *pointer, unsigned value) { *(unsigned *)pointer = value; }
s32 func_151C87E0(s32 eventValue, u8 *owner) {
    validateCalls++;
    if ((unsigned)eventValue != load32(eventData) || owner != ownerData) failed = 1;
    return validateResult;
}
s32 func_151C899C(s32 eventValue, u8 *owner) {
    actionCalls++;
    if ((unsigned)eventValue != (unsigned)expectedAction || owner != ownerData) failed = 2;
    return 0;
}
static s32 one(unsigned seed) {
    static const unsigned codes[] = {0,0x20,0x120,0x3A,0x13A,0xFF};
    static const unsigned selectors[] = {0,1,2,3,0xFF};
    unsigned code = codes[seed % 6], selector = selectors[(seed / 6) % 5];
    unsigned equal = (seed >> 3) & 1, gate = (seed >> 4) & 1;
    unsigned key = 0x10203040u + seed * 0x101u;
    unsigned event0 = key, word4 = key;
    unsigned index;
    for (index = 0; index < sizeof(ownerData); index++) ownerData[index] = (u8)(seed + index * 13u);
    for (index = 0; index < sizeof(eventData); index++) eventData[index] = (u8)(seed + index * 7u);
    ownerData[0x196] = gate ? 0x12 : 0;
    if ((code & 0xFFu) == 0x20u) {
        word4 = equal ? key : key ^ 0x01000001u;
    } else if ((code & 0xFFu) == 0x3Au) {
        event0 = equal ? key : key ^ 0x00010000u;
        word4 = selector << 24;
    }
    store32(ownerData + 0x138, key);
    store32(eventData, event0);
    store32(eventData + 4, word4);
    if ((code & 0xFFu) == 0x3Au) eventData[4] = (u8)selector;
    validateResult = (seed >> 5) & 1;
    validateCalls = actionCalls = failed = 0;
    expectedEvent = expectedAction = 0;
    if ((code & 0xFFu) == 0x20u && gate && equal) {
        expectedEvent = 1;
        if (validateResult) expectedAction = (s32)event0;
    } else if ((code & 0xFFu) == 0x3Au && equal && selector == 2u) {
        expectedAction = 0;
    }
    func_151C86AC(ownerData, eventData, (u8)code);
    if (failed) return 10 + failed;
    if (validateCalls != expectedEvent) return 20;
    if (actionCalls != (expectedAction != 0 ||
            (((code & 0xFFu) == 0x3Au) && equal && selector == 2u))) return 21;
    if ((code & 0xFFu) == 0x3Au && equal) {
        unsigned wanted = gate ? 0x12u : 0u;
        if (selector == 0u) wanted |= 2u;
        else if (selector == 1u) wanted &= 0xFDu;
        if (ownerData[0x196] != wanted) return 22;
    }
    return 0;
}
static s32 run(void) {
    unsigned seed;
    if (sizeof(void *) != 4) return 9;
    for (seed = 0; seed < 4096; seed++) {
        s32 result = one(seed);
        if (result) return result;
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
        "gcc", "-m32", "-std=gnu89", optimization, "-fno-pie", "-no-pie",
        "-ffreestanding", "-fno-strict-aliasing", "-fno-stack-protector",
        "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
        "-Wall", "-Wextra", "-Werror", "-nostdlib", str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if should_pass and executed.returncode != 0:
        raise AssertionError((label, executed.returncode, executed.stderr))
    if not should_pass and executed.returncode == 0:
        raise AssertionError((label, "semantic control passed"))


class GameOwnerEventStateDispatchMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.prepared = match.prepare(ROOT)
        cls.retail = list(struct.unpack_from(
            ">%dI" % match.WORDS,
            (ROOT / match.ROM_IMAGE).read_bytes(), match.ROM,
        ))
        cls.natural = cls.retail.copy()

    def receipt(self, name, data):
        (self.output / (name + ".json")).write_text(
            json.dumps(data, indent=2) + "\n")

    def test_01_direct_profile_owner_neighbors_and_strict_image(self):
        selected = candidate.compare("test-selected", candidate.SELECTED)
        self.assertEqual(
            (selected["words"], selected["frame"], selected["differences"]),
            (64, 0x18, 0),
        )
        self.assertEqual(selected["bindings"], {
            "0x068": [("R_MIPS_26", "func_151C87E0")],
            "0x07C": [("R_MIPS_26", "func_151C899C")],
            "0x0E8": [("R_MIPS_26", "func_151C899C")],
        })
        report = self.prepared["report"]
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(
            (report["guards"], report["neighbors"], report["strict_exclusions"]),
            (0, 45, 0),
        )
        self.assertTrue(report["all_addresses_fixed"])
        self.assertTrue(report["game_data"]["exact"])
        self.assertEqual(report["functions"], 6052)

    def test_02_guest_paths_low_byte_aliases_helpers_and_all_words(self):
        coverage = [set(), set()]
        corpus = cases()
        for case in corpus:
            initial = fixture(case)
            wanted, calls = reference(initial, case)
            for index, words in enumerate((self.retail, self.natural)):
                model = DispatchOracle(words, initial, case).run()
                self.assertEqual((public(model.memory), model.calls),
                                 (public(wanted), calls), case)
                coverage[index].update(model.visits)
        full = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4))
        unreachable = {0x151C8774}
        self.assertEqual(coverage[0], full - unreachable)
        self.assertEqual(coverage[1], full - unreachable)
        self.receipt("guest-contract", {
            "cases_per_body": len(corpus),
            "retail_words": len(coverage[0]),
            "natural_C_words": len(coverage[1]),
            "unreachable_retail_words": ["0x151c8774"],
            "event_code_low_byte_aliases": True,
            "helper_arguments": 2,
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

    def test_04_callback_registry_live_state_and_fault_boundaries(self):
        evidence = match.registry_evidence(ROOT)
        self.assertEqual(evidence["direct_jal_calls"], [])
        self.assertEqual(evidence["aligned_pointer_literals"], ["0x22ea30"])
        self.assertEqual(evidence["registry"], "D_80089F64[3]")
        predecessor, qualified, installed = match.source_states(
            (ROOT / match.SOURCE).read_text())
        self.assertEqual(installed, self.prepared["report"]["source_installed"])
        self.assertNotEqual(predecessor, qualified)
        states = []
        boundary_cases = [
            Case(0x20, 0x10, 7, 9, 7, True, 0, 1),
            Case(0x20, 0, 7, 9, 7, False, 8, 2),
            Case(0x3A, 0xFD, 7, 7, 0 << 24, False, 0, 3),
            Case(0x3A, 0xFF, 7, 7, 1 << 24, False, 8, 4),
            Case(0x3A, 0, 7, 7, 2 << 24, False, 0, 5),
        ]
        for words in (self.retail, self.natural):
            for case in boundary_cases:
                initial = fixture(case)
                baseline = DispatchOracle(words, initial, case).run()
                for cut in range(baseline.root_accesses):
                    model = DispatchOracle(words, initial, case, fault=cut)
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.root_accesses, cut)
                    states.append((model.current_pc, model.delay_of, cut))
        self.assertGreater(len(states), 30)
        self.receipt("callback-and-faults", {
            "registry": evidence["registry"],
            "fault_observations": len(states),
            "unique_boundaries": len(set(states)),
        })


if __name__ == "__main__":
    unittest.main()
