"""ABI, semantics, owner and image gates for func_150E4010."""

from dataclasses import dataclass
import itertools
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_direction_submission_match as match
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
ACTOR = 0x30000
ANGLE = 0x150484A0
SUBMIT = 0x1505D1C4
SCALE = 0x800A1050


@dataclass(frozen=True)
class Case:
    enabled: bool = True
    angle: int = bits(90.0)
    scale: int = bits(182.04444885253906)
    mutate: bool = False
    phase: int = 0
    fcsr: int = 0
    seed: int = 0


def u32(value):
    return value & 0xFFFFFFFF


def fields(case, late=False):
    seed = case.seed + (97 if late else 0)
    return {
        0x30: 0x3F000000 ^ seed,
        0x34: 0xBF800000 ^ (seed * 3),
        0x38: 0x41200000 ^ (seed * 5),
        0x60: 0x3E800000 ^ (seed * 7),
        0x64: 0xC0200000 ^ (seed * 11),
        0xA4: ((0x12000001 ^ (seed * 13)) if late else
               (0x12000001 ^ (case.seed * 13)) if case.enabled else 0),
    }


def fixture(case):
    memory = {STACK + case.phase + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x300, 0x100)}
    memory.update({ACTOR + index: (index * 29 + case.seed * 11 + 0x59) & 0xFF
                   for index in range(0x200)})
    for offset, value in fields(case).items():
        put(memory, ACTOR + 0x110 + offset, value)
    put(memory, SCALE, case.scale)
    return memory


def mutate_actor(memory, case):
    for offset, value in fields(case, True).items():
        put(memory, ACTOR + 0x110 + offset, value)


def converted_argument(angle, scale):
    product = floating(bits(floating(angle) * floating(scale)))
    if math.isfinite(product) and 0.0 <= product < 4294967296.0:
        converted = math.trunc(product)
    else:
        converted = 0xFFFFFFFF
    return u32(((converted & 0xFFFF) - 0x4000) | 1)


def expected_calls(case):
    if not case.enabled:
        return []
    first = fields(case)
    live = fields(case, True) if case.mutate else first
    return [
        (ANGLE, (first[0x60], first[0x64])),
        (SUBMIT, (live[0x30], live[0x34], live[0x38],
                  live[0xA4] | 0x60000, 0xFFFFFFFF,
                  converted_argument(case.angle, case.scale), 0, 0)),
    ]


class DirectionOracle(AreaOracle):
    def __init__(self, words, memory, case):
        super().__init__(words, memory, (ACTOR,), phase=case.phase,
                         fcsr=case.fcsr, entry=match.ENTRY)
        self.case = case

    def record_call(self, target):
        if target == ANGLE:
            arguments = (self.f[12], self.f[14])
        elif target == SUBMIT:
            arguments = (self.f[12], self.f[14], self.r[6], self.r[7],
                         *(read(self.memory, self.r[29] + offset)
                           for offset in range(0x10, 0x20, 4)))
        else:
            raise AssertionError("Unexpected direction-submission call %08X" % target)
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))

    def hook(self, target):
        if target == ANGLE and self.case.mutate:
            mutate_actor(self.memory, self.case)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        if target == ANGLE:
            self.f[0] = self.case.angle


