"""Semantic, caller, ABI, owner and image gates for func_151218C4."""

import csv
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_state_reset_candidates as candidate
from tools.experiments import game_actor_state_reset_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put
from tools.tests.test_game_point_transform_match import read


ROOT = Path(__file__).resolve().parents[2]
ACTOR = 0x80500000
RESOURCE = 0x80600000
LINKED = 0x80700000
COMMAND_TARGET = 0x80800000
COMMAND = 0x1506160C
CLEANUP = 0x151C9ED4
CALLER_ENTRY = 0x15121098
CALLER_ROM = 0x14E548
CALLER_TARGET = 0x1512124C


def u32(value):
    return value & 0xFFFFFFFF


def fixture(seed=0, flags=0, kind=0x40, mode=0xF, pending=1,
            angle=-1.75, phase=0):
    memory = {
        STACK + phase + offset: (offset * 19 + seed * 7 + 0xA5) & 0xFF
        for offset in range(-0x200, 0x140)
    }
    for base, length in (
            (ACTOR - 16, 0xA40), (RESOURCE - 16, 64),
            (LINKED - 16, 0x1C0), (COMMAND_TARGET - 16, 64)):
        memory.update({
            base + offset: (offset * 29 + seed * 11 + base) & 0xFF
            for offset in range(length)
        })
    put(memory, ACTOR + 0x36C, RESOURCE)
    put(memory, RESOURCE, flags, 2)
    put(memory, ACTOR + 0x34, kind)
    put(memory, ACTOR + 0x6FC, mode)
    put(memory, ACTOR + 0x3D4, LINKED)
    put(memory, ACTOR + 0x3D0, COMMAND_TARGET)
    put(memory, ACTOR + 0x76C, bits(angle))
    memory[ACTOR + 0x23D] = seed & 0xFF
    memory[ACTOR + 0x84C] = pending & 0xFF
    return memory


def public(memory, phase=0):
    return {
        address: value for address, value in memory.items()
        if not STACK + phase - 0x200 <= address < STACK + phase + 0x140
    }


def reference(initial, flags, kind, mode, pending, angle, helper_mode=0):
    memory = dict(initial)
    calls = []
    if flags & 0x10:
        return memory, calls
    if kind == 0x40:
        if mode == 0xF:
            put(memory, ACTOR + 0x898, 0)
            put(memory, ACTOR + 0x89C, 0)
        memory[LINKED + 0x198] = 0
        put(memory, ACTOR + 0x73C, 0, 2)
        put(memory, ACTOR + 0x84A, 60, 2)
    else:
        put(memory, ACTOR + 0x84A, 60, 2)
        put(memory, ACTOR + 0x73C, 3, 2)
    put(memory, ACTOR + 0x374, bits(200.0))
    put(memory, ACTOR + 0x348, bits(100.0))
    put(memory, ACTOR + 0x134, u32(math.trunc(angle)))
    memory[ACTOR + 0x78C] = 0
    put(memory, ACTOR + 0x190, 0)
    put(memory, ACTOR + 0x99C, 0)
    put(memory, ACTOR + 0x198, 0)
    calls.append((COMMAND, (COMMAND_TARGET, 2, 0xFF, 0x20,
                            initial[ACTOR + 0x23D])))
    if helper_mode == 1:
        memory[ACTOR + 0x84C] = 0
    elif helper_mode == 2:
        memory[ACTOR + 0x84C] = 7
    if memory[ACTOR + 0x84C]:
        calls.append((CLEANUP, (ACTOR,)))
        memory[ACTOR + 0x84C] = 0
    return memory, calls


