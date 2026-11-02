"""Native32 semantic corpus and effective controls for func_150DFCA8."""

from pathlib import Path
import subprocess

from tools.experiments import game_motion_target_clamp_guard_match as source
from tools.tests import game_motion_target_clamp_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def controls():
    body = source.BODY
    upward = """        if (target < state->velocity) {
            state->velocity = target;
        }
"""
    downward = """        if (state->velocity < target) {
            state->velocity = target;
        }
"""
    rows = {
        "low_threshold": body.replace("state->position < 11.0f",
                                       "state->position < 12.0f"),
        "high_threshold": body.replace("55.0f < state->position",
                                        "56.0f < state->position"),
        "low_target": body.replace("target = D_800A0FA0;",
                                    "target = D_800A0FA4;", 1),
        "high_sign": body.replace("target = -D_800A0FA4;",
                                   "target = D_800A0FA4;"),
        "missing_ticks": body.replace(
            "state->velocity * (f32)D_800BE9E4", "state->velocity"),
        "upward_step": body.replace("state->velocity += D_800A0FA8;",
                                     "state->velocity += D_800A0FAC;"),
        "no_upward_clamp": body.replace(upward, ""),
        "downward_step": body.replace("state->velocity -= D_800A0FAC;",
                                       "state->velocity -= D_800A0FA8;"),
        "no_downward_clamp": body.replace(downward, ""),
    }
    if len(rows) != 9 or any(value == body for value in rows.values()):
        raise AssertionError("Ineffective motion-target source control")
    return rows


def harness():
    rows = []
    selected_cases = [case for case in oracle.cases() if case.state == oracle.STATE]
    for case in selected_cases:
        initial = oracle.fixture(case)
        expected = oracle.reference(initial, case)
        values = oracle.result_words(expected, case)
        fields = (case.position, case.velocity, case.target, oracle.u32(case.ticks),
                  *case.constants, *values)
        rows.append("{" + ",".join("0x%08Xu" % value for value in fields) + "}")

    body = source.BODY
    variants = [("selected", body), *controls().items()]
    text = """#include <ultra64.h>
%s
f32 D_800A0FA0, D_800A0FA4, D_800A0FA8, D_800A0FAC;
s32 D_800BE9E4;
""" % source.TYPE
    for name, variant in variants:
        text += variant.replace(source.FUNCTION, "root_" + name) + "\n"
    text += """
typedef void (*Root)(MotionTargetState150DFCA8 *);
static Root roots[] = {%s};
typedef struct Fixture {
    u32 position, velocity, target, ticks;
    u32 low, high, upward, downward;
    u32 expectedPosition, expectedVelocity, expectedTarget;
} Fixture;
static const Fixture fixtures[] = {
%s
};
static f32 from_bits(u32 word) { union { u32 word; f32 value; } item; item.word = word; return item.value; }
static u32 to_bits(f32 value) { union { u32 word; f32 value; } item; item.value = value; return item.word; }
static s32 nan_bits(u32 word) { return (word & 0x7F800000u) == 0x7F800000u && (word & 0x7FFFFFu) != 0; }
static s32 same(u32 actual, u32 expected) { return actual == expected || (nan_bits(actual) && nan_bits(expected)); }
static s32 check(Root root) {
    u32 index, byte;
    MotionTargetState150DFCA8 state;
    const Fixture *fixture;
    for (index = 0; index < sizeof(fixtures) / sizeof(fixtures[0]); index++) {
        fixture = &fixtures[index];
        for (byte = 0; byte < sizeof(state); byte++) ((u8 *)&state)[byte] = (u8)(byte * 29 + index * 11 + 0x5A);
        state.position = from_bits(fixture->position);
        state.velocity = from_bits(fixture->velocity);
        state.targetVelocity = from_bits(fixture->target);
        D_800BE9E4 = (s32)fixture->ticks;
        D_800A0FA0 = from_bits(fixture->low);
        D_800A0FA4 = from_bits(fixture->high);
        D_800A0FA8 = from_bits(fixture->upward);
        D_800A0FAC = from_bits(fixture->downward);
        root(&state);
        if (!same(to_bits(state.position), fixture->expectedPosition) ||
            !same(to_bits(state.velocity), fixture->expectedVelocity) ||
            !same(to_bits(state.targetVelocity), fixture->expectedTarget)) return 1;
    }
    return 0;
}
static int run(void) {
    u32 index;
    if (sizeof(void *) != 4 || check(roots[0])) return 90;
    for (index = 1; index < sizeof(roots) / sizeof(roots[0]); index++) {
        if (!check(roots[index])) return 90 + index;
    }
    return 0;
}
%s
""" % (", ".join("root_" + name for name, _ in variants),
       ",\n".join(rows),
       START.replace("void _start(void)",
                     "__attribute__((force_align_arg_pointer)) void _start(void)"))
    return text, len(selected_cases), tuple(controls())


def qualify(root, output):
    root = Path(root)
    output = Path(output)
    text, cases, names = harness()
    unit = output / "native-motion-target.c"
    unit.write_text(text)
    reports = []
    for profile in ("-O0", "-O2", "-O3"):
        executable = output / ("native-motion-target-" + profile[1:])
        build = subprocess.run(
            native_command(profile) + ["-fno-strict-aliasing", "-ffp-contract=off",
                                       str(unit), "-o", str(executable)],
            cwd=root, capture_output=True, text=True)
        if build.returncode:
            raise AssertionError((profile, build.stdout, build.stderr))
        run = subprocess.run([str(executable)], capture_output=True, timeout=60)
        if run.returncode:
            raise AssertionError((profile, run.returncode, run.stdout, run.stderr))
        reports.append({
            "profile": profile,
            "cases": cases,
            "executions": cases * (len(names) + 1),
            "controls": list(names),
            "UBSan": True,
            "NaN_payload_equivalence_only": True,
        })
    return reports
