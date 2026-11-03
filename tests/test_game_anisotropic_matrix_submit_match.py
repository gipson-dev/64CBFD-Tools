"""Semantic and strict-image gates for func_151B9310."""

import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_anisotropic_matrix_submit_candidates as candidate
from tools.experiments import game_anisotropic_matrix_submit_match as match
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK, put, read


ROOT = Path(__file__).resolve().parents[2]
ROTATE = 0x150A8050
CONVERT = 0x150A7790
STATE = 0x220000
OUTPUT = 0x230000


def product(left, right):
    return bits(floating(left) * floating(right))


def matrix_seed(seed):
    return [bits(((index * 5 + seed * 3) % 29 - 14) * 0.125)
            for index in range(16)]


def fixture(seed):
    memory = {STACK + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x500, 0x100)}
    memory.update({STATE + index: (index * 13 + seed * 19 + 0x59) & 0xFF
                   for index in range(-16, 0x190)})
    memory.update({OUTPUT + index: (index * 11 + seed * 23 + 0x37) & 0xFF
                   for index in range(0x80)})
    values = {
        0x18: (0.0, -0.5, 1.25, -2.0)[seed & 3],
        0x1C: (2.0, 0.25, -1.5, -0.0)[seed & 3],
        0x38: (seed - 7) * 1.25,
        0x3C: (9 - seed) * -0.75,
        0x40: (seed % 5 - 2) * 3.5,
        0x170: (seed % 13 - 6) * 0.125,
    }
    for offset, value in values.items():
        put(memory, STATE + offset, bits(value))
    return memory


def mutate(memory, seed, mode):
    if mode & 1:
        put(memory, STATE + 0x18, bits((-1.0, 0.5, 2.0)[seed % 3]))
    if mode & 2:
        put(memory, STATE + 0x1C, bits((0.0, -0.25, 1.5)[seed % 3]))
    if mode & 4:
        put(memory, STATE + 0x38, bits((seed + 1) * -2.25))
        put(memory, STATE + 0x3C, bits((seed - 3) * 1.75))
        put(memory, STATE + 0x40, bits((seed % 7 - 3) * -4.0))
        put(memory, STATE + 0x170, bits(99.0))


def reference(initial, seed, mode):
    memory = dict(initial)
    rotation = read(memory, STATE + 0x170)
    values = matrix_seed(seed)
    mutate(memory, seed, mode)
    values[12] = read(memory, STATE + 0x38)
    values[13] = read(memory, STATE + 0x3C)
    values[14] = read(memory, STATE + 0x40)
    horizontal = read(memory, STATE + 0x18)
    vertical = read(memory, STATE + 0x1C)
    for index in (0, 1, 2, 8, 9, 10):
        values[index] = product(values[index], horizontal)
    for index in (4, 5, 6):
        values[index] = product(values[index], vertical)
    for index, value in enumerate(values):
        put(memory, OUTPUT + index * 4, value)
    return memory, [(ROTATE, rotation), (CONVERT, tuple(values))]


def public(memory):
    return (bytes(memory[STATE + index] for index in range(0x180)),
            bytes(memory[OUTPUT + index] for index in range(0x80)))


class MatrixSubmitOracle(TimingOracle):
    def __init__(self, words, memory, seed, mode, phase=0):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(OUTPUT, STATE))
        self.seed = seed
        self.mode = mode
        self.ordinal = 0

    def record_call(self, target):
        if target == ROTATE:
            args = tuple(self.arguments(4))
            if args[1] != 0 or args[2] != 0:
                raise AssertionError("Rotation helper did not receive two zero angles")
            event = (target, args[3])
        elif target == CONVERT:
            args = tuple(self.arguments(2))
            values = tuple(read(self.memory, args[0] + index * 4)
                           for index in range(16))
            event = (target, values)
        else:
            raise AssertionError("Unexpected matrix-submit helper %08X" % target)
        self.calls.append(event)
        self.events.append(("CALL",) + event)

    def hook(self, target):
        expected = ROTATE if self.ordinal == 0 else CONVERT
        if target != expected or self.ordinal >= 2:
            raise AssertionError("Unexpected matrix-submit hook %08X" % target)
        if target == ROTATE:
            matrix = self.r[4]
            for index, value in enumerate(matrix_seed(self.seed)):
                put(self.memory, matrix + index * 4, value)
            mutate(self.memory, self.seed, self.mode)
        else:
            matrix, output = self.r[4], self.r[5]
            if output != OUTPUT:
                raise AssertionError("Matrix conversion output pointer changed")
            for index in range(16):
                put(self.memory, output + index * 4,
                    read(self.memory, matrix + index * 4))
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011
        self.ordinal += 1