def native_harness(body):
    return r'''
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
extern f32 D_800A1050;
f32 func_150484A0(f32, f32);
void func_1505D1C4(f32, f32, f32, s32, s32, u16, s32, s32);
''' + body + r'''
f32 D_800A1050;
static f32 angle_value;
static u32 wanted_x, wanted_y, wanted_z, wanted_a, wanted_b, wanted_flags;
static u32 wanted_angle, calls, error;
static u32 word(f32 value) { union { f32 f; u32 u; } v; v.f = value; return v.u; }
__attribute__((noinline,noclone)) f32 func_150484A0(f32 a, f32 b) {
    calls++;
    if (calls != 1 || word(a) != wanted_a || word(b) != wanted_b) error = 1;
    return angle_value;
}
__attribute__((noinline,noclone)) void func_1505D1C4(
        f32 x, f32 y, f32 z, s32 flags, s32 owner, u16 direction,
        s32 sixth, s32 seventh) {
    calls++;
    if (calls != 2 || word(x) != wanted_x || word(y) != wanted_y ||
            word(z) != wanted_z || (u32)flags != wanted_flags || owner != -1 ||
            direction != (u16)wanted_angle || sixth != 0 || seventh != 0) error = 1;
}
static void store(u8 *base, u32 offset, u32 value) { *(u32 *)(base + offset) = value; }
static int run(void) {
    union { u32 align; u8 bytes[0x300]; } storage;
    static const f32 angles[] = {0.0f, 1.0f, 123.5f, 1048576.0f,
        2147483520.0f, 3000000000.0f, 4294967040.0f};
    u8 *actor = storage.bytes;
    u32 n, i;
    for (n = 0; n < 4096; n++) {
        for (i = 0; i < sizeof(storage.bytes); i++) actor[i] = (u8)(n + i * 17);
        wanted_x = 0x3F000000u ^ n;
        wanted_y = 0xBF800000u ^ (n * 3u);
        wanted_z = 0x41200000u ^ (n * 5u);
        wanted_a = 0x3E800000u ^ (n * 7u);
        wanted_b = 0xC0200000u ^ (n * 11u);
        wanted_flags = ((n & 15u) ? (0x12000001u ^ (n * 13u)) : 0u) | 0x60000u;
        store(actor, 0x140, wanted_x); store(actor, 0x144, wanted_y);
        store(actor, 0x148, wanted_z); store(actor, 0x170, wanted_a);
        store(actor, 0x174, wanted_b);
        store(actor, 0x1B4, (n & 15u) ? (0x12000001u ^ (n * 13u)) : 0u);
        angle_value = angles[n % (sizeof(angles) / sizeof(angles[0]))];
        D_800A1050 = 1.0f;
        wanted_angle = ((((u32)(angle_value * D_800A1050)) & 0xFFFFu) - 0x4000u) | 1u;
        calls = error = 0;
        func_150E4010(actor);
        if (n & 15u) {
            if (calls != 2 || error) return 10;
        } else if (calls != 0 || error) return 11;
    }
    return 0;
}
''' + START


def controls():
    selected = match.SELECTED
    return {
        "wrong_enable_field": selected.replace("0x1B4", "0x1B0", 1),
        "wrong_x_field": selected.replace("extension + 0x30", "extension + 0x34", 1),
        "wrong_flags": selected.replace("0x60000", "0x40000", 1),
        "wrong_owner": selected.replace("                      -1,", "                      0,", 1),
        "wrong_mask": selected.replace("& 0xFFFF", "& 0x7FFF", 1),
        "wrong_bias": selected.replace("- 0x4000", "- 0x2000", 1),
        "wrong_odd_bit": selected.replace(") | 1,", ") | 2,", 1),
        "wrong_tail": selected.replace("                      0, 0);", "                      1, 0);")
    }


class ActorDirectionSubmissionTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.out = ROOT / match.BUILD
        cls.report, cls.before_owner, cls.after_owner, cls.before_elf, cls.after_elf = match.prepare(ROOT)
        image = cls.after_elf.read_bytes()
        at = elf_slot_offset(image, match.ENTRY, match.SIZE)
        cls.words = struct.unpack_from(">%dI" % match.WORDS, image, at)
        cls.retail = struct.unpack_from(">%dI" % match.WORDS,
                                        (ROOT / match.ROM_IMAGE).read_bytes(), match.ROM)
        cls.fresh = cls.out / ("test-run-" + str(os.getpid()))
        cls.fresh.mkdir(exist_ok=False)

    @classmethod
    def tearDownClass(cls):
        (cls.out / ("test-receipt-" + str(os.getpid()) + ".json")).write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_direct_owner_image_and_registry_closure(self):
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.report["words"], self.report["frame"],
                          self.report["natural_positional_differences"],
                          self.report["guards"], self.report["relocations"]),
                         (67, 56, 0, 0, 4))
        self.assertEqual(self.report["neighbors"], 12)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(self.report["registry"]["aligned_pointers"], [hex(match.TABLE_ROM)])
        self.assertEqual(self.report["registry"]["direct_jal_calls"], 0)
        self.assertEqual((self.report["strict_exclusions"],
                          self.report["game_data"]["different_bytes"]), (0, 0))
        self.receipt["closure"] = self.report

    def test_02_guest_calls_unsigned_conversion_and_word_coverage(self):
        angle_values = (bits(0.0), bits(1.0), bits(16384.5), bits(2147483520.0),
                        bits(3000000000.0), bits(4294967040.0), bits(-1.0),
                        0x7FC12345)
        seen = set()
        cases = 0
        for enabled, angle, mutate, phase, fcsr, seed in itertools.product(
                (False, True), angle_values, (False, True), (0, 8),
                (0, 3, 0xA5A50003), (0, 19)):
            case = Case(enabled, angle, bits(1.0), mutate, phase, fcsr, seed)
            initial = fixture(case)
            model = DirectionOracle(self.words, initial, case).run()
            self.assertEqual(model.calls, expected_calls(case), case)
            self.assertEqual(model.fcsr, case.fcsr)
            if mutate and enabled:
                for offset, value in fields(case, True).items():
                    self.assertEqual(read(model.memory, ACTOR + 0x110 + offset), value)
            seen.update(pc for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            cases += 1
        missing = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - seen
        # +0xCC is the compiler's duplicate mfc1 immediately after an
        # unconditional branch; no control-flow edge can reach it.
        self.assertEqual(missing, {match.ENTRY + 0xCC})
        self.receipt["guest"] = {
            "cases": cases, "covered_words": len(seen),
            "unreachable_compiler_words": ["+0xCC"], "stack_phases": 2,
            "incoming_FCSR_states": 3, "helper_mutation_modes": 2,
            "unsigned_conversion_paths": 4, "all_packet_arguments": True,
        }

    def test_03_native32_defined_domain_and_compiled_controls(self):
        selected = self.fresh / "native-selected.c"
        selected.write_text(native_harness(match.SELECTED))
        rows = []
        for profile in ("-O0", "-O2", "-O3"):
            target = self.fresh / ("native-selected" + profile)
            build = subprocess.run(
                native_command(profile) + ["-fno-strict-aliasing", str(selected), "-o", str(target)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(target)], capture_output=True)
            self.assertEqual(run.returncode, 0, (profile, run.stdout, run.stderr))
            rows.append({"profile": profile, "cases": 4096, "UBSan_trap": True})
        effective = []
        for name, body in controls().items():
            source = self.fresh / ("control-" + name + ".c")
            target = self.fresh / ("control-" + name)
            source.write_text(native_harness(body))
            build = subprocess.run(
                native_command("-O2", valid=False) + ["-fno-strict-aliasing", str(source), "-o", str(target)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, (name, build.stdout, build.stderr))
            run = subprocess.run([str(target)], capture_output=True)
            self.assertNotEqual(run.returncode, 0, name)
            effective.append(name)
        self.receipt["native"] = {"profiles": rows, "effective_controls": effective}

    def test_04_payload_and_complete_image_reject_stale_inputs(self):
        raw, bindings = match.payload(
            self.out / "qualified-compact.o", match.FUNCTION)
        match.checked_candidate(ROOT, self.out / "qualified-compact.o")
        with self.assertRaises(ValueError):
            match.checked_candidate(ROOT, self.out / "predecessor-compact.o")
        before = self.before_elf.read_bytes()
        retail = match.retail_bytes(ROOT)
        expected = match.expected_image(before, retail)
        self.assertEqual(expected, self.after_elf.read_bytes())
        positions = [elf_slot_offset(before, match.ENTRY, match.SIZE),
                     next(at for at, name, _, _ in match.symbol_rows(before)
                          if name == match.FUNCTION) + 8,
                     next(at for at, name, _, _ in match.symbol_rows(before)
                          if name == "D_800A1050"),
                     next(string_at for _, name, _, string_at in match.symbol_rows(before)
                          if name == "D_800A1050")]
        for position in positions:
            bad = bytearray(expected)
            bad[position] ^= 1
            with self.assertRaises(ValueError):
                match.check_image(before, bytes(bad), retail)
        with self.assertRaises(ValueError):
            match.check_image(before, expected[:-1], retail)
        self.assertEqual(bindings, match.BINDINGS)
        self.assertEqual(raw, match.retail_object_bytes(ROOT))
        self.receipt["rejections"] = {
            "payload_hash_and_bindings": True, "image_corruptions": len(positions) + 1,
            "closed_symbol_cycle": ["D_800A1050", "D_800A92A0"],
            "strict_exclusions": 0,
        }


if __name__ == "__main__":
    unittest.main()