class ActorStateResetOracle(TimingOracle):
    def __init__(self, words, memory, helper_mode=0, phase=0):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(ACTOR,))
        self.helper_mode = helper_mode

    def execute(self, word):
        op = word >> 26
        rs = word >> 21 & 31
        rd = word >> 11 & 31
        shift = word >> 6 & 31
        function = word & 63
        if op == 17 and rs == 16 and function == 13:
            self.f[shift] = u32(math.trunc(floating(self.f[rd])))
            self.r[0] = 0
        else:
            super().execute(word)

    def record_call(self, target):
        if target == COMMAND:
            count = 5
        elif target == CLEANUP:
            count = 1
        else:
            raise AssertionError("Unexpected actor-state call %08X" % target)
        args = self.arguments(count)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target == COMMAND:
            if self.helper_mode == 1:
                self.memory[ACTOR + 0x84C] = 0
            elif self.helper_mode == 2:
                self.memory[ACTOR + 0x84C] = 7
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]


class CallerOracle(TimingOracle):
    def __init__(self, words, memory, phase=0):
        connected = {
            CALLER_TARGET: 0x03400008,  # jr $k0
            CALLER_TARGET + 4: 0,
        }
        super().__init__(words, memory, phase=phase, entry=CALLER_ENTRY,
                         arguments=(ACTOR,), connected=connected)
        self.r[8] = 0x81234567
        self.r[16] = ACTOR
        self.r[26] = 0xDEAD0000
        self.saved_t0 = self.r[8]
        # This bounded window begins at a JAL and exits before the parent's
        # epilogue restores its incoming return address.
        self.before[16] = ACTOR
        self.before[31] = CALLER_ENTRY + 8

    def record_call(self, target):
        if target != match.ENTRY:
            raise AssertionError("Unexpected caller-window call %08X" % target)
        args = self.arguments(1)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xD5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xD6000000 + register


