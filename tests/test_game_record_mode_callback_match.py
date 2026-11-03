"""Direct C, semantics, ABI, registry, owner and image gates for func_15013C38."""

import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_record_mode_callback_match as match
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read


RECORD, STATUS = 0x220000, 0x230000
TABLE, SCALE = 0x80082F28, 0x80096650
GLOBAL_MODE, SEQUENCE = 0x800BE9F0, 0x800C35E8
PLAYER_MODE, STATUS_POINTER = 0x800C35EA, 0x800D2E4C
CALLBACK = 0x16010000


def rounded(value):
    """Round a Python number through IEEE binary32 and return its raw bits."""
    return bits(value)


def scaled_bits(raw, scale_word):
    """Mirror retail's signed-convert plus 2^32 unsigned correction."""
    converted = floating(rounded(float(signed(raw))))
    if raw & 0x80000000:
        converted = floating(rounded(converted + floating(0x4F800000)))
    return rounded(converted * floating(scale_word))


def fixture(status_flags, global_mode, player_mode, sequence, mode,
            callback, raw, scale_word, phase):
    memory = {STACK + i: (i * 17 + 0xA5) & 0xFF
              for i in range(-0x100, 0x100)}
    memory.update({RECORD + i: (i * 13 + 0x59) & 0xFF for i in range(0x40)})
    memory.update({STATUS + i: (i * 29 + 0x71) & 0xFF for i in range(0x20)})
    for index in range(-2, 8):
        put(memory, TABLE + index * 4, 0)
    memory[STATUS + 0x11] = status_flags
    put(memory, STATUS_POINTER, STATUS)
    put(memory, GLOBAL_MODE, global_mode)
    memory[PLAYER_MODE] = player_mode
    memory[SEQUENCE] = sequence
    put(memory, SCALE, scale_word)
    memory[RECORD + 0x16] = 0xA1
    put(memory, RECORD + 0x18, mode)
    put(memory, RECORD + 0x1C, raw)
    if callback:
        put(memory, TABLE + mode * 4, CALLBACK)
    return memory


def external(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x100 <= address < STACK + 0x100}


def reference(initial, status_flags, global_mode, player_mode, sequence,
              mode, callback, raw, scale_word):
    memory, calls = dict(initial), []
    memory[RECORD + 0x16] |= 4
    first_suppressed = bool(status_flags & 4) and global_mode == 0x13
    second_suppressed = (player_mode == 1 and sequence in (0xF, 0x10, 0x11))
    if not first_suppressed and not second_suppressed and mode < 6 and callback:
        calls.append((CALLBACK, (RECORD, scaled_bits(raw, scale_word))))
    return memory, calls


