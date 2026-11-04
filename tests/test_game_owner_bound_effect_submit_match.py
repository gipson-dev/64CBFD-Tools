"""Semantic, callback, owner and strict-image gates for func_1519E464."""

from dataclasses import dataclass
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_owner_bound_effect_submit_candidates as candidate
from tools.experiments import game_owner_bound_effect_submit_match as match
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_frame_timing_oracle import STACK, TimingOracle
from tools.tests.test_game_point_transform_match import put, read


ROOT = Path(__file__).resolve().parents[2]
RECORD = 0x22000
OWNER = 0x24000
MATRICES = 0x28000
ATTACH_ROOT = 0x2A000
EFFECT = 0x2C000
BUILD_EFFECT = 0x1519D030
ATTACH_EFFECT = 0x1514ED3C
LINK_EFFECT = 0x1514EC1C


@dataclass(frozen=True)
class Case:
    live: bool = True
    same_identity: bool = True
    matrices: bool = True
    effect: bool = True
    attach: bool = True
    duration: int = 300
    flags: int = 0xA4
    slot: int = 0x56
    context: int = 0x78
    preset: int = 0x12345678
    phase: int = 0
    seed: int = 0


def signed16(value):
    value &= 0xFFFF
    return value if value < 0x8000 else value - 0x10000


def fixture(case=Case()):
    memory = {
        STACK + index: (index * 17 + case.seed + 0xA5) & 0xFF
        for index in range(-0x300, 0x100)
    }
    memory.update({
        RECORD - 0x20 + index: (index * 13 + case.seed * 19 + 0x59) & 0xFF
        for index in range(0x90)
    })
    memory.update({
        OWNER + index: (index * 7 + case.seed * 11 + 0x31) & 0xFF
        for index in range(0x300)
    })
    identity = (case.seed * 29 + 0x6B) & 0xFF
    put(memory, OWNER, 0x13579BDF if case.live else 0)
    memory[OWNER + 0x3B] = identity
    put(memory, OWNER + 0x1D4, MATRICES if case.matrices else 0)
    put(memory, OWNER + 0x2F4, ATTACH_ROOT)
    put(memory, RECORD + 0x28, OWNER)
    memory[RECORD + 0x2C] = identity if case.same_identity else identity ^ 0xFF
    put(memory, RECORD + 0x30, case.preset)
    memory[RECORD + 1] = case.context & 0xFF
    memory[RECORD + 0xC] = case.slot & 0xFF
    memory[RECORD + 0xD] = case.flags & 0xFF
    put(memory, RECORD + 0xE, case.duration, 2)
    return memory


def public(memory):
    return {
        address: value for address, value in memory.items()
        if not STACK - 0x300 <= address < STACK + 0x100
    }


def reference(initial, case):
    memory = dict(initial)
    retire = not case.live or not case.same_identity
    calls = []
    if not retire and case.matrices:
        calls.append((BUILD_EFFECT, (
            OWNER,
            case.preset & 0xFFFFFFFF,
            signed16(case.duration) & 0xFFFFFFFF,
            case.flags & 1,
            case.slot & 0xFF,
            case.context & 0xFF,
        )))
        retire = True
        if case.effect:
            calls.append((ATTACH_EFFECT, (ATTACH_ROOT, RECORD, 0)))
            if case.attach:
                calls.append((LINK_EFFECT, (EFFECT, OWNER, 0x10, EFFECT)))
    if retire:
        put(memory, RECORD + 0xE, 0xFFFF, 2)
        memory[RECORD + 0xD] |= 1
    return memory, calls


