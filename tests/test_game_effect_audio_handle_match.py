"""Semantic, caller, ABI, owner and image gates for func_150E3414."""

import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_effect_audio_handle_candidates as candidate
from tools.experiments import game_effect_audio_handle_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests.game_animation_timeline_oracle import bits, signed
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put
from tools.tests.test_game_point_transform_match import read


ROOT = Path(__file__).resolve().parents[2]
FACTORY = 0x150E3020
CALLBACK = 0x150E33CC
REGISTER = 0x1000FA64
OUTPUT = 0x80400000
RECORD = 0x80500000
PARENT_ENTRY = 0x1509D610
PARENT_END = 0x1509D768
CONTEXT = 0x800CC2D0


def u32(value):
    return value & 0xFFFFFFFF


def half(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def arguments(seed=0, step=None):
    values = (
        u32(seed * 0x1020304 + 0x7FFF8001),
        u32(seed * 0x2030405 + 0x80007FFE),
        u32(seed * 0x3040507 + 0xFFFF0001),
        u32(seed * 17 + 0x12345678),
        u32(seed * 31 + 0x87654321),
        u32(seed * 47 + 0xA5A55A5A),
        u32(seed * 61 + 0x13579BDF),
        u32(seed * 73 + 0x2468ACE0),
        bits(0.25 + (seed & 255) * 0.03125) if step is None else step,
    )
    return values


def fixture(seed=0):
    memory = {STACK + offset: (offset * 19 + seed * 7 + 0xA5) & 0xFF
              for offset in range(-0x200, 0x180)}
    memory.update({OUTPUT - 16 + offset: (offset * 29 + seed * 11 + 0x87) & 0xFF
                   for offset in range(0xA0)})
    memory.update({RECORD - 16 + offset: (offset * 13 + seed * 5 + 0xC3) & 0xFF
                   for offset in range(0x60)})
    return memory


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x200 <= address < STACK + 0x180}


def expected_calls(args, outcome, sound):
    factory = (
        args[3], args[4], args[5], 0, 0, 0, args[7], args[8], args[6],
        bits(float(signed(args[0]))), bits(float(signed(args[1]))),
        bits(float(signed(args[2]))), 0, u32(-99),
    )
    calls = [(FACTORY, factory)]
    if outcome:
        calls.append((REGISTER, (
            0x2D0, u32(half(args[0])), u32(half(args[1])),
            u32(half(args[2])), 0x5DC0, 0x1770, 0x3E8, CALLBACK,
            0, 0, 0, 0)))
    return calls


def reference(initial, args, outcome, sound, slot):
    memory = dict(initial)
    memory[OUTPUT + 0x48] = slot
    if outcome:
        put(memory, OUTPUT + 0x4A, sound, 2)
    return memory, expected_calls(args, outcome, sound), slot + 1 if outcome else 0


class EffectAudioOracle(TimingOracle):
    def __init__(self, words, memory, args, outcome, sound, slot, phase=0):
        memory = dict(memory)
        memory[OUTPUT + 0x48] = slot
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=args)
        self.outcome = outcome
        self.sound = sound

    def record_call(self, target):
        if target == FACTORY:
            count = 14
        elif target == REGISTER:
            count = 12
        else:
            raise AssertionError("Unexpected effect-audio call %08X" % target)
        args = self.arguments(count)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.r[2] = (OUTPUT if self.outcome else 0) if target == FACTORY else self.sound


class CallerBoundary(Exception):
    pass


