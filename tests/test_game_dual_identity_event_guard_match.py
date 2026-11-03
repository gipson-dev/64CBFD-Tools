"""Guarded C, semantics, ABI, registry, owner and image gates for func_151B5A9C."""

import csv
import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_dual_identity_event_guard_match as match
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read


OWNER, EVENT = 0x220000, 0x230000
STATE = OWNER + 0x5A8
RELEASE = 0x1516972C


def fixture(event_key0, event_key1, event_tag0, event_tag1,
            owner_tag0, owner_tag1, alias, phase):
    memory = {STACK + i: (i * 17 + 0xA5) & 0xFF
              for i in range(-0x100, 0x100)}
    memory.update({OWNER + i: (i * 13 + 0x59) & 0xFF for i in range(0x5C0)})
    memory.update({EVENT + i: (i * 29 + 0x71) & 0xFF for i in range(0x20)})
    put(memory, STATE, 0x11223344)
    memory[STATE + 4] = owner_tag0
    put(memory, STATE + 8, 0x55667788)
    memory[STATE + 12] = owner_tag1
    event = STATE if alias else EVENT
    if not alias:
        put(memory, event, event_key0)
        put(memory, event + 4, event_key1)
        memory[event + 8] = event_tag0
        memory[event + 9] = event_tag1
    return memory, event


def external(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x100 <= address < STACK + 0x100}


def reference(initial, event, raw_command):
    memory, calls = dict(initial), []
    command = raw_command & 0xFF
    if command == 0x2D:
        current = read(memory, STATE)
        key = read(memory, event)
        if key == current:
            put(memory, STATE, read(memory, event + 4))
            memory[STATE + 4] = memory[event + 9]
        else:
            other = read(memory, event + 4)
            if other == current:
                put(memory, STATE, key)
                memory[STATE + 4] = memory[event + 8]
        other = read(memory, event + 4)
        key = read(memory, event)
        current = read(memory, STATE + 8)
        if key == current:
            put(memory, STATE + 8, other)
            memory[STATE + 12] = memory[event + 9]
        elif other == current:
            put(memory, STATE + 8, key)
            memory[STATE + 12] = memory[event + 8]
    elif command == 0:
        key = read(memory, event)
        tag = memory[event + 4]
        if (key == read(memory, STATE) or key == read(memory, STATE + 8) or
                tag == memory[STATE + 4] or tag == memory[STATE + 12]):
            calls.append((RELEASE, (OWNER,)))
    return memory, calls


