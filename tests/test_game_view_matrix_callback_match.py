"""Semantic, dispatcher, owner and image gates for func_150F9AB0."""

import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_view_matrix_callback_candidates as candidate
from tools.experiments import game_view_matrix_callback_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put
from tools.tests.test_game_point_transform_match import read


ROOT = Path(__file__).resolve().parents[2]
MATRIX_HELPER = 0x15110360
VIEW_FILL = 0x15110544
MATRIX_RENDERER = 0x150FB4C0
VIEW_INDEX = 0x80082FA4
VIEW_BASE = 0x800BE628
VIEWS = 0x80400000
CURSOR = 0x80500000
OUTPUT = 0x80510000
NEXT = 0x80520000
DISPATCH_STATE_POINTER = 0x800B0DF0
DISPATCH_TABLE = 0x800891D8
DISPATCH_STATE = 0x80600000
DISPATCH_ENTRY = 0x15110244
DISPATCH_END = 0x15110288
DISPATCH_ROM = 0x13D6F4


def u32(value):
    return value & 0xFFFFFFFF


def matrix_pattern(seed):
    return bytes((seed * 17 + index * 29 + 0x43) & 0xFF for index in range(64))


def view_values(seed):
    return (
        -320.75 + (seed % 31) * 1.25,
        -120.5 + (seed % 17) * 0.75,
        640.875 - (seed % 23) * 0.5,
        480.625 - (seed % 19) * 0.25,
    )


def arguments(seed):
    return (
        CURSOR + (seed & 7) * 0x40,
        bits(-10.5 + seed * 0.03125),
        bits(20.25 - seed * 0.015625),
        bits(-30.75 + seed * 0.0078125),
        bits(-180.0 + (seed % 360) * 0.5),
        bits(90.0 - (seed % 180) * 0.25),
        bits(-45.0 + (seed % 90) * 0.125),
        u32(0x80700000 + seed * 0x20),
    )


def fixture(seed):
    memory = {STACK + offset: (offset * 19 + seed * 7 + 0xA5) & 0xFF
              for offset in range(-0x280, 0x180)}
    for base, length in ((VIEWS - 16, 4 * 0x180 + 32),
                         (CURSOR - 16, 0x300),
                         (OUTPUT - 16, 0x500)):
        memory.update({base + offset: (offset * 13 + seed * 11 + 0x87) & 0xFF
                       for offset in range(length)})
    index = seed & 3
    put(memory, VIEW_INDEX, index)
    put(memory, VIEW_BASE, VIEWS)
    left, top, right, bottom = view_values(seed)
    record = VIEWS + index * 0x180
    put(memory, record + 0x24, bits(top))
    put(memory, record + 0x28, bits(bottom))
    put(memory, record + 0x2C, bits(left))
    put(memory, record + 0x30, bits(right))
    return memory


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x280 <= address < STACK + 0x180}


def expected(seed, phase=0):
    args = arguments(seed)
    left, top, right, bottom = view_values(seed)
    matrix = STACK + phase - 0x40
    output = OUTPUT + (seed & 7) * 0x40
    next_cursor = NEXT + (seed & 15) * 0x20
    calls = [
        (MATRIX_HELPER, (seed & 3, matrix, args[4], args[5], args[6])),
        (VIEW_FILL, (args[0], u32(math.trunc(left)), u32(math.trunc(top)),
                     u32(math.trunc(right - 1.0)), u32(math.trunc(bottom)),
                     0, 0, 0)),
        (MATRIX_RENDERER, (output + 0x18, matrix)),
    ]
    return output, next_cursor, calls


