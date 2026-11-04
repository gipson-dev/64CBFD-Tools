"""Closure, semantic, guard and strict-image gates for func_1509C120."""

import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_random_state_block_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests import game_random_state_block_oracle as oracle
from tools.tests.game_view_render_pass_oracle import STACK


ROOT = Path(__file__).resolve().parents[2]


NATIVE_PREFIX = r'''typedef unsigned char u8;
typedef signed int s32;
typedef unsigned int u32;
#define NULL ((void *)0)

typedef struct struct102 {
    u8 bytes[0x1B];
} struct102;

struct102 *D_800D2E4C;
s32 func_150ADA20(void);
s32 allocate_memory(s32 size, s32 color, s32 side, s32 flags);
void func_10004074(void *block);
void bcopy(const void *source, void *destination, int length);
'''


NATIVE_SUFFIX = r'''
enum { EVENT_RANDOM = 1, EVENT_ALLOCATE = 2, EVENT_RELEASE = 3,
       EVENT_BCOPY = 4 };

typedef struct Event {
    s32 kind;
    u32 a0;
    u32 a1;
    u32 a2;
    u32 a3;
} Event;

static struct102 oldBlock;
static struct102 allocations[5];
static struct102 allocationBefore[5];
static u32 randomValues[2];
static Event events[20];
static s32 eventCount;
static s32 randomCalls;
static s32 allocationCalls;

static u32 address(const void *pointer) {
    return (u32)(unsigned long)pointer;
}

static void event(s32 kind, u32 a0, u32 a1, u32 a2, u32 a3) {
    Event *row = &events[eventCount++];
    row->kind = kind;
    row->a0 = a0;
    row->a1 = a1;
    row->a2 = a2;
    row->a3 = a3;
}

s32 func_150ADA20(void) {
    s32 ordinal = randomCalls++;
    event(EVENT_RANDOM, 0, 0, 0, 0);
    return (s32)randomValues[ordinal];
}

s32 allocate_memory(s32 size, s32 color, s32 side, s32 flags) {
    struct102 *result = &allocations[allocationCalls++];
    event(EVENT_ALLOCATE, (u32)size, (u32)color, (u32)side, (u32)flags);
    return (s32)address(result);
}

void func_10004074(void *block) {
    event(EVENT_RELEASE, address(block), 0, 0, 0);
}

void bcopy(const void *source, void *destination, int length) {
    const u8 *input = (const u8 *)source;
    u8 *output = (u8 *)destination;
    int index;
    event(EVENT_BCOPY, address(source), address(destination), (u32)length, 0);
    for (index = 0; index < length; index++)
        output[index] = input[index];
}

static int same_event(s32 ordinal, s32 kind, u32 a0, u32 a1,
                      u32 a2, u32 a3) {
    Event *row = &events[ordinal];
    return row->kind == kind && row->a0 == a0 && row->a1 == a1 &&
           row->a2 == a2 && row->a3 == a3;
}

static int one(s32 choice, s32 oldPresent, s32 gate, s32 pattern) {
    s32 index, byte, expectedEvents, proceed;
    struct102 *selected;

    for (byte = 0; byte < 0x1B; byte++) {
        oldBlock.bytes[byte] = (u8)(byte * 13 + pattern * 29 + 0x5A);
        for (index = 0; index < 5; index++) {
            allocations[index].bytes[byte] =
                (u8)(byte * 19 + index * 37 + pattern * 11 + 0x63);
            allocationBefore[index].bytes[byte] = allocations[index].bytes[byte];
        }
    }
    randomValues[0] = ((u32)pattern * 0x125A5A5U & ~3U) | (u32)choice;
    randomValues[1] = ((u32)pattern * 0x243137U & ~4U) | (u32)gate;
    D_800D2E4C = oldPresent ? &oldBlock : (struct102 *)0;
    eventCount = 0;
    randomCalls = 0;
    allocationCalls = 0;

    func_1509C120();
    proceed = !oldPresent || gate == 4;
    if (randomCalls != 1 + oldPresent)
        return 1;
    if (allocationCalls != (proceed ? choice + 1 : 0))
        return 2;
    if (!same_event(0, EVENT_RANDOM, 0, 0, 0, 0))
        return 3;
    expectedEvents = 1;
    if (oldPresent) {
        if (!same_event(expectedEvents, EVENT_RANDOM, 0, 0, 0, 0))
            return 4;
        expectedEvents++;
    }
    if (!proceed) {
        if (eventCount != expectedEvents || D_800D2E4C != &oldBlock)
            return 5;
        return 0;
    }
    for (index = 0; index <= choice; index++) {
        if (!same_event(expectedEvents, EVENT_ALLOCATE, 0x1B, 0xFF, 2, 0))
            return 6;
        expectedEvents++;
    }
    for (index = 0; index < choice; index++) {
        if (!same_event(expectedEvents, EVENT_RELEASE,
                        address(&allocations[index]), 0, 0, 0))
            return 7;
        expectedEvents++;
    }
    selected = &allocations[choice];
    if (D_800D2E4C != selected)
        return 8;
    if (oldPresent) {
        if (!same_event(expectedEvents, EVENT_BCOPY, address(&oldBlock),
                        address(selected), 0x1B, 0))
            return 9;
        expectedEvents++;
        if (!same_event(expectedEvents, EVENT_RELEASE,
                        address(&oldBlock), 0, 0, 0))
            return 10;
        expectedEvents++;
    }
    if (eventCount != expectedEvents)
        return 11;
    for (index = 0; index < 5; index++)
        for (byte = 0; byte < 0x1B; byte++) {
            u8 expected = allocationBefore[index].bytes[byte];
            if (oldPresent && index == choice)
                expected = oldBlock.bytes[byte];
            if (allocations[index].bytes[byte] != expected)
                return 12;
        }
    return 0;
}

static int run(void) {
    s32 choice, oldPresent, gate, pattern;
    if (sizeof(void *) != 4 || sizeof(struct102) != 0x1B)
        return 20;
    for (choice = 0; choice < 4; choice++)
        for (oldPresent = 0; oldPresent < 2; oldPresent++)
            for (gate = 0; gate <= 4; gate += 4)
                for (pattern = 0; pattern < 8; pattern++) {
                    int status = one(choice, oldPresent, gate, pattern);
                    if (status)
                        return 32 + status;
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


class RandomStateBlockMatchTests(unittest.TestCase):
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

    def test_01_owner_image_callers_ABI_and_protected_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_frame"], report["retail_frame"],
             report["natural_positional_differences"], report["guards"],
             report["relocations"], report["retail_relocations"]),
            (66, 0x50, 0x50, 7, 7, 12, 12))
        self.assertEqual(report["neighbors"], 16)
        self.assertEqual(report["functions"], 6051)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"], {
            "direct_jal_calls": ["0x34dec", "0x44c48", "0xc897c"],
            "direct_jumps": [],
            "aligned_pointer_literals": [],
            "callers": ["func_15007830", "func_15017790", "func_1509B4A0"],
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
        image = (ROOT / match.ROM_IMAGE).read_bytes()
        jal = 0x0C000000 | ((match.ENTRY >> 2) & 0x03FFFFFF)
        self.assertEqual(
            [offset for offset in (0x34DEC, 0x44C48, 0xC897C)
             if struct.unpack_from(">I", image, offset)[0] == jal],
            [0x34DEC, 0x44C48, 0xC897C])
        self.receipt["closure"] = {
            "words": 66, "guards": 7, "natural_relocations": 12,
            "retail_relocations": 12, "neighbors": 16,
            "functions": 6051, "changed_only_target": True,
            "strict_exclusions": 0, "protected_game_bytes": 189088,
            "protected_data_exact": True, "direct_callers": 3,
            "arguments": 0, "return_type": "void",
        }

    def test_02_guest_all_choices_gates_copy_release_order_and_all_words(self):
        visits = set()
        cases = 0
        for choice, old_present, gate, pattern, phase in itertools.product(
                range(4), (False, True), (0, 4), range(4), (0, 8)):
            case = oracle.Case(choice, old_present, gate, pattern, phase)
            initial = oracle.fixture(case)
            expected_memory, expected_calls = oracle.reference(initial, case)
            model = oracle.RandomStateBlockOracle(
                self.words, initial, case).run()
            self.assertEqual(model.calls, expected_calls, case)
            self.assertEqual(oracle.public(model.memory),
                             oracle.public(expected_memory), case)
            self.assertEqual(model.r[29], STACK + phase, case)
            visits.update(model.visits)
            cases += 1
        self.assertEqual(
            visits, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.receipt["guest"] = {
            "cases": cases, "stack_phases": [0, 8],
            "retail_words_reached": 66, "all_words_reached": True,
            "allocation_choices": [0, 1, 2, 3],
            "old_block_states": ["null", "present"],
            "random_gate_states": ["reject", "replace"],
            "allocator_arguments_checked": True,
            "decoy_release_order_checked": True,
            "copy_then_old_release_checked": True,
            "helper_call_clobbering": True,
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
            profiles[optimization] = {"cases": 128, "exit": 0, "UBSan": True}
        controls = {
            "wrong-choice-mask": body.replace("& 3", "& 2", 1),
            "wrong-random-gate": body.replace("& 4", "& 8", 1),
            "wrong-allocation-size": body.replace("0x1B, 0xFF", "0x1A, 0xFF", 1),
            "extra-allocation": body.replace("i <= index", "i <= index + 1", 1),
            "release-selected": body.replace("i != index", "i == index", 1),
            "keep-first-block": body.replace("blocks[index]", "blocks[0]", 1),
            "short-copy": body.replace("D_800D2E4C, 0x1B", "D_800D2E4C, 0x1A", 1),
            "reverse-copy": body.replace(
                "bcopy(old, D_800D2E4C, 0x1B);",
                "bcopy(D_800D2E4C, old, 0x1B);"),
            "skip-old-release": body.replace(
                "            func_10004074(old);",
                "            /* old block release skipped */"),
            "skip-decoy-release": body.replace(
                "                func_10004074((void *)blocks[i]);",
                "                /* decoy release skipped */"),
            "null-only-replacement": body.replace(
                "if ((old == NULL) || ((func_150ADA20() & 4) != 0))",
                "if (old == NULL)"),
        }
        rejected = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body, name)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0, name)
            rejected[name] = "independent state-block corpus mismatch"
        self.receipt["native"] = {"profiles": profiles, "controls": rejected}

    def test_04_raw_bytes_relocations_and_guard_rows_fail_closed(self):
        self.assertEqual(len(self.raw), match.SIZE)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), match.RAW_SHA256)
        self.assertEqual(self.bindings, match.BINDINGS)
        raw_controls = 0
        for index in range(len(self.raw)):
            changed = bytearray(self.raw)
            changed[index] ^= 1
            self.assertNotEqual(hashlib.sha256(changed).hexdigest(),
                                match.RAW_SHA256)
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

        rows = [dict(row) for row in self.values["qualified_rows"]]
        relocation_index = next(
            index for index in target_indices
            if int(rows[index]["offset"], 0) == 0x0CC)
        rows[relocation_index]["expected_relocations"] = \
            "R_MIPS_LO16:D_80123450"
        path = self.output / "bad-relocation.csv"
        harness.write_patches(path, self.values["fields"], rows)
        with self.assertRaises(ValueError):
            match.emit_owner(
                self.values["qualified_compact"], ROOT / match.ASM,
                word_patches_path=path, filename=match.FILENAME)

        self.assertEqual(raw_controls, 264)
        self.assertEqual(guard_controls, 7)
        self.receipt["fail_closed"] = {
            "raw_byte_controls": raw_controls,
            "guard_preimage_controls": guard_controls,
            "relocation_binding_controls": 1,
            "insertions": 0, "omissions": 0,
        }


if __name__ == "__main__":
    unittest.main()
