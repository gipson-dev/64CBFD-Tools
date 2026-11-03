"""Guarded C, semantics, ABI, registry, owner and image gates for func_151CD3CC."""

from dataclasses import dataclass
import csv
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_event_link_dispatch_match as match
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
OWNER, EVENT = 0x220000, 0x230000
SOURCE_A, SOURCE_B, EFFECT, NEW_EFFECT = 0x240000, 0x250000, 0x260000, 0x270000
FACTORY, RETIRE = 0x151CD4C0, 0x151CE47C
LINK = OWNER + 0x28


@dataclass(frozen=True)
class Case:
    command: int
    match: bool
    active: bool
    mutate: bool
    alias: bool
    phase: int
    seed: int


def fixture(case):
    memory = {STACK + case.phase + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x180, 0x100)}
    for base, length in ((OWNER, 0x60), (EVENT, 0x10),
                         (SOURCE_A, 0x40), (SOURCE_B, 0x40), (EFFECT, 0x40)):
        memory.update({base + index: (index * 29 + case.seed + 0x59) & 0xFF
                       for index in range(length)})
    memory[OWNER + 1] = (0x31 + case.seed) & 0xFF
    memory[OWNER + 0xC] = (0x71 + case.seed) & 0xFF
    identity = 0x11223344 ^ (case.seed * 0x10101)
    put(memory, LINK, SOURCE_A)
    put(memory, LINK + 4, identity)
    put(memory, LINK + 8, EFFECT if case.active else 0)
    memory[LINK + 0xC] = (0x91 + case.seed) & 0xFF
    pointer = LINK + 4 if case.alias else EVENT
    if not case.alias:
        put(memory, pointer, identity if case.match else identity ^ 0x01000000)
    elif not case.match:
        raise ValueError("Aliased identity is necessarily matching")
    return memory, pointer


def external(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x180 <= address < STACK + 0x100}


def reference(initial, pointer, case):
    memory, calls = dict(initial), []
    command = case.command & 0xFF
    matching = read(memory, LINK + 4) == read(memory, pointer)
    effect = read(memory, LINK + 8)
    if command == 0x17 and matching and effect == 0:
        calls.append((FACTORY, (read(memory, LINK), memory[LINK + 0xC],
                                read(memory, LINK + 4), memory[OWNER + 0xC],
                                memory[OWNER + 1])))
        if case.mutate:
            put(memory, LINK, SOURCE_B)
        put(memory, LINK + 8, NEW_EFFECT)
        memory[read(memory, LINK) + 0x14] = 0
    elif command == 0x18 and matching and effect != 0:
        calls.append((RETIRE, (effect,)))
    elif command == 0x23 and matching:
        put(memory, LINK + 8, 0)
        memory[read(memory, LINK) + 0x14] = 1
    return memory, calls


