"""Semantic, owner, guard and full-image gates for func_15158920."""

import csv
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_translation_scale_matrix_candidates as candidate
from tools.experiments import game_translation_scale_matrix_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK, put, read


ROOT = Path(__file__).resolve().parents[2]
CONVERT = 0x150A7790
STATE = 0x220000
OUTPUT = 0x230000
SCALE_COEFFICIENT = 0x800A6070
IDENTITY = 0x8008AE18
COEFFICIENT_BITS = 0x3B808081


def product(left, right):
    return bits(floating(left) * floating(right))


def fixture(seed, mode):
    memory = {STACK + index: (index * 17 + seed * 11 + 0xA5) & 0xFF
              for index in range(-0x500, 0x100)}
    memory.update({STATE + index: (index * 13 + seed * 19 + 0x59) & 0xFF
                   for index in range(-16, 0x120)})
    memory.update({OUTPUT + index: (index * 11 + seed * 23 + 0x37) & 0xFF
                   for index in range(0x80)})
    identity = [bits(1.0 if index in (0, 5, 10, 15) else 0.0)
                for index in range(16)]
    for index, value in enumerate(identity):
        put(memory, IDENTITY + index * 4, value)
    put(memory, IDENTITY + 0x40, 0xA5000000 | seed)
    put(memory, IDENTITY + 0x44, 0x5A000000 | mode)
    put(memory, SCALE_COEFFICIENT, COEFFICIENT_BITS)
    positions = (
        ((seed - 15) * 1.25, (19 - seed) * -0.75,
         (seed % 9 - 4) * 3.5),
        ((seed + 1) * -2.25, (seed - 7) * 1.75,
         (seed % 7 - 3) * -4.0),
    )[mode & 1]
    scales = (-255.0, -0.0, 127.5, 255.0, 510.0)
    for offset, value in zip((0x48, 0x4C, 0x50), positions):
        put(memory, STATE + offset, bits(value))
    put(memory, STATE + 0xF8, bits(scales[(seed + mode) % len(scales)]))
    return memory


def reference(initial):
    memory = dict(initial)
    values = [read(memory, IDENTITY + index * 4) for index in range(16)]
    values[12] = read(memory, STATE + 0x48)
    values[13] = read(memory, STATE + 0x4C)
    values[14] = read(memory, STATE + 0x50)
    scale = product(read(memory, STATE + 0xF8),
                    read(memory, SCALE_COEFFICIENT))
    for index in (0, 1, 2, 4, 5, 6, 8, 9, 10):
        values[index] = product(values[index], scale)
    for index, value in enumerate(values):
        put(memory, OUTPUT + index * 4, value)
    return memory, [(CONVERT, tuple(values))]


def public(memory):
    return (
        bytes(memory[STATE + index] for index in range(0x110)),
        bytes(memory[OUTPUT + index] for index in range(0x80)),
        bytes(memory[IDENTITY + index] for index in range(0x48)),
        bytes(memory[SCALE_COEFFICIENT + index] for index in range(4)),
    )


class TranslationScaleOracle(TimingOracle):
    def __init__(self, words, memory, phase=0):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(OUTPUT, STATE))
        self.ordinal = 0

    def record_call(self, target):
        if target != CONVERT or self.ordinal:
            raise AssertionError("Unexpected matrix callback helper %08X" % target)
        matrix, output = self.arguments(2)
        if output != OUTPUT:
            raise AssertionError("Matrix callback output pointer changed")
        values = tuple(read(self.memory, matrix + index * 4)
                       for index in range(16))
        event = (target, values)
        self.calls.append(event)
        self.events.append(("CALL",) + event)

    def hook(self, target):
        matrix, output = self.r[4], self.r[5]
        for index in range(16):
            put(self.memory, output + index * 4,
                read(self.memory, matrix + index * 4))
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.hi, self.lo = 0xA7000010, 0xA7000011
        self.ordinal += 1


