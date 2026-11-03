"""Semantic, ABI and strict-image gates for func_150B709C."""

import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_menu_record_diagonal_fade_candidates as candidate
from tools.experiments import game_menu_record_diagonal_fade_match as match
from tools.tests.game_animation_timeline_oracle import bits, signed
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK, put, read


ROOT = Path(__file__).resolve().parents[2]
RECORD = 0x220000
TICKS = 0x800BE9E4


def quotient(numerator, denominator):
    value = abs(numerator) // abs(denominator)
    return -value if (numerator < 0) != (denominator < 0) else value


def fixture(progress, ticks, opacity, phase=0):
    memory = {STACK + index: (index * 17 + phase * 3 + 0xA5) & 0xFF
              for index in range(-0x100, 0x100)}
    memory.update({RECORD + index: (index * 13 + progress * 7 + opacity) & 0xFF
                   for index in range(0x50)})
    put(memory, RECORD + 0x18, progress & 0xFFFFFFFF)
    put(memory, RECORD + 0x2C, 0x7FC12345)
    put(memory, RECORD + 0x30, 0xFFC54321)
    memory[RECORD + 0x45] = opacity
    put(memory, TICKS, ticks & 0xFFFFFFFF)
    return memory


def reference(initial):
    memory = dict(initial)
    progress = signed(read(memory, RECORD + 0x18))
    ticks = signed(read(memory, TICKS))
    if progress == 30:
        opacity = memory[RECORD + 0x45] + ticks * 8
        memory[RECORD + 0x45] = opacity & 0xFF if opacity < 256 else 0
    progress = signed((progress + ticks * 2) & 0xFFFFFFFF)
    if progress >= 31:
        progress = 30
    put(memory, RECORD + 0x18, progress & 0xFFFFFFFF)
    x_position = quotient(progress * -84, 30) + 230
    y_position = quotient(progress * -50, 30) + 170
    put(memory, RECORD + 0x2C, bits(float(x_position)))
    put(memory, RECORD + 0x30, bits(float(y_position)))
    return memory


def public(memory):
    return (bytes(memory[RECORD + index] for index in range(0x50)),
            read(memory, TICKS))