class RecordModeOracle(TimingOracle):
    def __init__(self, words, memory, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(RECORD,))

    def execute(self, word):
        op, fmt, fs, fd, fn = (word >> 26, (word >> 21) & 31,
                               (word >> 11) & 31, (word >> 6) & 31,
                               word & 63)
        if op == 17 and fmt == 20 and fn == 32:
            self.f[fd] = rounded(float(signed(self.f[fs])))
            self.r[0] = 0
        else:
            super().execute(word)

    def record_call(self, target):
        if target != CALLBACK:
            raise AssertionError("Unexpected record-mode callback %08X" % target)
        args = self.arguments(2)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target != CALLBACK:
            raise AssertionError("Unexpected record-mode hook %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]


def native_harness(body):
    return r'''typedef unsigned char u8;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
#define NULL ((void *)0)
typedef void (*RecordModeCallback40490)(u8 *, f32);
static void callback(u8 *, f32);
RecordModeCallback40490 D_80082F28[6];
f32 D_80096650;
u8 D_800C35E8;
u8 D_800C35EA;
s32 D_800BE9F0;
u8 status[0x20];
u8 *D_800D2E4C = status;
%s
static union { u32 align; u8 bytes[0x40]; } record;
static s32 calls, badRecord;
static u32 callbackBits;
static u32 rawBits(f32 value) { union { u32 u; f32 f; } word; word.f = value; return word.u; }
static f32 rawFloat(u32 value) { union { u32 u; f32 f; } word; word.u = value; return word.f; }
static void callback(u8 *value, f32 scaled) {
    calls++;
    if (value != record.bytes) badRecord = 1;
    callbackBits = rawBits(scaled);
}
static int one(u32 statusFlags, s32 globalMode, u32 playerMode, u32 sequence,
               s32 mode, u32 enabled, u32 raw, u32 scale) {
    u32 i, expectedCalls, expectedBits = 0;
    s32 result;
    for (i = 0; i < sizeof(record.bytes); i++) record.bytes[i] = (u8)(i * 13 + 0x59);
    record.bytes[0x16] = 0xA1;
    for (i = 0; i < sizeof(status); i++) status[i] = (u8)(i * 29 + 0x71);
    status[0x11] = (u8)statusFlags;
    D_800BE9F0 = globalMode;
    D_800C35EA = (u8)playerMode;
    D_800C35E8 = (u8)sequence;
    D_80096650 = rawFloat(scale);
    *(s32 *)(record.bytes + 0x18) = mode;
    *(u32 *)(record.bytes + 0x1C) = raw;
    for (i = 0; i < 6; i++) D_80082F28[i] = NULL;
    if (mode >= 0 && mode < 6 && enabled) D_80082F28[mode] = callback;
    expectedCalls = !((statusFlags & 4) && globalMode == 0x13) &&
        !(playerMode == 1 && (sequence == 0xF || sequence == 0x10 || sequence == 0x11)) &&
        mode < 6 && enabled;
    if (expectedCalls)
        expectedBits = rawBits((f32)raw * D_80096650);
    calls = badRecord = 0;
    callbackBits = 0xDEADBEEF;
    result = func_15013C38(record.bytes);
    if (result != 1 || badRecord || calls != (s32)expectedCalls) return 10;
    if (record.bytes[0x16] != 0xA5) return 11;
    if (expectedCalls && callbackBits != expectedBits) return 12;
    return 0;
}
static int run(void) {
    static const u32 statuses[] = {0, 4};
    static const s32 globals[] = {0x12, 0x13};
    static const u32 players[] = {0, 1};
    static const u32 sequences[] = {0, 0xF, 0x10, 0x11, 0x12};
    static const s32 modes[] = {0, 1, 5, 6, 7};
    static const u32 values[] = {0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF};
    static const u32 scales[] = {0, 0x3F000000, 0x3F800000, 0x3B808081, 0xC0000000};
    u32 a, b, c, d, e, f, g, h;
    for (a = 0; a < 2; a++) for (b = 0; b < 2; b++)
    for (c = 0; c < 2; c++) for (d = 0; d < 5; d++)
    for (e = 0; e < 5; e++) for (f = 0; f < 2; f++)
    for (g = 0; g < 5; g++) for (h = 0; h < 5; h++) {
        int result = one(statuses[a], globals[b], players[c], sequences[d],
                         modes[e], f, values[g], scales[h]);
        if (result) return result;
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int statusCode = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(statusCode) : "memory");
    __builtin_unreachable();
}
''' % body


class RecordModeCallbackMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / match.BUILD
        (cls.report, cls.predecessor_owner, cls.qualified_owner,
         cls.predecessor_elf, cls.qualified_elf) = match.prepare(
             cls.root, cls.output)
        rom = (cls.root / match.ROM_IMAGE).read_bytes()
        cls.words = list(struct.unpack_from(">%dI" % match.WORDS, rom, match.ROM))

    def test_01_direct_C_owner_image_and_protected_data(self):
        self.assertEqual((self.report["words"], self.report["slot_words"],
                          self.report["frame"], self.report["natural_differences"],
                          self.report["guards"], self.report["relocations"]),
                         (64, 64, 24, 0, 0, 12))
        self.assertEqual(self.report["neighbors"], 31)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))
        self.assertEqual(self.qualified_elf.read_bytes(), match.expected_image(
            self.predecessor_elf.read_bytes(), match.retail_bytes(self.root)))

    def test_02_guest_suppression_callbacks_unsigned_scaling_and_all_words(self):
        visits, cases = set(), 0
        for status_flags, global_mode, player_mode, sequence, mode, callback, raw, scale_word, phase in itertools.product(
                (0, 4), (0x12, 0x13), (0, 1), (0, 0xF, 0x10, 0x11, 0x12),
                (-1, 0, 5, 6), (0, 1),
                (0, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF),
                (0x3F000000, 0x3B808081), (0, 8)):
            initial = fixture(status_flags, global_mode, player_mode, sequence,
                              mode, callback, raw, scale_word, phase)
            wanted, calls = reference(initial, status_flags, global_mode,
                                      player_mode, sequence, mode, callback,
                                      raw, scale_word)
            model = RecordModeOracle(self.words, initial, phase).run()
            self.assertEqual(external(model.memory), external(wanted))
            self.assertEqual(model.calls, calls)
            self.assertEqual((model.r[2], model.r[29]), (1, STACK + phase))
            visits.update(model.visits)
            cases += 1
        # The emulator executes branch-delay words without adding them to
        # ``visits``; +0x8C is the only instruction observed exclusively as
        # such a delay slot. Every independently dispatched word is reached.
        self.assertEqual(
            set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - visits,
            {match.ENTRY + 0x8C})
        self.assertEqual(cases, 5120)

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
            "no-flag": body.replace("record[0x16] |= 4;", "record[0x16] |= 0;"),
            "wrong-status-mask": body.replace("[0x11] & 4", "[0x11] & 2"),
            "wrong-global-mode": body.replace("D_800BE9F0 == 0x13", "D_800BE9F0 == 0x12"),
            "wrong-player-mode": body.replace("D_800C35EA == 1", "D_800C35EA == 2"),
            "missing-sequence": body.replace("D_800C35E8 == 0x11", "D_800C35E8 == 0x12"),
            "wrong-bound": body.replace("mode >= 6", "mode >= 5"),
            "signed-value": body.replace("(f32)*(u32 *)", "(f32)*(s32 *)"),
            "wrong-scale": body.replace(" * D_80096650", " + D_80096650"),
            "wrong-callback": body.replace("D_80082F28[mode]", "D_80082F28[0]"),
            "wrong-return": body.replace("return 1;", "return 0;"),
        }
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0, name)

    def test_04_registry_literal_and_live_source_state(self):
        rom = (self.root / match.ROM_IMAGE).read_bytes()
        jal = 0x0C000000 | (match.ENTRY >> 2 & 0x03FFFFFF)
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == jal], [])
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == match.ENTRY],
                         [0x2279AC])
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
        self.assertIn("Dispatch the record's scaled value", qualified)
        self.assertNotIn("s32 func_15013C38();", qualified)


if __name__ == "__main__":
    unittest.main()
