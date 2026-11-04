"""Semantic, ABI, guard, owner and image gates for func_15172D80."""

import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_channel_release_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put


ROOT = Path(__file__).resolve().parents[2]
ACTORS = 0x800CC2D0
CHANNELS, PAYLOADS, CURRENT = 0x800DD2B0, 0x800DD2C0, 0x800BE9F0
EFFECT, STATUS = 0x1517EE40, 0x1517F40C
SCENE, TEARDOWN, APPLY = 0x1501C730, 0x15172CA8, 0x15172D28


def signed8(value):
    value &= 0xFF
    return value - 0x100 if value & 0x80 else value


def fixture(channel, health, selector, payload, current, phase):
    memory = {STACK + offset: (offset * 17 + 0xA5) & 0xFF
              for offset in range(-0x180, 0x100)}
    memory.update({CHANNELS + index: 0x55 for index in range(16)})
    memory.update({PAYLOADS + index: 0x66 for index in range(16)})
    memory[ACTORS + channel * 0x32C + 0x1CA] = health & 0xFF
    memory[CHANNELS + channel] = selector & 0xFF
    memory[PAYLOADS + channel] = payload & 0xFF
    put(memory, CURRENT, current & 0xFFFFFFFF)
    return memory


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x180 <= address < STACK + 0x100}


def reference(initial, channel, health, selector, payload, current, status):
    memory, calls = dict(initial), []
    selected = signed8(selector)
    if selected != -1:
        if health == 0:
            memory[CHANNELS + channel] = 0xFF
            selected = -1
            calls.append((EFFECT, (0, 0, 0, 0x32, 0, channel)))
        calls.append((STATUS, (channel,)))
        if status != 0:
            if current != selected:
                calls.append((SCENE, (1, selected & 0xFFFFFFFF, 0, 0, 0)))
            else:
                calls.append((TEARDOWN, (channel,)))
                calls.append((APPLY, (
                    ACTORS + channel * 0x32C, payload & 0xFF)))
    return memory, calls


