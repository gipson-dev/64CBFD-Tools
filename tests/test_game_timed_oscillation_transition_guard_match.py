"""Semantic, guarded-owner and full-image gates for func_151B9214."""

import itertools
import os
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_timed_oscillation_transition_candidates as candidate
from tools.experiments import game_timed_oscillation_transition_match as match
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK, put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
WRAP = 0x15144B68
SINE = 0x15047D60
TICKS = 0x800BE9A4
SCALE = 0x800AA564
OWNER = 0x220000
STATE = OWNER + 0x170


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


def wrap_result(seed):
    return bits((seed % 9 - 4) * 0.25)


def sine_result(seed):
    return bits((seed % 7 - 3) * 0.125)


def fixture(seed=0, active=True):
    memory = {STACK + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x500, 0x100)}
    memory.update({OWNER + index: (index * 13 + seed * 29 + 0x59) & 0xFF
                   for index in range(-16, 0x1B0)})
    values = (
        99.0,
        (seed % 11 + 1) * 0.25,
        (seed % 13 - 6) * 0.125,
        (seed % 9 - 4) * 0.0625,
        (seed % 7 + 1) * 0.375,
        (seed % 5 - 2) * 0.1875,
        (seed % 5 + 1) * 0.5 if active else -(seed % 3) * 0.5,
        (seed % 7 - 3) * 0.03125,
        (seed % 11 - 5) * 0.015625,
    )
    for index, value in enumerate(values):
        put(memory, STATE + index * 4, bits(value))
    put(memory, TICKS, bits((0.25, 0.5, 1.0, 2.0)[seed & 3]))
    put(memory, SCALE, bits((0.125, 0.25, 0.5)[seed % 3]))
    return memory


def effect(memory, seed, mode, ordinal):
    if ordinal == 0:
        if mode & 1:
            put(memory, TICKS, bits(0.75))
        if mode & 2:
            put(memory, STATE + 0x04, bits(2.25))
            put(memory, STATE + 0x18, bits(1.5))
    else:
        if mode & 4:
            put(memory, STATE + 0x04, bits(-1.75))
            put(memory, STATE + 0x18, bits(-0.5))
        if mode & 8:
            put(memory, TICKS, bits(0.125))
            put(memory, SCALE, bits(0.375))
            put(memory, STATE + 0x10, bits(3.5))
            put(memory, STATE + 0x14, bits(-0.625))
            put(memory, STATE + 0x1C, bits(0.09375))
            put(memory, STATE + 0x20, bits(-0.046875))


def reference(initial, seed, mode):
    memory = dict(initial)
    phase = operation(read(memory, STATE + 0x08),
                      operation(read(memory, STATE + 0x0C),
                                read(memory, TICKS), "mul"), "add")
    put(memory, STATE + 0x08, phase)
    effect(memory, seed, mode, 0)
    wrapped = wrap_result(seed)
    put(memory, STATE + 0x08, wrapped)
    effect(memory, seed, mode, 1)
    sine = sine_result(seed)
    amplitude = read(memory, STATE + 0x04)
    transition = read(memory, STATE + 0x18)
    put(memory, STATE + 0x00, operation(sine, amplitude, "mul"))
    if floating(transition) > 0.0:
        put(memory, STATE + 0x18,
            operation(transition, read(memory, TICKS), "sub"))
        put(memory, STATE + 0x0C,
            operation(read(memory, STATE + 0x0C),
                      operation(read(memory, STATE + 0x20),
                                read(memory, TICKS), "mul"), "add"))
        put(memory, STATE + 0x04,
            operation(amplitude,
                      operation(read(memory, STATE + 0x1C),
                                read(memory, TICKS), "mul"), "add"))
    else:
        scale = read(memory, SCALE)
        put(memory, STATE + 0x0C,
            operation(read(memory, STATE + 0x0C),
                      operation(operation(read(memory, STATE + 0x14),
                                          read(memory, STATE + 0x0C), "sub"),
                                scale, "mul"), "add"))
        put(memory, STATE + 0x04,
            operation(amplitude,
                      operation(operation(read(memory, STATE + 0x10),
                                          amplitude, "sub"),
                                scale, "mul"), "add"))
    return memory, [(WRAP, phase), (SINE, wrapped)]


