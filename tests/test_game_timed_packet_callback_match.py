"""Semantic and strict-image gates for func_1515BAE0."""

import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_timed_packet_callback_candidates as candidate
from tools.experiments import game_timed_packet_callback_match as match
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK, put, read


ROOT = Path(__file__).resolve().parents[2]
RECORD = 0x220000
PACKET_VALUE = 0x330000
TICKS = 0x800BE9E4
UPDATE_TABLE = 0x8008B078
REMOVE_TABLE = 0x8008B07C
UPDATE_CALLBACK = 0x16000100
REMOVE_CALLBACK = 0x16000200
PACKET_UPDATE = 0x1514401C
RELEASE = 0x1516972C


def signed(value, width=32):
    mask = (1 << width) - 1
    return ((value & mask) ^ (1 << (width - 1))) - (1 << (width - 1))


def half(value):
    return signed(value, 16)


def byte(value):
    return value & 0xFF


def fixture(case):
    memory = {STACK + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x300, 0x100)}
    memory.update({RECORD + index: (index * 13 + case["seed"] * 19 + 0x59) & 0xFF
                   for index in range(0x40)})
    memory.update({address + index: 0xA5 for address in (TICKS, UPDATE_TABLE, REMOVE_TABLE)
                   for index in range(16)})
    put(memory, RECORD + 0x10, case["mode"], 1)
    put(memory, RECORD + 0x11, case["flags"], 1)
    put(memory, RECORD + 0x12, case["command"], 1)
    put(memory, RECORD + 0x14, case["timer"], 2)
    put(memory, RECORD + 0x18, case["cursor"])
    put(memory, RECORD + 0x1C, case["packet"])
    put(memory, RECORD + 0x38, case["update_index"], 1)
    put(memory, RECORD + 0x39, case["remove_index"], 1)
    put(memory, TICKS, case["ticks"])
    put(memory, UPDATE_TABLE, UPDATE_CALLBACK)
    put(memory, REMOVE_TABLE + 4, REMOVE_CALLBACK)
    return memory


def record_bytes(memory):
    return bytes(memory[RECORD + index] for index in range(0x40))


def reference(initial, case):
    memory = dict(initial)
    calls = []
    remove = 0
    if memory[RECORD + 0x11] & 1:
        timer = half(read(memory, RECORD + 0x14, 2) - signed(read(memory, TICKS)))
        put(memory, RECORD + 0x14, timer, 2)
        if timer < 0:
            remove = 1
    if remove == 0:
        index = signed(memory[RECORD + 0x38], 8)
        if index != -1:
            calls.append((UPDATE_CALLBACK, (RECORD,)))
            if case["update_mutation"]:
                put(memory, RECORD + 0x10, 0x71, 1)
                put(memory, RECORD + 0x12, 0x93, 1)
                put(memory, RECORD + 0x18, 0x11223344)
                put(memory, RECORD + 0x1C, PACKET_VALUE)
            if case["update_result"] == 0:
                remove = 1
        if read(memory, RECORD + 0x1C) != 0:
            calls.append((PACKET_UPDATE, (
                memory[RECORD + 0x10], RECORD + 0x1C, RECORD + 0x18,
                memory[RECORD + 0x12])))
            put(memory, RECORD + 0x1C,
                read(memory, RECORD + 0x1C) ^ 0x13579BDF)
            put(memory, RECORD + 0x18,
                read(memory, RECORD + 0x18) + 0x10203)
            remove = case["packet_result"] & 0xFF
    if remove != 0:
        index = signed(memory[RECORD + 0x39], 8)
        if index != -1:
            calls.append((REMOVE_CALLBACK, (RECORD,)))
            if case["remove_mutation"]:
                memory[RECORD + 0x11] ^= 0x80
            if case["remove_result"] != 0:
                calls.append((RELEASE, (RECORD,)))
        else:
            calls.append((RELEASE, (RECORD,)))
    return memory, calls