class EventLinkOracle(TimingOracle):
    def __init__(self, words, memory, pointer, case):
        super().__init__(words, memory, phase=case.phase, entry=match.ENTRY,
                         arguments=(OWNER, pointer, case.command))
        self.case = case

    def record_call(self, target):
        if target == FACTORY:
            args = self.arguments(5)
        elif target == RETIRE:
            args = self.arguments(1)
        else:
            raise AssertionError("Unexpected event-link call %08X" % target)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target == FACTORY:
            if self.case.mutate:
                self.put(LINK, SOURCE_B, 4)
            result = NEW_EFFECT
        elif target == RETIRE:
            result = 0xA5000002
        else:
            raise AssertionError("Unexpected event-link hook %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.r[2] = result


def native_harness(body):
    return r'''
typedef unsigned char u8;
typedef unsigned int u32;
typedef int s32;
''' + match.TYPES + body + r'''
static EffectLinkOwner151CD3CC owner;
static u8 sourceA[64], sourceB[64], effect[64], newEffect[64];
static s32 factoryCalls, retireCalls, errors, mutateSource;
void *func_151CD4C0(void *source, s32 variant, s32 identity,
                    s32 ownerMode, s32 sourceKind) {
    factoryCalls++;
    if (source != sourceA || variant != owner.link.variant ||
            identity != owner.link.identity || ownerMode != owner.ownerMode ||
            sourceKind != owner.sourceKind) errors = 1;
    if (mutateSource) owner.link.source = sourceB;
    return newEffect;
}
void func_151CE47C(u8 *value) {
    retireCalls++;
    if (value != effect) errors = 1;
}
static int one(u32 n, u32 matching, u32 active, u8 command) {
    s32 identity = (s32)(0x11223344u ^ n * 0x10101u);
    s32 eventIdentity = matching ? identity : identity ^ 0x01000000;
    u32 i;
    for (i = 0; i < 64; i++) {
        sourceA[i] = (u8)(n + i * 3u + 1u);
        sourceB[i] = (u8)(n + i * 5u + 2u);
        effect[i] = (u8)(n + i * 7u + 3u);
        newEffect[i] = (u8)(n + i * 11u + 4u);
    }
    owner.sourceKind = (u8)(0x31u + n);
    owner.ownerMode = (u8)(0x71u + n);
    owner.link.source = sourceA;
    owner.link.identity = identity;
    owner.link.effect = active ? effect : (u8 *)0;
    owner.link.variant = (u8)(0x91u + n);
    mutateSource = n >> 2 & 1u;
    factoryCalls = retireCalls = errors = 0;
    func_151CD3CC(&owner, &eventIdentity, command);
    if (errors) return 10;
    if (command == 0x17 && matching && !active) {
        if (factoryCalls != 1 || retireCalls || owner.link.effect != newEffect)
            return 11;
        if ((mutateSource ? sourceB : sourceA)[0x14] != 0) return 12;
    } else if (command == 0x18 && matching && active) {
        if (factoryCalls || retireCalls != 1 || owner.link.effect != effect)
            return 13;
    } else if (command == 0x23 && matching) {
        if (factoryCalls || retireCalls || owner.link.effect != 0 ||
                sourceA[0x14] != 1) return 14;
    } else if (factoryCalls || retireCalls ||
               owner.link.effect != (active ? effect : (u8 *)0)) return 15;
    return 0;
}
static int run(void) {
    static const u8 commands[] = {0x17, 0x18, 0x23, 0x44};
    u32 n, c, matching, active;
    for (n = 0; n < 256; n++)
        for (c = 0; c < 4; c++)
            for (matching = 0; matching < 2; matching++)
                for (active = 0; active < 2; active++) {
                    int result = one(n, matching, active, commands[c]);
                    if (result) return result;
                }
    return 0;
}
''' + START


def controls():
    body = match.SELECTED
    return {
        "wrong-create-command": body.replace("command == 0x17", "command == 0x16"),
        "wrong-identity": body.replace("link->identity == *identity", "link->identity != *identity", 1),
        "wrong-empty-gate": body.replace("link->effect == 0", "link->effect != 0", 1),
        "wrong-source": body.replace("link->source, link->variant", "link->effect, link->variant"),
        "wrong-variant": body.replace("link->source, link->variant", "link->source, link->variant + 1"),
        "wrong-factory-identity": body.replace("link->variant, link->identity", "link->variant, link->identity + 1"),
        "wrong-owner-mode": body.replace("owner->ownerMode, owner->sourceKind", "owner->sourceKind, owner->sourceKind"),
        "wrong-source-kind": body.replace("owner->ownerMode, owner->sourceKind", "owner->ownerMode, owner->ownerMode"),
        "wrong-post-flag": body.replace("link->source[0x14] = 0", "link->source[0x14] = 1"),
        "wrong-retire-command": body.replace("command == 0x18", "command == 0x19"),
        "wrong-detach-command": body.replace("command == 0x23", "command == 0x22"),
        "wrong-detach-flag": body.replace("link->source[0x14] = 1", "link->source[0x14] = 2"),
    }


class EventLinkDispatchMatchTests(unittest.TestCase):
    receipt = {}

    @classmethod
    def setUpClass(cls):
        cls.out = ROOT / match.BUILD
        (cls.report, cls.before_owner, cls.after_owner,
         cls.before_elf, cls.after_elf) = match.prepare(ROOT)
        cls.words = struct.unpack_from(">%dI" % match.WORDS,
                                       (ROOT / match.ROM_IMAGE).read_bytes(), match.ROM)
        cls.fresh = cls.out / ("test-run-" + str(os.getpid()))
        cls.fresh.mkdir(exist_ok=False)

    @classmethod
    def tearDownClass(cls):
        (cls.out / ("test-receipt-" + str(os.getpid()) + ".json")).write_text(
            json.dumps(cls.receipt, indent=2) + "\n")

    def test_01_guarded_owner_image_registry_and_data_closure(self):
        self.assertEqual((self.report["natural_words"], self.report["words"],
                          self.report["frame"], self.report["guards"],
                          self.report["insertions"], self.report["relocations"]),
                         (60, 61, 0x40, 10, 1, 2))
        self.assertEqual(self.report["neighbors"], 51)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        self.assertEqual(self.report["registry"]["aligned_pointer_literals"],
                         [hex(match.REGISTRY_ROM)])
        self.assertEqual(self.report["registry"]["direct_jal_calls"], [])
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))
        self.receipt["closure"] = self.report

    def test_02_guest_routes_live_source_and_all_word_coverage(self):
        coverage, cases = set(), 0
        for command, match_id, active, mutate, alias, phase, seed in itertools.product(
                (0x17, 0x18, 0x23, 0x44, 0x117, 0x118, 0x123),
                (False, True), (False, True), (False, True), (False, True),
                (0, 8), (0, 19)):
            if alias and not match_id:
                continue
            case = Case(command, match_id, active, mutate, alias, phase, seed)
            initial, pointer = fixture(case)
            wanted, calls = reference(initial, pointer, case)
            model = EventLinkOracle(self.words, initial, pointer, case).run()
            self.assertEqual(external(model.memory), external(wanted), case)
            self.assertEqual(model.calls, calls, case)
            coverage.update(pc for pc in model.visits
                            if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            cases += 1
        self.assertEqual(coverage, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.receipt["guest"] = {"cases": cases, "covered_words": len(coverage),
                                  "stack_phases": 2, "helper_mutation_modes": 2,
                                  "identity_alias_modes": 2}

    def test_03_native32_profiles_and_effective_controls(self):
        selected = self.fresh / "native-selected.c"
        selected.write_text(native_harness(match.SELECTED))
        rows = []
        for profile in ("-O0", "-O2", "-O3"):
            target = self.fresh / ("native-selected" + profile)
            build = subprocess.run(native_command(profile) + [str(selected), "-o", str(target)],
                                   cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(target)], capture_output=True)
            self.assertEqual(run.returncode, 0, (profile, run.stdout, run.stderr))
            rows.append({"profile": profile, "cases": 4096, "UBSan_trap": True})
        effective = []
        for name, body in controls().items():
            source = self.fresh / ("control-" + name + ".c")
            target = self.fresh / ("control-" + name)
            source.write_text(native_harness(body))
            build = subprocess.run(native_command("-O2", valid=False) +
                                   [str(source), "-o", str(target)], cwd=ROOT,
                                   capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, (name, build.stdout, build.stderr))
            run = subprocess.run([str(target)], capture_output=True)
            self.assertNotEqual(run.returncode, 0, name)
            effective.append(name)
        self.receipt["native"] = {"profiles": rows, "effective_controls": effective}

    def test_04_guards_payload_and_image_corruption_fail_closed(self):
        with (self.out / "proposed-guards.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        target_rows = [row for row in rows if row["filename"] == match.FILENAME and
                       row["function"] == match.FUNCTION]
        self.assertEqual(len(target_rows), len(match.GUARD_ROWS))
        compact = self.out / "qualified-compact.o"
        for index, selected in enumerate(target_rows):
            changed = [dict(row) for row in rows]
            row_index = next(i for i, row in enumerate(changed)
                             if row["filename"] == match.FILENAME and
                             row["function"] == match.FUNCTION and
                             row["offset"] == selected["offset"])
            changed[row_index]["expected"] = "0x%08X" % (
                int(changed[row_index]["expected"], 0) ^ 1)
            path = self.fresh / ("stale-guard-%d.csv" % index)
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=changed[0].keys(),
                                        lineterminator="\n")
                writer.writeheader()
                writer.writerows(changed)
            with self.assertRaises(ValueError):
                emit_padded_assembly(compact, ROOT / match.ASM,
                    word_patches_path=path, filename=match.FILENAME)
        match.checked_candidate(compact)
        with self.assertRaises(ValueError):
            match.checked_candidate(self.out / "predecessor-compact.o")
        before = self.before_elf.read_bytes()
        retail = match.retail_bytes(ROOT)
        expected = match.expected_image(before, retail)
        self.assertEqual(expected, self.after_elf.read_bytes())
        function_symbol = next(at for at, name, _, _ in match.symbol_rows(before)
                               if name == match.FUNCTION)
        for position in (elf_slot_offset(before, match.ENTRY, match.SIZE),
                         function_symbol + 8):
            bad = bytearray(expected)
            bad[position] ^= 1
            with self.assertRaises(ValueError):
                match.check_image(before, bytes(bad), retail)
        with self.assertRaises(ValueError):
            match.check_image(before, expected[:-1], retail)
        self.receipt["rejections"] = {"stale_guards": len(target_rows),
                                       "image_corruptions": 3,
                                       "predecessor_payload": True}


if __name__ == "__main__":
    unittest.main()