def controls():
    body = candidate.SELECTED
    variants = {
        "wrong-terminal-progress": body.replace("progress == 30", "progress == 29", 1),
        "wrong-opacity-rate": body.replace("D_800BE9E4 * 8", "D_800BE9E4 * 4", 1),
        "wrong-opacity-reset": body.replace("opacity = 0;", "opacity = 1;", 1),
        "wrong-progress-rate": body.replace("D_800BE9E4 * 2", "D_800BE9E4", 1),
        "wrong-progress-limit": body.replace("progress >= 31", "progress >= 32", 1),
        "wrong-progress-cap": body.replace("        progress = 30;", "        progress = 29;", 1),
        "wrong-x-slope": body.replace("progress * -84", "progress * -83", 1),
        "wrong-y-slope": body.replace("progress * -50", "progress * -49", 1),
        "wrong-x-origin": body.replace("+ 230", "+ 231", 1),
        "wrong-y-origin": body.replace("+ 170", "+ 171", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("A diagonal menu-record control did not alter the source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
''' + candidate.TYPES + r'''
typedef struct {
    u32 left[4];
    DiagonalMenuRecord150B709C record;
    u32 right[4];
} FencedRecord;
typedef char SizeCheck[(sizeof(DiagonalMenuRecord150B709C) == 0x48) ? 1 : -1];
typedef char ProgressCheck[(__builtin_offsetof(DiagonalMenuRecord150B709C, progress) == 0x18) ? 1 : -1];
typedef char XCheck[(__builtin_offsetof(DiagonalMenuRecord150B709C, xPosition) == 0x2C) ? 1 : -1];
typedef char YCheck[(__builtin_offsetof(DiagonalMenuRecord150B709C, yPosition) == 0x30) ? 1 : -1];
typedef char OpacityCheck[(__builtin_offsetof(DiagonalMenuRecord150B709C, opacity) == 0x45) ? 1 : -1];
s32 D_800BE9E4;
''' + body + r'''
static FencedRecord actual, expected;
static s32 divide(s32 value, s32 divisor) {
    u32 left = value < 0 ? (u32)(-(value + 1)) + 1u : (u32)value;
    u32 right = divisor < 0 ? (u32)(-(divisor + 1)) + 1u : (u32)divisor;
    s32 result = (s32)(left / right);
    return ((value < 0) != (divisor < 0)) ? -result : result;
}
static int one(s32 progress, s32 ticks, u32 opacity, u32 seed) {
    u32 index;
    u8 *left = (u8 *)&actual;
    u8 *right = (u8 *)&expected;
    s32 next, value;
    for (index = 0; index < sizeof(actual); index++)
        left[index] = (u8)(index * 13u + seed * 17u + opacity);
    actual.record.progress = progress;
    actual.record.xPosition = -123.25f;
    actual.record.yPosition = 456.5f;
    actual.record.opacity = (u8)opacity;
    for (index = 0; index < sizeof(actual); index++) right[index] = left[index];
    D_800BE9E4 = ticks;
    if (progress == 30) {
        value = (s32)opacity + ticks * 8;
        expected.record.opacity = value < 256 ? (u8)value : 0;
    }
    next = progress + ticks * 2;
    if (next >= 31) next = 30;
    expected.record.progress = next;
    expected.record.xPosition = (f32)(divide(next * -84, 30) + 230);
    expected.record.yPosition = (f32)(divide(next * -50, 30) + 170);
    func_150B709C(&actual.record);
    for (index = 0; index < sizeof(actual); index++)
        if (left[index] != right[index]) return 1;
    return 0;
}
__attribute__((force_align_arg_pointer,noreturn)) void _start(void) {
    static const s32 progresses[] = {-40, -1, 0, 1, 28, 29, 30, 31, 100};
    static const s32 ticks[] = {-3, -1, 0, 1, 2, 5};
    u32 i, j, opacity, seed = 0;
    int result = 0;
    for (i = 0; i < sizeof(progresses) / sizeof(progresses[0]); i++)
        for (j = 0; j < sizeof(ticks) / sizeof(ticks[0]); j++)
            for (opacity = 0; opacity < 256; opacity += 17)
                result |= one(progresses[i], ticks[j], opacity, seed++);
    result |= one(30, 1, 255, seed++);
    result |= one(30, 32, 1, seed++);
    __asm__ volatile("int $0x80" :: "a"(1), "b"(result));
    __builtin_unreachable();
}
'''


def run_native(label, body, optimization, expected):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / label
    source.write_text(native_source(body))
    command = [
        "gcc", "-m32", optimization, "-std=c99", "-fno-strict-aliasing",
        "-ffreestanding", "-nostdlib", "-static", "-fno-pie", "-no-pie",
        "-fno-stack-protector", "-msse2", "-mfpmath=sse", "-mstackrealign",
        "-ffp-contract=off", "-fsanitize=undefined",
        "-fsanitize-undefined-trap-on-error", "-Wall", "-Wextra", "-Werror",
        str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if executed.returncode != expected:
        raise AssertionError((label, executed.returncode, executed.stderr))


class MenuRecordDiagonalFadeTest(unittest.TestCase):
    def test_guest_semantics_and_reachable_word_coverage(self):
        data = (ROOT / match.ROM_IMAGE).read_bytes()[match.ROM:match.ROM + match.SIZE]
        words = list(struct.unpack(">%dI" % match.WORDS, data))
        seen = set()
        cases = 0
        for progress, ticks, opacity, phase in itertools.product(
                (-40, -1, 0, 1, 28, 29, 30, 31, 100),
                (-3, -1, 0, 1, 2, 5), (0, 1, 127, 247, 254, 255), (0, 8)):
            initial = fixture(progress, ticks, opacity, phase)
            wanted = reference(initial)
            model = TimingOracle(words, initial, phase=phase, entry=match.ENTRY,
                                 arguments=(RECORD,)).run()
            self.assertEqual(public(model.memory), public(wanted))
            self.assertFalse(model.calls)
            seen.update(pc - match.ENTRY for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            cases += 1
        self.assertEqual(cases, 648)
        dead = set(range(0, match.SIZE, 4)) - seen
        self.assertEqual(dead, {
            0x8C, 0x9C, 0xA0, 0xA4,
            0xE4, 0xF4, 0xF8, 0xFC,
        })

    def test_native_profiles_and_effective_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED,
                       optimization, 0)
        for label, body in controls().items():
            run_native("control-" + label, body, "-O2", 1)

    def test_callback_registry_and_void_callers(self):
        evidence = match.registry_evidence(ROOT)
        self.assertEqual(evidence["registry"], "D_8008CA20[8]")
        phase = (ROOT / "conker/src/game/generated_196DB0.c").read_text()
        actor = (ROOT / "conker/src/game_1944C0.c").read_text()
        self.assertIn("typedef void (*RecordPhaseCallback)(void *);", phase)
        self.assertIn("D_8008CA20[selector](record);", phase)
        self.assertIn("extern void (*D_8008CA20[])(void *);", actor)
        self.assertIn("D_8008CA20[idx](arg0);", actor)

    def test_direct_owner_and_full_image(self):
        candidate_report = candidate.compare("test-direct-owner", candidate.SELECTED)
        self.assertEqual(candidate_report["words"], match.WORDS)
        self.assertEqual(candidate_report["differences"], 0)
        result = match.prepare(ROOT)
        report = result["report"]
        installed = candidate.SELECTED in (ROOT / candidate.SOURCE).read_text()
        self.assertEqual(report["source_installed"], installed)
        self.assertEqual(report["guards"], 0)
        self.assertEqual(report["natural_positional_differences"], 0)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertTrue(report["game_data"]["exact"])


if __name__ == "__main__":
    unittest.main()