def cases():
    for seed in range(128):
        yield {
            "seed": seed,
            "mode": (seed * 17 + 3) & 0xFF,
            "flags": (0, 1, 2, 3)[seed & 3],
            "command": (seed * 29 + 7) & 0xFF,
            "timer": (-32768, -1, 0, 1, 2, 32767)[seed % 6],
            "ticks": (-1, 0, 1, 2)[(seed // 3) & 3],
            "cursor": (0x40000000 + seed * 0x10101) & 0xFFFFFFFF,
            "packet": (0, PACKET_VALUE)[(seed // 5) & 1],
            "update_index": (-1, 0)[(seed // 7) & 1],
            "update_result": (0, 1, -7)[(seed // 11) % 3],
            "packet_result": (0, 1, 0x100, 0x101, -1)[(seed // 13) % 5],
            "remove_index": (-1, 1)[(seed // 17) & 1],
            "remove_result": (0, 1, -9)[(seed // 19) % 3],
            "update_mutation": (seed % 23) == 0,
            "remove_mutation": (seed % 29) == 0,
        }
    # Explicitly preserve the update-failure result until the final callback,
    # and separately prove that a packet result can clear that failure.
    for seed, packet, packet_result, remove_index, remove_result in (
            (200, 0, 0, 1, 0), (201, 0, 0, 1, 1),
            (202, PACKET_VALUE, 0, 1, 1),
            (203, PACKET_VALUE, 0x101, -1, 0)):
        yield {
            "seed": seed, "mode": 0x12, "flags": 0, "command": 0x34,
            "timer": 9, "ticks": 1, "cursor": 0x55667788,
            "packet": packet, "update_index": 0, "update_result": 0,
            "packet_result": packet_result, "remove_index": remove_index,
            "remove_result": remove_result, "update_mutation": False,
            "remove_mutation": False,
        }


class TimedPacketOracle(TimingOracle):
    def __init__(self, words, memory, case, phase=0):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(RECORD,))
        self.case = case

    def execute(self, word):
        op = word >> 26
        if op == 32:  # lb
            base = self.r[word >> 21 & 31]
            target = word >> 16 & 31
            self.r[target] = signed(self.get(
                (base + signed(word, 16)) & 0xFFFFFFFF, 1), 8) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)

    def record_call(self, target):
        widths = {UPDATE_CALLBACK: 1, REMOVE_CALLBACK: 1,
                  PACKET_UPDATE: 4, RELEASE: 1}
        if target not in widths:
            raise AssertionError("Unexpected timed-packet helper %08X" % target)
        args = tuple(self.arguments(widths[target]))
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target == UPDATE_CALLBACK:
            if self.case["update_mutation"]:
                put(self.memory, RECORD + 0x10, 0x71, 1)
                put(self.memory, RECORD + 0x12, 0x93, 1)
                put(self.memory, RECORD + 0x18, 0x11223344)
                put(self.memory, RECORD + 0x1C, PACKET_VALUE)
            result = self.case["update_result"]
        elif target == PACKET_UPDATE:
            put(self.memory, RECORD + 0x1C,
                read(self.memory, RECORD + 0x1C) ^ 0x13579BDF)
            put(self.memory, RECORD + 0x18,
                read(self.memory, RECORD + 0x18) + 0x10203)
            result = self.case["packet_result"]
        elif target == REMOVE_CALLBACK:
            if self.case["remove_mutation"]:
                self.memory[RECORD + 0x11] ^= 0x80
            result = self.case["remove_result"]
        else:
            result = 0xDEADBEEF
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.lo, self.hi = 0xA5000010, 0xA5000011
        self.r[2] = result & 0xFFFFFFFF


def controls():
    body = candidate.SELECTED_MATCH
    variants = {
        "wrong-timer-flag": body.replace("record->flags & 1", "record->flags & 2", 1),
        "zero-is-expired": body.replace("record->timer < 0", "record->timer <= 0", 1),
        "inverted-update-result": body.replace(
            "D_8008B078[callbackIndex](record) == 0",
            "D_8008B078[callbackIndex](record) != 0", 1),
        "inverted-packet-presence": body.replace(
            "record->packet != 0", "record->packet == 0", 1),
        "full-packet-result": body.replace(" & 0xFF;", ";", 1),
        "swapped-packet-cursors": body.replace(
            "&record->packet,\n                                  &record->cursor",
            "&record->cursor,\n                                  &record->packet", 1),
        "inverted-remove-result": body.replace(
            "D_8008B07C[callbackIndex](record) != 0",
            "D_8008B07C[callbackIndex](record) == 0", 1),
        "missing-sentinel-release": body.replace(
            "        } else {\n            func_1516972C(record);\n        }",
            "        }", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("A timed-packet semantic control did not alter the source")
    return variants


def native_source(body):
    return r'''typedef unsigned char u8;
typedef signed char s8;
typedef signed short s16;
typedef signed int s32;
typedef unsigned int u32;
''' + candidate.INSTALL_TYPES + r'''
typedef s32 (*TimedPacketCallback1515BAE0)(void *);
static TimedPacketRecord1515BAE0 actual, expected;
s32 D_800BE9E4;
static s32 updateResult, packetResult, removeResult, updateMutation, removeMutation;
static s32 updateCalls, packetCalls, removeCalls, releaseCalls, failed;
static s32 updateCallback(void *value) {
    TimedPacketRecord1515BAE0 *record = value; updateCalls++;
    if (record != &actual) failed = 1;
    if (updateMutation) { record->mode = 0x71; record->command = 0x93;
        record->cursor = 0x11223344; record->packet = 0x00330000; }
    return updateResult;
}
static s32 removeCallback(void *value) {
    TimedPacketRecord1515BAE0 *record = value; removeCalls++;
    if (record != &actual) failed = 2;
    if (removeMutation) record->flags ^= 0x80;
    return removeResult;
}
TimedPacketCallback1515BAE0 D_8008B078[2] = {updateCallback, updateCallback};
TimedPacketCallback1515BAE0 D_8008B07C[2] = {removeCallback, removeCallback};
s32 func_1514401C(u8 mode, s32 *packet, s32 *cursor, u8 command) {
    packetCalls++;
    if (mode != actual.mode || command != actual.command ||
        packet != &actual.packet || cursor != &actual.cursor) failed = 3;
    *packet ^= 0x13579BDF; *cursor += 0x10203;
    return packetResult;
}
void func_1516972C(void *value) {
    releaseCalls++; if (value != &actual) failed = 4;
}
''' + body + r'''
static void reference(void) {
    s32 remove = 0; s8 index;
    if (expected.flags & 1) { expected.timer = (s16)(expected.timer - D_800BE9E4);
        if (expected.timer < 0) remove = 1; }
    if (remove == 0) {
        index = expected.updateCallback;
        if (index != -1) { updateCalls--;
            if (updateMutation) { expected.mode = 0x71; expected.command = 0x93;
                expected.cursor = 0x11223344; expected.packet = 0x00330000; }
            if (updateResult == 0) remove = 1; }
        if (expected.packet != 0) { packetCalls--;
            expected.packet ^= 0x13579BDF; expected.cursor += 0x10203;
            remove = packetResult & 0xFF; }
    }
    if (remove != 0) {
        index = expected.removeCallback;
        if (index != -1) { removeCalls--;
            if (removeMutation) expected.flags ^= 0x80;
            if (removeResult != 0) releaseCalls--; }
        else releaseCalls--;
    }
}
static void fill(u8 *bytes, u32 seed) {
    u32 i; for (i = 0; i < sizeof(actual); i++) bytes[i] = (u8)(i * 13u + seed * 19u + 0x59u);
}
static int one(u32 seed) {
    u32 i; fill((u8 *)&actual, seed);
    actual.mode = (u8)(seed * 17u + 3u); actual.flags = (u8)(seed & 3u);
    actual.command = (u8)(seed * 29u + 7u);
    { static const s16 timers[] = {-20,-1,0,1,2,20}; actual.timer = timers[seed % 6u]; }
    actual.cursor = (s32)(0x40000000u + seed * 0x10101u);
    actual.packet = ((seed / 5u) & 1u) ? 0x00330000 : 0;
    actual.updateCallback = ((seed / 7u) & 1u) ? 0 : -1;
    actual.removeCallback = ((seed / 17u) & 1u) ? 1 : -1;
    expected = actual;
    { static const s32 ticks[] = {-1,0,1,2}; D_800BE9E4 = ticks[(seed / 3u) & 3u]; }
    { static const s32 values[] = {0,1,-7}; updateResult = values[(seed / 11u) % 3u];
      removeResult = values[(seed / 19u) % 3u]; }
    { static const s32 values[] = {0,1,0x100,0x101,-1}; packetResult = values[(seed / 13u) % 5u]; }
    updateMutation = seed % 23u == 0u; removeMutation = seed % 29u == 0u;
    updateCalls = packetCalls = removeCalls = releaseCalls = failed = 0;
    func_1515BAE0(&actual); reference();
    if (failed || updateCalls || packetCalls || removeCalls || releaseCalls) return 1;
    for (i = 0; i < sizeof(actual); i++) if (((u8 *)&actual)[i] != ((u8 *)&expected)[i]) return 1;
    return 0;
}
int main(void) { u32 seed; for (seed = 0; seed < 256u; seed++) if (one(seed)) return 1; return 0; }
'''


def run_native(label, body, optimization, expected):
    output = ROOT / match.BUILD / "native"
    output.mkdir(parents=True, exist_ok=True)
    source = output / (label + ".c")
    binary = output / (label + ".exe")
    source.write_text(native_source(body))
    command = [
        "gcc", optimization, "-std=c99", "-fno-strict-aliasing",
        "-ffp-contract=off", "-fsanitize=undefined",
        "-fsanitize-undefined-trap-on-error", "-Wall", "-Wextra", "-Werror",
        str(source), "-o", str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    executed = subprocess.run([str(binary)], capture_output=True, timeout=30)
    if executed.returncode != expected:
        raise AssertionError((label, executed.returncode, executed.stderr))


class TimedPacketCallbackTest(unittest.TestCase):
    def test_guest_semantics_cover_every_word(self):
        data = (ROOT / match.ROM_IMAGE).read_bytes()[match.ROM:match.ROM + match.SIZE]
        words = list(struct.unpack(">%dI" % match.WORDS, data))
        seen = set()
        count = 0
        for case, phase in itertools.product(cases(), (0, 8)):
            initial = fixture(case)
            wanted, calls = reference(initial, case)
            model = TimedPacketOracle(words, initial, case, phase).run()
            self.assertEqual(record_bytes(model.memory), record_bytes(wanted))
            self.assertEqual(model.calls, calls)
            seen.update(pc - match.ENTRY for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            count += 1
        self.assertEqual(count, 264)
        self.assertEqual(seen, set(range(0, match.SIZE, 4)))

    def test_native_profiles_and_controls(self):
        for optimization in ("-O0", "-O2", "-O3"):
            run_native("positive" + optimization[1:], candidate.SELECTED_MATCH,
                       optimization, 0)
        for label, body in controls().items():
            run_native("control-" + label, body, "-O2", 1)

    def test_guarded_owner_registry_and_full_image(self):
        candidate_report = candidate.compare(
            "test-guarded-owner", candidate.SELECTED_MATCH)
        self.assertEqual(candidate_report["words"], match.WORDS)
        self.assertEqual(candidate_report["differences"], 2)
        self.assertEqual([row["offset"] for row in candidate_report["difference_rows"]],
                         [0x70, 0x80])
        result = match.prepare(ROOT)
        report = result["report"]
        installed = candidate.SELECTED_MATCH in (ROOT / candidate.SOURCE).read_text()
        self.assertEqual(report["source_installed"], installed)
        self.assertEqual(report["guards"], 2)
        self.assertEqual(report["natural_positional_differences"], 2)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertTrue(report["game_data"]["exact"])
        self.assertEqual(report["registry"]["aligned_pointer_literals"], ["0x23131c"])


if __name__ == "__main__":
    unittest.main()
