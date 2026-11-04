"""Semantic, dispatch, guard, owner and image gates for func_15075938."""

import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_path_offset_condition_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests import game_path_offset_condition_oracle as oracle
from tools.tests.game_view_render_pass_oracle import STACK


ROOT = Path(__file__).resolve().parents[2]


NATIVE_PREFIX = r'''typedef unsigned char u8;
typedef signed char s8;
typedef signed int s32;
typedef unsigned int u32;

struct struct127 {
    u8 pad0[0x13F];
    u8 unk13F;
    u8 pad140[0xDE];
    u8 unk21E;
    u8 pad21F[2];
    s8 unk221;
};

struct struct127 *D_800D154C;
u8 *D_800D2108;
u8 D_800D1890;
u8 D_800D1891;
u8 D_800D1892;
void func_15075400(s32 argument);
'''


NATIVE_SUFFIX = r'''
static u8 actorBytes[0x260];
static u8 pathCounts[256];
static s32 helperCalls;
static s32 helperArgument;

void func_15075400(s32 argument) {
    helperCalls++;
    helperArgument = argument;
}

static u32 digest(const u8 *bytes, u32 length) {
    u32 value = 2166136261U;
    u32 index;
    for (index = 0; index < length; index++)
        value = (value ^ bytes[index]) * 16777619U;
    return value;
}

static s32 signed_byte(u8 value) {
    return value & 0x80 ? (s32)value - 0x100 : value;
}

static int one(u8 pathCount, u8 currentByte, u8 offsetByte,
               u8 targetByte, u8 modeByte, u8 pathIndex, u8 commandByte) {
    u32 actorBefore, tableBefore;
    s32 current, target, changed;
    u32 index;

    for (index = 0; index < sizeof(actorBytes); index++)
        actorBytes[index] = (u8)(index * 13U + pathIndex * 7U + 0x5AU);
    for (index = 0; index < sizeof(pathCounts); index++)
        pathCounts[index] = (u8)(index * 29U + 0xA5U);

    D_800D154C = (struct struct127 *)actorBytes;
    D_800D2108 = pathCounts;
    D_800D154C->unk13F = pathIndex;
    D_800D154C->unk21E = currentByte;
    D_800D154C->unk221 = (s8)offsetByte;
    D_800D2108[pathIndex] = pathCount;
    D_800D1890 = commandByte;
    D_800D1891 = targetByte;
    D_800D1892 = modeByte;
    helperCalls = 0;
    helperArgument = -1;
    actorBefore = digest(actorBytes, sizeof(actorBytes));
    tableBefore = digest(pathCounts, sizeof(pathCounts));

    current = currentByte - signed_byte(offsetByte);
    if (current < 0)
        current += pathCount - 1;
    else if (current >= pathCount - 1)
        current -= pathCount - 1;
    target = targetByte == 0xFF ? pathCount - 2 : targetByte;
    if (modeByte == 0)
        changed = target == current;
    else if (modeByte == 1)
        changed = target != current;
    else if (modeByte == 2)
        changed = target < current;
    else
        changed = target > current;

    func_15075938();
    if (helperCalls != changed)
        return 1;
    if (changed && helperArgument != commandByte)
        return 2;
    if (digest(actorBytes, sizeof(actorBytes)) != actorBefore ||
        digest(pathCounts, sizeof(pathCounts)) != tableBefore)
        return 3;
    if (D_800D1890 != commandByte || D_800D1891 != targetByte ||
        D_800D1892 != modeByte)
        return 4;
    return 0;
}

static int run(void) {
    static const u8 counts[] = {2, 3, 8, 32, 255};
    static const u8 currents[] = {0, 1, 6, 31, 127, 255};
    static const u8 offsets[] = {0, 1, 7, 127, 128, 255};
    static const u8 targets[] = {0, 1, 5, 254, 255};
    u32 ci, ui, oi, ti, mode;
    struct struct127 layout;

    if (sizeof(void *) != 4 || sizeof(struct struct127) != 0x222 ||
        (u8 *)&layout.unk13F - (u8 *)&layout != 0x13F ||
        (u8 *)&layout.unk21E - (u8 *)&layout != 0x21E ||
        (u8 *)&layout.unk221 - (u8 *)&layout != 0x221)
        return 10;
    for (ci = 0; ci < sizeof(counts); ci++)
        for (ui = 0; ui < sizeof(currents); ui++)
            for (oi = 0; oi < sizeof(offsets); oi++)
                for (ti = 0; ti < sizeof(targets); ti++)
                    for (mode = 0; mode < 4; mode++) {
                        u8 pathIndex = (u8)(ci * 53U + ui * 17U +
                            oi * 11U + ti * 7U + mode);
                        if (one(counts[ci], currents[ui], offsets[oi],
                                targets[ti], (u8)mode, pathIndex,
                                (u8)(0x31U + pathIndex)))
                            return 20 + (int)mode;
                    }
    return 0;
}

__attribute__((noreturn)) void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
'''