def controls():
    body = candidate.SELECTED_MATCH
    variants = {
        "wrong-rotation": body.replace("state->zRotation", "state->xPosition", 1),
        "wrong-x-position": body.replace("state->xPosition", "state->yPosition", 1),
        "wrong-y-position": body.replace("state->yPosition", "state->zPosition", 1),
        "wrong-z-position": body.replace("state->zPosition", "state->xPosition", 1),
        "wrong-horizontal-scale": body.replace(
            "workspace.values[0][0] *= state->horizontalScale;",
            "workspace.values[0][0] *= state->verticalScale;", 1),
        "wrong-vertical-scale": body.replace(
            "workspace.values[1][0] *= state->verticalScale;",
            "workspace.values[1][0] *= state->horizontalScale;", 1),
        "missing-basis-scale": body.replace(
            "    workspace.values[2][2] *= state->horizontalScale;\n", "", 1),
        "scaled-translation": body.replace(
            "    workspace.values[2][2] *= state->horizontalScale;",
            "    workspace.values[2][2] *= state->horizontalScale;\n"
            "    workspace.values[3][0] *= state->horizontalScale;", 1),
        "wrong-conversion-output": body.replace(
            "guMtxF2L(workspace.values, output);",
            "guMtxF2L(workspace.values, (Mtx *)state);", 1),
        "wrong-return": body.replace("    return 1;", "    return 0;", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("A matrix-submit semantic control did not alter the source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef int s32;
typedef float f32;
typedef union { u64 align; u8 bytes[64]; } Mtx;
''' + candidate.TYPES + r'''
typedef union { u64 align; u8 bytes[0x180]; } StateStore;
static StateStore stateStore;
static Mtx output;
static u32 seedValue, modeValue, calls, failed, rotationWord;
static u32 observed[16];
static f32 number(u32 value) { union { u32 u; f32 f; } cast; cast.u = value; return cast.f; }
static u32 word(f32 value) { union { u32 u; f32 f; } cast; cast.f = value; return cast.u; }
static u32 matrixWord(u32 index) {
    s32 value = (s32)((index * 5u + seedValue * 3u) % 29u) - 14;
    return word(value * 0.125f);
}
static void applyMutation(AnisotropicMatrixState151B9310 *state) {
    if (modeValue & 1u) state->horizontalScale = (seedValue % 3u == 0u) ? -1.0f : (seedValue % 3u == 1u) ? 0.5f : 2.0f;
    if (modeValue & 2u) state->verticalScale = (seedValue % 3u == 0u) ? 0.0f : (seedValue % 3u == 1u) ? -0.25f : 1.5f;
    if (modeValue & 4u) {
        state->xPosition = (seedValue + 1u) * -2.25f;
        state->yPosition = ((s32)seedValue - 3) * 1.75f;
        state->zPosition = ((s32)(seedValue % 7u) - 3) * -4.0f;
        state->zRotation = 99.0f;
    }
}
__attribute__((noinline)) void func_150A8050(f32 matrix[4][4], f32 x, f32 y, f32 z) {
    u32 index; AnisotropicMatrixState151B9310 *state = (AnisotropicMatrixState151B9310 *)stateStore.bytes;
    if (calls++ != 0u || word(x) != 0u || word(y) != 0u || word(z) != rotationWord) failed = 1u;
    for (index = 0; index < 16; index++) ((u32 *)matrix)[index] = matrixWord(index);
    applyMutation(state);
}
__attribute__((noinline)) void guMtxF2L(f32 matrix[4][4], Mtx *destination) {
    u32 index;
    if (calls++ != 1u || destination != &output) failed = 1u;
    for (index = 0; index < 16; index++) {
        u32 value = ((u32 *)matrix)[index];
        if (value != observed[index]) failed = 1u;
        ((u32 *)destination)[index] = value;
    }
}
''' + body + r'''
static int one(u32 seed, u32 mode) {
    AnisotropicMatrixState151B9310 *state = (AnisotropicMatrixState151B9310 *)stateStore.bytes;
    u32 index; f32 horizontal, vertical;
    seedValue = seed; modeValue = mode;
    for (index = 0; index < sizeof(stateStore.bytes); index++) stateStore.bytes[index] = (u8)(index * 13u + seed * 19u + 0x59u);
    state->horizontalScale = (seed & 3u) == 0u ? 0.0f : (seed & 3u) == 1u ? -0.5f : (seed & 3u) == 2u ? 1.25f : -2.0f;
    state->verticalScale = (seed & 3u) == 0u ? 2.0f : (seed & 3u) == 1u ? 0.25f : (seed & 3u) == 2u ? -1.5f : -0.0f;
    state->xPosition = ((s32)seed - 7) * 1.25f;
    state->yPosition = (9 - (s32)seed) * -0.75f;
    state->zPosition = ((s32)(seed % 5u) - 2) * 3.5f;
    state->zRotation = ((s32)(seed % 13u) - 6) * 0.125f;
    rotationWord = word(state->zRotation);
    applyMutation(state);
    horizontal = state->horizontalScale; vertical = state->verticalScale;
    for (index = 0; index < 16; index++) observed[index] = matrixWord(index);
    observed[12] = word(state->xPosition); observed[13] = word(state->yPosition); observed[14] = word(state->zPosition);
    for (index = 0; index < 3; index++) observed[index] = word(number(observed[index]) * horizontal);
    for (index = 4; index < 7; index++) observed[index] = word(number(observed[index]) * vertical);
    for (index = 8; index < 11; index++) observed[index] = word(number(observed[index]) * horizontal);
    state->horizontalScale = (seed & 3u) == 0u ? 0.0f : (seed & 3u) == 1u ? -0.5f : (seed & 3u) == 2u ? 1.25f : -2.0f;
    state->verticalScale = (seed & 3u) == 0u ? 2.0f : (seed & 3u) == 1u ? 0.25f : (seed & 3u) == 2u ? -1.5f : -0.0f;
    state->xPosition = ((s32)seed - 7) * 1.25f; state->yPosition = (9 - (s32)seed) * -0.75f;
    state->zPosition = ((s32)(seed % 5u) - 2) * 3.5f; state->zRotation = number(rotationWord);
    calls = failed = 0u;
    if (func_151B9310(&output, state) != 1 || calls != 2u || failed) return 1;
    for (index = 0; index < 16; index++) if (((u32 *)&output)[index] != observed[index]) return 1;
    return 0;
}
__attribute__((force_align_arg_pointer,noreturn)) void _start(void) {
    u32 seed, mode; int result = 0;
    for (seed = 0; seed < 32; seed++) for (mode = 0; mode < 8; mode++) result |= one(seed, mode);
    __asm__ volatile("int $0x80" :: "a"(1), "b"(result)); __builtin_unreachable();
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
        "-Wno-unused-parameter", str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if executed.returncode != expected:
        raise AssertionError((label, executed.returncode, executed.stderr))


class AnisotropicMatrixSubmitTest(unittest.TestCase):
    def test_guest_semantics_cover_every_word(self):
        data = (ROOT / match.ROM_IMAGE).read_bytes()[match.ROM:match.ROM + match.SIZE]
        words = list(struct.unpack(">%dI" % match.WORDS, data))
        seen = set()
        count = 0
        for seed, mode, phase in itertools.product(range(32), range(8), (0, 8)):
            initial = fixture(seed)
            wanted, calls = reference(initial, seed, mode)
            model = MatrixSubmitOracle(words, initial, seed, mode, phase).run()
            self.assertEqual(public(model.memory), public(wanted))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[2], 1)
            self.assertEqual(model.ordinal, 2)
            seen.update(pc - match.ENTRY for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            count += 1
        self.assertEqual(count, 512)
        self.assertEqual(seen, set(range(0, match.SIZE, 4)))

    def test_native_profiles_and_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED_MATCH,
                       optimization, 0)
        for label, body in controls().items():
            run_native("control-" + label, body, "-O2", 1)

    def test_direct_owner_and_full_image(self):
        candidate_report = candidate.compare(
            "test-direct-owner", candidate.SELECTED_MATCH)
        self.assertEqual(candidate_report["words"], match.WORDS)
        self.assertEqual(candidate_report["differences"], 0)
        result = match.prepare(ROOT)
        report = result["report"]
        installed = candidate.SELECTED_MATCH in (ROOT / candidate.SOURCE).read_text()
        self.assertEqual(report["source_installed"], installed)
        self.assertEqual(report["guards"], 0)
        self.assertEqual(report["natural_positional_differences"], 0)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertTrue(report["game_data"]["exact"])


if __name__ == "__main__":
    unittest.main()
