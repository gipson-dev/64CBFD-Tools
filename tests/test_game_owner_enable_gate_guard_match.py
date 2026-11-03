"""Guarded C, callback ABI and image gates for func_1514E920."""

import csv
import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_owner_enable_gate_guard_match as match
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read


OWNER, ATTACHED = 0x220000, 0x230000
FALLBACK = 0x1514E89C


def fixture(mode, flags, attached, context, phase):
    memory = {STACK + i: (i * 17 + 0xA5) & 0xFF
              for i in range(-0x100, 0x100)}
    memory.update({OWNER + i: (i * 13 + 0x59) & 0xFF
                   for i in range(0x200)})
    memory.update({ATTACHED + i: (i * 29 + 0x71) & 0xFF
                   for i in range(0x80)})
    put(memory, OWNER + 0x10, flags & 0xFFFFFFFF)
    put(memory, OWNER + 0x154, ATTACHED if attached else 0)
    memory[ATTACHED + 0x30] = 0xA7
    return memory


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x100 <= address < STACK + 0x100}


def reference(initial, mode, context, fallback_result):
    memory, calls = dict(initial), []
    flags = read(memory, OWNER + 0x10)
    attached = read(memory, OWNER + 0x154)
    if mode == 0:
        if flags & 1:
            put(memory, OWNER + 0x10, flags & ~1)
            if attached:
                memory[attached + 0x30] = 0
        else:
            put(memory, OWNER + 0x10, flags | 1)
        result = 1
    elif mode == 2:
        put(memory, OWNER + 0x10, flags & ~1)
        if attached:
            memory[attached + 0x30] = 0
        result = 1
    elif mode == 1:
        put(memory, OWNER + 0x10, flags | 1)
        result = 1
    else:
        calls.append((FALLBACK, (OWNER, mode & 0xFFFFFFFF,
                                 context & 0xFFFFFFFF)))
        result = fallback_result
    return memory, calls, result & 0xFFFFFFFF


