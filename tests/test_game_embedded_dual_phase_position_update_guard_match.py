"""Semantic, ABI, guarded-owner and full-image gates for func_151B1828."""

import itertools
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_embedded_dual_phase_position_update_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as match
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK, put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
HELPER = 0x151423D8
TICKS = 0x800BE9E4
STATE = 0x220000


def sample(angle, ordinal):
    """Return stable, exactly representable single-precision helper results."""
    return bits((signed(angle) - 128) * 0.03125 + ordinal * 0.125)


def operation(left, right, kind):
    left = floating(left)
    right = floating(right)
    if kind == "mul":
        return bits(left * right)
    if kind == "add":
        return bits(left + right)
    if kind == "sub":
        return bits(left - right)
    raise AssertionError(kind)


def eased(current, base, scale, result):
    target = operation(base, operation(scale, result, "mul"), "add")
    delta = operation(target, current, "sub")
    return operation(current, operation(delta, bits(0.5), "mul"), "add")


def effect(memory, mode, ordinal):
    """Model mutations performed by the two trigonometric callbacks."""
    if ordinal == 0:
        if mode & 1:
            memory[STATE + 0x121] = 0x91
        if mode & 2:
            put(memory, STATE + 0x124, bits(-7.5))
            put(memory, STATE + 0x12C, bits(3.25))
        if mode & 8:
            put(memory, TICKS, 0x87654321)
            memory[STATE + 0x122] = 0xA7
            memory[STATE + 0x123] = 0x39
    else:
        if mode & 4:
            put(memory, STATE + 0x2C, bits(11.5))
            put(memory, STATE + 0x30, bits(-13.25))
            put(memory, STATE + 0x128, bits(5.75))
            put(memory, STATE + 0x130, bits(-0.625))


def fixture(first_phase=17, second_phase=201, first_rate=3,
            second_rate=241, ticks=3, seed=0):
    memory = {STACK + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x500, 0x100)}
    memory.update({STATE + index: (index * 13 + seed * 29 + 0x59) & 0xFF
                   for index in range(-16, 0x160)})
    memory[STATE + 0x120] = first_phase
    memory[STATE + 0x121] = second_phase
    memory[STATE + 0x122] = first_rate
    memory[STATE + 0x123] = second_rate
    put(memory, STATE + 0x2C, bits((seed - 127) * 0.125))
    put(memory, STATE + 0x30, bits((seed - 101) * -0.0625))
    put(memory, STATE + 0x124, bits((seed - 91) * 0.25))
    put(memory, STATE + 0x128, bits((seed - 67) * -0.125))
    put(memory, STATE + 0x12C, bits((seed % 17 - 8) * 0.1875))
    put(memory, STATE + 0x130, bits((seed % 13 - 6) * -0.3125))
    put(memory, TICKS, ticks)
    return memory


def reference(initial, mode):
    memory = dict(initial)
    ticks = read(memory, TICKS)
    memory[STATE + 0x120] = (
        memory[STATE + 0x120] + signed(memory[STATE + 0x122]) * ticks) & 0xFF
    ticks = read(memory, TICKS)
    memory[STATE + 0x121] = (
        memory[STATE + 0x121] + signed(memory[STATE + 0x123]) * ticks) & 0xFF

    first_angle = (memory[STATE + 0x120] - 0x40) & 0xFF
    effect(memory, mode, 0)
    second_angle = (memory[STATE + 0x121] - 0x40) & 0xFF
    effect(memory, mode, 1)

    first = eased(read(memory, STATE + 0x2C),
                  read(memory, STATE + 0x124),
                  read(memory, STATE + 0x12C), sample(first_angle, 0))
    second = eased(read(memory, STATE + 0x30),
                   read(memory, STATE + 0x128),
                   read(memory, STATE + 0x130), sample(second_angle, 1))
    put(memory, STATE + 0x2C, first)
    put(memory, STATE + 0x30, second)
    return memory, [(HELPER, (first_angle,)), (HELPER, (second_angle,))]


def public(memory):
    return (bytes(memory[STATE + index] for index in range(0x148)),
            read(memory, TICKS))


