"""Semantic, callback, owner and strict-image gates for func_150C2700."""

from dataclasses import dataclass
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_effect_band_packet_callback_candidates as candidate
from tools.experiments import game_effect_band_packet_callback_match as match
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_frame_timing_oracle import STACK, TimingOracle
from tools.tests.test_game_point_transform_match import put, read


ROOT = Path(__file__).resolve().parents[2]
SUBMIT = 0x15150178
GLOBALS = (0x800A0274, 0x800A0278, 0x800A027C)
PATTERNS = (
    0x00000000, 0x80000000, 0x3F800000, 0xBF400000,
    0x7F800000, 0xFF800000, 0x7FC12345, 0xC2480000,
)


@dataclass(frozen=True)
class Case:
    x: int = 0x3F800000
    y: int = 0xC0200000
    z: int = 0x40400000
    parameter0: int = 0x3E800000
    parameter1: int = 0xBE000000
    parameter2: int = 0x41200000
    channel: int = 0xFF
    phase: int = 0
    seed: int = 0


def fixture(case=Case()):
    memory = {
        STACK + index: (index * 17 + case.seed * 23 + 0xA5) & 0xFF
        for index in range(-0x500, 0x180)
    }
    for address, value in zip(
            GLOBALS, (case.parameter0, case.parameter1, case.parameter2)):
        put(memory, address, value)
    return memory


def callback_arguments(case):
    unused = tuple(
        (case.seed * 0x9E3779B9 + index * 0x1020304 + 0x12345678) & 0xFFFFFFFF
        for index in range(11)
    )
    return (
        unused[0], unused[1], case.x, case.y, case.z,
        *unused[2:], case.channel & 0xFFFFFFFF,
    )


def packet_bytes(initial, case):
    stack = STACK + case.phase
    descriptor_address = stack - 0x48
    payload_address = stack - 0x40
    descriptor = {descriptor_address + index: initial[descriptor_address + index]
                  for index in range(8)}
    payload = {payload_address + index: initial[payload_address + index]
               for index in range(0x40)}
    for offset, value in ((0, 0x6B), (2, 0x46), (4, 0xFFE1), (6, 0x2E)):
        put(descriptor, descriptor_address + offset, value, 2)
    for offset, value, size in (
            (0x00, case.x, 4), (0x04, case.y, 4), (0x08, case.z, 4),
            (0x0C, 6, 2), (0x0E, 5, 2),
            (0x10, 0x41F00000, 4), (0x14, 0x420C0000, 4),
            (0x18, 100, 2), (0x1A, 0, 2),
            (0x1C, case.parameter0, 4), (0x20, case.parameter1, 4),
            (0x24, 0x9B, 1), (0x25, 100, 1),
            (0x28, case.parameter2, 4), (0x2C, 0, 4),
            (0x30, 1, 1), (0x31, 6, 1),
            (0x34, 0, 4), (0x38, 1, 1), (0x3C, 0, 4)):
        put(payload, payload_address + offset, value, size)
    return (
        descriptor_address,
        payload_address,
        bytes(descriptor[descriptor_address + index] for index in range(8)),
        bytes(payload[payload_address + index] for index in range(0x40)),
    )


def public(memory):
    return {
        address: value for address, value in memory.items()
        if not STACK - 0x500 <= address < STACK + 0x180
    }


class PacketOracle(TimingOracle):
    def __init__(self, words, memory, case=Case(), fault=None):
        super().__init__(
            words, memory, phase=case.phase, entry=match.ENTRY,
            arguments=callback_arguments(case),
        )
        self.case = case
        self.root_fault = fault
        self.snapshots = []

    def record_call(self, target):
        if target != SUBMIT:
            raise AssertionError("Unexpected effect-band helper %08X" % target)
        arguments = tuple(self.arguments(5))
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))
        self.snapshots.append((
            bytes(self.memory[arguments[0] + index] for index in range(8)),
            bytes(self.memory[arguments[1] + index] for index in range(0x40)),
        ))

    def hook(self, target):
        if target != SUBMIT:
            raise AssertionError("Unbounded effect-band helper %08X" % target)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678


