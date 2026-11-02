"""Native32 semantic corpus and effective controls for the cleanup callback pair."""

from pathlib import Path
import subprocess

from tools.experiments import game_cleanup_pair_guard_match as source
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def controls(body, finalizer):
    other = "func_1513CAA0" if finalizer == "func_1513CA6C" else "func_1513CA6C"
    last = """    resource = *(void **)(state + 0x50);
    if (resource != NULL) {
        func_1516972C(resource);
    }
"""
    rows = {
        "wrong_first_slot": body.replace("owner + 0x13C", "owner + 0x144", 1),
        "missing_unregister": body.replace(
            "        func_1000FD38(func_151C87AC, state, 0);\n", "", 1),
        "wrong_release_order": body.replace("state + 0x38", "state + 0x58", 1)
                                    .replace("state + 0x3C", "state + 0x38", 1)
                                    .replace("state + 0x58", "state + 0x3C", 1),
        "wrong_finalizer": body.replace(finalizer + "(owner);", other + "(owner);", 1),
        "missing_final_slot": body.replace(last, "", 1),
        "unconditional_release": body.replace("    if (resource != NULL) {",
                                                "    if (1) {", 1),
        "stale_resource": body.replace(
            "    resource = *(void **)(state + 0x3C);",
            "    resource = *(void **)(state + 0x38);", 1),
        "wrong_state_base": body.replace("owner + 0x110", "owner + 0x114"),
    }
    if len(rows) != 8 or any(value == body for value in rows.values()):
        raise AssertionError("Ineffective cleanup-pair source control")
    return rows