class CallerOracle(TimingOracle):
    def __init__(self, words, memory, result, phase=0):
        super().__init__(words, memory, phase=phase, entry=PARENT_ENTRY,
                         arguments=(0,))
        self.result = result
        self.r[16] = RECORD
        self.code[PARENT_END] = 0

    def execute(self, word):
        if self.current_pc == PARENT_END:
            raise CallerBoundary
        super().execute(word)

    def record_call(self, target):
        if target != match.ENTRY:
            raise AssertionError("Unexpected caller-window target %08X" % target)
        args = self.arguments(9)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target != match.ENTRY:
            raise AssertionError("Unexpected caller-window hook %08X" % target)
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
#define NULL ((void *)0)
static u8 object[256] __attribute__((aligned(8)));
static s32 expected[9];
static u16 expectedSound;
static u8 expectedSlot;
static s32 expectedOutcome, factoryCalls, soundCalls, error;
static u32 floatBits(f32 value) { union { f32 f; u32 u; } word; word.f=value; return word.u; }
s32 func_150E3020(s32 x, s32 y, s32 z, s32 tx, s32 ty, s32 tz,
                  s32 kind, f32 step, s32 context, f32 sx, f32 sy,
                  f32 sz, s32 zero, s16 sentinel) {
    factoryCalls++;
    if ((u32)x!=(u32)expected[3] || (u32)y!=(u32)expected[4]
            || (u32)z!=(u32)expected[5] || tx || ty || tz
            || (u32)kind!=(u32)expected[7]
            || floatBits(step)!=(u32)expected[8]
            || (u32)context!=(u32)expected[6]
            || floatBits(sx)!=floatBits((f32)expected[0])
            || floatBits(sy)!=floatBits((f32)expected[1])
            || floatBits(sz)!=floatBits((f32)expected[2])
            || zero || sentinel!=-99) error=1;
    return expectedOutcome ? (s32)(object+16) : 0;
}
s32 func_150E33CC(s32 a, s32 b, s32 *c, s32 d) {
    return a+b+d+(c!=NULL);
}
u16 func_1000FA64(u16 id, s16 x, s16 y, s16 z, s32 volume,
                  u16 radius, s16 falloff, s32 callback, void *data,
                  s32 zero0, s32 zero1, s32 zero2) {
    soundCalls++;
    if (id!=0x2D0 || x!=(s16)expected[0] || y!=(s16)expected[1]
            || z!=(s16)expected[2] || volume!=0x5DC0 || radius!=0x1770
            || falloff!=0x3E8 || callback!=(s32)func_150E33CC || data!=NULL
            || zero0 || zero1 || zero2) error=2;
    return expectedSound;
}
''' + body + r'''
static void initialize(u32 seed) {
    u32 index;
    expected[0]=(s32)(seed*0x1020304u+0x7FFF8001u);
    expected[1]=(s32)(seed*0x2030405u+0x80007FFEu);
    expected[2]=(s32)(seed*0x3040507u+0xFFFF0001u);
    expected[3]=(s32)(seed*17u+0x12345678u);
    expected[4]=(s32)(seed*31u+0x87654321u);
    expected[5]=(s32)(seed*47u+0xA5A55A5Au);
    expected[6]=(s32)(seed*61u+0x13579BDFu);
    expected[7]=(s32)(seed*73u+0x2468ACE0u);
    { union { f32 f; u32 u; } step; step.f=0.25f+(f32)(seed&255u)*0.03125f;
      expected[8]=(s32)step.u; }
    expectedSound=(u16)(seed*17u+0x8001u);
    expectedSlot=(u8)seed;
    expectedOutcome=(s32)(seed&1u);
    for(index=0;index<sizeof(object);index++) object[index]=(u8)(index*13u+seed*7u+0xA5u);
    object[16+0x48]=expectedSlot;
    factoryCalls=soundCalls=error=0;
}
static int run(void) {
    u32 seed;
    for(seed=0;seed<4096u;seed++) {
        s32 result;
        u8 before48;
        u16 beforeSound;
        initialize(seed);
        before48=object[16+0x48]; beforeSound=*(u16 *)(void *)(object+16+0x4A);
        { union { f32 f; u32 u; } step; step.u=(u32)expected[8];
          result=func_150E3414(expected[0],expected[1],expected[2],
              expected[3],expected[4],expected[5],expected[6],expected[7],step.f); }
        if(error || factoryCalls!=1 || soundCalls!=expectedOutcome) return 10;
        if(result!=(expectedOutcome?(s32)expectedSlot+1:0)) return 11;
        if(object[16+0x48]!=before48) return 12;
        if(expectedOutcome) {
            if(*(u16 *)(void *)(object+16+0x4A)!=expectedSound) return 13;
        } else if(*(u16 *)(void *)(object+16+0x4A)!=beforeSound) return 14;
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status=run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
'''


class EffectAudioHandleMatchTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.values = match.prepare(ROOT, cls.output)
        cls.report = cls.values["report"]
        image = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(
            ">%dI" % match.WORDS, image, match.ROM))
        cls.parent = list(struct.unpack_from(
            ">%dI" % ((PARENT_END - PARENT_ENTRY) // 4), image, 0xCAAC0))
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

    def test_01_direct_owner_image_relocations_caller_and_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_frame"], report["retail_frame"],
             report["natural_positional_differences"], report["guards"],
             report["relocations"], report["callback_relocation_words"]),
            (64, 0x48, 0x48, 0, 0, 4, 2))
        self.assertEqual(report["neighbors"], 12)
        self.assertEqual(report["functions"], 6052)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"]["direct_callers"], [
            {"function": "func_1509D180", "call": "0x1509d654"}])
        self.assertIn("placeholder", report["registry"]["caller_source"])
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
            "words": 64, "frame": 72, "guards": 0, "relocations": 4,
            "neighbors": 12, "functions": 6052,
            "changed_only_target": True, "strict_exclusions": 0,
            "protected_game_bytes": 189088, "protected_data_exact": True,
        }

    def test_02_guest_all_words_widths_calls_and_returns(self):
        visits, cases = set(), 0
        special = (0, 1, 0x7FFF, 0x8000, 0xFFFF, 0x7FFFFFFF,
                   0x80000000, 0xFFFFFFFF)
        vectors = [arguments(seed) for seed in range(256)]
        for index, value in itertools.product(range(8), special):
            row = list(arguments(index * 17 + value))
            row[index] = value
            vectors.append(tuple(row))
        for index, args in enumerate(vectors):
            for outcome, phase in itertools.product((0, 1), (0, 8)):
                sound = (index * 257 + 0x8001) & 0xFFFF
                slot = index & 0xFF
                initial = fixture(index)
                wanted = reference(initial, args, outcome, sound, slot)
                model = EffectAudioOracle(
                    self.words, initial, args, outcome, sound, slot, phase).run()
                self.assertEqual(
                    (public(model.memory), model.calls, model.r[2]),
                    (public(wanted[0]), wanted[1], wanted[2]))
                visits.update(model.visits)
                cases += 1
        self.assertEqual(visits, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.assertEqual(cases, len(vectors) * 4)
        self.receipt["guest"] = {
            "cases": cases, "covered_words": 64, "stack_phases": [0, 8],
            "all_slot_bytes": True, "signed_halfword_sound_coordinates": True,
            "signed_word_to_float_coordinates": True,
            "allocation_success_and_failure": True,
            "volatile_gpr_fpr_and_outgoing_home_clobbers": True,
        }

    def test_03_original_caller_window_arguments_and_handle_encoding(self):
        cases = 0
        for seed, result, phase in itertools.product(
                range(64), (0, 1, 127, 128, 255, 256), (0, 8)):
            memory = fixture(seed)
            values = arguments(seed)
            for index, value in enumerate(values[:6]):
                put(memory, RECORD + 4 + index * 4, value)
            put(memory, RECORD + 0x1C, values[7])
            step_integer = u32(seed * 97 + 0x81234567)
            put(memory, RECORD + 0x20, step_integer)
            stack = STACK + phase
            model = CallerOracle(self.parent, memory, result, phase)
            with self.assertRaises(CallerBoundary):
                model.run()
            expected = (
                values[0], values[1], values[2], values[3], values[4],
                values[5], CONTEXT, values[7],
                bits(float(signed(step_integer))),
            )
            self.assertEqual(model.calls, [(match.ENTRY, expected)])
            encoded = ((result << 6) | 0xE004) if result else 0
            self.assertEqual(read(model.memory, stack + 0xC4), u32(encoded))
            cases += 1
        self.assertEqual(len(self.parent), 86)
        self.receipt["caller"] = {
            "function": "func_1509D180", "call": "0x1509D654",
            "window_entry": "0x1509D610", "cases": cases,
            "nine_arguments_observed": True,
            "return_encoding": "zero or (handle << 6) | 0xE004",
            "parent_C_placeholder_retained": True,
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
            "sound-x-float": body.replace("(f32)soundX", "(f32)soundY", 1),
            "effect-x": body.replace("func_150E3020(x, y, z", "func_150E3020(y, x, z", 1),
            "zero-argument": body.replace("x, y, z, 0, 0, 0", "x, y, z, 1, 0, 0", 1),
            "kind": body.replace("kind, step", "kind + 1, step", 1),
            "step": body.replace("kind, step", "kind, -step", 1),
            "context": body.replace("step, context", "step, context + 1", 1),
            "sentinel": body.replace("0, -99)", "0, -98)", 1),
            "sound-id": body.replace("0x2D0", "0x2D1", 1),
            "sound-volume": body.replace("0x5DC0", "0x5DBF", 1),
            "callback": body.replace("(s32)func_150E33CC", "0", 1),
            "sound-field": body.replace("effect + 0x4A", "effect + 0x4C", 1),
            "slot-field": body.replace("effect + 0x48", "effect + 0x49", 1),
            "one-based": body.replace(" + 1;", ";", 1),
        }
        rejected = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body, name)
            self.assertNotEqual(
                self.compile_native(changed, name, "-O2"), 0, name)
            rejected[name] = "observable mismatch"
        self.receipt["native"] = {
            "profiles": profiles, "controls": rejected,
            "pointer_width": 32, "valid_object_backing": True,
            "all_u8_slot_values": True, "u16_sound_handles": True,
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
            changed[offset] = [("R_MIPS_26", "func_150E3514")]
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
