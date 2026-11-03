"""Guarded C, semantics, ABI and image gates for func_1507FEA0."""

import csv
import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_child_state_finish_guard_match as match
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put


ACTOR, CHILD, ALT_CHILD = 0x220000, 0x230000, 0x240000
TICK, PLAYER_MODE = 0x800BE9E4, 0x800C35EA
FINISH, RESET = 0x1507FC2C, 0x1507FF94


def signed32(value):
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def signed16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def half(memory, address):
    return (memory[address] << 8) | memory[address + 1]


def fixture(child_present, marker, countdown, mode, player_mode, count,
            timer, tick, phase):
    memory = {STACK + i: (i * 17 + 0xA5) & 0xFF
              for i in range(-0x100, 0x100)}
    memory.update({ACTOR + i: (i * 13 + 0x59) & 0xFF
                   for i in range(0x340)})
    for base, multiplier in ((CHILD, 29), (ALT_CHILD, 31)):
        memory.update({base + i: (i * multiplier + 0x71) & 0xFF
                       for i in range(0x100)})
    put(memory, ACTOR + 0x31C, CHILD if child_present else 0)
    memory[ACTOR + 0x127] = marker
    memory[ACTOR + 0x13A] = countdown
    memory[CHILD + 0x58] = mode
    put(memory, CHILD + 0x5A, count, 2)
    put(memory, CHILD + 0x66, timer & 0xFFFF, 2)
    put(memory, ALT_CHILD + 0x66, 0x3456, 2)
    memory[PLAYER_MODE] = player_mode
    put(memory, TICK, tick & 0xFFFFFFFF)
    return memory


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x100 <= address < STACK + 0x100}


def reference(initial, replace_child):
    memory, calls = dict(initial), []
    child = ((memory[ACTOR + 0x31C] << 24) |
             (memory[ACTOR + 0x31D] << 16) |
             (memory[ACTOR + 0x31E] << 8) |
             memory[ACTOR + 0x31F])
    if child == 0 or memory[ACTOR + 0x127] == 0xFF:
        return memory, calls
    if memory[ACTOR + 0x13A] != 0:
        memory[ACTOR + 0x13A] = (memory[ACTOR + 0x13A] - 1) & 0xFF
    state = child + 0x58
    tick = signed32((memory[TICK] << 24) | (memory[TICK + 1] << 16) |
                    (memory[TICK + 2] << 8) | memory[TICK + 3])
    if memory[state] == 1 and memory[PLAYER_MODE] != 1:
        count = half(memory, state + 2)
        limit = signed32((0xFFFF - tick) & 0xFFFFFFFF)
        if count < limit:
            put(memory, state + 2, (count + tick) & 0xFFFF, 2)
    else:
        put(memory, state + 2, 0, 2)
        memory[state + 4] = 0
        memory[state + 5] = 0
        memory[state + 0xC] = 0
        memory[state + 0xD] = 0
    timer = signed16(half(memory, child + 0x66))
    if timer != 0:
        if tick < timer:
            put(memory, child + 0x66, (timer - tick) & 0xFFFF, 2)
        else:
            calls.append((RESET, (ACTOR,)))
            if replace_child:
                put(memory, ACTOR + 0x31C, ALT_CHILD)
                child = ALT_CHILD
            put(memory, child + 0x66, 0, 2)
    calls.append((FINISH, (ACTOR,)))
    return memory, calls


class ChildStateOracle(TimingOracle):
    def __init__(self, words, memory, replace_child, phase):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(ACTOR,))
        self.replace_child = replace_child

    def record_call(self, target):
        if target not in (RESET, FINISH):
            raise AssertionError("Unexpected child-state call %08X" % target)
        args = self.arguments(1)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target == RESET and self.replace_child:
            self.put(ACTOR + 0x31C, ALT_CHILD, 4)
        elif target not in (RESET, FINISH):
            raise AssertionError("Unexpected child-state hook %08X" % target)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]


