"""Semantics, ABI, owner and image gates for func_150B7560."""

import csv
import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_menu_dual_record_replace_match as match
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read


FIRST_GLOBAL = 0x800D9898
SECOND_GLOBAL = 0x800D98A4
STATE_GLOBAL = 0x800D9890
ASSET = 0x800918DC
RELEASE = 0x1516972C
FACTORY = 0x15169968
FIRST_RECORD = 0x220000
SECOND_RECORD = 0x230000
MUTATED_SECOND = 0x240000
CREATED = 0x250000


def fixture(first, second, phase):
    memory = {STACK + i: (i * 17 + 0xA5) & 0xFF
              for i in range(-0x200, 0x100)}
    put(memory, FIRST_GLOBAL, first)
    put(memory, SECOND_GLOBAL, second)
    memory[STATE_GLOBAL] = 0xA5
    return memory


def descriptor(memory, address):
    return {
        "asset": read(memory, address),
        "field14": read(memory, address + 0x14, 2),
        "field16": read(memory, address + 0x16, 2),
        "field18": read(memory, address + 0x18, 2),
        "field1C": read(memory, address + 0x1C),
        "field20": read(memory, address + 0x20),
        "field24": read(memory, address + 0x24, 2),
        "field26": read(memory, address + 0x26, 2),
        "field28": read(memory, address + 0x28, 2),
        "field2A": read(memory, address + 0x2A, 2),
        "field2C": read(memory, address + 0x2C, 2),
        "field2E": read(memory, address + 0x2E, 2),
        "bytes30_39": tuple(memory[address + i] for i in range(0x30, 0x3A)),
    }


EXPECTED_DESCRIPTOR = {
    "asset": ASSET,
    "field14": 0,
    "field16": 0,
    "field18": 77,
    "field1C": 0x42700000,
    "field20": 0x42700000,
    "field24": 0,
    "field26": 0,
    "field28": 4096,
    "field2A": 4096,
    "field2C": 88,
    "field2E": 88,
    "bytes30_39": (0, 15, 255, 0, 0, 255, 7, 17, 1, 0),
}


class MenuReplaceOracle(TimingOracle):
    def __init__(self, words, memory, mutate, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=())
        self.mutate = mutate
        self.descriptors = []

    def record_call(self, target):
        if target not in (RELEASE, FACTORY):
            raise AssertionError("Unexpected menu-record call %08X" % target)
        args = self.arguments(1)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))
        if target == FACTORY:
            self.descriptors.append(descriptor(self.memory, args[0]))

    def hook(self, target):
        argument = self.calls[-1][1][0]
        if target == RELEASE:
            if argument == FIRST_RECORD:
                put(self.memory, FIRST_GLOBAL, 0x260000)
                if self.mutate:
                    put(self.memory, SECOND_GLOBAL, MUTATED_SECOND)
            else:
                put(self.memory, SECOND_GLOBAL, 0x270000)
        elif target == FACTORY:
            put(self.memory, SECOND_GLOBAL, 0x280000)
            self.memory[STATE_GLOBAL] = 0xEE
            self.r[2] = CREATED
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        if target == FACTORY:
            self.r[2] = CREATED


