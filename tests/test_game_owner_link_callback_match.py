"""Semantic, ABI, owner and image gates for func_1519E1F4."""

import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_owner_link_callback_match as match
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put


ROOT = Path(__file__).resolve().parents[2]
RECORD, LINK, EVENT = 0x80300000, 0x80400000, 0x80500000
BEFORE, AFTER, OTHER = 0x81601020, 0x82702030, 0x83803040
RELEASE = 0x1519CFA0


def get(memory, address, size):
    value = 0
    for offset in range(size):
        value = value << 8 | memory.get(address + offset, 0)
    return value


def fixture(relation, identity_match, category_match, phase):
    memory = {STACK + offset: (offset * 19 + 0xB7) & 0xFF
              for offset in range(-0x100, 0x100)}
    current = (BEFORE, AFTER, OTHER)[relation]
    put(memory, RECORD + 0x98, LINK, 4)
    put(memory, LINK, current, 4)
    put(memory, EVENT, BEFORE, 4)
    put(memory, EVENT + 4, AFTER, 4)
    memory[EVENT + 8] = 0xA1
    memory[EVENT + 9] = 0xB2
    memory[LINK + 4] = memory[EVENT + 4] if identity_match else (
        memory[EVENT + 4] ^ 0x7F)
    memory[LINK + 0x4C] = memory[EVENT] if category_match else (
        memory[EVENT] ^ 0x7F)
    return memory


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x100 <= address < STACK + 0x100}


def reference(initial, command, relation, identity_match, category_match):
    memory, calls = dict(initial), []
    if command in (0, 7):
        if relation == 0 or identity_match:
            calls.append((RELEASE, (RECORD,)))
    elif command == 6:
        if category_match:
            calls.append((RELEASE, (RECORD,)))
    elif command == 0x2D:
        if relation == 0:
            put(memory, LINK, AFTER, 4)
            memory[LINK + 4] = memory[EVENT + 9]
        elif relation == 1:
            put(memory, LINK, BEFORE, 4)
            memory[LINK + 4] = memory[EVENT + 8]
    return memory, calls