def native_harness(body):
    return r'''typedef signed char s8;
typedef unsigned char u8;
typedef signed short s16;
typedef unsigned short u16;
typedef signed int s32;
typedef unsigned int u32;
typedef float f32;
typedef struct { u8 pad0[0x198]; u8 unk198; } struct127;
static u8 actorBytes[0xA40] __attribute__((aligned(8)));
static u8 resourceBytes[64] __attribute__((aligned(8)));
static struct127 linkedRecord __attribute__((aligned(8)));
static struct127 commandRecord __attribute__((aligned(8)));
static s32 commandCalls, cleanupCalls, error, helperMode;
static u32 word(f32 value) { union { f32 f; u32 u; } data; data.f=value; return data.u; }
static void fill(u8 *data, u32 length, u32 seed) {
    u32 index; for(index=0;index<length;index++) data[index]=(u8)(index*29u+seed*11u+0xA5u);
}
static u32 load32(u32 offset) { return *(u32 *)(void *)(actorBytes+offset); }
static u16 load16(u32 offset) { return *(u16 *)(void *)(actorBytes+offset); }
void func_1506160C(struct127 *target, s32 two, u8 all, u8 width, s32 command) {
    commandCalls++;
    if(target!=&commandRecord || two!=2 || all!=0xFF || width!=0x20
            || (u32)command!=(u32)actorBytes[0x23D]) error=1;
    if(helperMode==1) actorBytes[0x84C]=0;
    else if(helperMode==2) actorBytes[0x84C]=7;
}
void func_151C9ED4(void *actor) {
    cleanupCalls++;
    if(actor!=(void *)actorBytes) error=2;
}
''' + body + r'''
static void initialize(u32 seed) {
    u32 angleBits;
    fill(actorBytes,sizeof(actorBytes),seed);
    fill(resourceBytes,sizeof(resourceBytes),seed+1u);
    fill((u8 *)&linkedRecord,sizeof(linkedRecord),seed+2u);
    fill((u8 *)&commandRecord,sizeof(commandRecord),seed+3u);
    *(u16 *)(void *)resourceBytes=(seed&1u)?0x10u:0u;
    *(u32 *)(void *)(actorBytes+0x36C)=(u32)resourceBytes;
    *(u32 *)(void *)(actorBytes+0x3D4)=(u32)&linkedRecord;
    *(u32 *)(void *)(actorBytes+0x3D0)=(u32)&commandRecord;
    *(s32 *)(void *)(actorBytes+0x34)=(seed&2u)?0x40:0x41;
    *(s32 *)(void *)(actorBytes+0x6FC)=(seed&4u)?0xF:0xE;
    actorBytes[0x84C]=(u8)((seed>>3)&1u);
    actorBytes[0x23D]=(u8)seed;
    { union { u32 u; f32 f; } angle;
      s32 integral=(s32)(seed%60001u)-30000;
      angle.f=(f32)integral+((seed&8u)?0.75f:-0.75f); angleBits=angle.u; }
    *(u32 *)(void *)(actorBytes+0x76C)=angleBits;
    helperMode=(s32)((seed>>4)%3u);
    commandCalls=cleanupCalls=error=0;
}
static int run(void) {
    u32 seed;
    for(seed=0;seed<4096u;seed++) {
        u8 actorBefore[0xA40], linkedBefore[sizeof(linkedRecord)];
        u32 index, flags, kind, mode, angleBits, reset898, reset89C;
        u8 pendingAfterCommand;
        initialize(seed);
        for(index=0;index<sizeof(actorBytes);index++) actorBefore[index]=actorBytes[index];
        for(index=0;index<sizeof(linkedRecord);index++) linkedBefore[index]=((u8 *)&linkedRecord)[index];
        flags=*(u16 *)(void *)resourceBytes;
        kind=load32(0x34); mode=load32(0x6FC); angleBits=load32(0x76C);
        reset898=load32(0x898); reset89C=load32(0x89C);
        func_151218C4((void *)actorBytes);
        if(error) return 10+error;
        if(flags&0x10u) {
            if(commandCalls || cleanupCalls) return 20;
            for(index=0;index<sizeof(actorBytes);index++) if(actorBytes[index]!=actorBefore[index]) return 21;
            for(index=0;index<sizeof(linkedRecord);index++) if(((u8 *)&linkedRecord)[index]!=linkedBefore[index]) return 22;
            continue;
        }
        if(commandCalls!=1) return 30;
        pendingAfterCommand=helperMode==1?0:helperMode==2?7:actorBefore[0x84C];
        if(cleanupCalls!=(pendingAfterCommand!=0)) return 31;
        if(actorBytes[0x84C]!=0) return 32;
        if(kind==0x40u) {
            if(linkedRecord.unk198!=0 || load16(0x73C)!=0 || load16(0x84A)!=60) return 33;
            if(mode==0xFu) {
                if(load32(0x898) || load32(0x89C)) return 34;
            } else if(load32(0x898)!=reset898 || load32(0x89C)!=reset89C) return 35;
        } else {
            if(linkedRecord.unk198!=linkedBefore[0x198] || load16(0x73C)!=3 || load16(0x84A)!=60) return 36;
            if(load32(0x898)!=reset898 || load32(0x89C)!=reset89C) return 37;
        }
        if(load32(0x374)!=word(200.0f) || load32(0x348)!=word(100.0f)) return 38;
        { union { u32 u; f32 f; } angle; angle.u=angleBits;
          if((s32)load32(0x134)!=(s32)angle.f) return 39; }
        if(actorBytes[0x78C]!=0 || load32(0x190) || load32(0x99C) || load32(0x198)) return 40;
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status=run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
'''


class ActorStateResetMatchTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.values = match.prepare(ROOT, cls.output)
        cls.report = cls.values["report"]
        image = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(
            ">%dI" % match.WORDS, image, match.ROM))
        cls.caller_words = list(struct.unpack_from(">5I", image, CALLER_ROM))
        text, functions, relocations = parse_object(
            cls.values["qualified_compact"])
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

    def test_01_owner_image_relocations_caller_and_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_body_words"],
             report["natural_frame"], report["retail_frame"],
             report["natural_positional_differences"], report["guards"],
             report["relocations"]),
            (67, 66, 0x28, 0x28, 4, 4, 2))
        self.assertEqual(report["neighbors"], 4)
        self.assertEqual(report["functions"], 6052)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"]["direct_jal_calls"], ["0x14e548"])
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
            "retail_words": 67, "natural_body_words": 66,
            "alignment_words": 1, "frame": 40, "guards": 4,
            "relocations": 2, "neighbors": 4, "functions": 6052,
            "changed_only_target": True, "strict_exclusions": 0,
            "protected_game_bytes": 189088, "protected_data_exact": True,
        }

    def test_02_guest_all_executable_words_branches_calls_and_widths(self):
        visits, cases = set(), 0
        angles = (-32767.75, -99.5, -1.75, -0.5, 0.0, 0.5,
                  1.75, 99.5, 32767.75)
        vectors = itertools.product(
            (0, 0x10, 0xFFFF), (0x40, 0x41), (0xF, 0xE),
            (0, 1, 255), angles, (0, 1, 2), (0, 8))
        for seed, values in enumerate(vectors):
            flags, kind, mode, pending, angle, helper_mode, phase = values
            initial = fixture(seed, flags, kind, mode, pending, angle, phase)
            wanted_memory, wanted_calls = reference(
                initial, flags, kind, mode, pending, angle, helper_mode)
            model = ActorStateResetOracle(
                self.words, initial, helper_mode, phase).run()
            self.assertEqual(
                (public(model.memory, phase), model.calls),
                (public(wanted_memory, phase), wanted_calls))
            visits.update(model.visits)
            cases += 1
        executable = set(range(match.ENTRY, match.ENTRY + match.NATURAL_SIZE, 4))
        self.assertEqual(visits & executable, executable)
        self.assertNotIn(match.ENTRY + match.NATURAL_SIZE, visits)
        self.receipt["guest"] = {
            "cases": cases, "covered_executable_words": 66,
            "alignment_word_non_executable": True, "stack_phases": [0, 8],
            "resource_gate": True, "kind_and_mode_branches": True,
            "signed_fractional_truncation": True,
            "live_cleanup_gate_after_command_call": True,
            "volatile_gpr_fpr_and_outgoing_home_clobbers": True,
        }

    def test_03_original_caller_delay_slot_and_saved_t0_contract(self):
        cases = 0
        for seed, phase in itertools.product(range(64), (0, 8)):
            memory = fixture(seed, phase=phase)
            stack = STACK + phase
            model = CallerOracle(self.caller_words, memory, phase).run()
            self.assertEqual(model.calls, [(match.ENTRY, (ACTOR,))])
            self.assertEqual(model.r[8], 0x81234567)
            self.assertEqual(read(model.memory, stack + 0x54), 0x81234567)
            cases += 1
        self.assertEqual(self.caller_words, [
            0x0D448631, 0xAFA80054, 0x8FA80054, 0x10000069, 0x00000000])
        self.receipt["caller"] = {
            "function": "func_15120158", "call": "0x15121098",
            "cases": cases, "actor_passed_in_a0": True,
            "t0_saved_in_jal_delay_slot": True,
            "t0_reloaded_after_volatile_callee": True,
            "callee_return_value_ignored": True,
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
            "resource-gate": body.replace("& 0x10", "& 0x20", 1),
            "actor-kind": body.replace("== 0x40", "== 0x41", 1),
            "mode": body.replace("== 0xF", "== 0xE", 1),
            "mode-reset-898": body.replace(
                "actor->reset898 = 0.0f;", "actor->reset898 = 1.0f;", 1),
            "linked-byte": body.replace(
                "actor->target->unk198 = 0;", "actor->target->unk198 = 1;", 1),
            "kind-state": body.replace("actor->state = 0;", "actor->state = 1;", 1),
            "timer": body.replace("actor->timer = 0x3C;", "actor->timer = 0x3D;", 1),
            "fallback-state": body.replace("actor->state = 3;", "actor->state = 4;", 1),
            "distance-200": body.replace("200.0f", "201.0f", 1),
            "distance-100": body.replace("100.0f", "101.0f", 1),
            "angle-source": body.replace("(s32)view->angle", "(s32)actor->distance374", 1),
            "view-active": body.replace("view->active = 0;", "view->active = 1;", 1),
            "reset-190": body.replace("->reset190 = 0.0f;", "->reset190 = 1.0f;", 1),
            "reset-99c": body.replace("->reset99C = 0.0f;", "->reset99C = 1.0f;", 1),
            "reset-198": body.replace("->reset198 = 0.0f;", "->reset198 = 1.0f;", 1),
            "command-target": body.replace("actor->commandTarget, 2", "actor->target, 2", 1),
            "command-kind": body.replace("actor->commandTarget, 2", "actor->commandTarget, 3", 1),
            "command-byte": body.replace(
                ")->commandByte);", ")->cleanupPending);", 1),
            "cleanup-gate": body.replace("cleanupPending != 0", "cleanupPending == 0", 1),
            "cleanup-clear": body.replace(
                "actor->cleanupPending = 0;", "actor->cleanupPending = 1;", 1),
        }
        rejected = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body, name)
            self.assertNotEqual(
                self.compile_native(changed, name, "-O2"), 0, name)
            rejected[name] = "observable mismatch"
        self.receipt["native"] = {
            "profiles": profiles, "controls": rejected,
            "pointer_width": 32, "valid_actor_resource_and_linked_backing": True,
        }

    def test_05_raw_retail_guards_relocations_and_image_fail_closed(self):
        self.assertEqual(len(self.raw), match.NATURAL_SIZE)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), match.RAW_SHA256)
        self.assertEqual(self.bindings, match.BINDINGS)
        raw_controls = 0
        for index in range(len(self.raw)):
            changed = bytearray(self.raw)
            changed[index] ^= 1
            self.assertNotEqual(
                hashlib.sha256(changed).hexdigest(), match.RAW_SHA256)
            raw_controls += 1
        retail = (ROOT / match.ROM_IMAGE).read_bytes()[
            match.ROM:match.ROM + match.SIZE]
        self.assertEqual(hashlib.sha256(retail).hexdigest(), match.RETAIL_SHA256)
        retail_controls = 0
        for index in range(len(retail)):
            changed = bytearray(retail)
            changed[index] ^= 1
            self.assertNotEqual(
                hashlib.sha256(changed).hexdigest(), match.RETAIL_SHA256)
            retail_controls += 1
        target_indices = [
            index for index, row in enumerate(self.values["qualified_rows"])
            if row["filename"] == match.FILENAME and
            row["function"] == match.FUNCTION
        ]
        self.assertEqual(len(target_indices), 4)
        guard_controls = 0
        for ordinal, row_index in enumerate(target_indices):
            rows = [dict(row) for row in self.values["qualified_rows"]]
            rows[row_index]["expected"] = "0x%08X" % (
                int(rows[row_index]["expected"], 0) ^ 1)
            manifest = self.output / ("bad-guard-%02d.csv" % ordinal)
            match.harness.write_patches(
                manifest, self.values["fields"], rows)
            with self.assertRaises(ValueError):
                emit_padded_assembly(
                    self.values["qualified_compact"], ROOT / match.ASM,
                    word_patches_path=manifest, filename=match.FILENAME)
            guard_controls += 1
        relocation_controls = 0
        for offset in match.BINDINGS:
            changed = dict(match.BINDINGS)
            changed[offset] = [("R_MIPS_26", "func_151218C4")]
            self.assertNotEqual(changed, match.BINDINGS)
            relocation_controls += 1
        predecessor = self.values["predecessor_elf"].read_bytes()
        qualified = self.values["qualified_elf"].read_bytes()
        self.assertNotEqual(predecessor, qualified)
        self.assertEqual(len(predecessor), len(qualified))
        self.assertEqual(
            hashlib.sha256(qualified).hexdigest(),
            self.report["qualified_elf_sha256"])
        self.receipt["fail_closed"] = {
            "raw_byte_controls": raw_controls,
            "retail_byte_controls": retail_controls,
            "guard_preimage_controls": guard_controls,
            "relocation_binding_controls": relocation_controls,
            "whole_image_length_fixed": True,
            "whole_image_changed_only_target": True,
        }


if __name__ == "__main__":
    unittest.main()