def native_harness(body):
    return r'''typedef unsigned char u8;
typedef short s16;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
#define NULL ((void *)0)
u8 D_800D9898[4] __attribute__((aligned(4)));
u8 D_800D98A4[4] __attribute__((aligned(4)));
u8 D_800918DC[4];
u8 D_800D9890;
void func_1516972C(void *);
void *func_15169968(void *);
typedef struct {
    u8 *asset; u8 reserved04[0x10]; s16 field14; s16 field16; s16 field18;
    u8 reserved1A[2]; f32 field1C; f32 field20; s16 field24; s16 field26;
    s16 field28; s16 field2A; s16 field2C; s16 field2E; u8 field30;
    u8 field31; u8 field32; u8 field33; u8 field34; u8 field35;
    u8 field36; u8 field37; u8 field38; u8 field39; u8 reserved3A[2];
} MenuRecordDescriptorE4070;
%s
static u32 firstRecord, secondRecord, mutatedSecond, created;
static void *releaseLog[3];
static s32 releaseCalls, mutationMode, descriptorBad;
void func_1516972C(void *value) {
    releaseLog[releaseCalls++] = value;
    if (value == &firstRecord) {
        *(void **)D_800D9898 = (void *)0x260000;
        if (mutationMode) *(void **)D_800D98A4 = &mutatedSecond;
    } else {
        *(void **)D_800D98A4 = (void *)0x270000;
    }
}
void *func_15169968(void *value) {
    MenuRecordDescriptorE4070 *d = value;
    descriptorBad |= d->asset != D_800918DC;
    descriptorBad |= d->field14 != 0 || d->field16 != 0 || d->field18 != 77;
    descriptorBad |= d->field1C != 60.0f || d->field20 != 60.0f;
    descriptorBad |= d->field24 != 0 || d->field26 != 0;
    descriptorBad |= d->field28 != 4096 || d->field2A != 4096;
    descriptorBad |= d->field2C != 88 || d->field2E != 88;
    descriptorBad |= d->field30 != 0 || d->field31 != 15;
    descriptorBad |= d->field32 != 255 || d->field33 != 0;
    descriptorBad |= d->field34 != 0 || d->field35 != 255;
    descriptorBad |= d->field36 != 7 || d->field37 != 17;
    descriptorBad |= d->field38 != 1 || d->field39 != 0;
    *(void **)D_800D98A4 = (void *)0x280000;
    D_800D9890 = 0xEE;
    return &created;
}
static int one(s32 first, s32 second, s32 mutate) {
    void *wantedSecond;
    s32 wantedCalls = 0;
    *(void **)D_800D9898 = first ? &firstRecord : NULL;
    *(void **)D_800D98A4 = second ? &secondRecord : NULL;
    D_800D9890 = 0xA5;
    releaseCalls = descriptorBad = 0;
    mutationMode = mutate;
    wantedSecond = second ? &secondRecord : NULL;
    if (first) {
        releaseLog[wantedCalls++] = NULL;
        if (mutate) wantedSecond = &mutatedSecond;
    }
    if (wantedSecond) releaseLog[wantedCalls++] = NULL;
    func_150B7560();
    if (descriptorBad || releaseCalls != wantedCalls) return 10;
    if (first && releaseLog[0] != &firstRecord) return 11;
    if (wantedSecond && releaseLog[wantedCalls - 1] != wantedSecond) return 12;
    if (*(void **)D_800D9898 != NULL) return 13;
    if (*(void **)D_800D98A4 != &created) return 14;
    if (D_800D9890 != 3) return 15;
    return 0;
}
static int run(void) {
    s32 a, b, c;
    for (a = 0; a < 2; a++) for (b = 0; b < 2; b++)
        for (c = 0; c < 2; c++) {
            int status = one(a, b, c);
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


class MenuDualRecordReplaceMatchTests(unittest.TestCase):
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

    def test_01_direct_C_owner_image_and_protected_data(self):
        self.assertEqual((self.report["words"], self.report["slot_words"],
                          self.report["frame"],
                          self.report["natural_positional_differences"],
                          self.report["guards"], self.report["relocations"]),
                         (63, 63, 88, 0, 0, 15))
        self.assertEqual(self.report["neighbors"], 20)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))
        self.assertEqual(self.qualified_elf.read_bytes(), match.expected_image(
            self.predecessor_elf.read_bytes(), match.retail_bytes(self.root)))

    def test_02_guest_release_mutations_descriptor_and_all_words(self):
        visits, cases = set(), 0
        for first, second, mutate, phase in itertools.product(
                (0, FIRST_RECORD), (0, SECOND_RECORD), (0, 1), (0, 8)):
            model = MenuReplaceOracle(
                self.words, fixture(first, second, phase), mutate, phase).run()
            wanted = []
            effective_second = second
            if first:
                wanted.append((RELEASE, (FIRST_RECORD,)))
                if mutate:
                    effective_second = MUTATED_SECOND
            if effective_second:
                wanted.append((RELEASE, (effective_second,)))
            descriptor_address = model.calls[-1][1][0]
            wanted.append((FACTORY, (descriptor_address,)))
            self.assertEqual(model.calls, wanted)
            self.assertEqual(model.descriptors, [EXPECTED_DESCRIPTOR])
            self.assertEqual(read(model.memory, FIRST_GLOBAL), 0)
            self.assertEqual(read(model.memory, SECOND_GLOBAL), CREATED)
            self.assertEqual(model.memory[STATE_GLOBAL], 3)
            self.assertEqual(model.r[29], STACK + phase)
            visits.update(model.visits); cases += 1
        self.assertEqual(visits, set(range(match.ENTRY,
                                           match.ENTRY + match.SIZE, 4)))
        self.assertEqual(cases, 16)

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
            "first-clear": body.replace(
                "        *(void **)D_800D9898 = NULL;", "        (void)0;"),
            "field18": body.replace("field18 = 77", "field18 = 76"),
            "field31": body.replace("field31 = 15", "field31 = 14"),
            "asset": body.replace("descriptor.asset = D_800918DC",
                                   "descriptor.asset = D_800D9898"),
            "field35": body.replace("field35 = 255", "field35 = 0"),
            "field37": body.replace("field37 = 17", "field37 = 18"),
            "field28": body.replace("field28 = 4096", "field28 = 4095"),
            "float": body.replace("field1C = 60.0f", "field1C = 61.0f"),
            "second-release": body.replace(
                "        func_1516972C(*(void **)D_800D98A4);", "        (void)0;"),
            "state": body.replace("D_800D9890 = 3", "D_800D9890 = 2"),
        }
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0,
                                name)

    def test_04_source_control_registry_and_live_state(self):
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
        with (self.root / match.GUARDS).open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertFalse([row for row in rows if row["filename"] == match.FILENAME
                          and row["function"] == match.FUNCTION])
        wrong = qualified.replace("D_800D9890 = 3", "D_800D9890 = 2")
        obj, _ = match.compile_owner(self.root, self.output, wrong,
                                     "wrong-final-state")
        with self.assertRaises(ValueError):
            match.checked_candidate(obj)

    def test_05_caller_frame_and_reference_registry(self):
        rom = (self.root / match.ROM_IMAGE).read_bytes()
        jal = 0x0C000000 | (match.ENTRY >> 2 & 0x03FFFFFF)
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == jal],
                         [0xE40E8])
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == match.ENTRY],
                         [])
        self.assertEqual(tuple(self.words[:4]),
                         (0x27BDFFA8, 0xAFBF0014, 0x3C04800E, 0x8C849898))
        self.assertEqual(tuple(self.words[-4:]),
                         (0x8FBF0014, 0x27BD0058, 0x03E00008, 0))


if __name__ == "__main__":
    unittest.main()