class ReleaseOracle(TimingOracle):
    def __init__(self, words, memory, channel, status, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(channel,))
        self.status = status

    def execute(self, word):
        op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
        if op == 32:  # LB
            immediate = word & 0xFFFF
            if immediate & 0x8000:
                immediate -= 0x10000
            address = (self.r[rs] + immediate) & 0xFFFFFFFF
            self.r[rt] = signed8(self.get(address, 1)) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)

    def record_call(self, target):
        counts = {EFFECT: 6, STATUS: 1, SCENE: 5, TEARDOWN: 1, APPLY: 2}
        if target not in counts:
            raise AssertionError("Unexpected actor-channel-release call %08X" % target)
        args = self.arguments(counts[target])
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target not in (EFFECT, STATUS, SCENE, TEARDOWN, APPLY):
            raise AssertionError("Unexpected actor-channel-release hook %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        if target == STATUS:
            self.r[2] = self.status & 0xFFFFFFFF


def native_harness(body):
    return """typedef unsigned char u8;
typedef signed char s8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int s32;
typedef struct struct127 {
    u8 pad0[0x1CA];
    u8 health;
    u8 pad1CB[0x161];
} struct127;
struct127 D_800CC2D0[16];
s8 D_800DD2B0[16];
u8 D_800DD2C0[16];
s32 D_800BE9F0;
void func_1501C730(s32, s32, s32, s32, s32);
void func_15172CA8(s32);
void func_15172D28(u8 *, s32);
void func_1517EE40(s32, s32, s32, s32, s8, s32);
s32 func_1517F40C(s32);
%s
static s32 logValues[8];
static s32 logCount, badArgs, wantedChannel, wantedPayload, wantedStatus;
static void add(s32 value) {
    if (logCount < 8) logValues[logCount] = value;
    logCount++;
}
void func_1517EE40(s32 a0, s32 a1, s32 a2, s32 a3, s8 a4, s32 a5) {
    add(1);
    if (a0 || a1 || a2 || a3 != 0x32 || a4 || a5 != wantedChannel)
        badArgs = 1;
}
s32 func_1517F40C(s32 channel) {
    add(2);
    if (channel != wantedChannel) badArgs = 1;
    return wantedStatus;
}
void func_1501C730(s32 a0, s32 a1, s32 a2, s32 a3, s32 a4) {
    add(3);
    if (a0 != 1 || a1 != D_800DD2B0[wantedChannel] || a2 || a3 || a4)
        badArgs = 1;
}
void func_15172CA8(s32 channel) {
    add(4);
    if (channel != wantedChannel) badArgs = 1;
}
void func_15172D28(u8 *actor, s32 payload) {
    add(5);
    if (actor != (u8 *)&D_800CC2D0[wantedChannel] ||
            payload != wantedPayload) badArgs = 1;
}
static int one(s32 channel, s32 health, s32 selector, s32 status,
               s32 currentKind, s32 payload) {
    s32 expected[5], expectedCount = 0, selected = (s8)selector;
    s32 effective = health == 0 ? -1 : selected;
    s32 current = currentKind == 0 ? effective :
        (currentKind == 1 ? effective + 1 : (effective & 0xFF));
    s32 index;
    wantedChannel = channel;
    wantedPayload = payload & 0xFF;
    wantedStatus = status;
    D_800CC2D0[channel].health = (u8)health;
    D_800DD2B0[channel] = (s8)selector;
    D_800DD2C0[channel] = (u8)payload;
    D_800BE9F0 = current;
    logCount = badArgs = 0;
    if (selected != -1) {
        if (health == 0) expected[expectedCount++] = 1;
        expected[expectedCount++] = 2;
        if (status) {
            if (current != effective) expected[expectedCount++] = 3;
            else {
                expected[expectedCount++] = 4;
                expected[expectedCount++] = 5;
            }
        }
    }
    func_15172D80(channel);
    if (badArgs || logCount != expectedCount) return 10;
    for (index = 0; index < expectedCount; index++)
        if (logValues[index] != expected[index]) return 11;
    if ((u8)D_800DD2B0[channel] !=
            (u8)(selected != -1 && health == 0 ? -1 : selector)) return 12;
    if (D_800DD2C0[channel] != (u8)payload) return 13;
    return 0;
}
static int run(void) {
    static const s32 channels[] = {0, 7, 15};
    static const s32 selectors[] = {-1, 0, 0x7F, 0x80};
    static const s32 payloads[] = {0, 0x7F, 0x80, 0xFF};
    s32 c, h, s, q, m, p;
    for (c = 0; c < 3; c++)
        for (h = 0; h < 2; h++)
            for (s = 0; s < 4; s++)
                for (q = 0; q < 2; q++)
                    for (m = 0; m < 3; m++)
                        for (p = 0; p < 4; p++)
                            if (one(channels[c], h, selectors[s], q, m,
                                    payloads[p])) return 20;
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
""" % body


class ActorChannelReleaseMatchTests(unittest.TestCase):
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
        (cls.output / "test-receipt.json").write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_checked_slot_owner_image_and_protected_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_frame"], report["retail_frame"],
             report["natural_positional_differences"], report["guards"],
             report["relocations"]),
            (63, 0x40, 0x38, 2, 2, 13))
        self.assertEqual(report["neighbors"], 4)
        self.assertEqual(report["functions"], 6051)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"], {
            "direct_jal_calls": ["0x464e8"],
            "aligned_pointer_literals": [],
            "caller": "func_15018F80",
            "abi": "promoted signed channel index in a0; return value ignored",
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
            "words": 63, "guards": 2, "relocations": 13,
            "neighbors": 4, "functions": 6051,
            "changed_only_target": True, "strict_exclusions": 0,
            "protected_game_bytes": 189088, "protected_data_exact": True,
        }

    def test_02_guest_paths_stack_phases_unsigned_payload_and_all_words(self):
        visits, cases = set(), 0
        for channel, health, selector, status, current_kind, payload, phase in itertools.product(
                (0, 7, 15), (0, 1), (-1, 0, 0x7F, 0x80), (0, 1),
                (0, 1, 2), (0, 0x7F, 0x80, 0xFF), (0, 8)):
            effective = -1 if health == 0 else signed8(selector)
            current = (effective if current_kind == 0 else
                       effective + 1 if current_kind == 1 else effective & 0xFF)
            initial = fixture(
                channel, health, selector, payload, current, phase)
            wanted, calls = reference(
                initial, channel, health, selector, payload, current, status)
            model = ReleaseOracle(
                self.words, initial, channel, status, phase).run()
            self.assertEqual(public(model.memory), public(wanted))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[29], STACK + phase)
            visits.update(model.visits)
            cases += 1
        self.assertEqual(visits, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.assertEqual(cases, 1152)
        self.receipt["guest"] = {
            "cases": cases, "stack_phases": [0, 8],
            "all_63_words_covered": True, "unsigned_payload_edges": [0x80, 0xFF],
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
            profiles[optimization] = {"cases": 576, "exit": 0, "UBSan": True}
        controls = {
            "sentinel": body.replace("*slot != -1", "*slot == -1"),
            "health": body.replace("actor->health == 0", "actor->health != 0"),
            "clear": body.replace("*slot = -1;", "*slot = 0;"),
            "duration": body.replace("0x32, 0, channel", "0x31, 0, channel"),
            "status": body.replace("func_1517F40C(channel) != 0",
                                   "func_1517F40C(channel) == 0"),
            "current": body.replace("D_800BE9F0 != *slot", "D_800BE9F0 == *slot"),
            "scene-mode": body.replace("func_1501C730(1,", "func_1501C730(2,"),
            "teardown": body.replace("func_15172CA8(channel);", "(void)channel;"),
            "payload": body.replace("D_800DD2C0[channel]", "D_800DD2C0[0]"),
            "actor": body.replace("func_15172D28((u8 *)actor,",
                                  "func_15172D28((u8 *)(actor + 1),"),
        }
        rejected = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0, name)
            rejected[name] = "output mismatch"
        self.receipt["native"] = {"profiles": profiles, "controls": rejected}

    def test_04_raw_bindings_and_guard_preimages_fail_closed(self):
        self.assertEqual(len(self.raw), match.SIZE)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), match.RAW_SHA256)
        self.assertEqual(self.bindings, match.BINDINGS)
        raw_controls = 0
        for index in range(len(self.raw)):
            changed = bytearray(self.raw)
            changed[index] ^= 1
            self.assertNotEqual(hashlib.sha256(changed).hexdigest(), match.RAW_SHA256)
            raw_controls += 1
        fields = (
            "filename", "function", "offset", "expected", "replacement",
            "expected_relocations", "replacement_relocations", "note",
            "insert_after", "insert_after_relocations", "omit")
        rows = [{
            "filename": match.FILENAME,
            "function": match.FUNCTION,
            "offset": row["offset"],
            "expected": row["expected"],
            "replacement": row["replacement"],
            "expected_relocations": "-",
            "replacement_relocations": "-",
            "note": row["note"],
            "insert_after": "",
            "insert_after_relocations": "",
            "omit": "false",
        } for row in match.PATCH_ROWS]
        guard_controls = 0
        for index in range(len(rows)):
            changed = [dict(row) for row in rows]
            changed[index]["expected"] = hex(int(changed[index]["expected"], 0) ^ 1)
            manifest = self.output / ("guard-control-%d.csv" % index)
            with manifest.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(changed)
            with self.assertRaises(ValueError):
                emit_padded_assembly(
                    self.values["qualified_compact"], ROOT / match.ASM,
                    word_patches_path=manifest, filename=match.FILENAME)
            guard_controls += 1
        self.assertEqual((raw_controls, guard_controls), (252, 2))
        self.receipt["fail_closed"] = {
            "raw_byte_controls": raw_controls,
            "guard_preimage_controls": guard_controls,
        }


if __name__ == "__main__":
    unittest.main()