def controls():
    body = candidate.SELECTED_MATCH
    variants = {
        "wrong-x-position": body.replace(
            "state->xPosition", "state->yPosition", 1),
        "wrong-y-position": body.replace(
            "state->yPosition", "state->zPosition", 1),
        "wrong-z-position": body.replace(
            "state->zPosition", "state->xPosition", 1),
        "wrong-scale-source": body.replace(
            "state->scaleByte", "state->xPosition", 1),
        "missing-first-scale": body.replace(
            "    workspace.values[0][0] *= scale;\n", "", 1),
        "missing-last-scale": body.replace(
            "    workspace.values[2][2] *= scale;\n", "", 1),
        "scaled-translation": body.replace(
            "    workspace.values[2][2] *= scale;",
            "    workspace.values[2][2] *= scale;\n"
            "    workspace.values[3][0] *= scale;", 1),
        "wrong-conversion-output": body.replace(
            "guMtxF2L(workspace.values, output);",
            "guMtxF2L(workspace.values, (Mtx *)state);", 1),
        "wrong-return": body.replace("    return 1;", "    return 0;", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("A translation-scale control did not alter the source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
typedef union { unsigned long long align; u8 bytes[64]; } Mtx;
''' + candidate.INSTALL_TYPES + r'''
static MatrixOnlyWorkspace15158920 D_8008AE18;
static f32 D_800A6070;
static union { unsigned long long align; u8 bytes[0x110]; } stateStore;
static Mtx output;
static u32 expected[16], calls, failed;
static f32 number(u32 value) { union { u32 u; f32 f; } cast; cast.u = value; return cast.f; }
static u32 word(f32 value) { union { u32 u; f32 f; } cast; cast.f = value; return cast.u; }
__attribute__((noinline)) void guMtxF2L(f32 matrix[4][4], Mtx *destination) {
    u32 index;
    if (calls++ != 0u || destination != &output) failed = 1u;
    for (index = 0; index < 16; index++) {
        u32 value = ((u32 *)matrix)[index];
        if (value != expected[index]) failed = 1u;
        ((u32 *)destination)[index] = value;
    }
}
''' + body + r'''
static int one(u32 seed) {
    TranslationScaleState15158920 *state = (TranslationScaleState15158920 *)stateStore.bytes;
    static const f32 scales[5] = {-255.0f, -0.0f, 127.5f, 255.0f, 510.0f};
    u32 index; f32 scale;
    for (index = 0; index < sizeof(stateStore.bytes); index++) stateStore.bytes[index] = (u8)(index * 13u + seed * 19u + 0x59u);
    for (index = 0; index < 16; index++) D_8008AE18.values[index / 4][index % 4] = ((s32)((index * 7u + seed * 3u) % 31u) - 15) * 0.125f;
    D_800A6070 = number(0x3B808081u);
    state->xPosition = ((s32)seed - 2047) * 1.25f;
    state->yPosition = (2049 - (s32)seed) * -0.75f;
    state->zPosition = ((s32)(seed % 17u) - 8) * 3.5f;
    state->scaleByte = scales[seed % 5u];
    for (index = 0; index < 16; index++) expected[index] = word(D_8008AE18.values[index / 4][index % 4]);
    expected[12] = word(state->xPosition); expected[13] = word(state->yPosition); expected[14] = word(state->zPosition);
    scale = state->scaleByte * D_800A6070;
    for (index = 0; index < 3; index++) expected[index] = word(number(expected[index]) * scale);
    for (index = 4; index < 7; index++) expected[index] = word(number(expected[index]) * scale);
    for (index = 8; index < 11; index++) expected[index] = word(number(expected[index]) * scale);
    calls = failed = 0u;
    if (func_15158920(&output, state) != 1 || calls != 1u || failed) return 1;
    for (index = 0; index < 16; index++) if (((u32 *)&output)[index] != expected[index]) return 1;
    return 0;
}
__attribute__((force_align_arg_pointer,noreturn)) void _start(void) {
    u32 seed; int result = 0;
    for (seed = 0; seed < 4096u; seed++) result |= one(seed);
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


class TranslationScaleMatrixMatchTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.values = match.prepare(ROOT, cls.output)
        cls.report = cls.values["report"]
        image = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(">%dI" % match.WORDS, image, match.ROM))

    @classmethod
    def tearDownClass(cls):
        (cls.output / "test-receipt.json").write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_owner_image_registry_relocations_and_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_frame"], report["retail_frame"],
             report["natural_positional_differences"], report["guards"],
             report["relocations"], report["neighbors"]),
            (64, 0x60, 0x60, 22, 22, 5, 36))
        self.assertEqual(report["functions"], 6052)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"]["aligned_pointer_literals"],
                         ["0x22f8d4"])
        self.assertEqual(report["game_data"]["bytes"], 189088)
        self.assertEqual(report["game_data"]["owner_count"], 720)
        self.assertTrue(report["game_data"]["exact"])
        text, functions, relocations = parse_object(self.values["qualified_owner"])
        info = functions[match.FUNCTION]
        bindings = {
            offset - info["value"]: rows for offset, rows in relocations.items()
            if info["value"] <= offset < info["value"] + info["size"]
        }
        self.assertEqual(bindings, match.RETAIL_BINDINGS)
        with (ROOT / match.GUARDS).open(newline="") as stream:
            rows = [row for row in csv.DictReader(stream)
                    if row["filename"] == match.FILENAME and
                    row["function"] == match.FUNCTION]
        expected = [match.complete_row(row) for row in match.PATCH_ROWS]
        self.assertEqual(rows, expected if report["source_installed"] else [])
        self.receipt["owner_image"] = {
            "words": report["words"],
            "guards": report["guards"],
            "relocations": report["relocations"],
            "neighbors": report["neighbors"],
            "functions": report["functions"],
            "protected_game_data_bytes": report["game_data"]["bytes"],
        }

    def test_02_guest_semantics_cover_every_word(self):
        seen = set()
        count = 0
        for seed, mode, phase in itertools.product(range(32), range(4), (0, 8)):
            initial = fixture(seed, mode)
            wanted, calls = reference(initial)
            model = TranslationScaleOracle(
                self.words, initial, phase=phase).run()
            self.assertEqual(public(model.memory), public(wanted))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[2], 1)
            self.assertEqual(model.ordinal, 1)
            seen.update(pc - match.ENTRY for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            count += 1
        self.assertEqual(count, 256)
        self.assertEqual(seen, set(range(0, match.SIZE, 4)))
        self.receipt["guest"] = {
            "cases": count,
            "covered_words": len(seen),
        }

    def test_03_native_profiles_and_semantic_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED_MATCH,
                       optimization, 0)
        variants = controls()
        for label, body in variants.items():
            run_native("control-" + label, body, "-O2", 1)
        self.receipt["native"] = {
            "positive_cases": 4096 * 3,
            "controls": sorted(variants),
        }

    def test_04_direct_candidate_shape_and_retail_closure(self):
        result = candidate.compare(
            "test-direct-owner", candidate.SELECTED_MATCH)
        self.assertEqual(
            (result["words"], result["frame"], result["differences"],
             result["raw_sha256"], result["retail_sha256"]),
            (64, 0x60, 22,
             "1836ec5d90aeb2ca1280db25c74d9050c7d91568bb99961efed0e0551c7d3782",
             match.RETAIL_SHA256))
        self.assertEqual(
            [row["offset"] for row in result["difference_rows"]],
            [int(row["offset"], 0) for row in match.PATCH_ROWS])
        retail = (ROOT / match.ROM_IMAGE).read_bytes()[
            match.ROM:match.ROM + match.SIZE]
        retail_words = list(struct.unpack(">%dI" % match.WORDS, retail))
        old, _, _ = load_elf_functions(
            str(self.values["predecessor_elf"]), "mips-linux-gnu-objdump")
        new, _, _ = load_elf_functions(
            str(self.values["qualified_elf"]), "mips-linux-gnu-objdump")
        self.assertNotEqual(old[match.FUNCTION], retail_words)
        self.assertEqual(new[match.FUNCTION], retail_words)
        self.receipt["closure"] = {
            "natural_differences": result["differences"],
            "retail_sha256": result["retail_sha256"],
            "changed_bodies": self.report["changed_bodies"],
        }


if __name__ == "__main__":
    unittest.main()