def harness():
    selected = source.selected_bodies()
    variants = []
    declarations = []
    for index, (name, _, _, finalizer) in enumerate(source.TARGETS):
        bodies = [("selected", selected[name]), *controls(selected[name], finalizer).items()]
        for label, body in bodies:
            replacement = "root_%d_%s" % (index, label)
            declarations.append(body.replace(name, replacement, 1))
            variants.append((replacement, index, label))

    text = r'''#include <ultra64.h>
void func_1516972C(void *resource);
void func_151C87AC(void);
void func_1000FD38(void (*callback)(void), u8 *state, s32 zero);
void func_1513CA6C(u8 *owner);
void func_1513CAA0(u8 *owner);
''' + "\n".join(declarations) + r'''

typedef void (*Root)(u8 *owner);
typedef struct Call { u32 kind, a, b, c; } Call;
static u8 owner[0x180] __attribute__((aligned(16)));
static u8 expected_owner[0x180] __attribute__((aligned(16)));
static u32 resources[40] __attribute__((aligned(16)));
static const u32 offsets[] = {0x13C,0x144,0x148,0x14C,0x150,0x154,0x158,0x15C,0x160};
static Call calls[16], expected[16];
static u32 count, expected_count, mode, error;
static u8 *active_owner;

static void put(u8 *base, u32 offset, void *value) { *(void **)(base + offset) = value; }
static void *get(u8 *base, u32 offset) { return *(void **)(base + offset); }
static void mutate(u8 *base, u32 ordinal) {
    u32 index;
    if (mode == 1 && ordinal == 1) {
        for (index = 1; index < 9; index++) put(base, offsets[index], 0);
    } else if (mode == 2) {
        for (index = 1; index < 9; index++)
            put(base, offsets[index], &resources[(index + ordinal) % 40]);
    } else if (mode == 3) {
        for (index = 1; index < 9; index++)
            put(base, offsets[index], ((index + ordinal) & 1) ? 0 : &resources[index]);
    } else if (mode == 4) {
        index = 1 + ordinal % 8;
        put(base, offsets[index], ordinal & 1 ? 0 : &resources[24 + index]);
    }
}
static void append(Call *rows, u32 *used, u32 kind, u32 a, u32 b, u32 c) {
    if (*used >= 16) { error = 41; return; }
    rows[*used].kind = kind; rows[*used].a = a; rows[*used].b = b; rows[*used].c = c;
    (*used)++;
}
static void setup(u8 *base, u32 pattern) {
    u32 index;
    for (index = 0; index < sizeof(owner); index++) base[index] = 0;
    for (index = 0; index < 9; index++)
        put(base, offsets[index], pattern & (1u << index) ? &resources[index] : 0);
}
static void make_expected(u32 final_kind) {
    u32 index; void *resource;
    expected_count = 0;
    resource = get(expected_owner, offsets[0]);
    if (resource) {
        append(expected, &expected_count, 1, (u32)resource, 0, 0);
        mutate(expected_owner, expected_count);
        append(expected, &expected_count, 2, (u32)func_151C87AC,
               (u32)(expected_owner + 0x110), 0);
        mutate(expected_owner, expected_count);
    }
    for (index = 1; index < 9; index++) {
        resource = get(expected_owner, offsets[index]);
        if (resource) {
            append(expected, &expected_count, 1, (u32)resource, 0, 0);
            mutate(expected_owner, expected_count);
        }
    }
    append(expected, &expected_count, final_kind, (u32)expected_owner, 0, 0);
    mutate(expected_owner, expected_count);
}
void func_1516972C(void *resource) {
    append(calls, &count, 1, (u32)resource, 0, 0); mutate(active_owner, count);
}
void func_1000FD38(void (*callback)(void), u8 *state, s32 zero) {
    append(calls, &count, 2, (u32)callback, (u32)state, (u32)zero);
    mutate(active_owner, count);
}
void func_151C87AC(void) {}
void func_1513CA6C(u8 *value) {
    append(calls, &count, 3, (u32)value, 0, 0); mutate(active_owner, count);
}
void func_1513CAA0(u8 *value) {
    append(calls, &count, 4, (u32)value, 0, 0); mutate(active_owner, count);
}
static s32 same_call(const Call *left, const Call *right) {
    if (left->kind != right->kind) return 0;
    if (left->kind == 2) return left->a == right->a && left->c == right->c &&
        left->b - (u32)owner == right->b - (u32)expected_owner;
    if (left->kind == 3 || left->kind == 4)
        return left->b == right->b && left->c == right->c &&
            left->a - (u32)owner == right->a - (u32)expected_owner;
    return left->a == right->a && left->b == right->b && left->c == right->c;
}
static s32 check(Root root, u32 final_kind) {
    u32 pattern, index;
    for (pattern = 0; pattern < 512; pattern++) for (mode = 0; mode < 5; mode++) {
        error = 0; setup(expected_owner, pattern); make_expected(final_kind);
        setup(owner, pattern); active_owner = owner; count = 0; root(owner);
        if (error || count != expected_count) return 51;
        for (index = 0; index < count; index++)
            if (!same_call(&calls[index], &expected[index])) return 52;
    }
    return 0;
}
static s32 run(void) {
    if (sizeof(void *) != 4) return 61;
ROOT_ROWS
    return 0;
}
''' + START

    checks = []
    for name, index, label in variants:
        final_kind = 3 if index == 0 else 4
        if label == "selected":
            checks.append("    if (check(%s, %d)) return 70 + %d;" %
                          (name, final_kind, index))
        else:
            checks.append("    if (!check(%s, %d)) return 80 + %d;" %
                          (name, final_kind, len(checks)))
    return text.replace("ROOT_ROWS", "\n".join(checks)), len(variants), 512 * 5


def qualify(root, output):
    root, output = Path(root), Path(output)
    text, variants, cases = harness()
    unit = output / "native-cleanup-pair.c"
    unit.write_text(text)
    reports = []
    for profile in ("-O0", "-O2", "-O3"):
        executable = output / ("native-cleanup-pair-" + profile[1:])
        build = subprocess.run(
            native_command(profile) + ["-fno-strict-aliasing", str(unit),
                                       "-o", str(executable)],
            cwd=root, capture_output=True, text=True)
        if build.returncode:
            raise AssertionError((profile, build.stdout, build.stderr))
        run = subprocess.run([str(executable)], capture_output=True, timeout=60)
        if run.returncode:
            raise AssertionError((profile, run.returncode, run.stdout, run.stderr))
        reports.append({"profile": profile, "cases_per_variant": cases,
                        "variants": variants, "controls_per_function": 8,
                        "UBSan": True})
    return reports
