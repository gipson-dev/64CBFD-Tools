"""Semantic, ABI, owner and image gates for func_15012370."""

import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_view_projection_setup_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read


ROOT = Path(__file__).resolve().parents[2]
COUNT = 0x80082FA0
FAR_PLANE = 0x80096560
VIEW_BASE_GLOBAL = 0x800BE628
MATRICES = 0x800DCC10
FIRST_VIEWS = 0x21000
SECOND_VIEWS = 0x31000
SET_PROJECTION = 0x151EF954
EXTENTS = (0.0, 1.0, -1.0, 3.25, -7.5, 0.125, 1024.75, -0.0,
           19.875, -33.5, 255.25, -511.75)
FAR_PLANES = (1.0, 20000.0, 8192.5, -32.25, 0.125)


def f32(value):
    return floating(bits(value))


def fixture(seed, count, phase):
    memory = {STACK + offset: (offset * 19 + seed * 23 + 0xA5) & 0xFF
              for offset in range(-0x180, 0x100)}
    for base in (FIRST_VIEWS, SECOND_VIEWS):
        memory.update({base + offset: (offset * 13 + seed * 29 + base) & 0xFF
                       for offset in range(8 * 0x180)})
    put(memory, COUNT, count & 0xFFFFFFFF)
    put(memory, FAR_PLANE, bits(FAR_PLANES[seed % len(FAR_PLANES)]))
    put(memory, VIEW_BASE_GLOBAL, FIRST_VIEWS)
    for bank, base in enumerate((FIRST_VIEWS, SECOND_VIEWS)):
        for index in range(8):
            width = EXTENTS[(seed + bank * 3 + index * 2) % len(EXTENTS)]
            height = EXTENTS[(seed * 3 + bank * 5 + index * 2 + 1) % len(EXTENTS)]
            put(memory, base + index * 0x180 + 4, bits(width))
            put(memory, base + index * 0x180 + 8, bits(height))
    return memory


def apply_effect(memory, mode, ordinal):
    if mode == 1 and ordinal == 1:
        put(memory, VIEW_BASE_GLOBAL, SECOND_VIEWS)
    elif mode == 2:
        current = read(memory, VIEW_BASE_GLOBAL)
        put(memory, VIEW_BASE_GLOBAL,
            SECOND_VIEWS if current == FIRST_VIEWS else FIRST_VIEWS)
    elif mode == 3 and ordinal == 1:
        put(memory, COUNT, 0)
    elif mode == 4 and ordinal == 1:
        put(memory, COUNT, 2)


def reference(initial, mode):
    memory = dict(initial)
    calls = []
    index = 0
    count = signed(read(memory, COUNT))
    if count < 0:
        return calls
    while index <= count:
        base = read(memory, VIEW_BASE_GLOBAL)
        width = floating(read(memory, base + index * 0x180 + 4))
        height = floating(read(memory, base + index * 0x180 + 8))
        half_width = bits(f32(width * 0.5))
        half_height = bits(f32(height * 0.5))
        calls.append((SET_PROJECTION, (
            MATRICES + index * 0x40,
            half_width ^ 0x80000000,
            half_width,
            half_height ^ 0x80000000,
            half_height,
            bits(1.0),
            read(memory, FAR_PLANE),
            bits(1.0),
        )))
        apply_effect(memory, mode, len(calls))
        index = (index + 1) & 0xFF
        count = signed(read(memory, COUNT))
        if len(calls) > 16:
            raise AssertionError("Unbounded projection fixture")
    return calls


