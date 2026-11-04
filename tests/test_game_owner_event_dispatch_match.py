"""Semantic, registry, owner and strict-image gates for func_15191980."""

from dataclasses import dataclass
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_owner_event_dispatch_candidates as candidate
from tools.experiments import game_owner_event_dispatch_match as match
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_frame_timing_oracle import STACK, TimingOracle
from tools.tests.test_game_point_transform_match import put, read


ROOT = Path(__file__).resolve().parents[2]
RECORD = 0x22000
EVENT = 0x24000
OWNER_A = 0x26000
OWNER_B = 0x28000
RELEASE = 0x1516972C
FORWARD = 0x15169850


def s16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


@dataclass(frozen=True)
class Case:
    command: int = 0
    match_mode: int = 0
    timer: int = 0x1234
    flags: int = 0xA4
    phase: int = 0
    upper: int = 0
    seed: int = 0


def fixture(case=Case()):
    memory = {STACK + index: (index * 17 + case.seed + 0xA5) & 0xFF
              for index in range(-0x300, 0x100)}
    for base, size in ((RECORD - 0x20, 0x80), (EVENT - 0x20, 0x50)):
        memory.update({base + index: (index * 13 + case.seed * 19 + 0x59) & 0xFF
                       for index in range(size)})
    record_owner = OWNER_A
    event_owner = OWNER_A if case.match_mode in (1, 3) else OWNER_B
    record_id = 0x31
    event_id = record_id if case.match_mode in (2, 3) else 0x72
    put(memory, RECORD + 0x10, record_owner)
    memory[RECORD + 0x14] = record_id
    put(memory, RECORD + 0x16, case.timer, 2)
    memory[RECORD + 0x18] = case.flags & 0xFF
    put(memory, EVENT, event_owner)
    memory[EVENT + 4] = event_id
    return memory


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x300 <= address < STACK + 0x100}


def raw_command(case):
    return ((case.upper & 0xFFFFFF) << 8) | (case.command & 0xFF)


def reference(initial, case):
    memory = dict(initial)
    calls = []
    command = case.command & 0xFF
    matched = (read(memory, RECORD + 0x10) == read(memory, EVENT) or
               memory[RECORD + 0x14] == memory[EVENT + 4])
    if command == 0x0D:
        if matched:
            put(memory, RECORD + 0x16, 100, 2)
            memory[RECORD + 0x18] |= 1
    elif command in (0x0C, 0x50, 0x0E):
        if matched:
            calls.append((RELEASE, (RECORD,)))
    elif command == 0x4E:
        calls.append((RELEASE, (RECORD,)))
    else:
        calls.append((FORWARD, (
            EVENT, command, RECORD + 0x10, RECORD + 0x14, RECORD)))
    return memory, calls


