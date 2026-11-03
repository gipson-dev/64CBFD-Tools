"""Semantics, ABI, guard, owner and image gates for func_150C2424."""

import csv
import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_dual_effect_band_emitter_guard_match as match
from tools.pad_c_object import emit_padded_assembly
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read


RANDOM = 0x150ADA68
EMITTER = 0x1514C470
FIRST_GLOBAL = 0x800A0268
SECOND_GLOBAL = 0x800A026C


def rounded(value):
    return bits(value)


def expression(sample, multiplier, bias):
    product = floating(rounded(floating(sample) * multiplier))
    return rounded(product + bias)


def fixture(first_global, second_global, phase):
    memory = {STACK + i: (i * 17 + 0xA5) & 0xFF
              for i in range(-0x100, 0x100)}
    put(memory, FIRST_GLOBAL, first_global)
    put(memory, SECOND_GLOBAL, second_global)
    return memory


def expected_calls(channel, first_sample, second_sample,
                   first_global, second_global):
    return [
        (RANDOM, ()),
        (EMITTER, (
            first_global, bits(-490.0), bits(-328.0), first_global,
            bits(-490.0), bits(328.0), expression(first_sample, 8.0, 8.0),
            1, 0, 0, 0, channel & 0xFF)),
        (RANDOM, ()),
        (EMITTER, (
            second_global, bits(-560.0), bits(-580.0), bits(8117.0),
            bits(-560.0), bits(-580.0), expression(second_sample, 3.0, 4.0),
            3, 0, 0, 0, channel & 0xFF)),
    ]


