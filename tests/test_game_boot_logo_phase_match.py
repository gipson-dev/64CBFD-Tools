"""Semantic, ABI, owner and image gates for func_151DE6D4."""

import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_boot_logo_phase_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put


ROOT = Path(__file__).resolve().parents[2]
OBJECTS = 0x800CC2D0
INPUT_FLAG = 0x80000300
TIMER = 0x800E0A90
STATUS_FLAGS = 0x800E0B9A
MODE = 0x8008FE28
PHASE = 0x800E0B94
TRANSITION = 0x800D2E40
INTENSITY = 0x800E0B96
REFRESH = 0x151E530C
REQUEST = 0x1501C730
TIMERS = (-1, 0, 0x14A, 0x14B, 0x1DF, 0x1E0, 0x258,
          0x259, 0x2CF, 0x2D0, 0x2D1, 0x348, 0x349, 0x400)
FLAGS = (0, 0x7FFF, 0x8000, 0xFFFF)


def get(memory, address, size):
    value = 0
    for offset in range(size):
        value = value << 8 | memory.get(address + offset, 0)
    return value


def fixture(timer, flags, input_value, phase):
    memory = {STACK + offset: (offset * 23 + 0x93) & 0xFF
              for offset in range(-0x100, 0x100)}
    put(memory, OBJECTS + 0x25C, 0xA5000101, 4)
    put(memory, OBJECTS + 0x18, 0x3F000000, 4)
    put(memory, INPUT_FLAG, input_value, 4)
    put(memory, TIMER, timer & 0xFFFFFFFF, 4)
    put(memory, STATUS_FLAGS, flags, 2)
    memory[MODE] = 0x51
    memory[PHASE] = 0x52
    memory[TRANSITION] = 0x53
    memory[INTENSITY] = 0x54
    return memory


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x100 <= address < STACK + 0x100}


def reference(initial, timer, flags, input_value):
    memory = dict(initial)
    calls = [(REFRESH, ())]
    put(memory, OBJECTS + 0x25C,
        get(memory, OBJECTS + 0x25C, 4) | 0x200, 4)
    put(memory, OBJECTS + 0x18, 0x447A0000, 4)
    if input_value == 0:
        timer = 0
        put(memory, TIMER, 0, 4)
    if timer >= 0x14B and flags & 0x8000:
        if timer < 0x1E0:
            timer = 0x1E0
            put(memory, TIMER, timer, 4)
        if timer >= 0x259 and timer < 0x2D0:
            timer = 0x2D0
            put(memory, TIMER, timer, 4)
    if timer >= 0x349:
        memory[MODE] = 2
        memory[PHASE] = 1
        memory[TRANSITION] = 0
        memory[INTENSITY] = 0xFF
        calls.append((REQUEST, (6, 0x21, 0, 0, 1)))
    return memory, calls