def native_harness(body):
    return r'''typedef unsigned char u8;
typedef unsigned short u16;
typedef short s16;
typedef int s32;
#define NULL ((void *)0)
s32 D_800BE9E4;
u8 D_800C35EA;
void func_1507FC2C(u8 *);
void func_1507FF94(u8 *);
%s
static union { s32 align; u8 bytes[0x340]; } actor;
static union { s32 align; u8 bytes[0x100]; } child, alternate;
static s32 resets, finishes, badActor, replaceChild;
void func_1507FF94(u8 *value) {
    resets++;
    if (value != actor.bytes) badActor = 1;
    if (replaceChild) *(u8 **)(actor.bytes + 0x31C) = alternate.bytes;
}
void func_1507FC2C(u8 *value) {
    finishes++;
    if (value != actor.bytes) badActor = 1;
}
static int one(s32 marker, s32 countdown, s32 mode, s32 player,
               s32 count, s32 timer, s32 tick, s32 replace) {
    s32 i, expectedReset = 0;
    u16 expectedCount = (u16)count;
    s16 expectedTimer = (s16)timer;
    for (i = 0; i < (s32)sizeof(actor.bytes); i++) actor.bytes[i] = (u8)(i * 13 + 0x59);
    for (i = 0; i < (s32)sizeof(child.bytes); i++) {
        child.bytes[i] = (u8)(i * 29 + 0x71);
        alternate.bytes[i] = (u8)(i * 31 + 0x71);
    }
    *(u8 **)(actor.bytes + 0x31C) = child.bytes;
    actor.bytes[0x127] = (u8)marker;
    actor.bytes[0x13A] = (u8)countdown;
    child.bytes[0x58] = (u8)mode;
    *(u16 *)(child.bytes + 0x5A) = (u16)count;
    *(s16 *)(child.bytes + 0x66) = (s16)timer;
    *(s16 *)(alternate.bytes + 0x66) = 0x3456;
    D_800C35EA = (u8)player;
    D_800BE9E4 = tick;
    if (marker != 0xFF) {
        if (mode == 1 && player != 1) {
            if ((u16)count < 0xFFFF - tick) expectedCount = (u16)(count + tick);
        } else expectedCount = 0;
        if ((s16)timer != 0) {
            if (tick < (s16)timer) expectedTimer = (s16)(timer - tick);
            else { expectedReset = 1; expectedTimer = 0; }
        }
    }
    resets = finishes = badActor = 0;
    replaceChild = replace;
    func_1507FEA0(actor.bytes);
    if (badActor || resets != expectedReset || finishes != (marker == 0xFF ? 0 : 1)) return 10;
    if (actor.bytes[0x13A] != (u8)(marker == 0xFF ? countdown :
                                   (countdown ? countdown - 1 : 0))) return 11;
    if (*(u16 *)(child.bytes + 0x5A) != expectedCount) return 12;
    if (marker != 0xFF && (mode != 1 || player == 1) &&
        (child.bytes[0x5C] != 0 || child.bytes[0x5D] != 0 ||
         child.bytes[0x64] != 0 || child.bytes[0x65] != 0)) return 16;
    if (expectedReset && replace) {
        if (*(s16 *)(alternate.bytes + 0x66) != 0) return 13;
        if (*(s16 *)(child.bytes + 0x66) != (s16)timer) return 14;
    } else if (*(s16 *)(child.bytes + 0x66) != expectedTimer) return 15;
    return 0;
}
static int run(void) {
    static const s32 modes[] = {0, 1, 2};
    static const s32 counts[] = {0, 0xFFFE, 0xFFFF};
    static const s32 timers[] = {0, 1, -1, 32767};
    static const s32 ticks[] = {0, 1, 30, -1};
    s32 a, b, c, d, e, f, g;
    if (one(0xFF, 1, 1, 0, 0xFFFE, 1, 1, 0)) return 20;
    for (a = 0; a < 2; a++) for (b = 0; b < 3; b++)
    for (c = 0; c < 2; c++) for (d = 0; d < 3; d++)
    for (e = 0; e < 4; e++) for (f = 0; f < 4; f++)
    for (g = 0; g < 2; g++) {
        int result = one(0, a, modes[b], c, counts[d], timers[e], ticks[f], g);
        if (result) return result;
    }
    return 0;
}
__attribute__((noreturn)) void _start(void) {
    int status = run();
    __asm__ volatile("int $0x80" :: "a"(1), "b"(status) : "memory");
    __builtin_unreachable();
}
''' % body