def public(memory):
    return (bytes(memory[OWNER + index] for index in range(0x1A0)),
            read(memory, TICKS), read(memory, SCALE))


class TimedOscillationOracle(TimingOracle):
    def __init__(self, words, memory, seed, mode=0, phase=0):
        super().__init__(words, memory, phase=phase, entry=match.ENTRY,
                         arguments=(OWNER,))
        self.seed = seed
        self.mode = mode
        self.ordinal = 0

    def record_call(self, target):
        if target not in (WRAP, SINE):
            raise AssertionError("Unexpected timed-oscillation helper %08X" % target)
        argument = self.f[12]
        self.calls.append((target, argument))
        self.events.append(("CALL", target, argument))

    def hook(self, target):
        expected = WRAP if self.ordinal == 0 else SINE
        if target != expected or self.ordinal >= 2:
            raise AssertionError("Unexpected timed-oscillation hook %08X" % target)
        effect(self.memory, self.seed, self.mode, self.ordinal)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011
        self.f[0] = wrap_result(self.seed) if self.ordinal == 0 else sine_result(self.seed)
        self.ordinal += 1


def controls():
    body = candidate.SELECTED_GUARDED
    variants = {
        "wrong-phase-rate": body.replace(
            "state->phaseRate * D_800BE9A4", "state->amplitude * D_800BE9A4", 1),
        "lost-wrap-result": body.replace(
            "state->phase = func_15144B68(state->phase);",
            "func_15144B68(state->phase);", 1),
        "wrong-oscillation-amplitude": body.replace(
            "sinf(state->phase) * state->amplitude",
            "sinf(state->phase) * state->phaseRate", 1),
        "inverted-transition-route": body.replace(
            "0.0f < state->transitionTime", "0.0f >= state->transitionTime", 1),
        "missing-transition-decrement": body.replace(
            "        state->transitionTime -= D_800BE9A4;\n", "", 1),
        "wrong-phase-velocity": body.replace(
            "state->phaseRateVelocity * D_800BE9A4",
            "state->amplitudeVelocity * D_800BE9A4", 1),
        "wrong-amplitude-velocity": body.replace(
            "state->amplitudeVelocity * D_800BE9A4",
            "state->phaseRateVelocity * D_800BE9A4", 1),
        "wrong-target-phase-rate": body.replace(
            "state->targetPhaseRate - state->phaseRate",
            "state->targetAmplitude - state->phaseRate", 1),
        "wrong-target-amplitude": body.replace(
            "state->targetAmplitude - state->amplitude",
            "state->targetPhaseRate - state->amplitude", 1),
        "wrong-return": body.replace("    return 1;", "    return 0;", 1),
    }
    if any(value == body for value in variants.values()):
        raise AssertionError("A timed-oscillation semantic control did not alter the source")
    return variants