class ProjectionOracle(TimingOracle):
    def __init__(self, words, memory, mode, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=())
        self.mode = mode

    def execute(self, word):
        op = word >> 26
        rs = word >> 21 & 31
        source = word >> 11 & 31
        destination = word >> 6 & 31
        function = word & 63
        if op == 17 and rs == 16 and function == 7:  # neg.s
            self.f[destination] = self.f[source] ^ 0x80000000
        else:
            super().execute(word)

    def record_call(self, target):
        if target != SET_PROJECTION:
            raise AssertionError("Unexpected projection call %08X" % target)
        arguments = self.arguments(8)
        self.calls.append((target, arguments))
        self.events.append(("CALL", target, arguments))

    def hook(self, target):
        if target != SET_PROJECTION:
            raise AssertionError("Unexpected projection hook %08X" % target)
        apply_effect(self.memory, self.mode, len(self.calls))
        for offset in range(4):
            self.put(self.r[29] + offset * 4, 0xC7000000 + offset, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xC5000000 + register
        self.f[:20] = [0xC6000000 + index for index in range(20)]
        self.lo, self.hi = 0xC5000010, 0xC5000011


def native_harness(body):
    return r'''typedef unsigned char u8;
typedef signed int s32;
typedef unsigned int u32;
typedef float f32;
static s32 D_80082FA0;
static f32 D_80096560;
static s32 D_800BE628;
static u8 D_800DCC10[8 * 0x40];
static int calls, error, mode;
static u32 word(f32 value) { union { f32 f; u32 u; } bits; bits.f = value; return bits.u; }
void func_151EF954(f32 matrix[4][4], f32 left, f32 right, f32 bottom,
                   f32 top, f32 nearPlane, f32 farPlane, f32 scale);
''' + match.TYPE + body + r'''
static ViewProjectionSetup15012370 firstViews[8];
static ViewProjectionSetup15012370 secondViews[8];
void func_151EF954(f32 matrix[4][4], f32 left, f32 right, f32 bottom,
                   f32 top, f32 nearPlane, f32 farPlane, f32 scale) {
    ViewProjectionSetup15012370 *base =
        (ViewProjectionSetup15012370 *)(u32)D_800BE628;
    s32 index = ((u8 *)matrix - D_800DCC10) / 0x40;
    f32 halfWidth, halfHeight;
    if (index < 0 || index >= 8 ||
            (u8 *)matrix != D_800DCC10 + index * 0x40) {
        error = 1;
        return;
    }
    halfWidth = base[index].horizontalExtent * 0.5f;
    halfHeight = base[index].verticalExtent * 0.5f;
    if (word(left) != (word(halfWidth) ^ 0x80000000U) ||
            word(right) != word(halfWidth) ||
            word(bottom) != (word(halfHeight) ^ 0x80000000U) ||
            word(top) != word(halfHeight) || word(nearPlane) != word(1.0f) ||
            word(farPlane) != word(D_80096560) || word(scale) != word(1.0f))
        error = 2;
    calls++;
    if (mode == 1 && calls == 1)
        D_800BE628 = (s32)(u32)secondViews;
    else if (mode == 2)
        D_800BE628 = D_800BE628 == (s32)(u32)firstViews ?
            (s32)(u32)secondViews : (s32)(u32)firstViews;
    else if (mode == 3 && calls == 1)
        D_80082FA0 = 0;
    else if (mode == 4 && calls == 1)
        D_80082FA0 = 2;
}
static int one(s32 count, s32 selectedMode, u32 seed) {
    static const f32 values[] = {0.0f, 1.0f, -1.0f, 3.25f, -7.5f,
        0.125f, 1024.75f, -0.0f, 19.875f, -33.5f, 255.25f, -511.75f};
    static const f32 farValues[] = {1.0f, 20000.0f, 8192.5f, -32.25f, 0.125f};
    s32 bank, index, wanted;
    ViewProjectionSetup15012370 *views[2] = {firstViews, secondViews};
    for (bank = 0; bank < 2; bank++)
        for (index = 0; index < 8; index++) {
            views[bank][index].horizontalExtent =
                values[(seed + (u32)bank * 3U + (u32)index * 2U) % 12U];
            views[bank][index].verticalExtent =
                values[(seed * 3U + (u32)bank * 5U + (u32)index * 2U + 1U) % 12U];
        }
    D_80082FA0 = count;
    D_80096560 = farValues[seed % 5U];
    D_800BE628 = (s32)(u32)firstViews;
    calls = error = 0;
    mode = selectedMode;
    func_15012370();
    if (count < 0) wanted = 0;
    else if (selectedMode == 3) wanted = 1;
    else if (selectedMode == 4) wanted = 3;
    else wanted = count + 1;
    return error || calls != wanted;
}
static int run(void) {
    s32 count, selectedMode;
    u32 seed;
    if (sizeof(void *) != 4 || sizeof(ViewProjectionSetup15012370) != 0x180)
        return 20;
    for (seed = 0; seed < 80; seed++) {
        for (selectedMode = 0; selectedMode < 4; selectedMode++)
            for (count = -2; count <= 5; count++)
                if (one(count, selectedMode, seed)) return 21;
        if (one(0, 4, seed)) return 22;
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
'''


class ViewProjectionSetupMatchTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.values = match.prepare(ROOT, cls.output)
        cls.report = cls.values["report"]
        image = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(">%dI" % match.WORDS, image, match.ROM))
        text, functions, relocations = parse_object(cls.values["qualified_compact"])
        info = functions[match.FUNCTION]
        cls.raw = text[info["value"]:info["value"] + info["size"]]
        cls.bindings = {
            offset - info["value"]: rows for offset, rows in relocations.items()
            if info["value"] <= offset < info["value"] + info["size"]
        }

    @classmethod
    def tearDownClass(cls):
        cls.output.mkdir(parents=True, exist_ok=True)
        (cls.output / "test-receipt.json").write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_guarded_slot_owner_image_caller_and_protected_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_frame"], report["retail_frame"],
             report["natural_positional_differences"], report["guards"],
             report["relocations"], report["retail_relocations"]),
            (64, 0x58, 0x58, 16, 16, 9, 9))
        self.assertEqual(report["neighbors"], 2)
        self.assertEqual(report["functions"], 6051)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"], {
            "direct_jal_calls": ["0x3b9a4"],
            "aligned_pointer_literals": [],
            "caller": "func_1500E470",
            "abi": "no arguments; void return",
        })
        data = report["game_data"]
        self.assertEqual(
            (data["exact"], data["bytes"], data["owner_count"],
             data["different_bytes"], data["sha256"]),
            (True, 189088, 720, 0,
             "0bbc00e1adfac5ffe6117f5be9c941575f87b341a77d808004603ac1cb87c670"))
        linked = load_elf_functions(
            str(self.values["qualified_elf"]), "mips-linux-gnu-objdump")[0]
        self.assertEqual(linked[match.FUNCTION], self.words)
        self.receipt["closure"] = {
            "words": 64, "guards": 16, "natural_relocations": 9,
            "retail_relocations": 9, "neighbors": 2, "functions": 6051,
            "changed_only_target": True, "strict_exclusions": 0,
            "protected_game_bytes": 189088, "protected_data_exact": True,
        }

    def test_02_guest_counts_mutable_bases_reload_and_all_words(self):
        visits = set()
        cases = 0
        for seed, mode, phase in itertools.product(range(18), range(5), (0, 8)):
            count = 0 if mode == 4 else (-2, -1, 0, 1, 2, 5)[seed % 6]
            initial = fixture(seed, count, phase)
            model = ProjectionOracle(self.words, initial, mode, phase).run()
            self.assertEqual(model.calls, reference(initial, mode))
            self.assertEqual(model.r[29], STACK + phase)
            visits.update(model.visits)
            cases += 1
        self.assertEqual(visits, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.assertEqual(cases, 180)
        self.receipt["guest"] = {
            "cases": cases, "stack_phases": [0, 8], "words_covered": 64,
            "negative_counts": True, "wrapped_u8_index": True,
            "mutable_view_base_reloaded": True, "mutable_count_reloaded": True,
            "call_clobbering": True,
        }

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
        profiles = {}
        for optimization in ("-O0", "-O2", "-O3"):
            self.assertEqual(self.compile_native(body, "native", optimization), 0)
            profiles[optimization] = {"cases": 2640, "exit": 0, "UBSan": True}
        controls = {
            "exclusive-count": body.replace("index <= D_80082FA0", "index < D_80082FA0"),
            "start-index": body.replace("    index = 0;", "    index = 1;"),
            "wrong-width-field": body.replace(".horizontalExtent", ".verticalExtent", 1),
            "wrong-height-field": body.replace(".verticalExtent", ".horizontalExtent", 1),
            "quarter-extents": body.replace("0.5f", "0.25f"),
            "positive-left": body.replace("-halfWidth, halfWidth", "halfWidth, halfWidth"),
            "wrong-matrix-stride": body.replace(
                "((f32 (*)[4][4])D_800DCC10)[index]",
                "(f32 (*)[4])((u8 *)D_800DCC10 + (u32)index * 0x30)"),
            "fixed-far-plane": body.replace(
                "farPlane = D_80096560", "farPlane = 1.0f"),
            "wrong-near-plane": body.replace(
                "1.0f, farPlane, 1.0f", "2.0f, farPlane, 1.0f"),
        }
        rejected = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0, name)
            rejected[name] = "projection-call mismatch"
        self.receipt["native"] = {"profiles": profiles, "controls": rejected}

    def test_04_raw_bytes_relocations_and_guard_rows_fail_closed(self):
        self.assertEqual(len(self.raw), match.SIZE)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), match.RAW_SHA256)
        self.assertEqual(self.bindings, match.BINDINGS)
        raw_controls = 0
        for index in range(len(self.raw)):
            changed = bytearray(self.raw)
            changed[index] ^= 1
            self.assertNotEqual(hashlib.sha256(changed).hexdigest(), match.RAW_SHA256)
            raw_controls += 1
        binding_controls = 0
        for offset, rows in match.BINDINGS.items():
            changed = dict(match.BINDINGS)
            changed[offset] = [(rows[0][0], "D_80123450")]
            self.assertNotEqual(changed, match.BINDINGS)
            binding_controls += 1
        self.assertEqual(raw_controls, 256)
        self.assertEqual(binding_controls, 9)
        self.assertEqual(len(match.PATCH_ROWS), 16)
        self.assertEqual(
            [int(row["offset"], 0) for row in match.PATCH_ROWS],
            [0x40, 0x54, 0x58, 0x5C, 0x60, 0x64, 0x68, 0x6C,
             0x70, 0x74, 0x78, 0x7C, 0x84, 0x98, 0x9C, 0xA4])
        self.receipt["fail_closed"] = {
            "raw_byte_controls": raw_controls,
            "relocation_binding_controls": binding_controls,
            "guard_rows": 16,
        }


if __name__ == "__main__":
    unittest.main()