def native_source(body):
    return NATIVE_PREFIX + body + NATIVE_SUFFIX


class PathOffsetConditionMatchTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.values = match.prepare(ROOT, cls.output)
        cls.report = cls.values["report"]
        image = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(
            ">%dI" % match.WORDS, image, match.ROM))
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
        cls.output.mkdir(parents=True, exist_ok=True)
        (cls.output / "test-receipt.json").write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_guarded_owner_full_image_dispatch_and_protected_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_frame"], report["retail_frame"],
             report["natural_positional_differences"], report["guards"],
             report["relocations"], report["retail_relocations"]),
            (70, 0x18, 0x18, 3, 3, 13, 13))
        self.assertEqual(report["neighbors"], 210)
        self.assertEqual(report["functions"], 6051)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"], {
            "direct_jal_calls": [],
            "direct_jumps": [],
            "aligned_pointer_literals": ["0x22b430"],
            "dispatch_table": "D_80086730",
            "dispatch_row": 144,
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
        rom = (ROOT / match.ROM_IMAGE).read_bytes()
        self.assertEqual(struct.unpack_from(">I", rom, 0x22B430)[0], match.ENTRY)
        self.receipt["closure"] = {
            "words": 70, "guards": 3, "natural_relocations": 13,
            "retail_relocations": 13, "neighbors": 210,
            "functions": 6051, "changed_only_target": True,
            "strict_exclusions": 0, "protected_game_bytes": 189088,
            "protected_data_exact": True, "dispatch_table": "D_80086730",
            "dispatch_row": 144,
        }

    def test_02_guest_wrap_sentinel_predicates_clobbering_and_all_words(self):
        visits = set()
        cases = 0
        for ordinal, values in enumerate(itertools.product(
                (2, 3, 8, 32, 255),
                (0, 1, 6, 31, 127, 255),
                (0, 1, 0xFF, 0x80),
                (0, 1, 5, 0xFE, 0xFF),
                (0, 1, 2, 3),
                (0, 8))):
            path_count, current, offset, target, mode, phase = values
            case = oracle.Case(
                path_count, current, offset, target, mode,
                (0x31 + ordinal * 17) & 0xFF,
                (ordinal * 53 + 7) & 0xFF, phase)
            initial = oracle.fixture(case)
            expected_memory, expected_calls = oracle.reference(initial, case)
            model = oracle.PathOffsetConditionOracle(
                self.words, initial, case).run()
            self.assertEqual(model.calls, expected_calls, case)
            self.assertEqual(oracle.public(model.memory),
                             oracle.public(expected_memory), case)
            self.assertEqual(model.r[29], STACK + phase, case)
            visits.update(model.visits)
            cases += 1
        unreachable = {match.ENTRY + 0x50, match.ENTRY + 0xCC}
        self.assertEqual(
            visits,
            set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - unreachable)
        self.receipt["guest"] = {
            "cases": cases, "stack_phases": [0, 8],
            "retail_words_reached": 68,
            "structurally_unreachable_words": ["0x15075988", "0x15075a04"],
            "all_retail_words_accounted": True,
            "positive_and_negative_wrap": True,
            "signed_offset_extremes": [-128, -1, 0, 1],
            "sentinel_target": "0xff resolves to path count minus two",
            "predicate_modes": ["equal", "not-equal", "less-than", "greater-than"],
            "helper_call_clobbering": True,
        }

    def compile_native(self, body, label, optimization):
        source = self.output / (label + optimization + ".c")
        binary = self.output / (label + optimization)
        source.write_text(native_source(body))
        result = subprocess.run([
            "gcc", "-m32", optimization, "-std=gnu89", "-ffreestanding",
            "-nostdlib", "-static", "-fno-pie", "-no-pie",
            "-fno-stack-protector", "-fno-strict-aliasing",
            "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
            "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
            str(source), "-o", str(binary)], capture_output=True, text=True)
        (self.output / (label + optimization + "-compiler.log")).write_text(
            result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr[:3000])
        return subprocess.run([str(binary)], timeout=30).returncode

    def test_03_native32_profiles_and_effective_semantic_controls(self):
        body = match.SELECTED
        profiles = {}
        for optimization in ("-O0", "-O2", "-O3"):
            self.assertEqual(self.compile_native(body, "native", optimization), 0)
            profiles[optimization] = {"cases": 3600, "exit": 0, "UBSan": True}
        controls = {
            "unsigned-offset": body.replace(
                "D_800D154C->unk21E - D_800D154C->unk221",
                "D_800D154C->unk21E - (u8)D_800D154C->unk221"),
            "wrong-negative-correction": body.replace(
                "current = current + pathCount - 1;",
                "current = current + pathCount + 1;"),
            "exclusive-upper-wrap": body.replace(
                "current >= pathCount - 1", "current > pathCount - 1"),
            "wrong-positive-correction": body.replace(
                "current = current - pathCount + 1;",
                "current = current - pathCount - 1;"),
            "wrong-sentinel": body.replace("D_800D1891 == 0xFF",
                                             "D_800D1891 == 0xFE"),
            "invert-equal": body.replace("target == current", "target != current", 1),
            "invert-not-equal": body.replace("target != current", "target == current", 1),
            "reverse-less-than": body.replace("target < current", "target > current", 1),
            "reverse-greater-than": body.replace("target > current", "target < current", 1),
            "wrong-helper-argument": body.replace(
                "func_15075400(D_800D1890);", "func_15075400(D_800D1891);"),
            "skip-helper": body.replace(
                "        func_15075400(D_800D1890);",
                "        /* helper skipped */"),
        }
        rejected = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body, name)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0, name)
            rejected[name] = "independent wrapped-path corpus mismatch"
        self.receipt["native"] = {"profiles": profiles, "controls": rejected}

    def test_04_raw_bytes_relocations_and_each_guard_row_fail_closed(self):
        self.assertEqual(len(self.raw), match.SIZE)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), match.RAW_SHA256)
        self.assertEqual(self.bindings, match.BINDINGS)
        raw_controls = 0
        for index in range(len(self.raw)):
            changed = bytearray(self.raw)
            changed[index] ^= 1
            self.assertNotEqual(hashlib.sha256(changed).hexdigest(), match.RAW_SHA256)
            raw_controls += 1

        target_indices = [
            index for index, row in enumerate(self.values["qualified_rows"])
            if row["filename"] == match.FILENAME and
            row["function"] == match.FUNCTION
        ]
        self.assertEqual(len(target_indices), len(match.PATCH_ROWS))
        guard_controls = 0
        for ordinal, row_index in enumerate(target_indices):
            rows = [dict(row) for row in self.values["qualified_rows"]]
            rows[row_index]["expected"] = "0x%08X" % (
                int(rows[row_index]["expected"], 0) ^ 1)
            path = self.output / ("bad-guard-%02d.csv" % ordinal)
            harness.write_patches(path, self.values["fields"], rows)
            with self.assertRaises(ValueError):
                match.emit_owner(
                    self.values["qualified_compact"], ROOT / match.ASM,
                    word_patches_path=path, filename=match.FILENAME)
            guard_controls += 1

        relocation_controls = 0
        for ordinal in range(len(match.PATCH_ROWS)):
            rows = [dict(row) for row in self.values["qualified_rows"]]
            rows[target_indices[ordinal]][
                "expected_relocations"] = "R_MIPS_LO16:D_80123450"
            path = self.output / ("bad-binding-%02d.csv" % ordinal)
            harness.write_patches(path, self.values["fields"], rows)
            with self.assertRaises(ValueError):
                match.emit_owner(
                    self.values["qualified_compact"], ROOT / match.ASM,
                    word_patches_path=path, filename=match.FILENAME)
            relocation_controls += 1

        self.assertEqual(raw_controls, 280)
        self.assertEqual(guard_controls, 3)
        self.assertEqual(relocation_controls, 3)
        self.receipt["fail_closed"] = {
            "raw_byte_controls": raw_controls,
            "guard_preimage_controls": guard_controls,
            "relocation_binding_controls": relocation_controls,
            "insertions": 0, "omissions": 0,
        }


if __name__ == "__main__":
    unittest.main()
