"""Semantic, ABI, guarded-owner and full-image gates for func_15035714."""

import csv
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_projection_probe_match as match
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
VIEW, ACTOR, PROJECTION, DESCRIPTOR = 0x220000, 0x230000, 0x240000, 0x250000
HELPER = 0x150A6360


def number(value):
    return floating(bits(value))


def fixture(identity, width, height, actor_y, descriptor_width,
            descriptor_height, x, z, threshold, phase):
    memory = {STACK + phase + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x180, 0x100)}
    for base, length in ((ACTOR, 0x180), (PROJECTION, 0x50),
                         (DESCRIPTOR, 0x30)):
        memory.update({base + index: (index * 29 + identity + 0x31) & 0xFF
                       for index in range(length)})
    put(memory, 0x800BE628, VIEW)
    put(memory, 0x800D1C90 + identity * 4, DESCRIPTOR)
    put(memory, 0x80097D70, bits(threshold))
    memory[ACTOR + 4] = identity
    put(memory, ACTOR + 0x14C, bits(width))
    put(memory, ACTOR + 0x150, bits(height))
    put(memory, ACTOR + 0x18, bits(actor_y))
    put(memory, DESCRIPTOR + 0xE, descriptor_width, 2)
    put(memory, DESCRIPTOR + 0x10, descriptor_height & 0xFFFF, 2)
    put(memory, PROJECTION + 0x30, bits(x))
    put(memory, PROJECTION + 0x38, bits(z))
    return memory


def expected_call(memory, mode, reflection_y):
    identity = memory[ACTOR + 4]
    descriptor_width = ((memory[DESCRIPTOR + 0xE] << 8) |
                        memory[DESCRIPTOR + 0xF])
    descriptor_height = ((memory[DESCRIPTOR + 0x10] << 8) |
                         memory[DESCRIPTOR + 0x11])
    if descriptor_height & 0x8000:
        descriptor_height -= 0x10000
    width = floating(struct.unpack(">I", bytes(memory[ACTOR + 0x14C + i]
                                                for i in range(4)))[0])
    height = floating(struct.unpack(">I", bytes(memory[ACTOR + 0x150 + i]
                                                 for i in range(4)))[0])
    actor_y = floating(struct.unpack(">I", bytes(memory[ACTOR + 0x18 + i]
                                                  for i in range(4)))[0])
    scale = number(float(descriptor_width))
    half_width = number(width * scale)
    half_height = number(height * scale)
    vertical = number(number(float(descriptor_height)) * height)
    reflection_y = number(reflection_y)
    if mode in (0, 1):
        projected_y = number(reflection_y -
            number(number(actor_y + vertical) - reflection_y))
    else:
        projected_y = number(actor_y + vertical)
    x = struct.unpack(">I", bytes(memory[PROJECTION + 0x30 + i]
                                   for i in range(4)))[0]
    z = struct.unpack(">I", bytes(memory[PROJECTION + 0x38 + i]
                                   for i in range(4)))[0]
    threshold = struct.unpack(">I", bytes(memory[0x80097D70 + i]
                                           for i in range(4)))[0]
    return (VIEW, 0x800D9C10, x, bits(projected_y), z,
            bits(half_width), bits(half_height), threshold)


