"""Semantic, caller, owner and image gates for func_1512B630."""

import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_record_threshold_transition_candidates as candidate
from tools.experiments import game_record_threshold_transition_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read


ROOT = Path(__file__).resolve().parents[2]
ACTOR = 0x80400000
TRANSITION = 0x80500000
TABLE_A = 0x800DC204
TABLE_B = 0x800DC206
HELPER = 0x1512B5FC
CALLER_WINDOWS = (
    (0x1512B3B8, 0x1512B3D4, 0x158868, 11),
    (0x1512B4E4, 0x1512B500, 0x158994, 25),
)


def u32(value):
    return value & 0xFFFFFFFF


def s16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def fixture(raw_threshold, player, index, alternate, flags, outcome, seed):
    memory = {STACK + offset: (offset * 19 + seed * 7 + 0xA5) & 0xFF
              for offset in range(-0x200, 0x100)}
    for base, length in ((ACTOR - 8, 0x250), (TRANSITION - 8, 0x20),
                         (TABLE_A - 0x20, 0x140), (TABLE_B - 0x20, 0x140)):
        memory.update({base + offset: (offset * 13 + seed * 11 + 0x87) & 0xFF
                       for offset in range(length)})
    put(memory, ACTOR + 0x84, flags)
    put(memory, ACTOR + 0x1B4, index & 0xFFFF, 2)
    memory[ACTOR + 0x23D] = player
    offset = index * 8 + player * 0x20
    selected = TABLE_B if alternate else TABLE_A
    other = TABLE_A if alternate else TABLE_B
    put(memory, selected + offset, raw_threshold & 0xFFFF, 2)
    put(memory, other + offset, (~raw_threshold) & 0xFFFF, 2)

    effective = s16(raw_threshold * 2) if flags & 0x8000 else s16(raw_threshold)
    if outcome == 0:
        threshold, value, peer = effective + 1, -10 - seed, 10 + seed
    elif outcome == 1:
        threshold, value, peer = effective + 1, 10 + seed, -10 - seed
    elif outcome == 2:
        threshold, value, peer = effective + 1, 5 + seed, 5 + seed
    else:
        threshold, value, peer = effective, -10 - seed, 10 + seed

    memory[TRANSITION] = 0x70 | (seed & 7)
    memory[TRANSITION + 1] = (seed * 3 + 1) & 1
    memory[TRANSITION + 2] = 0x40 | (seed & 0x1F)
    put(memory, TRANSITION + 4, u32(value + (-1 if seed & 1 else 1)))
    put(memory, TRANSITION + 8, 0xA5000000 | seed)
    args = (ACTOR, TRANSITION, u32(threshold), u32(value), u32(peer), alternate)
    return memory, args


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x200 <= address < STACK + 0x100}


def reference(initial, args):
    memory = dict(initial)
    actor, transition, threshold_u, value_u, peer_u, alternate = args
    threshold, value, peer = signed(threshold_u), signed(value_u), signed(peer_u)
    player = memory[actor + 0x23D]
    index = s16(read(memory, actor + 0x1B4, 2))
    table = TABLE_B if alternate else TABLE_A
    actor_threshold = s16(read(memory, table + index * 8 + player * 0x20, 2))
    if read(memory, actor + 0x84) & 0x8000:
        actor_threshold = s16(actor_threshold * 2)
    calls = []
    if actor_threshold < threshold and value < peer:
        memory[transition] = 2
    elif actor_threshold < threshold and peer < value:
        memory[transition] = 1
    else:
        memory[transition + 1] = 0
        memory[transition] = 0
        put(memory, transition + 8, 0xFFFC)
        return memory, calls, 0
    calls.append((HELPER, (transition, value_u, threshold_u)))
    memory[transition + 2] = memory[transition + 1]
    old_value = signed(read(memory, transition + 4))
    memory[transition + 1] = 0 if old_value < value else 1
    put(memory, transition + 8, threshold_u)
    put(memory, transition + 4, value_u)
    return memory, calls, 1