class BootLogoOracle(TimingOracle):
    def __init__(self, words, memory, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY)

    def record_call(self, target):
        if target == REFRESH:
            args = ()
        elif target == REQUEST:
            args = self.arguments(5)
        else:
            raise AssertionError("Unexpected boot-logo call %08X" % target)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target not in (REFRESH, REQUEST):
            raise AssertionError("Unexpected boot-logo hook %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xC7000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xC5000000 + register
        self.f[:20] = [0xC6000000 + index for index in range(20)]


def native_harness(body):
    return """typedef unsigned char u8;
typedef signed char s8;
typedef signed short s16;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
typedef struct {
    u8 pad0[0x18];
    f32 y_position;
    u8 pad1[0x240];
    s32 unk25C;
} struct127;
static struct127 D_800CC2D0[1];
static s32 D_80000300;
static s32 D_800E0A90;
static s16 D_800E0B9A;
static u8 D_8008FE28, D_800E0B94, D_800D2E40, D_800E0B96;
static s32 refreshCount, requestCount, badRequest;
void func_151E530C(void) { refreshCount++; }
void func_1501C730(s32 a, s32 b, s32 c, s32 d, s32 e) {
    requestCount++;
    if (a != 6 || b != 0x21 || c != 0 || d != 0 || e != 1)
        badRequest = 1;
}
%s
static int one(s32 timer, s32 flags, s32 input) {
    s32 expectedTimer = timer;
    s32 expectedRequest;
    D_800CC2D0[0].unk25C = (s32)0xA5000101U;
    D_800CC2D0[0].y_position = 0.5f;
    D_80000300 = input;
    D_800E0A90 = timer;
    D_800E0B9A = (s16)flags;
    D_8008FE28 = 0x51;
    D_800E0B94 = 0x52;
    D_800D2E40 = 0x53;
    D_800E0B96 = 0x54;
    refreshCount = requestCount = badRequest = 0;
    if (input == 0) expectedTimer = 0;
    if (expectedTimer >= 0x14B && (flags & 0x8000)) {
        if (expectedTimer < 0x1E0) expectedTimer = 0x1E0;
        if (expectedTimer >= 0x259 && expectedTimer < 0x2D0)
            expectedTimer = 0x2D0;
    }
    expectedRequest = expectedTimer >= 0x349;
    func_151DE6D4();
    if (refreshCount != 1 || badRequest || requestCount != expectedRequest)
        return 10;
    if ((u32)D_800CC2D0[0].unk25C != 0xA5000301U ||
            D_800CC2D0[0].y_position != 1000.0f) return 11;
    if (D_800E0A90 != expectedTimer) return 12;
    if (expectedRequest) {
        if (D_8008FE28 != 2 || D_800E0B94 != 1 ||
                D_800D2E40 != 0 || D_800E0B96 != 0xFF) return 13;
    } else if (D_8008FE28 != 0x51 || D_800E0B94 != 0x52 ||
            D_800D2E40 != 0x53 || D_800E0B96 != 0x54) return 14;
    return 0;
}
static int run(void) {
    static const s32 timers[] = {-1, 0, 0x14A, 0x14B, 0x1DF, 0x1E0,
        0x258, 0x259, 0x2CF, 0x2D0, 0x2D1, 0x348, 0x349, 0x400};
    static const s32 flags[] = {0, 0x7FFF, 0x8000, 0xFFFF};
    s32 i, j, input;
    for (i = 0; i < 14; i++)
        for (j = 0; j < 4; j++)
            for (input = 0; input < 2; input++)
                if (one(timers[i], flags[j], input ? 2 : 0)) return 20;
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
""" % body


class BootLogoPhaseMatchTests(unittest.TestCase):
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

    def test_01_direct_slot_owner_image_registry_and_protected_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_frame"], report["retail_frame"],
             report["natural_positional_differences"], report["guards"],
             report["relocations"]),
            (64, 0x20, 0x20, 0, 0, 20))
        self.assertEqual(report["neighbors"], 59)
        self.assertEqual(report["functions"], 6051)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"], {
            "direct_jal_calls": [],
            "aligned_pointer_literals": ["0x2348d8"],
            "registry": "D_8008FDEC[11] via func_151E51EC",
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
            "words": 64, "guards": 0, "relocations": 20,
            "neighbors": 59, "functions": 6051,
            "changed_only_target": True, "strict_exclusions": 0,
            "protected_game_bytes": 189088, "protected_data_exact": True,
        }

    def test_02_guest_routes_stack_phases_and_all_words(self):
        visits, cases = set(), 0
        for timer, flags, input_value, phase in itertools.product(
                TIMERS, FLAGS, (0, 2), (0, 8)):
            initial = fixture(timer, flags, input_value, phase)
            wanted, calls = reference(initial, timer, flags, input_value)
            model = BootLogoOracle(self.words, initial, phase).run()
            self.assertEqual(public(model.memory), public(wanted))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[29], STACK + phase)
            visits.update(model.visits)
            cases += 1
        self.assertEqual(
            visits, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.assertEqual(cases, 224)
        self.receipt["guest"] = {
            "cases": cases, "stack_phases": [0, 8],
            "words_covered": 64, "timers": list(TIMERS),
            "flags": list(FLAGS), "input_values": [0, 2],
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
            profiles[optimization] = {"cases": 112, "exit": 0, "UBSan": True}
        controls = {
            "refresh": body.replace("    func_151E530C();\n", ""),
            "object-flag": body.replace("0x200", "0x100", 1),
            "object-height": body.replace("1000.0f", "999.0f"),
            "input-reset": body.replace("D_80000300 == 0", "D_80000300 != 0"),
            "skip-start": body.replace("timer >= 0x14B", "timer >= 0x14A"),
            "skip-flag": body.replace("0x8000", "0x4000", 1),
            "first-snap": body.replace("0x1E0", "0x1DF"),
            "second-start": body.replace("timer >= 0x259", "timer >= 0x258"),
            "second-end": body.replace("timer < 0x2D0", "timer < 0x2D2"),
            "final-threshold": body.replace("timer >= 0x349", "timer >= 0x348"),
            "scene": body.replace("0x21, 0, 0, 1", "0x20, 0, 0, 1"),
            "intensity": body.replace("D_800E0B96 = 0xFF", "D_800E0B96 = 0xFE"),
        }
        rejected = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0, name)
            rejected[name] = "output mismatch"
        self.receipt["native"] = {"profiles": profiles, "controls": rejected}

    def test_04_raw_bytes_and_relocation_bindings_fail_closed(self):
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
            kind = rows[0][0]
            changed[offset] = [(kind, "D_80123450")]
            self.assertNotEqual(changed, match.BINDINGS)
            binding_controls += 1
        self.assertEqual((raw_controls, binding_controls), (256, 20))
        self.receipt["fail_closed"] = {
            "raw_byte_controls": raw_controls,
            "relocation_binding_controls": binding_controls,
        }


if __name__ == "__main__":
    unittest.main()