class ProjectionProbeOracle(TimingOracle):
    def __init__(self, words, memory, args, helper_result, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=args)
        self.helper_result = helper_result

    def record_call(self, target):
        if target != HELPER:
            raise AssertionError("Unexpected projection-probe call %08X" % target)
        args = self.arguments(8)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target != HELPER:
            raise AssertionError("Unexpected projection-probe hook %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.r[2] = self.helper_result


def native_harness(body):
    return r'''
typedef unsigned char u8;
typedef unsigned short u16;
typedef short s16;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
''' + match.DECLARATIONS + body + r'''
static union { u32 align; u8 bytes[0x180]; } actorStore;
static union { u32 align; u8 bytes[0x50]; } projectionStore;
static union { u32 align; u8 bytes[0x30]; } descriptorStore;
static u8 viewStore[0x40];
u8 *D_800BE628 = viewStore;
u8 *D_800D1C90[256];
f32 D_800D9C10[4][4];
f32 D_80097D70;
static f32 got[6];
static void *gotView, *gotMatrix;
static s32 helperResult, helperCalls;
s32 func_150A6360(u8 *view, f32 matrix[4][4], f32 x, f32 y,
                  f32 z, f32 width, f32 height, f32 threshold) {
    gotView = view; gotMatrix = matrix;
    got[0] = x; got[1] = y; got[2] = z;
    got[3] = width; got[4] = height; got[5] = threshold;
    helperCalls++;
    return helperResult;
}
static int one(s32 mode, f32 reflectionY, u16 descriptorWidth,
               s16 descriptorHeight, f32 width, f32 height, f32 actorY,
               f32 x, f32 z, f32 threshold, s32 result) {
    f32 scale = (f32)descriptorWidth;
    f32 vertical = (f32)descriptorHeight * height;
    f32 expectedY;
    u32 i;
    for (i = 0; i < sizeof(actorStore.bytes); i++) actorStore.bytes[i] = (u8)(i * 7u + 3u);
    for (i = 0; i < sizeof(projectionStore.bytes); i++) projectionStore.bytes[i] = (u8)(i * 11u + 5u);
    for (i = 0; i < sizeof(descriptorStore.bytes); i++) descriptorStore.bytes[i] = (u8)(i * 13u + 9u);
    actorStore.bytes[4] = 37;
    *(f32 *)(actorStore.bytes + 0x14C) = width;
    *(f32 *)(actorStore.bytes + 0x150) = height;
    *(f32 *)(actorStore.bytes + 0x18) = actorY;
    *(u16 *)(descriptorStore.bytes + 0xE) = descriptorWidth;
    *(s16 *)(descriptorStore.bytes + 0x10) = descriptorHeight;
    *(f32 *)(projectionStore.bytes + 0x30) = x;
    *(f32 *)(projectionStore.bytes + 0x38) = z;
    D_800D1C90[37] = descriptorStore.bytes;
    D_80097D70 = threshold;
    helperResult = result; helperCalls = 0;
    expectedY = mode == 0 || mode == 1 ?
        reflectionY - ((actorY + vertical) - reflectionY) : actorY + vertical;
    if (func_15035714(mode, actorStore.bytes, projectionStore.bytes, reflectionY)
            != (result == 0)) return 10;
    if (helperCalls != 1 || gotView != viewStore || gotMatrix != D_800D9C10) return 11;
    if (got[0] != x || got[1] != expectedY || got[2] != z) return 12;
    if (got[3] != width * scale || got[4] != height * scale ||
            got[5] != threshold) return 13;
    return 0;
}
static int run(void) {
    static const s32 modes[] = {0, 1, 2, -7};
    static const f32 values[] = {-17.5f, -0.0f, 0.0f, 0.125f, 3.5f, 91.0f};
    static const u16 widths[] = {0, 1, 32767, 65535};
    static const s16 heights[] = {-32768, -31, 0, 27, 32767};
    u32 m, a, b, w, h, result;
    for (m = 0; m < 4; m++) for (a = 0; a < 6; a++)
      for (b = 0; b < 6; b++) for (w = 0; w < 4; w++)
       for (h = 0; h < 5; h++) for (result = 0; result < 2; result++) {
        int code = one(modes[m], values[a], widths[w], heights[h],
            values[b], values[(a + b + 1) % 6], values[(a * 3 + b) % 6],
            values[(b + 2) % 6], values[(a + 4) % 6], values[(b + 5) % 6],
            (s32)result);
        if (code) return code;
    }
    return 0;
}
''' + START


def controls():
    body = match.SELECTED
    return {
        "wrong-identity": body.replace("identity = actor[4]", "identity = actor[5]"),
        "wrong-width": body.replace("actor + 0x14C", "actor + 0x148"),
        "wrong-height": body.replace("actor + 0x150", "actor + 0x14C"),
        "wrong-reflection-mode": body.replace("mode == 1 || mode == 0", "mode == 1"),
        "wrong-projection-x": body.replace("projection + 0x30", "projection + 0x34"),
        "wrong-return": body.replace("return 1;", "return 0;", 1),
    }


class ProjectionProbeMatchTests(unittest.TestCase):
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
        self.assertEqual((self.report["natural_words"], self.report["words"],
                          self.report["frame"], self.report["guards"],
                          self.report["insertions"], self.report["relocations"]),
                         (61, 61, 0x40, 17, 0, 9))
        self.assertEqual(self.report["neighbors"], 9)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(self.report["references"]["direct_jal_calls"], ["0x62fbc"])
        self.assertEqual(self.report["references"]["aligned_pointer_literals"], [])
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))
        self.receipt["closure"] = self.report

    def test_02_guest_float_abi_modes_returns_and_reachable_words(self):
        coverage, cases = set(), 0
        for mode, reflection, width, height, actor_y, dw, dh, result, phase in itertools.product(
                (0, 1, 2, -7), (-11.5, -0.0, 0.0, 7.25),
                (-3.0, 0.125, 9.5), (-2.0, 0.0, 4.0),
                (-8.0, 1.5), (0, 1, 32767, 65535),
                (-32768, -1, 0, 37, 32767), (0, 7), (0, 8)):
            memory = fixture(37, width, height, actor_y, dw, dh,
                             3.25, -6.5, 0.75, phase)
            expected = expected_call(memory, mode, reflection)
            model = ProjectionProbeOracle(
                self.words, memory,
                (mode & 0xFFFFFFFF, ACTOR, PROJECTION, bits(reflection)),
                result, phase).run()
            self.assertEqual(model.calls, [(HELPER, expected)])
            self.assertEqual(model.r[2], int(result == 0))
            coverage.update(pc for pc in model.visits
                            if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            cases += 1
        unreachable = {match.ENTRY + offset for offset in (0x48, 0x4C, 0x50, 0x9C)}
        self.assertEqual(coverage,
                         set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - unreachable)
        self.receipt["guest"] = {"cases": cases, "covered_words": len(coverage),
                                  "statically_unreachable_words": 4,
                                  "reason": "three dead u16 corrections and one annulled duplicate load"}

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
            profiles.append({"profile": profile, "cases": 5760, "UBSan_trap": True})
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
        self.receipt["native"] = {"profiles": profiles, "effective_controls": effective}

    def test_04_guards_payload_and_image_corruption_fail_closed(self):
        with (self.out / "proposed-guards.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        target_rows = [row for row in rows if row["filename"] == match.FILENAME and
                       row["function"] == match.FUNCTION]
        self.assertEqual(len(target_rows), len(match.GUARD_ROWS))
        compact = self.out / "qualified-compact.o"
        for index, selected in enumerate(target_rows):
            changed = [dict(row) for row in rows]
            row_index = next(i for i, row in enumerate(changed)
                             if row["filename"] == match.FILENAME and
                             row["function"] == match.FUNCTION and
                             row["offset"] == selected["offset"])
            changed[row_index]["expected"] = "0x%08X" % (
                int(changed[row_index]["expected"], 0) ^ 1)
            path = self.fresh / ("stale-guard-%d.csv" % index)
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=changed[0].keys(),
                                        lineterminator="\n")
                writer.writeheader(); writer.writerows(changed)
            with self.assertRaises(ValueError):
                emit_padded_assembly(compact, ROOT / match.ASM,
                    word_patches_path=path, filename=match.FILENAME)
        match.checked_candidate(compact)
        with self.assertRaises(ValueError):
            match.checked_candidate(self.out / "predecessor-compact.o")
        before = self.before_elf.read_bytes()
        retail = match.retail_bytes(ROOT)
        expected = match.expected_image(before, retail)
        self.assertEqual(expected, self.after_elf.read_bytes())
        symbol = next(at for at, name, _, _ in match.symbol_rows(before)
                      if name == match.FUNCTION)
        for position in (elf_slot_offset(before, match.ENTRY, match.SIZE), symbol + 8):
            bad = bytearray(expected); bad[position] ^= 1
            with self.assertRaises(ValueError):
                match.check_image(before, bytes(bad), retail)
        self.receipt["rejections"] = {"stale_guards": len(target_rows),
                                       "image_corruptions": 2,
                                       "predecessor_payload": True}


if __name__ == "__main__":
    unittest.main()