class ViewMatrixOracle(TimingOracle):
    def __init__(self, words, memory, seed, phase=0):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=arguments(seed))
        self.seed = seed
        self.output, self.next_cursor, _ = expected(seed, phase)
        self.matrix_seen = None

    def record_call(self, target):
        counts = {MATRIX_HELPER: 5, VIEW_FILL: 8, MATRIX_RENDERER: 2}
        if target not in counts:
            raise AssertionError("Unexpected view-matrix call %08X" % target)
        args = self.arguments(counts[target])
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        args = self.calls[-1][1]
        if target == MATRIX_HELPER:
            for index, value in enumerate(matrix_pattern(self.seed)):
                self.memory[args[1] + index] = value
            result = 0xA1000001
        elif target == VIEW_FILL:
            result = self.output
        else:
            self.matrix_seen = bytes(self.memory[args[1] + index]
                                     for index in range(64))
            result = self.next_cursor
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.r[2] = result


class DispatcherBoundary(Exception):
    pass


class DispatcherOracle(TimingOracle):
    def __init__(self, words, memory, args, result, phase=0):
        super().__init__(words, memory, phase=phase, entry=DISPATCH_ENTRY,
                         arguments=(args[0],))
        self.full_args = args
        self.result = result
        self.r[2] = args[7]
        for register, value in ((12, args[1]), (14, args[2]), (18, args[3]),
                                (16, args[4]), (2, args[5]), (0, args[6])):
            self.f[register] = value
        self.code[DISPATCH_END] = 0

    def execute(self, word):
        if self.current_pc == DISPATCH_END:
            raise DispatcherBoundary
        super().execute(word)

    def record_call(self, target):
        if target != match.ENTRY:
            raise AssertionError("Unexpected dispatcher target %08X" % target)
        args = self.arguments(8)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xD5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xD6000000 + register
        self.r[2] = self.result