class IdentityOracle(TimingOracle):
    def __init__(self, words, memory, event, command, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(OWNER, event, command))

    def record_call(self, target):
        if target != RELEASE:
            raise AssertionError("Unexpected dual-identity call %08X" % target)
        args = self.arguments(1)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target != RELEASE:
            raise AssertionError("Unexpected dual-identity hook %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]


def native_harness(body):
    return """typedef unsigned char u8;
typedef unsigned int u32;
typedef int s32;
typedef struct {
    u8 pad0[0x580];
    s32 key0;
    u8 tag0;
    u8 pad585[3];
    s32 key1;
    u8 tag1;
} DualIdentityState151B5A9C;
typedef struct {
    u8 pad0[0x28];
    DualIdentityState151B5A9C identity;
} DualIdentityOwner151B5A9C;
typedef struct {
    s32 key0;
    s32 key1;
    u8 tag0;
    u8 tag1;
} DualIdentityEvent151B5A9C;
void func_1516972C(DualIdentityOwner151B5A9C *);
%s
static DualIdentityOwner151B5A9C owner;
static DualIdentityEvent151B5A9C event;
static s32 releases, badOwner;
void func_1516972C(DualIdentityOwner151B5A9C *value) {
    releases++;
    if (value != &owner) badOwner = 1;
}
static int one(s32 command, s32 owner0, s32 owner1,
               s32 event0, s32 event1, s32 tags) {
    s32 wanted0 = owner0, wanted1 = owner1, wantedRelease = 0;
    u8 ownerTag0 = tags, ownerTag1 = tags >> 8;
    u8 eventTag0 = tags >> 16, eventTag1 = tags >> 24;
    u8 wantedTag0 = ownerTag0, wantedTag1 = ownerTag1;
    u8 eventByte4 = (u8)event1;
    owner.identity.key0 = owner0;
    owner.identity.tag0 = ownerTag0;
    owner.identity.key1 = owner1;
    owner.identity.tag1 = ownerTag1;
    event.key0 = event0;
    event.key1 = event1;
    event.tag0 = eventTag0;
    event.tag1 = eventTag1;
    if ((u8)command == 0x2D) {
        if (event0 == wanted0) { wanted0 = event1; wantedTag0 = eventTag1; }
        else if (event1 == wanted0) { wanted0 = event0; wantedTag0 = eventTag0; }
        if (event0 == wanted1) { wanted1 = event1; wantedTag1 = eventTag1; }
        else if (event1 == wanted1) { wanted1 = event0; wantedTag1 = eventTag0; }
    } else if ((u8)command == 0 &&
               (event0 == owner0 || event0 == owner1 ||
                eventByte4 == ownerTag0 || eventByte4 == ownerTag1)) {
        wantedRelease = 1;
    }
    releases = badOwner = 0;
    func_151B5A9C(&owner, &event, (u8)command);
    if (badOwner || releases != wantedRelease) return 10;
    if (owner.identity.key0 != wanted0 || owner.identity.key1 != wanted1)
        return 11;
    if (owner.identity.tag0 != wantedTag0) return 12;
    if (owner.identity.tag1 != wantedTag1) return 13;
    return 0;
}
static int run(void) {
    static const s32 values[] = {0x11223344, 0x55667788, 0xAA000001};
    static const s32 commands[] = {0, 1, 0x2D, 0x12D};
    s32 c, a, b, d, e;
    for (c = 0; c < 4; c++)
        for (a = 0; a < 3; a++)
            for (b = 0; b < 3; b++)
                for (d = 0; d < 3; d++)
                    for (e = 0; e < 3; e++)
                        if (one(commands[c], values[a], values[b],
                                values[d], values[e], 0x2211BBAA))
                            return one(commands[c], values[a], values[b],
                                       values[d], values[e], 0x2211BBAA);
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
""" % body


class DualIdentityEventGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / match.BUILD
        (cls.report, cls.predecessor_owner, cls.qualified_owner,
         cls.predecessor_elf, cls.qualified_elf) = match.prepare(
             cls.root, cls.output)
        rom = (cls.root / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(">%dI" % match.WORDS, rom, match.ROM))

    def test_01_guarded_C_owner_image_and_protected_data(self):
        self.assertEqual((self.report["natural_words"], self.report["words"],
                          self.report["slot_words"], self.report["frame"],
                          self.report["guards"], self.report["insertions"],
                          self.report["relocations"]),
                         (63, 64, 65, 24, 5, 1, 1))
        self.assertEqual(self.report["neighbors"], 2)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))
        self.assertEqual(self.qualified_elf.read_bytes(), match.expected_image(
            self.predecessor_elf.read_bytes(), match.retail_bytes(self.root)))

    def test_02_guest_replacements_release_aliases_and_all_words(self):
        visits, cases = set(), 0
        event0s = (0x11223344, 0x55667788, 0x99AABBCC)
        event1s = (0x11223344, 0x55667788, 0xAA000001, 0x99AABBCC)
        for event0, event1, event_tag0, event_tag1, owner_tag0, owner_tag1, command, alias, phase in itertools.product(
                event0s, event1s, (0x11, 0xEE), (0x22, 0xDD),
                (0xAA, 0x10), (0xBB, 0x20),
                (0, 1, 0x2D, 0x12D, 0x100), (0, 1), (0, 8)):
            initial, event = fixture(
                event0, event1, event_tag0, event_tag1,
                owner_tag0, owner_tag1, alias, phase)
            wanted, calls = reference(initial, event, command)
            model = IdentityOracle(
                self.words, initial, event, command, phase).run()
            self.assertEqual(external(model.memory), external(wanted))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[29], STACK + phase)
            visits.update(model.visits)
            cases += 1
        # The duplicate event-key reload at +0x50 is skipped by both
        # branch-likely paths.
        self.assertEqual(
            set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - visits,
            {match.ENTRY + 0x50})
        self.assertEqual(cases, 3840)

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
            "wrong-command": body.replace("command == 0x2D", "command == 0x2C"),
            "wrong-first-key": body.replace("state->key0 = event->key1;", "state->key0 = event->key0;", 1),
            "wrong-first-tag": body.replace("state->tag0 = event->tag1;", "state->tag0 = event->tag0;", 1),
            "wrong-second-key": body.replace("state->key1 = event->key1;", "state->key1 = event->key0;", 1),
            "wrong-zero": body.replace("command == 0", "command != 0"),
            "no-second-release-key": body.replace("state->key1 == key ||", "0 ||"),
            "wrong-first-tag-release": body.replace("[4] == state->tag0", "[4] != state->tag0"),
            "no-release": body.replace("func_1516972C(owner);", "(void)owner;"),
        }
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0, name)

    def test_04_guards_fail_closed_registry_and_live_state(self):
        with (self.output / "proposed-guards.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        target = [row for row in rows if row["filename"] == match.FILENAME and
                  row["function"] == match.FUNCTION]
        self.assertEqual(len(target), 5)
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
        jal = 0x0C000000 | (match.ENTRY >> 2 & 0x03FFFFFF)
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == jal], [])
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == match.ENTRY],
                         [0x22F3EC])
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