def native_harness(body):
    return r'''typedef unsigned char u8;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
''' + candidate.TYPES + r'''
typedef union { u32 align; u8 bytes[0x1A0]; } Owner;
typedef char state_size[sizeof(TimedOscillationTransition151B9214) == 0x24 ? 1 : -1];
typedef char phase_offset[__builtin_offsetof(TimedOscillationTransition151B9214, phase) == 8 ? 1 : -1];
typedef char timer_offset[__builtin_offsetof(TimedOscillationTransition151B9214, transitionTime) == 0x18 ? 1 : -1];
static Owner owner, expected;
static u32 wrapWord, sineWord, wrapArgument, sineArgument, calls;
f32 D_800BE9A4, D_800AA564;
static f32 number(u32 word) { union { u32 word; f32 value; } cast; cast.word = word; return cast.value; }
static u32 word(f32 value) { union { u32 word; f32 value; } cast; cast.value = value; return cast.word; }
static void copy(void *out, const void *in, u32 size) {
    u32 index; for (index = 0; index < size; index++) ((u8 *)out)[index] = ((const u8 *)in)[index];
}
static int same(const void *left, const void *right, u32 size) {
    u32 index; for (index = 0; index < size; index++)
        if (((const u8 *)left)[index] != ((const u8 *)right)[index]) return 0;
    return 1;
}
__attribute__((noinline)) f32 func_15144B68(f32 value) {
    if (calls++ != 0) return number(0x7FC00000u); wrapArgument = word(value); return number(wrapWord);
}
__attribute__((noinline)) f32 sinf(f32 value) {
    if (calls++ != 1) return number(0x7FC00000u); sineArgument = word(value); return number(sineWord);
}
''' + body + r'''
static int one(u32 seed, u32 active) {
    TimedOscillationTransition151B9214 *actualState;
    TimedOscillationTransition151B9214 *wanted;
    f32 tick, scale, phase;
    u32 index, result;
    for (index = 0; index < sizeof(owner); index++) owner.bytes[index] = (u8)(index * 13u + seed * 29u + 0x59u);
    actualState = (TimedOscillationTransition151B9214 *)(owner.bytes + 0x170);
    actualState->oscillation = 99.0f;
    actualState->amplitude = (seed % 11u + 1u) * 0.25f;
    actualState->phase = ((s32)(seed % 13u) - 6) * 0.125f;
    actualState->phaseRate = ((s32)(seed % 9u) - 4) * 0.0625f;
    actualState->targetAmplitude = (seed % 7u + 1u) * 0.375f;
    actualState->targetPhaseRate = ((s32)(seed % 5u) - 2) * 0.1875f;
    actualState->transitionTime = active ? (seed % 5u + 1u) * 0.5f : -((s32)(seed % 3u)) * 0.5f;
    actualState->amplitudeVelocity = ((s32)(seed % 7u) - 3) * 0.03125f;
    actualState->phaseRateVelocity = ((s32)(seed % 11u) - 5) * 0.015625f;
    tick = (0.25f * (1u << (seed & 3u)));
    scale = (seed % 3u == 0u) ? 0.125f : (seed % 3u == 1u) ? 0.25f : 0.5f;
    wrapWord = word(((s32)(seed % 9u) - 4) * 0.25f);
    sineWord = word(((s32)(seed % 7u) - 3) * 0.125f);
    copy(&expected, &owner, sizeof(owner));
    wanted = (TimedOscillationTransition151B9214 *)(expected.bytes + 0x170);
    phase = wanted->phase + wanted->phaseRate * tick;
    wanted->phase = number(wrapWord);
    wanted->oscillation = number(sineWord) * wanted->amplitude;
    if (0.0f < wanted->transitionTime) {
        wanted->transitionTime -= tick;
        wanted->phaseRate += wanted->phaseRateVelocity * tick;
        wanted->amplitude += wanted->amplitudeVelocity * tick;
    } else {
        wanted->phaseRate += (wanted->targetPhaseRate - wanted->phaseRate) * scale;
        wanted->amplitude += (wanted->targetAmplitude - wanted->amplitude) * scale;
    }
    D_800BE9A4 = tick; D_800AA564 = scale; calls = 0; wrapArgument = sineArgument = 0;
    result = (u32)func_151B9214(owner.bytes);
    if (result != 1 || calls != 2 || wrapArgument != word(phase) || sineArgument != wrapWord) return 10;
    if (!same(&owner, &expected, sizeof(owner))) return 11;
    return 0;
}
static int run(void) {
    u32 seed, active;
    if (sizeof(void *) != 4 || sizeof(f32) != 4 || sizeof(Owner) != 0x1A0) return 29;
    for (seed = 0; seed < 128; seed++) for (active = 0; active < 2; active++) {
        int code = one(seed, active); if (code) return code;
    }
    return 0;
}
''' + START


class GameTimedOscillationTransitionGuardMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = match.prepare(ROOT)
        cls.report = cls.state["report"]
        retail = (ROOT / match.ROM_IMAGE).read_bytes()
        cls.words = struct.unpack_from(">%dI" % match.WORDS, retail, match.ROM)
        cls.fresh = ROOT / match.BUILD / ("test-run-" + str(os.getpid()))
        cls.fresh.mkdir(exist_ok=False)

    def test_01_guarded_owner_image_registry_and_stale_rows(self):
        self.assertEqual(
            (self.report["words"], self.report["natural_frame"],
             self.report["retail_frame"],
             self.report["natural_positional_differences"],
             self.report["guards"], self.report["relocations"],
             self.report["neighbors"]),
            (63, 0x28, 0x20, 20, 20, 8, 4))
        self.assertEqual(self.report["changed_bodies"], [match.FUNCTION])
        self.assertEqual(self.report["functions"], 6051)
        self.assertTrue(self.report["all_addresses_fixed"])
        self.assertEqual(self.report["strict_exclusions"], 0)
        self.assertEqual(
            self.report["registry"],
            {"direct_jal_calls": [],
             "aligned_pointer_literals": ["0x22e394"],
             "registry": "D_800898B0[9]",
             "abi": "one owner pointer; callback returns one after updating the embedded oscillator"})
        data = self.report["game_data"]
        self.assertEqual((data["exact"], data["bytes"], data["owner_count"],
                          data["different_bytes"]), (True, 189088, 720, 0))

        target_indices = [
            index for index, row in enumerate(self.state["qualified_rows"])
            if row["filename"] == match.FILENAME and row["function"] == match.FUNCTION
        ]
        self.assertEqual(len(target_indices), 20)
        for sequence, index in enumerate(target_indices):
            stale = [dict(row) for row in self.state["qualified_rows"]]
            stale[index]["expected"] = "0xDEADBEEF"
            path = self.fresh / ("stale-%d.csv" % sequence)
            harness.write_patches(path, self.state["fields"], stale)
            with self.assertRaisesRegex(ValueError, "stale .*word patch"):
                emit_padded_assembly(
                    self.state["qualified_compact"], ROOT / match.ASM,
                    word_patches_path=path, filename=match.FILENAME)

    def test_02_guest_live_callbacks_both_routes_and_word_coverage(self):
        coverage = set()
        cases = 0
        for seed, active, mode, phase in itertools.product(
                range(32), (False, True), range(16), (0, 8)):
            initial = fixture(seed, active)
            wanted, calls = reference(initial, seed, mode)
            model = TimedOscillationOracle(
                self.words, initial, seed, mode=mode, phase=phase).run()
            self.assertEqual(model.r[2], 1)
            self.assertEqual(model.calls, calls)
            self.assertEqual(public(model.memory), public(wanted))
            coverage.update(pc for pc in model.visits
                            if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            cases += 1
        self.assertEqual(coverage, set(range(match.ENTRY, match.ENTRY + match.SIZE, 4)))
        self.assertEqual(cases, 2048)

    def test_03_native32_profiles_and_effective_controls(self):
        selected = self.fresh / "native-selected.c"
        selected.write_text(native_harness(candidate.SELECTED_GUARDED))
        for profile in ("-O0", "-O2", "-O3"):
            target = self.fresh / ("native-selected" + profile)
            build = subprocess.run(
                native_command(profile) + ["-mstackrealign", "-fno-strict-aliasing",
                                           "-ffp-contract=off", str(selected), "-o", str(target)],
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
                                          "-ffp-contract=off", str(source), "-o", str(target)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, (name, build.stdout, build.stderr))
            run = subprocess.run([str(target)], capture_output=True, timeout=60)
            self.assertNotEqual(run.returncode, 0, name)
            effective.append(name)
        self.assertEqual(len(effective), 10)


if __name__ == "__main__":
    unittest.main()