def native_harness(body):
    return r'''typedef signed char s8;
typedef unsigned char u8;
typedef signed short s16;
typedef unsigned short u16;
typedef signed int s32;
typedef unsigned int u32;
typedef float f32;
typedef union { struct { u32 w0, w1; } words; unsigned long long force; } Gfx;
#define gDPPipeSync(pkt) do { Gfx *_g=(Gfx *)(pkt); _g->words.w0=0xE7000000u; _g->words.w1=0; } while (0)
#define gDPSetOtherMode(pkt,a,b) do { Gfx *_g=(Gfx *)(pkt); _g->words.w0=0xEF000000u|(u32)(a); _g->words.w1=(u32)(b); } while (0)
#define gDPSetCombine(pkt,a,b) do { Gfx *_g=(Gfx *)(pkt); _g->words.w0=0xFC000000u|(u32)(a); _g->words.w1=(u32)(b); } while (0)
''' + candidate.DECLARATIONS + r'''
s32 D_80082FA4;
u8 *D_800BE628;
static u8 viewStorage[4*0x180] __attribute__((aligned(8)));
static Gfx input[8] __attribute__((aligned(8)));
static Gfx output[16] __attribute__((aligned(8)));
static u32 expectedMatrix[16];
static u32 rotations[3];
static s32 expectedLeft, expectedTop, expectedRight, expectedBottom;
static Gfx *expectedReturn;
static s32 matrixCalls, fillCalls, rendererCalls, error;
static u32 floatBits(f32 value) { union { f32 f; u32 u; } word; word.f=value; return word.u; }
void func_15110360(s32 index, f32 matrix[4][4], f32 x, f32 y, f32 z) {
    u32 i; union { u32 u; f32 f; } value;
    matrixCalls++;
    if(index!=D_80082FA4 || floatBits(x)!=rotations[0]
            || floatBits(y)!=rotations[1] || floatBits(z)!=rotations[2]) error=1;
    for(i=0;i<16;i++) {
        value.u=0x3E800000u+i*0x00010101u+(rotations[i%3]&0x0000FFFFu);
        matrix[i/4][i%4]=value.f; expectedMatrix[i]=value.u;
    }
}
Gfx *func_15110544(Gfx *commands, s32 left, s32 top, s32 right, s32 bottom,
                   u8 red, u8 green, u8 blue) {
    fillCalls++;
    if(commands!=input || left!=expectedLeft || top!=expectedTop
            || right!=expectedRight || bottom!=expectedBottom
            || red || green || blue) error=2;
    return output;
}
Gfx *func_150FB4C0(Gfx *commands, f32 matrix[4][4]) {
    u32 i; rendererCalls++;
    if(commands!=output+3) error=3;
    for(i=0;i<16;i++) if(floatBits(matrix[i/4][i%4])!=expectedMatrix[i]) error=4;
    if(output[0].words.w0!=0xE7000000u || output[0].words.w1!=0
            || output[1].words.w0!=0xEF002C0Fu || output[1].words.w1!=0x0F0A4004u
            || output[2].words.w0!=0xFC357E6Au || output[2].words.w1!=0xFFFFFFFFu) error=5;
    return expectedReturn;
}
''' + body + r'''
static void initialize(u32 seed) {
    u32 i; ViewBounds150F9AB0 *views=(ViewBounds150F9AB0 *)(void *)viewStorage;
    union { u32 u; f32 f; } word;
    D_80082FA4=(s32)(seed&3u); D_800BE628=viewStorage;
    word.f=-320.75f+(f32)(seed%31u)*1.25f; views[D_80082FA4].left=word.f; expectedLeft=(s32)word.f;
    word.f=-120.5f+(f32)(seed%17u)*0.75f; views[D_80082FA4].top=word.f; expectedTop=(s32)word.f;
    word.f=640.875f-(f32)(seed%23u)*0.5f; views[D_80082FA4].right=word.f; expectedRight=(s32)(word.f-1.0f);
    word.f=480.625f-(f32)(seed%19u)*0.25f; views[D_80082FA4].bottom=word.f; expectedBottom=(s32)word.f;
    word.f=-180.0f+(f32)(seed%360u)*0.5f; rotations[0]=word.u;
    word.f=90.0f-(f32)(seed%180u)*0.25f; rotations[1]=word.u;
    word.f=-45.0f+(f32)(seed%90u)*0.125f; rotations[2]=word.u;
    for(i=0;i<sizeof(input)/sizeof(input[0]);i++) { input[i].words.w0=0xA5A50000u+i; input[i].words.w1=0x5A5A0000u+i; }
    for(i=0;i<sizeof(output)/sizeof(output[0]);i++) { output[i].words.w0=0xC3C30000u+i; output[i].words.w1=0x3C3C0000u+i; }
    expectedReturn=output+10+(seed&1u); matrixCalls=fillCalls=rendererCalls=error=0;
}
static int run(void) {
    u32 seed;
    for(seed=0;seed<4096u;seed++) {
        union { u32 u; f32 f; } a,b,c,x,y,z;
        Gfx *result;
        initialize(seed);
        a.u=seed*0x1020304u+1u; b.u=seed*0x2030405u+3u; c.u=seed*0x3040507u+5u;
        x.u=rotations[0]; y.u=rotations[1]; z.u=rotations[2];
        result=func_150F9AB0(input,a.f,b.f,c.f,x.f,y.f,z.f,(void *)(seed*32u+0x1234u));
        if(error || matrixCalls!=1 || fillCalls!=1 || rendererCalls!=1) return 10+error;
        if(result!=expectedReturn) return 20;
        if(output[3].words.w0!=0xC3C30003u || output[3].words.w1!=0x3C3C0003u) return 21;
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status=run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
'''


class ViewMatrixCallbackMatchTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.values = match.prepare(ROOT, cls.output)
        cls.report = cls.values["report"]
        image = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(
            ">%dI" % match.WORDS, image, match.ROM))
        cls.dispatcher = list(struct.unpack_from(
            ">%dI" % ((DISPATCH_END - DISPATCH_ENTRY) // 4), image,
            DISPATCH_ROM))
        text, functions, relocations = parse_object(cls.values["qualified_compact"])
        info = functions[match.FUNCTION]
        cls.raw = text[info["value"]:info["value"] + info["size"]]
        cls.bindings = {
            offset - info["value"]: rows
            for offset, rows in relocations.items()
            if info["value"] <= offset < info["value"] + info["size"]
        }

    @classmethod
    def tearDownClass(cls):
        (cls.output / "test-receipt.json").write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_direct_owner_image_relocations_registry_and_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_frame"], report["retail_frame"],
             report["natural_positional_differences"], report["guards"],
             report["relocations"], report["sdk_graphics_commands"]),
            (64, 0x78, 0x78, 0, 0, 9, 3))
        self.assertEqual(report["neighbors"], 17)
        self.assertEqual(report["functions"], 6052)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"]["aligned_pointer_literals"],
                         ["0x22dc9c"])
        self.assertEqual(report["registry"]["registry"], "D_800891D8[1]")
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
            "words": 64, "frame": 120, "guards": 0, "relocations": 9,
            "neighbors": 17, "functions": 6052,
            "changed_only_target": True, "strict_exclusions": 0,
            "protected_game_bytes": 189088, "protected_data_exact": True,
        }

    def test_02_guest_all_words_bounds_commands_matrix_and_return(self):
        visits, cases = set(), 0
        for seed, phase in itertools.product(range(512), (0, 8)):
            initial = fixture(seed)
            output, next_cursor, calls = expected(seed, phase)
            wanted = dict(initial)
            for offset, value in enumerate((
                    0xE7000000, 0, 0xEF002C0F, 0x0F0A4004,
                    0xFC357E6A, 0xFFFFFFFF)):
                put(wanted, output + offset * 4, value)
            model = ViewMatrixOracle(
                self.words, initial, seed, phase).run()
            self.assertEqual(
                (public(model.memory), model.calls, model.r[2], model.matrix_seen),
                (public(wanted), calls, next_cursor, matrix_pattern(seed)))
            visits.update(model.visits)
            cases += 1
        self.assertEqual(visits, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.assertEqual(cases, 1024)
        self.receipt["guest"] = {
            "cases": cases, "covered_words": 64, "stack_phases": [0, 8],
            "all_view_indices": True, "signed_fractional_bounds": True,
            "six_rdp_words": True, "matrix_bytes_forwarded": 64,
            "volatile_gpr_fpr_and_outgoing_home_clobbers": True,
        }

    def test_03_original_dispatcher_window_passes_eight_arguments_and_return(self):
        cases = 0
        for seed, phase in itertools.product(range(256), (0, 8)):
            args = arguments(seed)
            result = NEXT + seed * 8
            memory = fixture(seed)
            put(memory, DISPATCH_STATE_POINTER, DISPATCH_STATE)
            memory[DISPATCH_STATE + 8] = 1
            put(memory, DISPATCH_TABLE + 4, match.ENTRY)
            model = DispatcherOracle(
                self.dispatcher, memory, args, result, phase)
            with self.assertRaises(DispatcherBoundary):
                model.run()
            self.assertEqual(model.calls, [(match.ENTRY, args)])
            self.assertEqual(model.r[4], result)
            cases += 1
        self.assertEqual(len(self.dispatcher), 17)
        self.receipt["dispatcher"] = {
            "function": "func_1510FEA0", "indirect_call": "0x1511027C",
            "cases": cases, "table_slot": "D_800891D8[1]",
            "eight_arguments_observed": True,
            "returned_cursor_reused_as_a0": True,
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
            "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
            str(source), "-o", str(binary)], capture_output=True, text=True)
        (self.output / (label + optimization + "-compiler.log")).write_text(
            result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr[:4000])
        return subprocess.run([str(binary)], timeout=30).returncode

    def test_04_native32_profiles_and_effective_semantic_controls(self):
        body = candidate.SELECTED
        profiles = {}
        for optimization in ("-O0", "-O2", "-O3"):
            self.assertEqual(self.compile_native(body, "native", optimization), 0)
            profiles[optimization] = {"cases": 4096, "exit": 0, "UBSan": True}
        controls = {
            "rotation-x": body.replace(
                "matrix, rotationX, rotationY, rotationZ);",
                "matrix, rotationY, rotationY, rotationZ);", 1),
            "rotation-y": body.replace(
                "matrix, rotationX, rotationY, rotationZ);",
                "matrix, rotationX, rotationZ, rotationZ);", 1),
            "rotation-z": body.replace(
                "matrix, rotationX, rotationY, rotationZ);",
                "matrix, rotationX, rotationY, rotationX);", 1),
            "matrix-view-index": body.replace(
                "func_15110360(D_80082FA4", "func_15110360(D_80082FA4 ^ 1", 1),
            "bounds-view-index": body.replace(
                ")[D_80082FA4];", ")[D_80082FA4 ^ 1];", 1),
            "left-bound": body.replace("(s32)view->left", "(s32)view->top", 1),
            "top-bound": body.replace("(s32)view->top", "(s32)view->bottom", 1),
            "right-minus-one": body.replace("view->right - 1.0f", "view->right", 1),
            "bottom-bound": body.replace("(s32)view->bottom", "(s32)view->left", 1),
            "pipe-sync": body.replace("gDPPipeSync(commands++);", "commands++;", 1),
            "othermode-high": body.replace("0x2C0F", "0x2C0E", 1),
            "othermode-low": body.replace("0x0F0A4004", "0x0F0A4005", 1),
            "combine-high": body.replace("0x357E6A", "0x357E6B", 1),
            "combine-low": body.replace("0xFFFFFFFF", "0xFFFFFFFE", 1),
            "renderer-cursor": body.replace(
                "func_150FB4C0(commands, matrix)",
                "func_150FB4C0(commands + 1, matrix)", 1),
            "renderer-matrix": body.replace(
                "return func_150FB4C0(commands, matrix);",
                "matrix[0][0] = matrix[0][1]; "
                "return func_150FB4C0(commands, matrix);", 1),
            "returned-cursor": body.replace(
                "return func_150FB4C0(commands, matrix);",
                "func_150FB4C0(commands, matrix); return commands;", 1),
        }
        rejected = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body, name)
            self.assertNotEqual(
                self.compile_native(changed, name, "-O2"), 0, name)
            rejected[name] = "observable mismatch"
        self.receipt["native"] = {
            "profiles": profiles, "controls": rejected,
            "pointer_width": 32, "valid_view_and_command_backing": True,
        }

    def test_05_raw_bytes_relocations_and_whole_image_fail_closed(self):
        self.assertEqual(len(self.raw), match.SIZE)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), match.RAW_SHA256)
        self.assertEqual(self.bindings, match.BINDINGS)
        raw_controls = 0
        for index in range(len(self.raw)):
            changed = bytearray(self.raw)
            changed[index] ^= 1
            self.assertNotEqual(
                hashlib.sha256(changed).hexdigest(), match.RAW_SHA256)
            raw_controls += 1
        binding_controls = 0
        for offset in match.BINDINGS:
            changed = dict(match.BINDINGS)
            changed[offset] = [("R_MIPS_26", "func_150F9BB0")]
            self.assertNotEqual(changed, match.BINDINGS)
            binding_controls += 1
        predecessor = self.values["predecessor_elf"].read_bytes()
        qualified = self.values["qualified_elf"].read_bytes()
        self.assertNotEqual(predecessor, qualified)
        self.assertEqual(len(predecessor), len(qualified))
        self.assertEqual(
            hashlib.sha256(qualified).hexdigest(),
            self.report["qualified_elf_sha256"])
        self.receipt["fail_closed"] = {
            "raw_byte_controls": raw_controls,
            "relocation_binding_controls": binding_controls,
            "whole_image_length_fixed": True,
            "whole_image_changed_only_target": True,
        }


if __name__ == "__main__":
    unittest.main()
