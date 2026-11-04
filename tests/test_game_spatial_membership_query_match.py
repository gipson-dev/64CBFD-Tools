"""Semantic, caller, guard, owner and image gates for func_1503F800."""

import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_spatial_membership_query_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import game_spatial_membership_query_oracle as oracle
from tools.tests.game_view_render_pass_oracle import STACK


ROOT = Path(__file__).resolve().parents[2]


NATIVE_PREFIX = r'''typedef unsigned char u8;
typedef signed short s16;
typedef unsigned short u16;
typedef signed int s32;
typedef unsigned int u32;
#define NULL ((void *)0)
'''


NATIVE_SUFFIX = r'''
u8 *D_800DBE48;
static SpatialMembershipNode1503F800 nodes[6];
static SpatialMembershipNode1503F800 *alternate;
static s32 initializeMode, initializeCalls, initializeArgument;

static void clear_nodes(void) {
    u8 *bytes = (u8 *)nodes;
    u32 index;
    for (index = 0; index < sizeof(nodes); index++)
        bytes[index] = 0;
}

static s16 relative(SpatialMembershipNode1503F800 *from,
                    SpatialMembershipNode1503F800 *to) {
    return (s16)((u8 *)to - (u8 *)from);
}

static void set_node(SpatialMembershipNode1503F800 *node, s16 mask,
                     SpatialMembershipNode1503F800 *sibling, u16 radius,
                     s16 x, s16 z, SpatialMembershipNode1503F800 *child) {
    node->unused0 = (s16)0x6A5A;
    node->categoryMask = mask;
    node->siblingOffset = sibling ? relative(node, sibling) : 0;
    node->radius = radius;
    node->centerX = x;
    node->centerZ = z;
    node->childOffset = child ? relative(node, child) : 0;
}

void func_1510F800(s32 context) {
    initializeCalls++;
    initializeArgument = context;
    if (initializeMode == 1)
        D_800DBE48 = (u8 *)alternate;
    else if (initializeMode == 2)
        D_800DBE48 = NULL;
    else if (initializeMode == 3)
        ((SpatialMembershipNode1503F800 *)D_800DBE48)->categoryMask = 0;
}

static int one(s32 kind, u32 highX, u32 highZ, s32 category) {
    SpatialMembershipNode1503F800 *a = &nodes[2];
    SpatialMembershipNode1503F800 *b = &nodes[5];
    SpatialMembershipNode1503F800 *c = &nodes[0];
    SpatialMembershipNode1503F800 *d = &nodes[4];
    s16 x = 100, z = -50;
    u16 radius = 9;
    s16 bit = (s16)(1 << category);
    s32 expected;
    s32 rawX = (s32)((highX & 0xFFFF0000U) | (u16)x);
    s32 rawZ = (s32)((highZ & 0xFFFF0000U) | (u16)z);

    clear_nodes();
    set_node(a, bit, NULL, radius, x, z, NULL);
    set_node(b, bit, NULL, radius, x, z, NULL);
    set_node(c, bit, NULL, radius, x, z, NULL);
    set_node(d, bit, NULL, radius, x, z, NULL);
    alternate = d;
    D_800DBE48 = (u8 *)a;
    initializeMode = initializeCalls = initializeArgument = 0;
    expected = 0;

    if (kind == 0) {
        D_800DBE48 = NULL;
        expected = 1;
    } else if (kind == 1) {
        expected = 0;
    } else if (kind == 2) {
        set_node(a, 0, b, radius, x, z, NULL);
        expected = 1;
    } else if (kind == 3) {
        set_node(a, bit, b, radius, x + radius + 1, z, NULL);
        expected = 0;
    } else if (kind == 4) {
        D_800DBE48 = (u8 *)b;
        set_node(b, bit, c, radius, x + radius + 1, z, NULL);
        expected = 0;
    } else if (kind == 5) {
        set_node(a, bit, NULL, radius, x, z, b);
        expected = 0;
    } else if (kind == 6) {
        D_800DBE48 = (u8 *)b;
        set_node(b, bit, NULL, radius, x, z, c);
        expected = 0;
    } else if (kind == 7) {
        set_node(a, bit, NULL, radius, x + radius + 1, z, NULL);
        expected = 1;
    } else if (kind == 8) {
        set_node(a, bit, NULL, radius, x - radius, z, NULL);
        expected = 0;
    } else if (kind == 9) {
        set_node(a, bit, NULL, radius, x + radius, z, NULL);
        expected = 0;
    } else if (kind == 10) {
        set_node(a, bit, NULL, radius, x, z - radius - 1, NULL);
        expected = 1;
    } else if (kind == 11) {
        set_node(a, bit, NULL, 0, x, z, NULL);
        expected = 0;
    } else if (kind == 12) {
        set_node(a, bit, NULL, 0xFFFF, x + 123, z - 321, NULL);
        expected = 0;
    } else if (kind == 13) {
        set_node(a, 0, NULL, radius, x, z, NULL);
        initializeMode = 1;
        expected = 0;
    } else if (kind == 14) {
        initializeMode = 2;
        expected = 1;
    } else {
        initializeMode = 3;
        expected = 1;
    }

    if (func_1503F800((void *)0x34567890U, rawX, rawZ, category,
                      (s32)(highX ^ highZ)) != expected)
        return 1;
    if (initializeCalls != 1 || initializeArgument != 0)
        return 2;
    return 0;
}

static int run(void) {
    static const u32 highs[] = {0, 0x12340000U, 0x80000000U, 0xFFFF0000U};
    static const s32 categories[] = {0, 1, 7, 14};
    s32 kind, categoryIndex;
    u32 xIndex, zIndex;
    if (sizeof(void *) != 4 || sizeof(SpatialMembershipNode1503F800) != 14)
        return 20;
    for (kind = 0; kind < 16; kind++)
        for (categoryIndex = 0; categoryIndex < 4; categoryIndex++)
            for (xIndex = 0; xIndex < 4; xIndex++)
                for (zIndex = 0; zIndex < 4; zIndex++)
                    if (one(kind, highs[xIndex], highs[zIndex],
                            categories[categoryIndex]))
                        return 21 + kind;
    return 0;
}

__attribute__((noreturn)) void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
'''