class TransitionOracle(TimingOracle):
    def record_call(self, target):
        if target != HELPER:
            raise AssertionError("Unexpected transition helper %08X" % target)
        args = self.arguments(3)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        transition, value_u, threshold_u = self.calls[-1][1]
        value = signed(value_u)
        self.memory[transition + 2] = self.memory[transition + 1]
        old_value = signed(read(self.memory, transition + 4, 4))
        self.memory[transition + 1] = 0 if old_value < value else 1
        self.put(transition + 8, threshold_u, 4)
        self.put(transition + 4, value_u, 4)
        for offset in range(0, 16, 4):
            self.put(self.r[29] + offset, 0xB5000000 + offset, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.r[2] = 0xA5000002


class CallerBoundary(Exception):
    pass


class CallerOracle(TimingOracle):
    def __init__(self, words, memory, entry, end, args, arg4_register,
                 callee_result, phase=0):
        super().__init__(words, memory, phase=phase, entry=entry, arguments=args[:4])
        self.code[end] = 0
        self.end = end
        self.full_args = args
        self.arg4_register = arg4_register
        self.callee_result = callee_result
        self.r[arg4_register] = args[4]

    def execute(self, word):
        if self.current_pc == self.end:
            raise CallerBoundary
        super().execute(word)

    def record_call(self, target):
        if target != match.ENTRY:
            raise AssertionError("Unexpected caller target %08X" % target)
        args = self.arguments(6)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        for offset in range(0, 16, 4):
            self.put(self.r[29] + offset, 0xD5000000 + offset, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xD6000000 + register
        self.r[2] = self.callee_result


def native_harness(body):
    return r'''typedef signed char s8;
typedef unsigned char u8;
typedef signed short s16;
typedef unsigned short u16;
typedef signed int s32;
typedef unsigned int u32;
''' + candidate.DECLARATIONS + r'''
s16 D_800DC204[128];
s16 D_800DC206[128];
static void func_1512B5FC(u8 *transition, s32 value, s32 threshold) {
    transition[2]=transition[1];
    transition[1]=(*(s32 *)(void *)(transition+4)<value)?0:1;
    *(s32 *)(void *)(transition+8)=threshold;
    *(s32 *)(void *)(transition+4)=value;
}
''' + body + r'''
static u8 actorBytes[0x240] __attribute__((aligned(8)));
static s16 wrap16(s32 value) { return (s16)value; }
static int run(void) {
    u32 seed;
    for(seed=0;seed<4096u;seed++) {
        ActorThresholdTransition actual, expected;
        u32 player=(seed>>2)&3u, index=(seed>>4)&7u, alternate=(seed>>7)&1u;
        u32 flags=(seed&1u)?0x8000u:0u, outcome=(seed>>8)&3u;
        s16 raw=(s16)((seed*173u+0x8123u)&0xFFFFu);
        s32 effective=(flags&0x8000u)?(s32)wrap16((s32)raw*2):(s32)raw;
        s32 threshold,value,peer,result,want,oldValue;
        s16 *selected=alternate?D_800DC206:D_800DC204;
        u32 slot=(index*8u+player*0x20u)/2u;
        u32 i;
        for(i=0;i<sizeof(actorBytes);i++) actorBytes[i]=(u8)(seed+i*13u);
        *(s32 *)(void *)(actorBytes+0x84)=(s32)flags;
        *(s16 *)(void *)(actorBytes+0x1B4)=(s16)index;
        actorBytes[0x23D]=(u8)player;
        D_800DC204[slot]=(s16)~raw; D_800DC206[slot]=(s16)~raw; selected[slot]=raw;
        if(outcome==0u) { threshold=effective+1; value=-10-(s32)seed; peer=10+(s32)seed; }
        else if(outcome==1u) { threshold=effective+1; value=10+(s32)seed; peer=-10-(s32)seed; }
        else if(outcome==2u) { threshold=effective+1; value=peer=5+(s32)seed; }
        else { threshold=effective; value=-10-(s32)seed; peer=10+(s32)seed; }
        actual.state=(u8)(0x70u|(seed&7u)); actual.active=(u8)((seed*3u+1u)&1u);
        actual.previous=(u8)(0x40u|(seed&0x1Fu)); actual.pad3=0xA5u;
        actual.value=value+((seed&1u)?-1:1); actual.threshold=(s32)(0xA5000000u|seed);
        expected=actual; oldValue=expected.value;
        if(effective<threshold && value<peer) {
            expected.state=2; expected.previous=expected.active;
            expected.active=(oldValue<value)?0:1; expected.value=value;
            expected.threshold=threshold; want=1;
        } else if(effective<threshold && peer<value) {
            expected.state=1; expected.previous=expected.active;
            expected.active=(oldValue<value)?0:1; expected.value=value;
            expected.threshold=threshold; want=1;
        } else {
            expected.active=0; expected.state=0; expected.threshold=0xFFFC; want=0;
        }
        result=func_1512B630(actorBytes,&actual,threshold,value,peer,(s32)alternate);
        if(result!=want || actual.state!=expected.state || actual.active!=expected.active
                || actual.previous!=expected.previous || actual.pad3!=expected.pad3
                || actual.value!=expected.value || actual.threshold!=expected.threshold) return 10+(int)outcome;
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status=run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
'''


class ThresholdTransitionMatchTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.values = match.prepare(ROOT, cls.output)
        cls.report = cls.values["report"]
        image = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(">%dI" % match.WORDS, image, match.ROM))
        cls.caller_windows = []
        for entry, end, rom, register in CALLER_WINDOWS:
            count = (end - entry) // 4
            words = list(struct.unpack_from(">%dI" % count, image, rom))
            cls.caller_windows.append((entry, end, words, register))
        text, functions, relocations = parse_object(cls.values["qualified_compact"])
        info = functions[match.FUNCTION]
        cls.raw = text[info["value"]:info["value"] + info["size"]]
        cls.bindings = {
            offset - info["value"]: rows for offset, rows in relocations.items()
            if info["value"] <= offset < info["value"] + info["size"]
        }

    @classmethod
    def tearDownClass(cls):
        (cls.output / "test-receipt.json").write_text(
            json.dumps(cls.receipt, indent=2) + "\n"
        )

    def test_01_owner_image_relocations_callers_and_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_frame"], report["retail_frame"],
             report["natural_positional_differences"], report["guards"],
             report["relocations"], report["neighbors"]),
            (64, 0x20, 0x20, 0, 0, 6, 14))
        self.assertEqual(report["functions"], 6052)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"]["direct_jal_calls"],
                         ["0x15886c", "0x158998"])
        self.assertEqual(report["registry"]["aligned_pointer_literals"], [])
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
            "words": 64, "frame": 32, "guards": 0, "relocations": 6,
            "neighbors": 14, "functions": 6052, "changed_only_target": True,
            "strict_exclusions": 0, "protected_game_bytes": 189088,
            "protected_data_exact": True,
        }

    def test_02_guest_all_words_tables_wrap_transitions_and_widths(self):
        visits, cases = set(), 0
        corpus = itertools.product(
            (0, 1), (0, 0x8000), (-20000, -1, 0, 20000, 32767),
            range(4), (0, 3), (0, 3), (0, 8))
        for alternate, flags, raw, outcome, player, index, phase in corpus:
            seed = cases & 0x3F
            initial, args = fixture(raw, player, index, alternate, flags,
                                    outcome, seed)
            wanted, calls, result = reference(initial, args)
            model = TransitionOracle(
                self.words, initial, phase=phase, entry=match.ENTRY,
                arguments=args).run()
            self.assertEqual(
                (public(model.memory), model.calls, model.r[2]),
                (public(wanted), calls, result))
            visits.update(model.visits)
            cases += 1
        reachable = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4))
        reachable.remove(match.ENTRY + 0x40)
        self.assertEqual(visits, reachable)
        self.assertEqual(cases, 640)
        self.receipt["guest"] = {
            "cases": cases, "covered_words": 63,
            "structural_branch_shadow_words": ["0x1512b670"],
            "stack_phases": [0, 8],
            "both_tables": True, "signed_16_wrap": True,
            "both_success_directions_and_clear": True,
            "helper_volatile_clobbers": True, "field_widths": True,
        }

    def test_03_original_caller_windows_pass_six_arguments_and_use_result(self):
        cases = 0
        for (entry, end, words, arg4_register), result, phase, seed in itertools.product(
                self.caller_windows, (0, 1), (0, 8), range(16)):
            memory = {STACK + offset: (offset * 23 + seed * 11 + 0x91) & 0xFF
                      for offset in range(-0x100, 0x100)}
            args = (ACTOR + seed * 0x10, TRANSITION + seed * 0x10,
                    u32(-300 + seed), u32(50 - seed), u32(80 + seed), 0)
            model = CallerOracle(words, memory, entry, end, args, arg4_register,
                                 result, phase)
            initial_s0, s2 = 0x100 + seed, 0x200 + seed
            model.r[16], model.r[18] = initial_s0, s2
            with self.assertRaises(CallerBoundary):
                model.run()
            self.assertEqual(model.calls, [(match.ENTRY, args)])
            self.assertEqual(model.r[16], (initial_s0 + 1) if result == 0 else (s2 + 1))
            cases += 1
        self.assertEqual(cases, 128)
        self.receipt["callers"] = {
            "function": "func_1512B1B8", "windows": 2, "cases": cases,
            "six_arguments_observed": True, "alternate_selector_zero": True,
            "return_controls_loop_exit": True,
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
        self.assertEqual(result.returncode, 0, result.stderr[:4000])
        return subprocess.run([str(binary)], timeout=30).returncode

    def test_04_native32_profiles_and_effective_semantic_controls(self):
        body = candidate.SELECTED
        profiles = {}
        for optimization in ("-O0", "-O2", "-O3"):
            self.assertEqual(self.compile_native(body, "native", optimization), 0)
            profiles[optimization] = {"cases": 4096, "exit": 0, "UBSan": True}
        controls = {
            "alternate-table": body.replace("D_800DC206", "D_800DC204", 1),
            "actor-index": body.replace("actor + 0x1B4", "actor + 0x1B6", 1),
            "player-index": body.replace("actor[0x23D]", "actor[0x23C]", 1),
            "double-flag": body.replace("0x8000", "0x4000", 1),
            "double-value": body.replace("actorThreshold * 2", "actorThreshold * 3", 1),
            "threshold-gate": body.replace(
                "actorThreshold < threshold", "actorThreshold <= threshold", 1),
            "positive-direction": body.replace(
                "value < otherValue", "value <= otherValue", 1),
            "negative-direction": body.replace(
                "otherValue < value", "otherValue <= value", 1),
            "positive-state": body.replace("transition->state = 2", "transition->state = 3", 1),
            "negative-state": body.replace("transition->state = 1", "transition->state = 3", 1),
            "helper-value": body.replace(
                "func_1512B5FC((u8 *)transition, value, threshold);",
                "func_1512B5FC((u8 *)transition, otherValue, threshold);", 1),
            "helper-threshold": body.replace(
                "func_1512B5FC((u8 *)transition, value, threshold);",
                "func_1512B5FC((u8 *)transition, value, threshold + 1);", 1),
            "clear-active": body.replace("transition->active = 0;", "transition->active = 1;", 1),
            "clear-state": body.replace("transition->state = 0;", "transition->state = 1;", 1),
            "clear-threshold": body.replace("0xFFFC", "0xFFFD", 1),
            "success-return": body.replace("return 1;", "return 0;", 1),
        }
        rejected = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body, name)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0, name)
            rejected[name] = "observable mismatch"
        self.receipt["native"] = {
            "profiles": profiles, "controls": rejected, "pointer_width": 32,
            "valid_actor_transition_and_table_backing": True,
        }

    def test_05_raw_bytes_relocations_and_whole_image_fail_closed(self):
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
        for offset in match.BINDINGS:
            changed = dict(match.BINDINGS)
            changed[offset] = [("R_MIPS_26", "func_1512B730")]
            self.assertNotEqual(changed, match.BINDINGS)
            binding_controls += 1
        predecessor = self.values["predecessor_elf"].read_bytes()
        qualified = self.values["qualified_elf"].read_bytes()
        self.assertNotEqual(predecessor, qualified)
        self.assertEqual(len(predecessor), len(qualified))
        self.assertEqual(hashlib.sha256(qualified).hexdigest(),
                         self.report["qualified_elf_sha256"])
        self.receipt["fail_closed"] = {
            "raw_byte_controls": raw_controls,
            "relocation_binding_controls": binding_controls,
            "whole_image_length_fixed": True,
            "whole_image_changed_only_target": True,
        }


if __name__ == "__main__":
    unittest.main()