class ActorChildStateFinishGuardMatchTests(unittest.TestCase):
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

    def test_01_guarded_C_owner_image_and_protected_data(self):
        self.assertEqual((self.report["words"], self.report["slot_words"],
                          self.report["frame"], self.report["natural_differences"],
                          self.report["guards"], self.report["insertions"],
                          self.report["relocations"]),
                         (61, 61, 24, 15, 15, 0, 8))
        self.assertEqual(self.report["neighbors"], 15)
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))
        self.assertEqual(self.qualified_elf.read_bytes(), match.expected_image(
            self.predecessor_elf.read_bytes(), match.retail_bytes(self.root)))

    def test_02_guest_state_timer_callbacks_and_all_words(self):
        visits, cases = set(), 0
        for phase in (0, 8):
            for child_present, marker in ((0, 0), (1, 0xFF)):
                initial = fixture(child_present, marker, 1, 1, 0,
                                  0xFFFE, 1, 1, phase)
                wanted, calls = reference(initial, False)
                model = ChildStateOracle(
                    self.words, initial, False, phase).run()
                self.assertEqual(public(model.memory), public(wanted))
                self.assertEqual(model.calls, calls)
                self.assertEqual(model.r[29], STACK + phase)
                visits.update(model.visits)
                cases += 1
        for countdown, mode, player, count, timer, tick, replace_child, phase in itertools.product(
                (0, 1), (0, 1, 2), (0, 1), (0, 0xFFFE, 0xFFFF),
                (0, 1, -1, 32767), (0, 1, 30, -1), (0, 1), (0, 8)):
            initial = fixture(True, 0, countdown, mode, player, count,
                              timer, tick, phase)
            wanted, calls = reference(initial, replace_child)
            model = ChildStateOracle(
                self.words, initial, replace_child, phase).run()
            self.assertEqual(public(model.memory), public(wanted))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[29], STACK + phase)
            visits.update(model.visits)
            cases += 1
        missing = set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)) - visits
        self.assertEqual(missing, set())
        self.assertEqual(cases, 2308)

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
            "no-countdown": body.replace("actor[0x13A] = countdown - 1;", "actor[0x13A] = countdown;"),
            "wrong-marker": body.replace("actor[0x127] == 0xFF", "actor[0x127] == 0xFE"),
            "wrong-mode": body.replace("state[0] == 1", "state[0] == 2"),
            "wrong-player": body.replace("D_800C35EA != 1", "D_800C35EA != 0"),
            "wrong-count-cap": body.replace("0xFFFF - tick", "0xFFFE - tick"),
            "wrong-count-update": body.replace("count + tick", "count - tick"),
            "partial-reset": body.replace("state[0xD] = 0;", "state[0xD] = 1;"),
            "wrong-timer-test": body.replace("tick < timer", "tick <= timer"),
            "wrong-timer-update": body.replace("timer - tick", "timer + tick"),
            "no-reload": body.replace("child = *(u8 **)(actor + 0x31C);\n            *(s16 *)(child + 0x66) = 0;", "*(s16 *)(child + 0x66) = 0;"),
            "no-finish": body.replace("func_1507FC2C(actor);", "(void)actor;"),
        }
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            self.assertNotEqual(self.compile_native(changed, name, "-O2"), 0,
                                name)

    def test_04_guards_fail_closed_caller_registry_and_live_state(self):
        with (self.output / "proposed-guards.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        target = [row for row in rows if row["filename"] == match.FILENAME and
                  row["function"] == match.FUNCTION]
        self.assertEqual(len(target), 15)
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
                          if struct.unpack_from(">I", rom, offset)[0] == jal],
                         [0x50CD4, 0x7A50C])
        self.assertEqual([offset for offset in range(0, len(rom) - 3, 4)
                          if struct.unpack_from(">I", rom, offset)[0] == match.ENTRY],
                         [])
        self.assertEqual(struct.unpack_from(">3I", rom, 0x50CD4),
                         (jal, 0x02002025, 0xA21402FF))
        self.assertEqual(struct.unpack_from(">3I", rom, 0x7A50C),
                         (jal, 0x02002025, 0x0D412EE2))
        caller = (self.root / "conker/src/game/generated_49D30.c").read_text()
        self.assertIn("void func_1507FEA0(struct127 *);", caller)
        self.assertIn("func_1507FEA0(actor);", caller)
        layout = (self.root / "conker/retail_layout.us.txt").read_text()
        self.assertIn("game,game_77AD0,func_1504CB98,0x1504CB98,0x150511E8",
                      layout)
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