def native_source(body):
    return NATIVE_PREFIX + match.PREAMBLE + body + NATIVE_SUFFIX


class SpatialMembershipQueryMatchTests(unittest.TestCase):
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

    def test_01_guarded_owner_full_image_callers_and_protected_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_frame"], report["retail_frame"],
             report["natural_positional_differences"], report["guards"],
             report["relocations"], report["retail_relocations"]),
            (65, 0x20, 0x18, 52, 52, 3, 3))
        self.assertEqual(report["neighbors"], 2)
        self.assertEqual(report["functions"], 6051)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"], {
            "direct_jal_calls": ["0x6cdfc", "0x1400e8"],
            "aligned_pointer_literals": [],
            "callers": ["func_1503F904", "func_15112A80"],
            "abi": ("query pointer, signed X/Z words, category bit, and an unused "
                    "fifth caller word; returns zero only for an accepted leaf"),
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
        jal = 0x0C000000 | ((match.ENTRY >> 2) & 0x03FFFFFF)
        self.assertEqual(struct.unpack_from(">I", rom, 0x6CDFC)[0], jal)
        self.assertEqual(struct.unpack_from(">I", rom, 0x1400E8)[0], jal)
        self.assertEqual(struct.unpack_from(">I", rom, 0x6CDD8)[0], 0xAFAB0010)
        self.assertEqual(struct.unpack_from(">I", rom, 0x1400EC)[0], 0xAFA00010)
        self.receipt["closure"] = {
            "words": 65, "guards": 52, "natural_relocations": 3,
            "retail_relocations": 3, "neighbors": 2, "functions": 6051,
            "changed_only_target": True, "strict_exclusions": 0,
            "protected_game_bytes": 189088, "protected_data_exact": True,
            "callers": 2, "caller_fifth_words": [1, 0],
        }

    def test_02_guest_tree_paths_initializer_clobbering_and_all_words(self):
        visits = set()
        cases = 0
        raw_values = (0x00000064, 0x12340064, 0x80000064, 0xFFFF0064)
        raw_z_values = (0x0000FFCE, 0xABCDFFCE, 0x8000FFCE, 0xFFFFFFCE)
        for kind, x, z, category, phase, fifth in itertools.product(
                range(14), raw_values, raw_z_values, (0, 1, 7, 14),
                (0, 8), (0, 1, 0xFFFFFFFF)):
            case = oracle.Case(kind, x, z, category, 0, phase, fifth)
            initial = oracle.fixture(case)
            expected_memory, expected_result, expected_calls = oracle.reference(initial, case)
            model = oracle.SpatialMembershipOracle(self.words, initial, case).run()
            self.assertEqual(model.r[2], expected_result, case)
            self.assertEqual(model.calls, expected_calls, case)
            self.assertEqual(oracle.public(model.memory), oracle.public(expected_memory), case)
            self.assertEqual(model.r[29], STACK + phase, case)
            visits.update(model.visits)
            cases += 1
        for kind, mode, wanted in ((2, 1, 0), (1, 2, 1), (1, 3, 1)):
            for phase, fifth in itertools.product((0, 8), (0, 1, 0xA5A5A5A5)):
                case = oracle.Case(kind, mode=mode, phase=phase, fifth=fifth)
                initial = oracle.fixture(case)
                expected_memory, expected_result, expected_calls = oracle.reference(initial, case)
                self.assertEqual(expected_result, wanted)
                model = oracle.SpatialMembershipOracle(self.words, initial, case).run()
                self.assertEqual((model.r[2], model.calls),
                                 (expected_result, expected_calls), case)
                self.assertEqual(oracle.public(model.memory),
                                 oracle.public(expected_memory), case)
                visits.update(model.visits)
                cases += 1
        unreachable = {match.ENTRY + 0xB4, match.ENTRY + 0xE4}
        self.assertEqual(
            visits,
            set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - unreachable)
        self.receipt["guest"] = {
            "cases": cases, "stack_phases": [0, 8], "retail_words_reached": 63,
            "structurally_unreachable_words": ["0x1503f8b4", "0x1503f8e4"],
            "all_retail_words_accounted": True,
            "signed_query_truncation": True, "unsigned_radius": True,
            "inclusive_bounds": True, "immediate_category_rejection": True,
            "positive_and_negative_sibling_offsets": True,
            "positive_and_negative_child_offsets": True,
            "initializer_precedes_head_load": True, "call_clobbering": True,
            "fifth_words_ignored": [0, 1, 0xFFFFFFFF, 0xA5A5A5A5],
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
            profiles[optimization] = {"cases": 1024, "exit": 0, "UBSan": True}
        controls = {
            "wrong-z-truncation": body.replace("queryZ = z;", "queryZ = z >> 16;"),
            "exclusive-upper-x": body.replace(
                "((centerX + radius) >= x)", "((centerX + radius) > x)"),
            "exclusive-lower-x": body.replace(
                "(x >= (centerX - radius))", "(x > (centerX - radius))"),
            "wrong-z-center": body.replace("centerZ = node->centerZ;",
                                             "centerZ = node->centerX;"),
            "inverted-category": body.replace(
                "if (!(node->categoryMask & (1 << category)))",
                "if (node->categoryMask & (1 << category))"),
            "sibling-for-child": body.replace("offset = childOffset;",
                                                "offset = node->siblingOffset;"),
            "unsigned-relative-offset": body.replace(
                "((u8 *)node + offset)", "((u8 *)node + (u16)offset)"),
            "accepted-leaf-is-miss": body.replace("                return 0;",
                                                    "                return 1;", 1),
            "skip-initializer": body.replace("    func_1510F800(0);",
                                              "    /* initializer skipped */"),
            "never-follow-sibling": body.replace("offset = node->siblingOffset;",
                                                   "offset = 0;"),
        }
        rejected = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body, name)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0, name)
            rejected[name] = "independent spatial corpus mismatch"
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

        target_indices = [index for index, row in enumerate(self.values["qualified_rows"])
                          if row["filename"] == match.FILENAME and
                          row["function"] == match.FUNCTION]
        self.assertEqual(len(target_indices), len(match.PATCH_ROWS))
        guard_controls = 0
        for ordinal, row_index in enumerate(target_indices):
            rows = [dict(row) for row in self.values["qualified_rows"]]
            rows[row_index]["expected"] = "0x%08X" % (
                int(rows[row_index]["expected"], 0) ^ 1)
            path = self.output / ("bad-guard-%02d.csv" % ordinal)
            harness.write_patches(path, self.values["fields"], rows)
            with self.assertRaises(ValueError):
                emit_padded_assembly(
                    self.values["qualified_compact"], ROOT / match.ASM,
                    word_patches_path=path, filename=match.FILENAME)
            guard_controls += 1

        relocation_controls = 0
        for offset in match.BINDINGS:
            row_index = target_indices[
                [int(row["offset"], 0) for row in match.PATCH_ROWS].index(offset)]
            rows = [dict(row) for row in self.values["qualified_rows"]]
            rows[row_index]["expected_relocations"] = "R_MIPS_LO16:D_80123450"
            path = self.output / ("bad-binding-%03X.csv" % offset)
            harness.write_patches(path, self.values["fields"], rows)
            with self.assertRaises(ValueError):
                emit_padded_assembly(
                    self.values["qualified_compact"], ROOT / match.ASM,
                    word_patches_path=path, filename=match.FILENAME)
            relocation_controls += 1

        self.assertEqual(raw_controls, 260)
        self.assertEqual(guard_controls, 52)
        self.assertEqual(relocation_controls, 3)
        self.receipt["fail_closed"] = {
            "raw_byte_controls": raw_controls,
            "guard_preimage_controls": guard_controls,
            "relocation_binding_controls": relocation_controls,
            "insertions": 0, "omissions": 0,
        }


if __name__ == "__main__":
    unittest.main()