class OwnerLinkOracle(TimingOracle):
    def __init__(self, words, memory, command, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(RECORD, EVENT, command))

    def record_call(self, target):
        if target != RELEASE:
            raise AssertionError("Unexpected owner-link callback %08X" % target)
        args = self.arguments(1)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target != RELEASE:
            raise AssertionError("Unexpected owner-link hook %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xC7000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xC5000000 + register
        self.f[:20] = [0xC6000000 + index for index in range(20)]


def native_harness(body):
    return """typedef unsigned char u8;
typedef signed char s8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int s32;
void func_1519CFA0(u8 *);
%s
static u8 record[0xA0] __attribute__((aligned(4)));
static u8 linkBytes[0x50] __attribute__((aligned(4)));
static u8 eventBytes[12] __attribute__((aligned(4)));
static u8 beforeObject[4], afterObject[4], otherObject[4];
static u8 *wantedRecord;
static s32 releaseCount, badArgument;
void func_1519CFA0(u8 *value) {
    releaseCount++;
    if (value != wantedRecord) badArgument = 1;
}
static void clear(u8 *data, s32 size) {
    s32 index;
    for (index = 0; index < size; index++) data[index] = 0;
}
static int one(s32 command, s32 relation, s32 identityMatch,
               s32 categoryMatch) {
    u8 *current = relation == 0 ? beforeObject :
        (relation == 1 ? afterObject : otherObject);
    u8 expectedIdentity;
    s32 expectedRelease = 0;
    clear(record, sizeof(record));
    clear(linkBytes, sizeof(linkBytes));
    clear(eventBytes, sizeof(eventBytes));
    *(u8 **)(void *)(record + 0x98) = linkBytes;
    *(u8 **)(void *)linkBytes = current;
    *(u8 **)(void *)eventBytes = beforeObject;
    *(u8 **)(void *)(eventBytes + 4) = afterObject;
    eventBytes[8] = 0xA1;
    eventBytes[9] = 0xB2;
    linkBytes[4] = identityMatch ? eventBytes[4] : (eventBytes[4] ^ 0x7F);
    linkBytes[0x4C] = categoryMatch ? eventBytes[0] : (eventBytes[0] ^ 0x7F);
    expectedIdentity = linkBytes[4];
    if (command == 0 || command == 7)
        expectedRelease = relation == 0 || identityMatch;
    else if (command == 6) expectedRelease = categoryMatch;
    else if (command == 0x2D) {
        if (relation == 0) {
            current = afterObject;
            expectedIdentity = eventBytes[9];
        } else if (relation == 1) {
            current = beforeObject;
            expectedIdentity = eventBytes[8];
        }
    }
    wantedRecord = record;
    releaseCount = badArgument = 0;
    func_1519E1F4(record, (s32)eventBytes, (u8)command);
    if (badArgument || releaseCount != expectedRelease) return 10;
    if (*(u8 **)(void *)linkBytes != current) return 11;
    if (linkBytes[4] != expectedIdentity) return 12;
    return 0;
}
static int run(void) {
    static const s32 commands[] = {0, 1, 5, 6, 7, 8, 0x2D, 0xFF};
    s32 command, relation, identity, category;
    for (command = 0; command < 8; command++)
        for (relation = 0; relation < 3; relation++)
            for (identity = 0; identity < 2; identity++)
                for (category = 0; category < 2; category++)
                    if (one(commands[command], relation, identity, category))
                        return 20;
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
""" % body


class OwnerLinkCallbackMatchTests(unittest.TestCase):
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

    def test_01_direct_slot_owner_image_registry_and_protected_data(self):
        report = self.report
        self.assertEqual(
            (report["words"], report["natural_frame"], report["retail_frame"],
             report["natural_positional_differences"], report["guards"],
             report["relocations"]),
            (68, 0x18, 0x18, 0, 0, 3))
        self.assertEqual(report["neighbors"], 22)
        self.assertEqual(report["functions"], 6051)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertEqual(report["registry"], {
            "direct_jal_calls": [],
            "aligned_pointer_literals": ["0x22ee60"],
            "registry": "D_8008A390[4] via func_15147D1C",
            "abi": "record pointer, event address, promoted unsigned command; void return",
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
            "words": 68, "guards": 0, "relocations": 3,
            "neighbors": 22, "functions": 6051,
            "changed_only_target": True, "strict_exclusions": 0,
            "protected_game_bytes": 189088, "protected_data_exact": True,
        }

    def test_02_guest_routes_stack_phases_and_all_words(self):
        visits, cases = set(), 0
        commands = (0, 1, 5, 6, 7, 8, 0x2D, 0xFF)
        for command, relation, identity, category, phase in itertools.product(
                commands, range(3), range(2), range(2), (0, 8)):
            initial = fixture(relation, identity, category, phase)
            wanted, calls = reference(
                initial, command, relation, identity, category)
            model = OwnerLinkOracle(
                self.words, initial, command, phase).run()
            self.assertEqual(public(model.memory), public(wanted))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[29], STACK + phase)
            visits.update(model.visits)
            cases += 1
        unreachable = {match.ENTRY + offset for offset in (0x7C, 0xB8, 0xE8)}
        self.assertEqual(
            visits,
            set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - unreachable)
        self.assertEqual(cases, 192)
        self.receipt["guest"] = {
            "cases": cases, "stack_phases": [0, 8],
            "reachable_words_covered": 65,
            "unreachable_branch_likely_shadows": ["0x7c", "0xb8", "0xe8"],
            "commands": list(commands), "relations": 3,
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
            profiles[optimization] = {"cases": 96, "exit": 0, "UBSan": True}
        controls = {
            "command-zero": body.replace("command == 0", "command == 1", 1),
            "command-six": body.replace("command == 6", "command == 5", 1),
            "category": body.replace("link[0x4C]", "link[0x4B]"),
            "command-seven": body.replace("command == 7", "command == 8", 1),
            "command-retarget": body.replace("command == 0x2D", "command == 0x2C"),
            "identity": body.replace("link[4] == event[4]", "link[5] == event[4]"),
            "release-argument": body.replace("func_1519CFA0(record);",
                                              "func_1519CFA0(event);"),
            "after-owner": body.replace("*(u8 **)(event + 4);",
                                         "*(u8 **)event;", 1),
            "after-identity": body.replace("link[4] = event[9];",
                                            "link[4] = event[8];"),
            "before-identity": body.replace("link[4] = event[8];",
                                             "link[4] = event[9];"),
        }
        rejected = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0, name)
            rejected[name] = "output mismatch"
        self.receipt["native"] = {"profiles": profiles, "controls": rejected}

    def test_04_raw_bytes_and_relocation_bindings_fail_closed(self):
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
            changed[offset] = [("R_MIPS_26", "func_1519E304")]
            self.assertNotEqual(changed, match.BINDINGS)
            binding_controls += 1
        self.assertEqual((raw_controls, binding_controls), (272, 3))
        self.receipt["fail_closed"] = {
            "raw_byte_controls": raw_controls,
            "relocation_binding_controls": binding_controls,
        }


if __name__ == "__main__":
    unittest.main()