class EmbeddedDualPhasePositionOracle(TimingOracle):
    def __init__(self, words, memory, mode=0, phase=0):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(STATE,))
        self.mode = mode
        self.ordinal = 0

    def execute(self, word):
        if word >> 26 == 32:  # lb
            base = word >> 21 & 31
            target = word >> 16 & 31
            immediate = ((word & 0xFFFF) ^ 0x8000) - 0x8000
            self.own_instruction = True
            try:
                value = self.get((self.r[base] + immediate) & 0xFFFFFFFF, 1)
                self.r[target] = ((value ^ 0x80) - 0x80) & 0xFFFFFFFF
                self.r[0] = 0
            finally:
                self.own_instruction = False
        else:
            super().execute(word)

    def record_call(self, target):
        if target != HELPER:
            raise AssertionError("Unexpected embedded dual-phase helper %08X" % target)
        args = self.arguments(1)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        if target != HELPER or self.ordinal >= 2:
            raise AssertionError("Unexpected embedded dual-phase helper hook %08X" % target)
        angle = self.calls[-1][1][0]
        effect(self.memory, self.mode, self.ordinal)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011
        self.f[0] = sample(angle, self.ordinal)
        self.ordinal += 1


def controls():
    body = candidate.SELECTED
    variants = {
        "wrong-second-rate": body.replace(
            "(s32)*(s8 *)(state + 0x123)", "(s32)*(s8 *)(state + 0x122)", 1),
        "wrong-first-phase": body.replace(
            "state[0x120] +=", "state[0x130] +=", 1),
        "wrong-second-phase": body.replace(
            "parameters[0x11]", "parameters[0x10]", 1),
        "wrong-angle": body.replace("- 0x40", "- 0x3F", 1),
        "missing-first-advance": body.replace(
            "    state[0x120] += (s32)*(s8 *)(state + 0x122) * (u32)D_800BE9E4;\n",
            "", 1),
        "wrong-first-base": body.replace(
            "parameters + 0x14", "parameters + 0x18", 1),
        "wrong-second-scale": body.replace(
            "parameters + 0x20", "parameters + 0x1C", 1),
        "swapped-samples": body.replace(
            "parameters + 0x1C) * firstSample",
            "parameters + 0x1C) * secondSample", 1).replace(
            "parameters + 0x20) * secondSample",
            "parameters + 0x20) * firstSample", 1),
        "missing-half": body.replace("* 0.5f", "* 1.0f", 1),
        "wrong-return": body.replace("    return 1;", "    return 0;", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("A embedded dual-phase semantic control did not alter the source")
    return variants


def native_harness(body):
    return "#include <ultra64.h>\n" + candidate.DECLARATIONS + body + r'''
typedef union { u32 align; u8 bytes[0x148]; } State;
static State state, expected;
static State *active;
static u8 wantedAngles[2];
static u32 mode, calls, error;
s32 D_800BE9E4;
static u32 word(f32 value) { union { u32 word; f32 value; } cast; cast.value = value; return cast.word; }
static void copy(void *out, const void *in, u32 size) {
    u32 index; for (index = 0; index < size; index++) ((u8 *)out)[index] = ((const u8 *)in)[index];
}
static int same(const void *left, const void *right, u32 size) {
    u32 index; for (index = 0; index < size; index++)
        if (((const u8 *)left)[index] != ((const u8 *)right)[index]) return 0;
    return 1;
}
static f32 getf(State *value, u32 offset) { return *(f32 *)(value->bytes + offset); }
static void setf(State *value, u32 offset, f32 number) { *(f32 *)(value->bytes + offset) = number; }
static f32 value(u8 angle, u32 ordinal) {
    return ((s32)angle - 128) * 0.03125f + ordinal * 0.125f;
}
static void effect(State *valueState, u32 ordinal, u32 live) {
    if (ordinal == 0) {
        if (mode & 1) valueState->bytes[0x121] = 0x91;
        if (mode & 2) { setf(valueState, 0x124, -7.5f); setf(valueState, 0x12C, 3.25f); }
        if (mode & 8) {
            valueState->bytes[0x122] = 0xA7; valueState->bytes[0x123] = 0x39;
            if (live) D_800BE9E4 = (s32)0x87654321u;
        }
    } else if (mode & 4) {
        setf(valueState, 0x2C, 11.5f); setf(valueState, 0x30, -13.25f);
        setf(valueState, 0x128, 5.75f); setf(valueState, 0x130, -0.625f);
    }
}
f32 func_151423D8(u8 angle) {
    u32 ordinal = calls;
    if (ordinal >= 2 || angle != wantedAngles[ordinal]) error = 1;
    effect(active, ordinal, 1); calls++;
    return value(angle, ordinal);
}
static int one(u32 seed, u32 rawTicks, u32 selectedMode) {
    u32 index, result, expectedClock = rawTicks;
    f32 target, current;
    mode = selectedMode;
    for (index = 0; index < sizeof(state); index++)
        state.bytes[index] = (u8)(index * 13u + seed * 29u + 0x59u);
    state.bytes[0x120] = (u8)seed;
    state.bytes[0x121] = (u8)(seed * 17u + 3u);
    state.bytes[0x122] = (u8)(seed * 7u + 1u);
    state.bytes[0x123] = (u8)(seed * 11u + 3u);
    setf(&state, 0x2C, ((s32)seed - 127) * 0.125f);
    setf(&state, 0x30, ((s32)seed - 101) * -0.0625f);
    setf(&state, 0x124, ((s32)seed - 91) * 0.25f);
    setf(&state, 0x128, ((s32)seed - 67) * -0.125f);
    setf(&state, 0x12C, ((s32)(seed % 17u) - 8) * 0.1875f);
    setf(&state, 0x130, ((s32)(seed % 13u) - 6) * -0.3125f);
    copy(&expected, &state, sizeof(state));
    expected.bytes[0x120] = (u8)(expected.bytes[0x120] +
        (s32)(s8)expected.bytes[0x122] * rawTicks);
    expected.bytes[0x121] = (u8)(expected.bytes[0x121] +
        (s32)(s8)expected.bytes[0x123] * rawTicks);
    wantedAngles[0] = (u8)(expected.bytes[0x120] - 0x40);
    effect(&expected, 0, 0);
    wantedAngles[1] = (u8)(expected.bytes[0x121] - 0x40);
    effect(&expected, 1, 0);
    target = getf(&expected, 0x124) + getf(&expected, 0x12C) * value(wantedAngles[0], 0);
    current = getf(&expected, 0x2C);
    setf(&expected, 0x2C, (target - current) * 0.5f + current);
    target = getf(&expected, 0x128) + getf(&expected, 0x130) * value(wantedAngles[1], 1);
    current = getf(&expected, 0x30);
    setf(&expected, 0x30, (target - current) * 0.5f + current);
    if (mode & 8) expectedClock = 0x87654321u;
    D_800BE9E4 = (s32)rawTicks; active = &state; calls = error = 0;
    result = (u32)func_151B1828(state.bytes);
    if (error || calls != 2) return 10;
    if (result != 1) return 11;
    if (!same(&state, &expected, sizeof(state))) return 12;
    if ((u32)D_800BE9E4 != expectedClock) return 13;
    if (word(getf(&state, 0x2C)) != word(getf(&expected, 0x2C)) ||
        word(getf(&state, 0x30)) != word(getf(&expected, 0x30))) return 14;
    return 0;
}
static int run(void) {
    static const u32 ticks[] = {0, 1, 7, 0x7FFFFFFFu, 0x80000000u, 0xFFFFFFFFu};
    u32 seed, tick, selectedMode;
    if (sizeof(void *) != 4 || sizeof(f32) != 4 || sizeof(State) != 0x148) return 29;
    for (seed = 0; seed < 64; seed++) for (tick = 0; tick < 6; tick++)
        for (selectedMode = 0; selectedMode < 16; selectedMode++) {
            int code = one(seed, ticks[tick], selectedMode);
            if (code) return code;
        }
    return 0;
}
''' + START


class GameEmbeddedDualPhasePositionUpdateGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = match.prepare(ROOT)
        cls.report = cls.state["report"]
        retail = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.words = struct.unpack_from(
            ">%dI" % match.WORDS, retail, match.ROM)
        cls.fresh = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.fresh.mkdir(exist_ok=False)

    def test_01_guarded_owner_image_registry_and_stale_rows(self):
        self.assertEqual(
            (self.report["words"], self.report["natural_frame"],
             self.report["retail_frame"],
             self.report["natural_positional_differences"],
             self.report["guards"], self.report["relocations"],
             self.report["neighbors"]),
            (60, 0x20, 0x30, 9, 9, 4, 15))
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(self.report["functions"], 6051)
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        self.assertEqual(
            self.report["registry"],
            {"direct_jal_calls": [],
             "aligned_pointer_literals": ["0x22e7bc"],
             "registry": "D_80089CB8[17]",
             "abi": "one state pointer; callback returns one after updating both planar coordinates"})
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))

        target_indices = [
            index for index, row in enumerate(self.state["qualified_rows"])
            if row["filename"] == match.FILENAME and
            row["function"] == match.FUNCTION
        ]
        self.assertEqual(len(target_indices), 9)
        for sequence, index in enumerate(target_indices):
            stale = [dict(row) for row in self.state["qualified_rows"]]
            stale[index]["expected"] = "0xDEADBEEF"
            path = self.fresh / ("stale-%d.csv" % sequence)
            match.write_patches(path, self.state["fields"], stale)
            with self.assertRaisesRegex(ValueError, "stale .*word patch"):
                emit_padded_assembly(
                    self.state["qualified_compact"], ROOT / match.ASM,
                    word_patches_path=path, filename=match.FILENAME)

    def test_02_guest_signed_rates_wrapping_callbacks_and_word_coverage(self):
        coverage = set()
        cases = 0

        def check(initial, mode, phase=0):
            nonlocal cases
            wanted, calls = reference(initial, mode)
            model = EmbeddedDualPhasePositionOracle(
                self.words, initial, mode=mode, phase=phase).run()
            self.assertEqual(model.r[2], 1)
            self.assertEqual(model.calls, calls)
            self.assertEqual(public(model.memory), public(wanted))
            coverage.update(pc for pc in model.visits
                            if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            cases += 1

        for ordinal, values in enumerate(itertools.product(
                (0, 63, 64, 127, 128, 191, 192, 255),
                ((0, 0), (1, 255), (128, 17)),
                (0, 1, 7, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF),
                (0, 1, 2, 4, 8, 15), (0, 8))):
            first, rates, ticks, mode, phase = values
            check(fixture(first, (first * 17 + 3) & 0xFF,
                          rates[0], rates[1], ticks, ordinal & 0xFF),
                  mode, phase)

        for byte in range(256):
            check(fixture(first_phase=byte, seed=byte), byte & 15)
            check(fixture(second_phase=byte, seed=byte), byte & 15)
            check(fixture(first_rate=byte, seed=byte), byte & 15)
            check(fixture(second_rate=byte, seed=byte), byte & 15)

        self.assertEqual(
            coverage, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.assertEqual(cases, 2752)

    def test_03_native32_profiles_and_effective_controls(self):
        selected = self.fresh / "native-selected.c"
        selected.write_text(native_harness(candidate.SELECTED))
        for profile in ("-O0", "-O2", "-O3"):
            target = self.fresh / ("native-selected" + profile)
            build = subprocess.run(
                native_command(profile) + ["-mstackrealign", "-fno-strict-aliasing",
                                           str(selected), "-o", str(target)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(target)], capture_output=True, timeout=60)
            self.assertEqual(run.returncode, 0, (profile, run.stdout, run.stderr))

        effective = []
        for name, body in controls().items():
            source = self.fresh / ("control-" + name + ".c")
            target = self.fresh / ("control-" + name)
            source.write_text(native_harness(body))
            build = subprocess.run(
                native_command("-O2") + ["-mstackrealign", "-fno-strict-aliasing",
                                          str(source), "-o", str(target)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, (name, build.stdout, build.stderr))
            run = subprocess.run([str(target)], capture_output=True, timeout=60)
            self.assertNotEqual(run.returncode, 0, name)
            effective.append(name)
        self.assertEqual(len(effective), 10)


if __name__ == "__main__":
    unittest.main()

