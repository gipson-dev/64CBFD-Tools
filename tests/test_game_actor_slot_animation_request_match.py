"""Semantic, ABI, direct-owner and full-image gates for func_1507F54C."""

import csv
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_animation_request_match as match
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
ACTOR = 0x220000
ANIMATE = 0x1505E650
TABLE = 0x800B85A4
MAPPING = {
    0x57: 0x115,
    0x8C: 0x1A5,
    0xA8: 0x1AF,
    0xA9: 0x1AF,
    0x89: 0x1FA,
    0xBA: 0x1FA,
}


def fixture(slot, kind, phase):
    memory = {STACK + phase + index: (index * 19 + 0xA7) & 0xFF
              for index in range(-0x100, 0x100)}
    memory.update({ACTOR + index: (index * 23 + slot + 0x31) & 0xFF
                   for index in range(0x180)})
    memory[ACTOR + 0x13C] = slot
    if slot >= 100:
        memory[TABLE + slot * 0x32C] = kind
    return memory


def expected(slot, kind):
    if slot < 100:
        return (ACTOR, 0xF, 0x3F800000, 0x40400000, 0, 0, 0)
    return (ACTOR, MAPPING.get(kind, 0xD8),
            0x3F800000, 0x40800000, 0, 0, 0)


class AnimationRequestOracle(TimingOracle):
    def record_call(self, target):
        if target != ANIMATE:
            raise AssertionError("Unexpected actor-animation-request call %08X" % target)
        args = self.arguments(7)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target != ANIMATE:
            raise AssertionError("Unexpected actor-animation-request hook %08X" % target)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]


def native_harness(body):
    return r'''
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
''' + match.DECLARATIONS + body + r'''
static union { u32 align; u8 bytes[0x180]; } actorStore;
u8 D_800B85A4[0x32D * 256];
static u8 *gotActor;
static u16 gotAnimation;
static f32 gotScale, gotBlend, gotX, gotY;
static s32 gotMode, calls;
void func_1505E650(u8 *actor, u16 animation, f32 scale, f32 blend,
                   f32 x, f32 y, s32 mode) {
    gotActor = actor;
    gotAnimation = animation;
    gotScale = scale;
    gotBlend = blend;
    gotX = x;
    gotY = y;
    gotMode = mode;
    calls++;
}
static u16 mapped(u8 kind) {
    switch (kind) {
    case 0x57: return 0x115;
    case 0x8C: return 0x1A5;
    case 0xA8:
    case 0xA9: return 0x1AF;
    case 0x89:
    case 0xBA: return 0x1FA;
    default: return 0xD8;
    }
}
static int one(u32 slot, u32 kind) {
    u32 i;
    for (i = 0; i < sizeof(actorStore.bytes); i++)
        actorStore.bytes[i] = (u8)(i * 13u + slot + 7u);
    actorStore.bytes[0x13C] = (u8)slot;
    D_800B85A4[slot * 0x32C] = (u8)kind;
    calls = 0;
    func_1507F54C(actorStore.bytes);
    if (calls != 1 || gotActor != actorStore.bytes) return 10;
    if (slot < 100) {
        if (gotAnimation != 0xF || gotScale != 1.0f || gotBlend != 3.0f)
            return 11;
    } else {
        if (gotAnimation != mapped((u8)kind) ||
                gotScale != 1.0f || gotBlend != 4.0f)
            return 12;
    }
    if (gotX != 0.0f || gotY != 0.0f || gotMode != 0) return 13;
    return 0;
}
static int run(void) {
    u32 slot, kind;
    for (slot = 0; slot < 256; slot++)
        for (kind = 0; kind < 256; kind++) {
            int code = one(slot, kind);
            if (code) return code;
        }
    return 0;
}
''' + START


def controls():
    body = match.SELECTED
    return {
        "wrong-slot-field": body.replace("actor[0x13C]", "actor[0x13B]"),
        "wrong-threshold": body.replace(">= 100", ">= 99"),
        "wrong-stride": body.replace("* 0x32C", "* 0x32D"),
        "wrong-default": body.replace("animation = 0xD8", "animation = 0xD9"),
        "wrong-57": body.replace("animation = 0x115", "animation = 0x116"),
        "wrong-8c": body.replace("animation = 0x1A5", "animation = 0x1A6"),
        "wrong-a8-a9": body.replace("animation = 0x1AF", "animation = 0x1B0"),
        "wrong-89-ba": body.replace("animation = 0x1FA", "animation = 0x1FB"),
        "wrong-high-scale": body.replace(
            "animation, 1.0f, 4.0f", "animation, 2.0f, 4.0f"),
        "wrong-high-blend": body.replace(
            "animation, 1.0f, 4.0f", "animation, 1.0f, 3.0f"),
        "wrong-low-animation": body.replace("actor, 0xF, 1.0f", "actor, 0x10, 1.0f"),
        "wrong-low-blend": body.replace("0xF, 1.0f, 3.0f", "0xF, 1.0f, 4.0f"),
    }


class ActorAnimationRequestMatchTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.out = ROOT / match.BUILD
        (cls.report, cls.before_owner, cls.after_owner,
         cls.before_elf, cls.after_elf) = match.prepare(ROOT)
        cls.words = struct.unpack_from(">%dI" % match.WORDS,
                                       (ROOT / match.ROM_IMAGE).read_bytes(), match.ROM)
        cls.fresh = cls.out / ("test-run-" + str(os.getpid()))
        cls.fresh.mkdir(exist_ok=False)

    @classmethod
    def tearDownClass(cls):
        (cls.out / ("test-receipt-" + str(os.getpid()) + ".json")).write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_owner_image_references_and_data_closure(self):
        self.assertEqual((self.report["words"], self.report["frame"],
                          self.report["natural_positional_differences"],
                          self.report["guards"], self.report["relocations"]),
                         (61, 0x28, 0, 0, 4))
        self.assertEqual(self.report["neighbors"], 15)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(self.report["caller"]["direct_jal_calls"],
                         ["0xace2c", "0xacf1c"])
        self.assertEqual(self.report["caller"]["aligned_pointer_literals"], [])
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))
        with (ROOT / match.GUARDS).open(newline="") as stream:
            rows = [row for row in csv.DictReader(stream)
                    if row["filename"] == match.FILENAME and
                    row["function"] == match.FUNCTION]
        self.assertEqual(rows, [])
        self.receipt["closure"] = self.report

    def test_02_guest_all_routes_abi_and_word_coverage(self):
        coverage = set()
        cases = 0
        work = [(slot, 0) for slot in (0, 1, 98, 99)]
        work += [(slot, kind) for slot in (100, 101, 127, 255)
                 for kind in range(256)]
        for slot, kind in work:
            for phase in (0, 8):
                model = AnimationRequestOracle(
                    self.words, fixture(slot, kind, phase), phase=phase,
                    entry=match.ENTRY, arguments=(ACTOR,)).run()
                self.assertEqual(model.calls, [(ANIMATE, expected(slot, kind))])
                coverage.update(pc for pc in model.visits
                                if match.ENTRY <= pc < match.ENTRY + match.SIZE)
                cases += 1
        self.assertEqual(coverage,
                         set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.receipt["guest"] = {
            "cases": cases, "covered_words": len(coverage),
            "slot_boundaries": [0, 1, 98, 99, 100, 101, 127, 255],
            "high_slot_kind_bytes": 256,
        }

    def test_03_native32_profiles_and_effective_controls(self):
        selected = self.fresh / "native-selected.c"
        selected.write_text(native_harness(match.SELECTED))
        profiles = []
        for profile in ("-O0", "-O2", "-O3"):
            target = self.fresh / ("native-selected" + profile)
            build = subprocess.run(native_command(profile) + [str(selected), "-o", str(target)],
                                   cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(target)], capture_output=True)
            self.assertEqual(run.returncode, 0, (profile, run.stdout, run.stderr))
            profiles.append({"profile": profile, "cases": 65536, "UBSan_trap": True})
        effective = []
        for name, body in controls().items():
            source = self.fresh / ("control-" + name + ".c")
            target = self.fresh / ("control-" + name)
            source.write_text(native_harness(body))
            build = subprocess.run(native_command("-O2", valid=False) +
                                   [str(source), "-o", str(target)], cwd=ROOT,
                                   capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, (name, build.stdout, build.stderr))
            run = subprocess.run([str(target)], capture_output=True)
            self.assertNotEqual(run.returncode, 0, name)
            effective.append(name)
        self.receipt["native"] = {
            "profiles": profiles, "effective_controls": effective,
        }

    def test_04_payload_and_image_corruption_fail_closed(self):
        qualified = self.out / "qualified-compact.o"
        match.checked_candidate(ROOT, qualified)
        with self.assertRaises(ValueError):
            match.checked_candidate(ROOT, self.out / "predecessor-compact.o")
        before = self.before_elf.read_bytes()
        retail = match.retail_bytes(ROOT)
        expected_image = match.expected_image(before, retail)
        self.assertEqual(expected_image, self.after_elf.read_bytes())
        symbol = next(at for at, name, _, _ in match.symbol_rows(before)
                      if name == match.FUNCTION)
        for position in (elf_slot_offset(before, match.ENTRY, match.SIZE), symbol + 8):
            bad = bytearray(expected_image)
            bad[position] ^= 1
            with self.assertRaises(ValueError):
                match.check_image(before, bytes(bad), retail)
        self.receipt["rejections"] = {
            "predecessor_payload": True, "image_corruptions": 2,
        }


if __name__ == "__main__":
    unittest.main()
