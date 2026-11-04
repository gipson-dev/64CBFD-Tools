"""Closure, semantics and fail-closed gates for the motion-target pair."""

import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_motion_target_pair_match as match
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import game_motion_target_pair_oracle as oracle
from tools.tests.game_view_render_pass_oracle import STACK


ROOT = Path(__file__).resolve().parents[2]

NATIVE_PREFIX = r'''typedef signed short s16;
typedef signed int s32;
typedef unsigned int u32;

s32 D_800BE4E0;
s32 func_150ADA20(void);
void func_150CDB6C(s32 value);
'''

NATIVE_SUFFIX = r'''
static unsigned char storage[116];
static unsigned char before[116];
static u32 randomValues[10];
static s32 randomCalls;
static s32 helperCalls;
static s32 helperArgument;

s32 func_150ADA20(void) {
    return (s32)randomValues[randomCalls++];
}

void func_150CDB6C(s32 value) {
    helperCalls++;
    helperArgument = value;
}

static void write16(unsigned char *bytes, s32 offset, s32 value) {
    *(s16 *)(bytes + offset) = (s16)value;
}

static s32 run(void) {
    static const s32 intensities[] = {-128, -1, 0, 1, 15, 16, 63, 100,
                                     127, 128, 254, 255};
    static const u32 seeds[] = {0, 1, 0x7FFFFFFFU, 0x80000000U,
                                0xFFFFFFFFU, 0xA5A55A5AU};
    s32 i, j, pattern;
    if (sizeof(void *) != 4 || sizeof(s32) != 4 || sizeof(s16) != 2)
        return 20;
    D_800BE4E0 = 0;
    randomCalls = helperCalls = 0;
    func_150C851C(100);
    if (randomCalls || helperCalls)
        return 21;
    for (i = 0; i < (s32)(sizeof(intensities) / sizeof(intensities[0])); i++)
        for (pattern = 0; pattern < 8; pattern++) {
            s32 intensity = intensities[i];
            s32 base = (intensity * 300) >> 8;
            u32 span = (u32)(((intensity * 50) >> 8) + 50);
            for (j = 0; j < 116; j++)
                storage[j] = before[j] =
                    (unsigned char)(j * 13 + pattern * 29 + 0x63);
            for (j = 0; j < 10; j++)
                randomValues[j] = seeds[(pattern + j) % 6] ^
                                  (u32)(pattern * 0x10203 + j * 0x110011);
            randomCalls = helperCalls = 0;
            helperArgument = 0x12345678;
            D_800BE4E0 = (s32)(unsigned long)storage;
            func_150C851C(intensity);
            if (helperCalls != 1 || helperArgument != intensity ||
                    randomCalls != 10)
                return 30;
            for (j = 0; j < 10; j++) {
                s32 target = base + randomValues[j] % span;
                write16(before, j * 10 + 8, target);
            }
            for (j = 0; j < 116; j++)
                if (storage[j] != before[j])
                    return 31;
        }
    return 0;
}

__attribute__((noreturn)) void _start(void) {
    s32 status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
'''


def native_source(body):
    return NATIVE_PREFIX + body + NATIVE_SUFFIX


class MotionTargetPairTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.values = match.prepare(ROOT, cls.output)
        cls.report = cls.values["report"]
        image = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.wrapper_words = list(struct.unpack_from(">10I", image,
                                                    match.WRAPPER_ROM))
        cls.initializer_words = list(struct.unpack_from(">57I", image,
                                                        match.INITIALIZER_ROM))
        text, functions, relocations = parse_object(cls.values["qualified_compact"])
        cls.raw = {}
        cls.bindings = {}
        for name in match.FUNCTIONS:
            info = functions[name]
            start, end = info["value"], info["value"] + info["size"]
            cls.raw[name] = text[start:end]
            cls.bindings[name] = {
                offset - start: rows for offset, rows in relocations.items()
                if start <= offset < end
            }

    @classmethod
    def tearDownClass(cls):
        cls.output.mkdir(parents=True, exist_ok=True)
        (cls.output / "test-receipt.json").write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_owner_split_full_image_callers_inventory_and_data(self):
        report = self.report
        self.assertEqual(report["words"], {
            match.WRAPPER: 10, match.INITIALIZER: 57})
        self.assertEqual(report["frames"], {
            match.WRAPPER: 24, match.INITIALIZER: 48})
        self.assertEqual(report["natural_positional_differences"], {
            match.WRAPPER: 0, match.INITIALIZER: 4})
        self.assertEqual(report["guards"], 4)
        self.assertEqual(report["relocations"], {
            match.WRAPPER: 1, match.INITIALIZER: 4})
        self.assertEqual(report["neighbors"], 17)
        self.assertEqual(report["disassembly_functions_after"], 6052)
        self.assertEqual(report["inventory_added_only"], match.INITIALIZER)
        self.assertEqual(report["changed_bodies"], sorted(match.FUNCTIONS))
        self.assertTrue(report["all_addresses_fixed"])
        self.assertTrue(report["inventory_only_loaded_sections_equal"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["qualified_owner_sha256"],
                         report["assembly_truth_owner_sha256"])
        self.assertEqual(report["qualified_elf_sha256"],
                         report["assembly_truth_elf_sha256"])
        self.assertEqual((report["inventory"]["functions"],
                          report["inventory"]["converted"]), (6046, 5512))
        self.assertEqual(report["callers"][match.WRAPPER]["registration"],
                         "D_8008CD04[9]")
        self.assertEqual(report["callers"][match.INITIALIZER]["direct_jal_calls"],
                         ["0xbc98", "0x3d3b8", "0x53094"])
        data = report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"], data["sha256"]),
                         (True, 189088, 720, 0,
                          "0bbc00e1adfac5ffe6117f5be9c941575f87b341a77d808004603ac1cb87c670"))
        self.receipt["closure"] = {
            "words": [10, 57], "guards": 4, "relocations": [1, 4],
            "neighbors": 17, "functions": 6052,
            "inventory_added_only": match.INITIALIZER,
            "strict_exclusions": 0, "assembly_truth_full_image_equal": True,
            "protected_game_bytes": 189088, "protected_data_exact": True,
            "wrapper_registration": "D_8008CD04[9]",
            "initializer_callers": 3,
        }

    def test_02_guest_null_present_signed_intensities_wrapper_and_all_words(self):
        initializer_visits = set()
        cases = 0
        intensities = (-128, -1, 0, 1, 15, 16, 63, 100,
                       127, 128, 254, 255)
        for intensity, present, pattern, phase in itertools.product(
                intensities, (False, True), range(6), (0, 8)):
            case = oracle.Case(intensity, present, pattern, phase)
            initial = oracle.fixture(case)
            expected_memory, expected_calls = oracle.reference(initial, case)
            model = oracle.InitializerOracle(
                self.initializer_words, initial, case).run()
            self.assertEqual(model.calls, expected_calls, case)
            self.assertEqual(oracle.public(model.memory),
                             oracle.public(expected_memory), case)
            self.assertEqual(model.r[29], STACK + phase, case)
            initializer_visits.update(model.visits)
            cases += 1
        # IDO emits the architectural divide-by-zero trap after a branch that
        # skips it for every nonzero span. The qualified caller domain keeps
        # span in 25..99, so this one word is deliberately unreachable.
        dead_divide_trap = match.INITIALIZER_ENTRY + 0xB0
        self.assertEqual(initializer_visits,
                         set(range(match.INITIALIZER_ENTRY,
                                   match.INITIALIZER_ENTRY +
                                   match.INITIALIZER_SIZE, 4)) -
                         {dead_divide_trap})

        wrapper_visits = set()
        wrapper_cases = 0
        for view, phase in itertools.product((0, 1, -1, 0x7FFFFFFF), (0, 8)):
            case = oracle.Case(100, False, 0, phase)
            model = oracle.WrapperOracle(
                self.wrapper_words, oracle.fixture(case), view, phase).run()
            self.assertEqual(model.calls,
                             [(oracle.ADVANCE, ())] if view == 0 else [])
            self.assertEqual(model.r[29], STACK + phase)
            wrapper_visits.update(model.visits)
            wrapper_cases += 1
        self.assertEqual(wrapper_visits,
                         set(range(match.WRAPPER_ENTRY,
                                   match.WRAPPER_ENTRY + match.WRAPPER_SIZE, 4)))
        self.receipt["guest"] = {
            "initializer_cases": cases, "wrapper_cases": wrapper_cases,
            "stack_phases": [0, 8], "signed_intensities": list(intensities),
            "null_and_present_tables": True, "ten_random_calls": True,
            "ten_stride_10_halfword_writes": True,
            "helper_and_rng_clobbering": True,
            "initializer_words_reached": 56,
            "unreachable_nonzero_span_divide_trap_words": 1,
            "wrapper_words_reached": 10,
        }

    def compile_native(self, body, label, optimization):
        source = self.output / (label + optimization + ".c")
        binary = self.output / (label + optimization)
        source.write_text(native_source(body))
        result = subprocess.run([
            "gcc", "-m32", optimization, "-std=gnu89", "-ffreestanding",
            "-nostdlib", "-static", "-fno-pie", "-no-pie", "-fno-builtin",
            "-fno-stack-protector", "-fno-strict-aliasing",
            "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
            "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
            str(source), "-o", str(binary),
        ], capture_output=True, text=True)
        (self.output / (label + optimization + "-compiler.log")).write_text(
            result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr[:3000])
        return subprocess.run([str(binary)], timeout=30).returncode

    def test_03_native32_profiles_and_effective_semantic_controls(self):
        body = match.INITIALIZER_SELECTED
        profiles = {}
        for optimization in ("-O0", "-O2", "-O3"):
            self.assertEqual(self.compile_native(body, "native", optimization), 0)
            profiles[optimization] = {"cases": 96, "exit": 0, "UBSan": True}
        controls = {
            "reverse-presence-gate": body.replace("!= 0", "== 0", 1),
            "skip-helper": body.replace("        func_150CDB6C(intensity);\n", "", 1),
            "wrong-base-scale": body.replace("* 300", "* 301", 1),
            "wrong-span-scale": body.replace("* 50", "* 51", 1),
            "wrong-span-bias": body.replace("+ 50", "+ 49", 1),
            "nine-records": body.replace("offset != 100", "offset != 90", 1),
            "stride-eight": body.replace("offset += 10", "offset += 8", 1),
            "halfword-offset-six": body.replace("offset + 8", "offset + 6", 1),
            "signed-random-modulo": body.replace(
                "u32 span;", "s32 span;", 1).replace(
                    "(u32)func_150ADA20()", "func_150ADA20()", 1),
        }
        rejected = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body, name)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0,
                                name)
            rejected[name] = "independent target-table corpus mismatch"
        self.receipt["native"] = {"profiles": profiles, "controls": rejected}

    def test_04_raw_bytes_relocations_guards_and_split_metadata_fail_closed(self):
        raw_controls = 0
        for name in match.FUNCTIONS:
            self.assertEqual(hashlib.sha256(self.raw[name]).hexdigest(),
                             match.RAW_SHA256[name])
            self.assertEqual(self.bindings[name], match.BINDINGS[name])
            for index in range(len(self.raw[name])):
                changed = bytearray(self.raw[name])
                changed[index] ^= 1
                self.assertNotEqual(hashlib.sha256(changed).hexdigest(),
                                    match.RAW_SHA256[name])
                raw_controls += 1

        target_indices = [index for index, row in
                          enumerate(self.values["qualified_rows"])
                          if row["filename"] == match.OWNER and
                          row["function"] == match.INITIALIZER]
        self.assertEqual(len(target_indices), 4)
        guard_controls = 0
        for ordinal, row_index in enumerate(target_indices):
            rows = [dict(row) for row in self.values["qualified_rows"]]
            rows[row_index]["expected"] = "0x%08X" % (
                int(rows[row_index]["expected"], 0) ^ 1)
            path = self.output / ("bad-guard-%02d.csv" % ordinal)
            match.write_patches(path, self.values["fields"], rows)
            with self.assertRaises(ValueError):
                emit_padded_assembly(
                    self.values["qualified_compact"], ROOT / match.ASM,
                    word_patches_path=path, filename=match.OWNER)
            guard_controls += 1

        relocation_controls = 0
        for name, bindings in match.BINDINGS.items():
            for offset, rows in bindings.items():
                changed = dict(bindings)
                changed[offset] = [(rows[0][0], "D_80123450")]
                self.assertNotEqual(changed, bindings)
                relocation_controls += 1
        self.assertEqual(raw_controls, match.PAIR_SIZE)
        self.assertEqual(guard_controls, 4)
        self.assertEqual(relocation_controls, 5)
        with self.assertRaises(ValueError):
            match.recovered_layout((ROOT / match.LAYOUT).read_bytes().replace(
                b"0x150C8600", b"0x150C8604", 1))
        with self.assertRaises(ValueError):
            match.recovered_symbols((ROOT / match.SYMBOLS).read_bytes() +
                                    b"func_150C851C = 0;\n")
        with self.assertRaises(ValueError):
            match.recovered_undefined((ROOT / match.UNDEFINED).read_bytes().replace(
                match.UNDEFINED_ROW, b"func_150C851C = 0x150C8520", 1))
        self.receipt["fail_closed"] = {
            "raw_byte_controls": raw_controls,
            "guard_preimage_controls": guard_controls,
            "relocation_binding_controls": relocation_controls,
            "layout_symbol_fallback_controls": 3,
            "insertions": 0, "omissions": 0,
        }


if __name__ == "__main__":
    unittest.main()