class EnableGateOracle(TimingOracle):
    def __init__(self, words, memory, mode, context, fallback_result, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(OWNER, mode, context))
        self.fallback_result = fallback_result & 0xFFFFFFFF

    def record_call(self, target):
        if target != FALLBACK:
            raise AssertionError("Unexpected enable-gate call %08X" % target)
        args = self.arguments(3)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target != FALLBACK:
            raise AssertionError("Unexpected enable-gate hook %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.r[2] = self.fallback_result
        self.f[:20] = [0xA5000000 + index for index in range(20)]


def native_harness(body):
    return r'''typedef unsigned char u8;
typedef int s32;
#define NULL ((void *)0)
s32 func_1514E89C(u8 *, s32, s32);
%s
static union { s32 align; u8 bytes[0x200]; } owner;
static union { s32 align; u8 bytes[0x80]; } attached;
static s32 calls, badArgs, helperResult;
s32 func_1514E89C(u8 *value, s32 mode, s32 context) {
    calls++;
    if (value != owner.bytes || mode != 7 || context != 0x12345678)
        badArgs = 1;
    return helperResult;
}
static int one(s32 mode, s32 flags, s32 present, s32 context, s32 result) {
    s32 i, wantedFlags = flags, wantedByte = 0xA7, wantedResult = 1;
    for (i = 0; i < (s32)sizeof(owner.bytes); i++)
        owner.bytes[i] = (u8)(i * 13 + 0x59);
    for (i = 0; i < (s32)sizeof(attached.bytes); i++)
        attached.bytes[i] = (u8)(i * 29 + 0x71);
    *(s32 *)(owner.bytes + 0x10) = flags;
    *(u8 **)(owner.bytes + 0x154) = present ? attached.bytes : NULL;
    attached.bytes[0x30] = 0xA7;
    calls = badArgs = 0;
    helperResult = result;
    if (mode == 0) {
        if (flags & 1) {
            wantedFlags = flags & ~1;
            if (present) wantedByte = 0;
        } else wantedFlags = flags | 1;
    } else if (mode == 2) {
        wantedFlags = flags & ~1;
        if (present) wantedByte = 0;
    } else if (mode == 1) wantedFlags = flags | 1;
    else wantedResult = result;
    if (func_1514E920(owner.bytes, mode, context) != wantedResult) return 10;
    if (*(s32 *)(owner.bytes + 0x10) != wantedFlags) return 11;
    if (attached.bytes[0x30] != wantedByte) return 12;
    if (calls != (mode != 0 && mode != 1 && mode != 2)) return 13;
    if (mode == 7 && (context == 0x12345678) && badArgs) return 14;
    return 0;
}
static int run(void) {
    static const s32 modes[] = {0, 1, 2, 7};
    static const s32 flags[] = {0, 1, 2, 3, -1};
    static const s32 contexts[] = {0, 0x12345678};
    static const s32 results[] = {0, 1, 0x13579BDF};
    s32 a, b, c, d, e;
    for (a = 0; a < 4; a++) for (b = 0; b < 5; b++)
    for (c = 0; c < 2; c++) for (d = 0; d < 2; d++)
    for (e = 0; e < 3; e++) {
        int status = one(modes[a], flags[b], c, contexts[d], results[e]);
        if (status) return status;
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
''' % body


class OwnerEnableGateGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / match.BUILD
        (cls.report, cls.predecessor_owner, cls.qualified_owner,
         cls.predecessor_elf, cls.qualified_elf) = match.prepare(
             cls.root, cls.output)
        rom = (cls.root / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(">%dI" % match.WORDS,
                                            rom, match.ROM))

    def test_01_guarded_C_owner_image_and_protected_data(self):
        self.assertEqual((self.report["words"], self.report["natural_words"],
                          self.report["frame"], self.report["guards"],
                          self.report["insertions"], self.report["relocations"]),
                         (47, 44, 24, 19, 3, 1))
        self.assertEqual(self.report["natural_positional_differences"], 40)
        self.assertEqual(self.report["neighbors"], 77)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))
        self.assertEqual(self.qualified_elf.read_bytes(), match.expected_image(
            self.predecessor_elf.read_bytes(), match.retail_bytes(self.root)))

    def test_02_guest_modes_context_return_and_all_words(self):
        visits, cases = set(), 0
        for mode, flags, attached, context, result, phase in itertools.product(
                (0, 1, 2, 7, 0xFFFFFFFF), (0, 1, 2, 3, 0xFFFFFFFF),
                (0, 1), (0, 0x12345678), (0, 1, 0x13579BDF), (0, 8)):
            initial = fixture(mode, flags, attached, context, phase)
            wanted, calls, wanted_result = reference(
                initial, mode, context, result)
            model = EnableGateOracle(
                self.words, initial, mode, context, result, phase).run()
            self.assertEqual(public(model.memory), public(wanted))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[2], wanted_result)
            self.assertEqual(model.r[29], STACK + phase)
            visits.update(model.visits)
            cases += 1
        missing = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - visits
        # The duplicate load immediately before the mode-2 label is skipped by
        # every predecessor: the branch-likely executes its own copy in the
        # delay slot and targets the following instruction.
        self.assertEqual(missing, {0x1514E984})
        self.assertEqual(cases, 600)

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
        for optimization in ("-O0", "-O2", "-O3"):
            self.assertEqual(self.compile_native(body, "native", optimization), 0)
        controls = {
            "wrong-bit": body.replace("& 1) != 0", "& 2) != 0", 1),
            "wrong-toggle-clear": body.replace("&= ~1;", "|= 1;", 1),
            "no-toggle-cleanup": body.replace("attached[0x30] = 0;", "attached[0x30] = 1;", 1),
            "wrong-disable": body.replace("case 2:\n            *(s32 *)(owner + 0x10) &= ~1;",
                                           "case 2:\n            *(s32 *)(owner + 0x10) |= 1;"),
            "wrong-enable": body.replace("case 1:\n            *(s32 *)(owner + 0x10) |= 1;",
                                          "case 1:\n            *(s32 *)(owner + 0x10) &= ~1;"),
            "wrong-context": body.replace("owner, mode, context",
                                          "owner, mode, context & 0"),
            "wrong-result": body.replace("return func_1514E89C(owner, mode, context);",
                                         "func_1514E89C(owner, mode, context); return 1;"),
        }
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0,
                                name)

    def test_04_guards_fail_closed_registry_wrapper_and_live_state(self):
        with (self.output / "proposed-guards.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        target = [row for row in rows if row["filename"] == match.FILENAME and
                  row["function"] == match.FUNCTION]
        self.assertEqual(len(target), 19)
        compact = self.output / "qualified-compact.o"
        for index, selected in enumerate(target):
            changed = [dict(row) for row in rows]
            row_index = next(i for i, row in enumerate(changed)
                             if row["filename"] == match.FILENAME and
                             row["function"] == match.FUNCTION and
                             row["offset"] == selected["offset"])
            changed[row_index]["expected"] = "0x%08X" % (
                int(changed[row_index]["expected"], 0) ^ 1)
            path = self.output / ("stale-guard-%d.csv" % index)
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=changed[0].keys(),
                                        lineterminator="\n")
                writer.writeheader()
                writer.writerows(changed)
            with self.assertRaises(ValueError):
                emit_padded_assembly(compact, self.root / match.ASM,
                    word_patches_path=path, filename=match.FILENAME)
        rom = (self.root / match.ROM_IMAGE).read_bytes()
        self.assertEqual(struct.unpack_from(">5I", rom, 0x22F624),
                         (0x1514E89C, 0x1514E920, 0x1514E9DC,
                          0x1514E9FC, 0x1514EA1C))
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == match.ENTRY],
                         [0x22F628])
        jal = 0x0C000000 | (match.ENTRY >> 2 & 0x03FFFFFF)
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == jal],
                         [0x17BE94])
        self.assertEqual(struct.unpack_from(">4I", rom, 0x17BE8C),
                         (0x27BDFFE8, 0xAFBF0014, jal, 0))
        predecessor, qualified, installed = match.source_states(
            (self.root / match.SOURCE).read_text())
        self.assertEqual(installed, self.report["installed"])
        expected_owner = self.qualified_owner if installed else self.predecessor_owner
        expected_elf = self.qualified_elf if installed else self.predecessor_elf
        self.assertEqual((self.root / match.OBJECT).read_bytes(),
                         expected_owner.read_bytes())
        self.assertEqual((self.root / match.ELF).read_bytes(),
                         expected_elf.read_bytes())
        self.assertNotEqual(predecessor, qualified)


if __name__ == "__main__":
    unittest.main()