class OwnerEventDispatchOracle(TimingOracle):
    def __init__(self, words, memory, case=Case(), fault=None):
        super().__init__(
            words, memory, phase=case.phase, entry=match.ENTRY,
            arguments=(RECORD, EVENT, raw_command(case)))
        self.root_fault = fault

    def record_call(self, target):
        if target == RELEASE:
            args = tuple(self.arguments(1))
        elif target == FORWARD:
            args = tuple(self.arguments(5))
        else:
            raise AssertionError("Unexpected owner-event helper %08X" % target)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target not in (RELEASE, FORWARD):
            raise AssertionError("Unbounded owner-event helper %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA6000000 + index for index in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678


def controls():
    body = candidate.SELECTED
    variants = {
        "wrong-arm-command": body.replace("== 0x0D", "== 0x0B", 1),
        "wrong-match-gate": body.replace(" && ", " || ", 2),
        "wrong-timer": body.replace("record->timer = 100;", "record->timer = 99;", 1),
        "wrong-flag": body.replace("record->flags |= 1;", "record->flags |= 2;", 1),
        "wrong-release-command": body.replace("== 0x50", "== 0x51", 1),
        "wrong-unconditional-release": body.replace("== 0x4E", "== 0x4F", 1),
        "wrong-forward-command": body.replace(
            "((volatile u8 *)&rawCommand)[3],", "0,", 1),
        "wrong-forward-owner": body.replace(
            "(s32)&record->owner, (s32)&record->ownerId",
            "(s32)&record->ownerId, (s32)&record->ownerId", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("An owner-event dispatcher control did not alter source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef signed short s16;
typedef signed int s32;
typedef unsigned int u32;
typedef struct {
    u8 retained00[0x10];
    u8 *owner;
    u8 ownerId;
    u8 retained15;
    s16 timer;
    u8 flags;
} OwnerEventRecord15191980;
typedef struct {
    u8 *owner;
    u8 ownerId;
} OwnerEvent15191980;
static u32 releaseCalls, forwardCalls, error;
static OwnerEventRecord15191980 *wantedRecord;
static OwnerEvent15191980 *wantedEvent;
static u8 wantedCommand;
void func_1516972C(OwnerEventRecord15191980 *record) {
    releaseCalls++;
    if (record != wantedRecord) error = 1;
}
void func_15169850(s32 eventAddress, u8 command, s32 ownerAddress,
                  s32 ownerIdAddress, s32 recordAddress) {
    forwardCalls++;
    if ((OwnerEvent15191980 *)eventAddress != wantedEvent ||
        command != wantedCommand ||
        ownerAddress != (s32)&wantedRecord->owner ||
        ownerIdAddress != (s32)&wantedRecord->ownerId ||
        (OwnerEventRecord15191980 *)recordAddress != wantedRecord) error = 1;
}
''' + body + r'''
static int one(u32 seed) {
    OwnerEventRecord15191980 record;
    OwnerEvent15191980 event;
    u8 ownerA, ownerB;
    u8 command = (u8)seed;
    u32 mode = (seed >> 8) & 3;
    s32 raw = (s32)(((u32)command << 24) | (seed & 0xFFFFFF));
    s16 oldTimer = (s16)(seed * 37u + 0x1234u);
    u8 oldFlags = (u8)(seed * 19u + (seed >> 8) * 7u + 0xA4u);
    u32 matched, release, forward;
    record.owner = &ownerA;
    event.owner = mode == 1 || mode == 3 ? &ownerA : &ownerB;
    record.ownerId = 0x31;
    event.ownerId = mode == 2 || mode == 3 ? 0x31 : 0x72;
    record.retained15 = 0xC7;
    record.timer = oldTimer;
    record.flags = oldFlags;
    matched = record.owner == event.owner || record.ownerId == event.ownerId;
    release = (command == 0x4E) ||
        ((command == 0x0C || command == 0x50 || command == 0x0E) && matched);
    forward = command != 0x0D && command != 0x0C && command != 0x50 &&
        command != 0x0E && command != 0x4E;
    releaseCalls = forwardCalls = error = 0;
    wantedRecord = &record;
    wantedEvent = &event;
    wantedCommand = command;
    func_15191980(&record, &event, raw);
    if (error || releaseCalls != release || forwardCalls != forward) return 1;
    if (command == 0x0D && matched) {
        if (record.timer != 100 || record.flags != (u8)(oldFlags | 1)) return 2;
    } else if (record.timer != oldTimer || record.flags != oldFlags) {
        return 3;
    }
    return 0;
}
static int run(void) {
    u32 seed;
    if (sizeof(void *) != 4 || sizeof(s32) != 4 ||
        __builtin_offsetof(OwnerEventRecord15191980, owner) != 0x10 ||
        __builtin_offsetof(OwnerEventRecord15191980, timer) != 0x16 ||
        __builtin_offsetof(OwnerEventRecord15191980, flags) != 0x18) return 9;
    for (seed = 0; seed < 4096; seed++) if (one(seed)) return 1;
    return 0;
}
void _start(void) {
    s32 code = run();
    __asm__ volatile("int $0x80"::"a"(1),"b"(code));
    __builtin_unreachable();
}
'''


def run_native(label, body, optimization, expected):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / (label + ".elf")
    source.write_text(native_source(body))
    command = [
        "gcc", "-m32", "-std=c99", optimization, "-fno-pie", "-no-pie",
        "-ffreestanding", "-fno-strict-aliasing", "-fno-stack-protector",
        "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
        "-Wall", "-Wextra", "-Werror", "-nostdlib", str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if executed.returncode != expected:
        raise AssertionError((label, executed.returncode, executed.stderr))


class GameOwnerEventDispatchMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.retail = list(struct.unpack_from(
            ">65I", (ROOT / match.ROM_IMAGE).read_bytes(), match.ROM))

    def receipt(self, name, data):
        (self.output / (name + ".json")).write_text(
            json.dumps(data, indent=2) + "\n")

    def test_01_guarded_profile_owner_neighbors_and_strict_image(self):
        selected = candidate.compare(
            "test-selected", candidate.SELECTED, ("-O2", "-g3"))
        self.assertEqual(
            (selected["words"], selected["frame"], selected["differences"]),
            (65, 0x28, 45))
        self.assertEqual(selected["bindings"], {
            "0x0AC": [("R_MIPS_26", "func_1516972C")],
            "0x0C8": [("R_MIPS_26", "func_1516972C")],
            "0x0E8": [("R_MIPS_26", "func_15169850")],
        })
        plain = candidate.compare(
            "test-plain", candidate.SELECTED, ("-O2",))
        self.assertEqual(
            (plain["words"], plain["frame"], plain["differences"]),
            (64, 0x28, 61))
        report = match.prepare(ROOT)["report"]
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(
            (report["guards"], report["neighbors"], report["strict_exclusions"]),
            (45, 60, 0))
        self.assertTrue(report["all_addresses_fixed"])
        self.assertTrue(report["game_data"]["exact"])
        rows = match.PATCH_ROWS
        self.assertEqual(len({row["offset"] for row in rows}), 45)
        self.assertEqual(sum(row["expected_relocations"] != "-" for row in rows), 2)
        self.assertEqual(sum(row["replacement_relocations"] != "-" for row in rows), 2)

    def test_02_guest_commands_matches_callbacks_and_all_words(self):
        cases = []
        for command in range(256):
            for match_mode in range(4):
                for phase in (0, 8):
                    cases.append(Case(
                        command, match_mode, (command * 257 + match_mode) & 0xFFFF,
                        (command * 19 + match_mode * 7) & 0xFF, phase,
                        (command * 0x12345 + match_mode) & 0xFFFFFF,
                        command ^ (match_mode << 4) ^ phase))
        coverage = set()
        releases = forwards = 0
        for case in cases:
            initial = fixture(case)
            wanted, calls = reference(initial, case)
            model = OwnerEventDispatchOracle(self.retail, initial, case).run()
            self.assertEqual((public(model.memory), model.calls),
                             (public(wanted), calls))
            coverage.update(model.visits)
            releases += sum(target == RELEASE for target, _ in calls)
            forwards += sum(target == FORWARD for target, _ in calls)
        unreachable = {match.ENTRY + 0x6C, match.ENTRY + 0xC0}
        self.assertEqual(
            coverage,
            set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - unreachable)
        self.receipt("guest-contract", {
            "cases": len(cases), "words": len(coverage),
            "commands": 256, "match_modes": 4, "stack_phases": 2,
            "release_calls": releases, "forward_calls": forwards,
            "unreachable_scheduling_words": [
                hex(address) for address in sorted(unreachable)],
            "callback_clobber": True,
        })

    def test_03_native_profiles_and_effective_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED,
                       optimization, 0)
        variants = controls()
        for label, body in variants.items():
            run_native("control-" + label, body, "-O2", 1)
        self.receipt("native-contract", {
            "profiles": ["O0", "O2", "O3"], "cases_per_profile": 4096,
            "controls": sorted(variants), "actual_32_bit_C": True,
        })

    def test_04_registry_abi_and_active_root_fault_boundaries(self):
        evidence = match.registry_evidence(ROOT)
        self.assertEqual(evidence["direct_jal_calls"], [])
        self.assertEqual(evidence["aligned_pointer_literals"], ["0x230604"])
        cases = (
            Case(0x0D, 0), Case(0x0D, 1), Case(0x0D, 2),
            Case(0x0C, 0), Case(0x0C, 1), Case(0x50, 2, phase=8),
            Case(0x0E, 3), Case(0x4E, 0), Case(0x33, 0, phase=8),
        )
        states = []
        for case in cases:
            initial = fixture(case)
            baseline = OwnerEventDispatchOracle(self.retail, initial, case).run()
            for cut in range(baseline.root_accesses):
                model = OwnerEventDispatchOracle(
                    self.retail, initial, case, fault=cut)
                with self.assertRaises(faults.AccessBoundary):
                    model.run()
                states.append((model.current_pc, model.delay_of,
                               model.root_accesses))
        self.assertGreater(len(states), 20)
        self.receipt("registry-and-faults", {
            "registry_pointer_offsets": evidence["aligned_pointer_literals"],
            "root_access_faults": states,
            "no_direct_call_sites_expected": True,
        })


if __name__ == "__main__":
    unittest.main()