class DualBandOracle(TimingOracle):
    def __init__(self, words, memory, channel, samples, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(channel,))
        self.samples = list(samples)
        self.random_index = 0

    def emitter_arguments(self):
        values = [self.f[12], self.f[14], self.r[6], self.r[7]]
        values.extend(read(self.memory, self.r[29] + offset)
                      for offset in range(0x10, 0x30, 4))
        return tuple(values)

    def record_call(self, target):
        if target == RANDOM:
            self.calls.append((target, ()))
        elif target == EMITTER:
            self.calls.append((target, self.emitter_arguments()))
        else:
            raise AssertionError("Unexpected dual-band call %08X" % target)
        self.events.append(("CALL", target, self.calls[-1][1]))

    def hook(self, target):
        if target == RANDOM:
            self.f[0] = self.samples[self.random_index]
            self.random_index += 1
            return
        if target != EMITTER:
            raise AssertionError("Unexpected dual-band hook %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]


def native_harness(body):
    return r'''typedef unsigned char u8;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
#define NULL ((void *)0)
static f32 rawFloat(u32 value);
f32 D_800A0268;
f32 D_800A026C;
f32 func_150ADA68(void);
void func_1514C470(f32, f32, f32, f32, f32, f32, f32, s32, s32, f32, void *, u8);
%s
static u32 samples[2], randomCalls, emitCalls;
static u32 captured[2][12];
static u32 rawBits(f32 value) { union { u32 u; f32 f; } word; word.f = value; return word.u; }
static f32 rawFloat(u32 value) { union { u32 u; f32 f; } word; word.u = value; return word.f; }
f32 func_150ADA68(void) { return rawFloat(samples[randomCalls++]); }
void func_1514C470(f32 a, f32 b, f32 c, f32 d, f32 e, f32 f, f32 g,
                   s32 h, s32 i, f32 j, void *k, u8 channel) {
    u32 *out = captured[emitCalls++];
    out[0]=rawBits(a); out[1]=rawBits(b); out[2]=rawBits(c); out[3]=rawBits(d);
    out[4]=rawBits(e); out[5]=rawBits(f); out[6]=rawBits(g); out[7]=(u32)h;
    out[8]=(u32)i; out[9]=rawBits(j); out[10]=(u32)k; out[11]=channel;
}
static int one(u32 channel, u32 first, u32 second, u32 global0, u32 global1) {
    u32 wanted[2][12] = {
      {global0,0xC3F50000,0xC3A40000,global0,0xC3F50000,0x43A40000,0,1,0,0,0,channel&255},
      {global1,0xC40C0000,0xC4110000,0x45FDA800,0xC40C0000,0xC4110000,0,3,0,0,0,channel&255}
    };
    u32 band, field;
    samples[0]=first; samples[1]=second; randomCalls=emitCalls=0;
    D_800A0268=rawFloat(global0); D_800A026C=rawFloat(global1);
    wanted[0][6]=rawBits(rawFloat(first)*8.0f+8.0f);
    wanted[1][6]=rawBits(rawFloat(second)*3.0f+4.0f);
    func_150C2424((u8)channel);
    if (randomCalls != 2 || emitCalls != 2) return 10;
    for (band=0; band<2; band++) for (field=0; field<12; field++)
        if (captured[band][field] != wanted[band][field])
            return 20 + (int)(band*12+field);
    return 0;
}
static int run(void) {
    static const u32 channels[] = {0,1,127,255};
    static const u32 values[] = {0,0x3E800000,0x3F7FBE77,0xBF000000};
    static const u32 globals[][2] = {{0x4604D000,0x460A2C00},{0x3F800000,0xC0000000}};
    u32 a,b,c,d;
    for (a=0;a<4;a++) for (b=0;b<4;b++) for (c=0;c<4;c++) for (d=0;d<2;d++) {
        int status=one(channels[a],values[b],values[c],globals[d][0],globals[d][1]);
        if (status) return status;
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status=run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
''' % body


class DualEffectBandEmitterGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / match.BUILD
        (cls.report, cls.predecessor_owner, cls.qualified_owner,
         cls.predecessor_elf, cls.qualified_elf) = match.prepare(
             cls.root, cls.output)
        rom = (cls.root / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(">%dI" % match.WORDS,
                                            rom, match.ROM))

    def test_01_guarded_C_owner_image_and_protected_data(self):
        self.assertEqual((self.report["words"], self.report["frame"],
                          self.report["natural_positional_differences"],
                          self.report["guards"], self.report["relocations"]),
                         (62, 56, 4, 4, 8))
        self.assertEqual(self.report["neighbors"], 17)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))
        self.assertEqual(self.qualified_elf.read_bytes(), match.expected_image(
            self.predecessor_elf.read_bytes(), match.retail_bytes(self.root)))

    def test_02_guest_two_bands_channel_lifetime_and_all_words(self):
        visits, cases = set(), 0
        samples = (bits(0.0), bits(0.25), bits(0.999), bits(-0.5))
        globals_ = ((bits(8500.0), bits(8843.0)),
                    (bits(1.0), bits(-2.0)))
        for channel, first, second, pair, phase in itertools.product(
                (0, 1, 127, 255, 0x1FF), samples, samples, globals_, (0, 8)):
            initial = fixture(pair[0], pair[1], phase)
            model = DualBandOracle(
                self.words, initial, channel, (first, second), phase).run()
            self.assertEqual(model.calls, expected_calls(
                channel, first, second, pair[0], pair[1]))
            self.assertEqual(model.r[29], STACK + phase)
            visits.update(model.visits); cases += 1
        self.assertEqual(visits, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.assertEqual(cases, 320)

    def compile_native(self, body, label, optimization):
        source = self.output / (label + optimization + ".c")
        binary = self.output / (label + optimization)
        source.write_text(native_harness(body))
        result = subprocess.run([
            "gcc", "-m32", optimization, "-std=gnu89", "-ffreestanding",
            "-nostdlib", "-static", "-fno-pie", "-no-pie",
            "-fno-stack-protector", "-fno-strict-aliasing",
            "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
            "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary)],
            capture_output=True, text=True)
        (self.output / (label + optimization + "-compiler.log")).write_text(
            result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr[:3000])
        return subprocess.run([str(binary)], timeout=30).returncode

    def test_03_native32_profiles_and_effective_controls(self):
        body = match.SELECTED
        for optimization in ("-O0", "-O2", "-O3"):
            self.assertEqual(self.compile_native(body, "native", optimization), 0)
        controls = {
            "first-origin": body.replace("D_800A0268, -490.0f", "D_800A026C, -490.0f", 1),
            "first-coordinate": body.replace("-328.0f", "-329.0f", 1),
            "first-scale": body.replace("* 8.0f", "* 7.0f", 1),
            "first-bias": body.replace("+ 8.0f", "+ 7.0f", 1),
            "first-mode": body.replace("                 1, 0,", "                 2, 0,", 1),
            "second-origin": body.replace("D_800A026C, -560.0f", "D_800A0268, -560.0f", 1),
            "second-order": body.replace("-560.0f, -580.0f, 8117.0f", "-580.0f, -560.0f, 8117.0f", 1),
            "second-scale": body.replace("* 3.0f", "* 2.0f", 1),
            "second-bias": body.replace("+ 4.0f", "+ 5.0f", 1),
            "channel": body.replace("NULL, channel", "NULL, 0", 1),
        }
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0,
                                name)

    def test_04_guards_fail_closed_caller_and_live_state(self):
        with (self.output / "proposed-guards.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        target = [row for row in rows if row["filename"] == match.FILENAME and
                  row["function"] == match.FUNCTION]
        self.assertEqual(len(target), 4)
        compact = self.output / "qualified-compact.o"
        for index, selected in enumerate(target):
            changed = [dict(row) for row in rows]
            row_index = next(i for i, row in enumerate(changed)
                             if row["filename"] == match.FILENAME and
                             row["function"] == match.FUNCTION and
                             row["offset"] == selected["offset"])
            changed[row_index]["expected"] = "0x%08X" % (
                int(changed[row_index]["expected"], 0) ^ 1)
            path = self.output / ("stale-guard-%d.csv" % index)
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=changed[0].keys(),
                                        lineterminator="\n")
                writer.writeheader(); writer.writerows(changed)
            with self.assertRaises(ValueError):
                emit_padded_assembly(compact, self.root / match.LAYOUT,
                    word_patches_path=path, filename=match.FILENAME)
        rom = (self.root / match.ROM_IMAGE).read_bytes()
        jal = 0x0C000000 | (match.ENTRY >> 2 & 0x03FFFFFF)
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == jal],
                         [0x56A9C])
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == match.ENTRY],
                         [])
        self.assertEqual(struct.unpack_from(">4I", rom, 0x56A94),
                         (0x0D4308A4, 0x320400FF, jal, 0x320400FF))
        predecessor, qualified, installed = match.source_states(
            (self.root / match.SOURCE).read_text())
        self.assertEqual(installed, self.report["installed"])
        expected_owner = self.qualified_owner if installed else self.predecessor_owner
        expected_elf = self.qualified_elf if installed else self.predecessor_elf
        self.assertEqual((self.root / match.OBJECT).read_bytes(),
                         expected_owner.read_bytes())
        self.assertEqual((self.root / match.ELF).read_bytes(),
                         expected_elf.read_bytes())
        self.assertNotEqual(predecessor, qualified)


if __name__ == "__main__":
    unittest.main()
