"""Guard, semantics, ABI, owner, and image gates for func_151283B8."""

import csv
import io
import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_camera_mode_dispatch_guard_match as match
from tools.pad_c_object import emit_padded_assembly
from tools.tests.test_game_camera_heading import (
    CAMERA, Case, HeadingOracle, STACK, complete)


MODES = (
    -0x80000000, -1, 0, 1, 2, 3, 7, 8, 9, 0x3F, 0x40, 0x41,
    0x7F, 0x80, 0x81, 0xFF, 0x100, 0x101, 0x3FF, 0x400, 0x401,
    0x7FF, 0x800, 0x801, 0x1FFF, 0x2000, 0x2001, 0x7FFFFF,
    0x800000, 0x800001, 0x7FFFFFFF,
)
EXPECTED = {
    1: 0x15122980,
    2: 0x151220D0,
    8: 0x15121C80,
    0x40: 0x15129934,
    0x80: 0x15122440,
    0x100: 0x15120158,
    0x400: 0x15122170,
    0x800: 0x15122980,
    0x800000: 0x1512DEA4,
}


class DispatchOracle(HeadingOracle):
    def __init__(self, words, mode, phase):
        self.call_arguments = []
        super().__init__(words, Case(flags=4), phase=phase,
                         entry=match.ENTRY, mode=mode & 0xFFFFFFFF)

    def record_call(self, target):
        self.call_arguments.append((target, self.arguments(2)))
        super().record_call(target)


def native_harness(body):
    cases = ",\n".join("{(s32)0x%08Xu,0x%08Xu}" %
                        (mode & 0xFFFFFFFF, EXPECTED.get(mode, 0))
                        for mode in MODES)
    return """typedef unsigned char u8;
typedef unsigned int u32;
typedef int s32;
typedef struct { u8 padding[0x2C]; s32 unk2C; } struct108;
%s
%s
static struct108 camera;
static struct108 *wanted;
static s32 called;
static s32 second;
static void record(struct108 *value, s32 id) {
    if (value != wanted || called != 0) called = -1;
    else called = id;
}
void func_15120158(struct108 *p) { record(p, 1); }
s32 func_15121C80(struct108 *p, s32 value) { second = value; record(p, 2); return 0; }
void func_151220D0(struct108 *p) { record(p, 3); }
void func_15122170(struct108 *p) { record(p, 4); }
void func_15122440(struct108 *p) { record(p, 5); }
void func_15122980(struct108 *p) { record(p, 6); }
void func_15129934(struct108 *p) { record(p, 7); }
void func_1512DEA4(struct108 *p) { record(p, 8); }
typedef struct { s32 mode; u32 target; } CaseRow;
static const CaseRow cases[] = {
%s
};
static s32 translated(u32 address) {
    switch (address) {
    case 0x15120158: return 1;
    case 0x15121C80: return 2;
    case 0x151220D0: return 3;
    case 0x15122170: return 4;
    case 0x15122440: return 5;
    case 0x15122980: return 6;
    case 0x15129934: return 7;
    case 0x1512DEA4: return 8;
    default: return 0;
    }
}
static int test_all(void) {
    u32 i;
    if (sizeof(void *) != 4 || __builtin_offsetof(struct108, unk2C) != 0x2C)
        return 90;
    wanted = &camera;
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        called = 0;
        second = 0x12345678;
        camera.unk2C = cases[i].mode;
        func_151283B8(&camera);
        if (called != translated(cases[i].target)) return 23;
        if (cases[i].mode == 8 && second != 0) return 24;
        if (cases[i].mode != 8 && second != 0x12345678) return 25;
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status = test_all();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
""" % (match.HELPER_DECLARATIONS, body, cases)


class CameraModeDispatchGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / match.BUILD
        (cls.report, cls.predecessor_owner, cls.qualified_owner,
         cls.predecessor_elf, cls.qualified_elf) = match.prepare(
             cls.root, cls.output)
        cls.retail = list(struct.unpack(">%dI" % match.WORDS,
                                        match.retail_bytes(cls.root)))
        cls.natural = list(cls.retail)
        cls.natural[0xA8 // 4] = 0x00002825

    def test_01_one_fail_closed_guard_reproduces_retail(self):
        self.assertEqual((self.report["words"], self.report["frame"],
                          self.report["natural_differences"],
                          self.report["guards"], self.report["relocations"]),
                         (67, 24, 1, 1, 9))
        row = match.guard_row()
        self.assertEqual((row["offset"], row["expected"], row["replacement"]),
                         ("0x0A8", "0x00002825", "0x24050000"))
        source = (self.root / match.SOURCE).read_text()
        _, qualified, _ = match.source_states(source)
        compact, _ = match.compile_owner(
            self.root, self.output, qualified, "stale-check-compact")
        guards = (self.output / "qualified-guards.csv").read_bytes()
        with io.StringIO(guards.decode(), newline="") as stream:
            rows = list(csv.DictReader(stream))
            fields = stream.seek(0) or next(csv.reader(io.StringIO(guards.decode())))
        for item in rows:
            if item["function"] == match.FUNCTION:
                item["expected"] = "0x00002824"
        stale = self.output / "stale-guard.csv"
        with stale.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields,
                                    lineterminator="\n")
            writer.writeheader(); writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "stale word patch"):
            emit_padded_assembly(compact, self.root / match.LAYOUT,
                                 match.FILENAME, word_patches_path=stale)

    def test_02_guest_switch_semantics_call_abi_and_full_coverage(self):
        visits = set()
        executions = 0
        for mode, phase in itertools.product(MODES, (0, 8)):
            models = []
            for words in (self.retail, self.natural):
                model = DispatchOracle(words, mode, phase).run()
                targets = [item[0] for item in model.calls]
                expected = [] if mode not in EXPECTED else [EXPECTED[mode]]
                self.assertEqual(targets, expected)
                if mode == 8:
                    self.assertEqual(model.call_arguments,
                                     [(0x15121C80, (CAMERA, 0))])
                self.assertEqual(model.r[29], STACK + phase)
                models.append(model)
                visits.update(model.visits)
                executions += 1
            self.assertEqual(complete(models[0]), complete(models[1]))
        self.assertTrue(set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) <= visits)
        self.assertEqual(executions, len(MODES) * 4)

    def compile_native(self, body, label, optimization):
        source = self.output / (label + optimization + ".c")
        binary = self.output / (label + optimization)
        source.write_text(native_harness(body))
        result = subprocess.run([
            "gcc", "-m32", optimization, "-std=gnu89", "-ffreestanding",
            "-nostdlib", "-static", "-fno-pie", "-no-pie",
            "-fno-stack-protector", "-fsanitize=undefined",
            "-fsanitize-undefined-trap-on-error", "-Wall", "-Wextra",
            "-Werror", str(source), "-o", str(binary)],
            capture_output=True, text=True)
        (self.output / (label + optimization + "-compiler.log")).write_text(
            result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr[:3000])
        return subprocess.run([str(binary)], timeout=30).returncode

    def test_03_native32_profiles_and_effective_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            self.assertEqual(self.compile_native(
                match.SELECTED, "native", optimization), 0)
        controls = {
            "wrong-zero": match.SELECTED.replace("camera, 0);", "camera, 1);"),
            "wrong-80": match.SELECTED.replace(
                "func_15122440(camera);", "func_15129934(camera);", 1),
            "wrong-high": match.SELECTED.replace(
                "func_1512DEA4(camera);", "func_15120158(camera);", 1),
            "missing-400": match.SELECTED.replace(
                "        func_15122170(camera);", "        break;", 1),
        }
        for name, body in controls.items():
            self.assertNotEqual(body, match.SELECTED)
            self.assertNotEqual(self.compile_native(body, name, "-O2"), 0, name)

    def test_04_owner_image_closure_and_protected_data(self):
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        self.assertEqual(self.report["neighbors"], 44)
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))
        self.assertEqual(self.qualified_elf.read_bytes(), match.expected_image(
            self.predecessor_elf.read_bytes(), match.retail_bytes(self.root)))

    def test_05_caller_census_and_live_state_are_closed(self):
        rom = (self.root / match.ROM_IMAGE).read_bytes()
        opcode = 0x0C000000 | (match.ENTRY >> 2 & 0x03FFFFFF)
        found = [offset for offset in range(0, len(rom) - 3, 4)
                 if struct.unpack_from(">I", rom, offset)[0] == opcode]
        self.assertEqual(found, [0x150408, 0x15042C, 0x150434, 0x156810])
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