def controls():
    body = candidate.SELECTED
    variants = {
        "wrong-kind": body.replace("kind = 0x6B", "kind = 0x6A", 1),
        "wrong-mode": body.replace("mode = 0x46", "mode = 0x45", 1),
        "wrong-offset": body.replace("offset = -0x1F", "offset = -0x1E", 1),
        "wrong-event": body.replace("eventCode = 0x2E", "eventCode = 0x2D", 1),
        "wrong-x": body.replace("payload.x = x", "payload.x = y", 1),
        "wrong-y": body.replace("payload.y = y", "payload.y = z", 1),
        "wrong-z": body.replace("payload.z = z", "payload.z = x", 1),
        "wrong-type": body.replace("payload.type = 6", "payload.type = 7", 1),
        "wrong-variant": body.replace("payload.variant = 5", "payload.variant = 4", 1),
        "wrong-width": body.replace("payload.width = 30.0f", "payload.width = 31.0f", 1),
        "wrong-height": body.replace("payload.height = 35.0f", "payload.height = 34.0f", 1),
        "wrong-lifetime": body.replace("payload.lifetime = 100", "payload.lifetime = 99", 1),
        "wrong-parameter": body.replace(
            "payload.parameter0 = D_800A0274",
            "payload.parameter0 = D_800A0278", 1),
        "wrong-opacity": body.replace("payload.opacity = 0x9B", "payload.opacity = 0x9A", 1),
        "wrong-class": body.replace("payload.classId = 6", "payload.classId = 5", 1),
        "negative-zero": body.replace("payload.velocity = 0.0f", "payload.velocity = -0.0f", 1),
        "wrong-channel": body.replace(
            "&locals.payload, 0, channel, 1",
            "&locals.payload, 0, (u8)(channel + 1), 1", 1),
        "wrong-return": body.replace("return 1;", "return 0;", 1),
    }
    if len(variants) != 18 or any(value == body for value in variants.values()):
        raise AssertionError("An effect-band packet control did not alter source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef signed short s16;
typedef signed int s32;
typedef unsigned int u32;
typedef float f32;
''' + candidate.DECLARATIONS + r'''
f32 D_800A0274;
f32 D_800A0278;
f32 D_800A027C;
static u32 wantedX, wantedY, wantedZ, wanted0, wanted1, wanted2;
static u32 calls, failed;
static u8 wantedChannel;
static u32 word(const f32 *value) { return *(const u32 *)value; }
void func_15150178(EffectBandDescriptor150C2700 *descriptor,
        EffectBandPayload150C2700 *payload, s32 zero, u8 channel, s32 one) {
    calls++;
    if (descriptor->kind != 0x6B || descriptor->mode != 0x46 ||
        descriptor->offset != -0x1F || descriptor->eventCode != 0x2E ||
        word(&payload->x) != wantedX || word(&payload->y) != wantedY ||
        word(&payload->z) != wantedZ || payload->type != 6 ||
        payload->variant != 5 || word(&payload->width) != 0x41F00000u ||
        word(&payload->height) != 0x420C0000u || payload->lifetime != 100 ||
        payload->zero != 0 || word(&payload->parameter0) != wanted0 ||
        word(&payload->parameter1) != wanted1 || payload->opacity != 0x9B ||
        payload->scale != 100 || word(&payload->parameter2) != wanted2 ||
        word(&payload->velocity) != 0 || payload->active != 1 ||
        payload->classId != 6 || word(&payload->acceleration) != 0 ||
        payload->loop != 1 || word(&payload->phase) != 0 || zero != 0 ||
        channel != wantedChannel || one != 1)
        failed = 1;
}
''' + body + r'''
static void set_word(f32 *value, u32 bits) { *(u32 *)value = bits; }
static int one(u32 seed) {
    static const u32 patterns[8] = {0, 0x80000000u, 0x3F800000u,
        0xBF400000u, 0x7F800000u, 0xFF800000u, 0x7FC12345u, 0xC2480000u};
    f32 x, y, z;
    s32 result;
    wantedX = patterns[seed & 7u];
    wantedY = patterns[(seed + 3u) & 7u];
    wantedZ = patterns[(seed + 5u) & 7u];
    wanted0 = patterns[(seed + 1u) & 7u];
    wanted1 = patterns[(seed + 2u) & 7u];
    wanted2 = patterns[(seed + 6u) & 7u];
    set_word(&x, wantedX); set_word(&y, wantedY); set_word(&z, wantedZ);
    set_word(&D_800A0274, wanted0); set_word(&D_800A0278, wanted1);
    set_word(&D_800A027C, wanted2);
    wantedChannel = (u8)(seed * 37u + 0xA5u);
    calls = failed = 0;
    result = func_150C2700((void *)(seed | 1u), (s32)(seed * 3u), x, y, z,
        (s32)(seed + 5u), (s32)(seed + 6u), (s32)(seed + 7u),
        (s32)(seed + 8u), (s32)(seed + 9u), (s32)(seed + 10u),
        (s32)(seed + 11u), (s32)(seed + 12u), (s32)(seed + 13u),
        wantedChannel);
    return failed || calls != 1 || result != 1;
}
static int run(void) {
    u32 seed;
    if (sizeof(void *) != 4 || sizeof(EffectBandDescriptor150C2700) != 8 ||
        sizeof(EffectBandPayload150C2700) != 0x40 ||
        sizeof(EffectBandLocals150C2700) != 0x48 ||
        __builtin_offsetof(EffectBandPayload150C2700, type) != 0x0C ||
        __builtin_offsetof(EffectBandPayload150C2700, parameter0) != 0x1C ||
        __builtin_offsetof(EffectBandPayload150C2700, parameter2) != 0x28 ||
        __builtin_offsetof(EffectBandPayload150C2700, phase) != 0x3C)
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
        "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
        "-nostdlib", str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if should_pass and executed.returncode != 0:
        raise AssertionError((label, executed.returncode, executed.stderr))
    if not should_pass and executed.returncode == 0:
        raise AssertionError((label, "semantic control passed"))


class GameEffectBandPacketCallbackMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.prepared = match.prepare(ROOT)
        cls.retail = list(struct.unpack_from(
            ">%dI" % match.WORDS,
            (ROOT / match.ROM_IMAGE).read_bytes(), match.ROM,
        ))
        candidate.compare("test-selected", candidate.SELECTED, ("-O2", "-g3"))
        compact = ROOT / candidate.BUILD / "test-selected.o"
        linked, functions = link_owner(ROOT, cls.output, compact, candidate.OWNER)
        info = functions[match.FUNCTION]
        cls.natural = list(struct.unpack_from(
            ">66I", linked, info["value"]
        ))

    def receipt(self, name, data):
        (self.output / (name + ".json")).write_text(
            json.dumps(data, indent=2) + "\n"
        )

    def test_01_guarded_profile_owner_neighbors_and_strict_image(self):
        selected = json.loads(
            (ROOT / candidate.BUILD / "measurements.json").read_text()
        )[0]
        self.assertEqual(
            (selected["words"], selected["frame"], selected["differences"]),
            (66, 0x68, 50),
        )
        self.assertEqual(selected["object_raw_sha256"], match.RAW_SHA256)
        report = self.prepared["report"]
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(
            (report["guards"], report["neighbors"], report["strict_exclusions"]),
            (24, 17, 0),
        )
        self.assertEqual((report["natural_words"], report["retail_words"]),
                         (66, 65))
        self.assertEqual(report["omissions"], 1)
        self.assertTrue(report["all_addresses_fixed"])
        self.assertTrue(report["game_data"]["exact"])
        self.assertEqual(report["functions"], 6052)
        self.assertEqual(match.registry_evidence(ROOT)["registry"],
                         "D_8008AA00[3]")

    def test_02_guest_packet_abi_reserved_bytes_and_all_words(self):
        cases = []
        for seed, values in enumerate(itertools.product(
                range(8), (0, 1, 0xFF, 0x12345678), (0, 8))):
            pattern, channel, phase = values
            cases.append(Case(
                PATTERNS[pattern], PATTERNS[(pattern + 3) & 7],
                PATTERNS[(pattern + 5) & 7],
                PATTERNS[(pattern + 1) & 7],
                PATTERNS[(pattern + 2) & 7],
                PATTERNS[(pattern + 6) & 7], channel, phase, seed,
            ))
        coverage = [set(), set()]
        for case in cases:
            initial = fixture(case)
            descriptor, payload, descriptor_bytes, payload_bytes = packet_bytes(
                initial, case
            )
            for index, words in enumerate((self.retail, self.natural)):
                model = PacketOracle(words, initial, case).run()
                self.assertEqual(public(model.memory), public(initial), case)
                self.assertEqual(model.calls, [(
                    SUBMIT,
                    (descriptor, payload, 0, case.channel & 0xFF, 1),
                )], case)
                self.assertEqual(model.snapshots,
                                 [(descriptor_bytes, payload_bytes)], case)
                self.assertEqual(model.r[2], 1, case)
                coverage[index].update(model.visits)
        self.assertEqual(
            coverage[0], set(range(match.ENTRY, match.ENTRY + match.SIZE, 4))
        )
        self.assertEqual(
            coverage[1], set(range(match.ENTRY, match.ENTRY + 66 * 4, 4))
        )
        self.receipt("guest-contract", {
            "cases_per_body": len(cases),
            "retail_words": len(coverage[0]),
            "natural_C_words": len(coverage[1]),
            "helper_calls_per_case": 1,
            "channel_stack_argument": 14,
            "reserved_payload_bytes_preserved": [
                "0x26..0x27", "0x32..0x33", "0x39..0x3B",
            ],
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

    def test_04_callback_registry_and_fault_boundaries(self):
        evidence = match.registry_evidence(ROOT)
        self.assertEqual(evidence["direct_jal_calls"], [])
        self.assertEqual(evidence["aligned_pointer_literals"], ["0x22f4cc"])
        states = []
        case = Case(
            0x7FC12345, 0x80000000, 0x7F800000,
            0x3E800000, 0xBE000000, 0x41200000,
            0x12345678, 8, 19,
        )
        for words in (self.retail, self.natural):
            initial = fixture(case)
            baseline = PacketOracle(words, initial, case).run()
            for cut in range(baseline.root_accesses):
                model = PacketOracle(words, initial, case, fault=cut)
                with self.assertRaises(faults.AccessBoundary):
                    model.run()
                self.assertEqual(model.root_accesses, cut)
                states.append((model.current_pc, model.delay_of, cut))
        self.assertGreater(len(states), 40)
        self.receipt("registry-and-faults", {
            "registry": evidence["registry"],
            "fault_observations": len(states),
            "unique_boundaries": len(set(states)),
        })


if __name__ == "__main__":
    unittest.main()