class OwnerBoundEffectOracle(TimingOracle):
    def __init__(self, words, memory, case=Case(), fault=None):
        super().__init__(
            words,
            memory,
            phase=case.phase,
            entry=match.ENTRY,
            arguments=(RECORD,),
        )
        self.case = case
        self.root_fault = fault

    def record_call(self, target):
        counts = {BUILD_EFFECT: 6, ATTACH_EFFECT: 3, LINK_EFFECT: 4}
        if target not in counts:
            raise AssertionError("Unexpected owner-bound helper %08X" % target)
        arguments = tuple(self.arguments(counts[target]))
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))

    def hook(self, target):
        if target not in (BUILD_EFFECT, ATTACH_EFFECT, LINK_EFFECT):
            raise AssertionError("Unbounded owner-bound helper %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678
        if target == BUILD_EFFECT:
            self.r[2] = EFFECT if self.case.effect else 0
        elif target == ATTACH_EFFECT:
            self.r[2] = 1 if self.case.attach else 0
        else:
            self.r[2] = 0xA5000002


def controls():
    body = candidate.SELECTED
    variants = {
        "inverted-live": body.replace(
            "*(s32 *)record->payload.owner == 0",
            "*(s32 *)record->payload.owner != 0", 1),
        "wrong-identity": body.replace("owner[0x3B]", "owner[0x3A]", 1),
        "wrong-matrix": body.replace("owner + 0x1D4", "owner + 0x1D0", 1),
        "wrong-preset": body.replace("payload->preset,", "payload->preset + 1,", 1),
        "wrong-duration": body.replace("record->duration,", "record->duration + 1,", 1),
        "wrong-flag-mask": body.replace("maskedFlags & 1,", "maskedFlags & 2,", 1),
        "wrong-slot": body.replace(
            "record->slot, record->context", "record->context, record->context", 1),
        "wrong-attachment": body.replace("+ 0x2F4", "+ 0x2F0", 1),
        "inverted-attach": body.replace(") != 0) {", ") == 0) {", 1),
        "wrong-link-mode": body.replace(", 0x10, effect);", ", 0x11, effect);", 1),
        "wrong-retired-duration": body.replace("record->duration = -1;", "record->duration = 0;", 1),
        "wrong-retired-flag": body.replace("record->flags |= 1;", "record->flags |= 2;", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("An owner-bound effect control did not alter source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef signed short s16;
typedef signed int s32;
typedef unsigned int u32;
#define NULL ((void *)0)
''' + candidate.TYPES + candidate.INSTALL_DECLARATIONS + r'''
static OwnerEffectRecord1519E464 actual, expected;
static u8 owner[0x300], ownerBefore[0x300], matrices[0x40], attachRoot[4], effect[4];
static u32 buildCalls, attachCalls, linkCalls, error;
static u32 returnEffect, returnAttach;
static s32 wantedPreset, wantedDuration;
static u32 wantedFlag, wantedSlot, wantedContext;
s32 func_1519D030(u8 *argOwner, s32 preset, s16 duration, s32 flag,
                  u32 slot, u32 context) {
    buildCalls++;
    if (argOwner != owner || preset != wantedPreset || duration != wantedDuration ||
        (u32)flag != wantedFlag || slot != wantedSlot || context != wantedContext)
        error = 1;
    return returnEffect ? (s32)(u32)effect : 0;
}
s32 func_1514ED3C(u8 *root, u8 *record, s32 zero) {
    attachCalls++;
    if (root != attachRoot || record != (u8 *)&actual || zero != 0) error = 1;
    return returnAttach;
}
s32 func_1514EC1C(u8 *argEffect, u8 *argOwner, s32 mode, u8 *again) {
    linkCalls++;
    if (argEffect != effect || argOwner != owner || mode != 0x10 || again != effect)
        error = 1;
    return 0;
}
''' + body + r'''
static void store32(u8 *bytes, u32 offset, u32 value) {
    *(u32 *)(bytes + offset) = value;
}
static int one(u32 seed) {
    u8 *recordBytes = (u8 *)&actual;
    u8 *expectedBytes = (u8 *)&expected;
    u32 index, live, same, haveMatrices, wantEffect, wantAttach, retire;
    for (index = 0; index < sizeof(actual); index++)
        recordBytes[index] = (u8)(seed * 19u + index * 13u + 0x59u);
    for (index = 0; index < sizeof(owner); index++)
        owner[index] = (u8)(seed * 11u + index * 7u + 0x31u);
    live = seed & 1; same = (seed >> 1) & 1; haveMatrices = (seed >> 2) & 1;
    wantEffect = (seed >> 3) & 1; wantAttach = (seed >> 4) & 1;
    store32(owner, 0, live ? 0x13579BDFu : 0);
    owner[0x3B] = (u8)(seed * 29u + 0x6Bu);
    store32(owner, 0x1D4, haveMatrices ? (u32)matrices : 0);
    store32(owner, 0x2F4, (u32)attachRoot);
    actual.payload.owner = owner;
    actual.payload.identity = same ? owner[0x3B] : (u8)(owner[0x3B] ^ 0xFF);
    actual.payload.preset = (s32)(seed * 0x9E3779B9u + 0x12345678u);
    actual.duration = (s16)(seed * 257u + 0x8001u);
    actual.flags = (u8)(seed * 37u + 0xA4u);
    actual.slot = (u8)(seed * 41u + 0x56u);
    actual.context = (u8)(seed * 43u + 0x78u);
    expected = actual;
    for (index = 0; index < sizeof(owner); index++) ownerBefore[index] = owner[index];
    wantedPreset = actual.payload.preset; wantedDuration = actual.duration;
    wantedFlag = actual.flags & 1; wantedSlot = actual.slot; wantedContext = actual.context;
    returnEffect = wantEffect; returnAttach = wantAttach;
    buildCalls = attachCalls = linkCalls = error = 0;
    retire = !live || !same;
    if (!retire && haveMatrices) {
        buildCalls = 0; retire = 1;
        if (wantEffect) { attachCalls = 0; if (wantAttach) linkCalls = 0; }
    }
    func_1519E464(&actual);
    if (retire) { expected.duration = -1; expected.flags |= 1; }
    if (error) return 1;
    if (buildCalls != ((!live || !same || !haveMatrices) ? 0u : 1u)) return 2;
    if (attachCalls != ((!live || !same || !haveMatrices || !wantEffect) ? 0u : 1u)) return 3;
    if (linkCalls != ((!live || !same || !haveMatrices || !wantEffect || !wantAttach) ? 0u : 1u)) return 4;
    for (index = 0; index < sizeof(actual); index++)
        if (recordBytes[index] != expectedBytes[index]) return 5;
    for (index = 0; index < sizeof(owner); index++)
        if (owner[index] != ownerBefore[index]) return 6;
    return 0;
}
static int run(void) {
    u32 seed;
    if (sizeof(void *) != 4 || sizeof(OwnerEffectPayload1519E464) != 12 ||
        sizeof(OwnerEffectRecord1519E464) != 52 ||
        __builtin_offsetof(OwnerEffectRecord1519E464, context) != 1 ||
        __builtin_offsetof(OwnerEffectRecord1519E464, slot) != 12 ||
        __builtin_offsetof(OwnerEffectRecord1519E464, duration) != 14 ||
        __builtin_offsetof(OwnerEffectRecord1519E464, payload) != 40)
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


class GameOwnerBoundEffectSubmitMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.prepared = match.prepare(ROOT)
        cls.retail = list(struct.unpack_from(
            ">%dI" % match.WORDS,
            (ROOT / match.ROM_IMAGE).read_bytes(), match.ROM,
        ))
        linked, functions = link_owner(
            ROOT, cls.output, cls.prepared["qualified_compact"], candidate.OWNER
        )
        info = functions[match.FUNCTION]
        cls.natural = list(struct.unpack_from(
            ">%dI" % match.WORDS, linked, info["value"]
        ))

    def receipt(self, name, data):
        (self.output / (name + ".json")).write_text(
            json.dumps(data, indent=2) + "\n"
        )

    def test_01_guarded_profile_owner_neighbors_and_strict_image(self):
        selected = candidate.compare("test-selected", candidate.SELECTED, ("-O2", "-g3"))
        self.assertEqual(
            (selected["words"], selected["frame"], selected["differences"]),
            (67, 0x40, 28),
        )
        self.assertEqual(selected["bindings"], {
            "0x080": [("R_MIPS_26", "func_1519D030")],
            "0x0AC": [("R_MIPS_26", "func_1514ED3C")],
            "0x0D0": [("R_MIPS_26", "func_1514EC1C")],
        })
        report = self.prepared["report"]
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(
            (report["guards"], report["neighbors"], report["strict_exclusions"]),
            (28, 22, 0),
        )
        self.assertTrue(report["all_addresses_fixed"])
        self.assertTrue(report["game_data"]["exact"])
        self.assertEqual(len({row["offset"] for row in match.PATCH_ROWS}), 28)
        self.assertEqual(self.prepared["report"]["registry"]["registry"], "D_8008A4E8[8]")

    def test_02_guest_validity_retry_submit_attach_and_all_words(self):
        cases = []
        for seed, values in enumerate(itertools.product(
                (False, True), (False, True), (False, True),
                (False, True), (False, True), (0, 8))):
            live, same, matrices, effect, attach, phase = values
            cases.append(Case(
                live=live, same_identity=same, matrices=matrices,
                effect=effect, attach=attach,
                duration=(seed * 257 + 0x8001) & 0xFFFF,
                flags=(seed * 37 + 0xA4) & 0xFF,
                slot=(seed * 41 + 0x56) & 0xFF,
                context=(seed * 43 + 0x78) & 0xFF,
                preset=(seed * 0x9E3779B9 + 0x12345678) & 0xFFFFFFFF,
                phase=phase, seed=seed,
            ))
        coverage = [set(), set()]
        helper_calls = 0
        for case in cases:
            initial = fixture(case)
            wanted, calls = reference(initial, case)
            helper_calls += len(calls)
            for index, words in enumerate((self.retail, self.natural)):
                model = OwnerBoundEffectOracle(words, initial, case).run()
                self.assertEqual(
                    (public(model.memory), model.calls),
                    (public(wanted), calls), case,
                )
                coverage[index].update(model.visits)
        full = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4))
        self.assertEqual(coverage[0], full)
        self.assertEqual(coverage[1], full)
        self.receipt("guest-contract", {
            "cases": len(cases), "retail_words": len(coverage[0]),
            "natural_C_words": len(coverage[1]), "helper_calls": helper_calls,
            "callback_clobber": True, "retry_without_matrix": True,
        })

    def test_03_native_profiles_and_effective_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED,
                       optimization, True)
        variants = controls()
        for label, body in variants.items():
            run_native("control-" + label, body, "-O2", False)
        self.receipt("native-contract", {
            "profiles": ["O0", "O2", "O3"], "cases_per_profile": 4096,
            "controls": sorted(variants), "actual_32_bit_C": True,
        })

    def test_04_callback_census_and_active_root_fault_boundaries(self):
        evidence = match.registry_evidence(ROOT)
        self.assertEqual(evidence["direct_jal_calls"], [])
        self.assertEqual(evidence["aligned_pointer_literals"], ["0x22efc8"])
        cases = (
            Case(live=False),
            Case(same_identity=False),
            Case(matrices=False),
            Case(effect=False),
            Case(attach=False),
            Case(duration=0x8000, flags=0xFF, slot=0, context=0xFF),
        )
        states = []
        for words in (self.retail, self.natural):
            for case in cases:
                initial = fixture(case)
                baseline = OwnerBoundEffectOracle(words, initial, case).run()
                for cut in range(baseline.root_accesses):
                    model = OwnerBoundEffectOracle(words, initial, case, fault=cut)
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.root_accesses, cut)
                    states.append((model.current_pc, model.delay_of, cut))
        self.assertGreater(len(states), 30)
        self.receipt("callback-and-faults", {
            "registry": evidence["registry"],
            "pointer": evidence["aligned_pointer_literals"],
            "fault_observations": len(states),
            "unique_boundaries": len(set(states)),
        })


if __name__ == "__main__":
    unittest.main()
