"""Native 32-bit semantic controls for func_1509D08C."""

from pathlib import Path
import subprocess

from tools.experiments.game_dependency_record_status_candidates import selected_body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def renamed(name, edits=()):
    body = selected_body().replace("func_1509D08C", name, 1)
    for old, new in edits:
        if body.count(old) != 1:
            raise ValueError("Ambiguous native control edit for %s: %r" % (name, old))
        body = body.replace(old, new, 1)
    return body


def variants():
    reloads = "        record = *(u8 **)(entry + 8);\n"
    return (
        ("selected", renamed("selected"), True),
        ("wrong_base_return", renamed("wrong_base_return",
            (("        return 0;\n    }\n\n    record =", "        return 1;\n    }\n\n    record ="),)), False),
        ("wrong_record_return", renamed("wrong_record_return",
            (("        return 0;\n    }\n\n    if (first", "        return 1;\n    }\n\n    if (first"),)), False),
        ("wrong_default", renamed("wrong_default",
            (("if (base == NULL) {\n        if (first != NULL) {\n            *first = 0xBF;",
              "if (base == NULL) {\n        if (first != NULL) {\n            *first = 0xBE;"),)), False),
        ("wrong_first_value", renamed("wrong_first_value",
            (("        *first = **(s16 **)(record + 8);",
              "        *first = 0;"),)), False),
        ("wrong_second_value", renamed("wrong_second_value",
            (("        *second = **(s16 **)record;",
              "        *second = 0;"),)), False),
        ("wrong_byte", renamed("wrong_byte",
            (("resource >> 3", "resource >> 4"),)), False),
        ("wrong_mask", renamed("wrong_mask",
            (("resource & 7", "resource & 6"),)), False),
        ("zero_count_failure", renamed("zero_count_failure",
            (("    return 1;\n}", "    return count != 0;\n}"),)), False),
    )


def harness():
    rows = variants()
    bodies = "\n\n".join(body for _, body, _ in rows)
    text = r'''
typedef signed int s32; typedef unsigned int u32; typedef signed short s16;
typedef unsigned short u16; typedef unsigned char u8;
#define NULL ((void *)0)
u8 *D_800D2FB0; u8 *D_800D2E4C;
FUNCTIONS
typedef s32 (*Query)(s32, s32, s32 *, s32 *);
typedef struct { s16 *second; u32 pad; s16 *deps; u32 count; } Record;
static void *entries[5]; static Record row; static s16 second_value;
static s16 deps[8]; static u8 bits[64];
static void clear(void *p, u32 n) { u8 *q = p; while (n--) *q++ = 0; }
static s32 reference(s32 index, s32 *first, s32 *second) {
    u8 *base = D_800D2FB0; u8 *entry = base + index * 8; Record *record;
    u32 position;
    if (!base) { if (first) *first = 0xBF; if (second) *second = 0; return 0; }
    record = *(Record **)(entry + 8);
    if (!record) { if (first) *first = 0xBF; if (second) *second = 0; return 0; }
    if (first) *first = *record->deps;
    if (second) *second = *record->second;
    for (position = 0; position < record->count; position++) {
        s32 resource = record->deps[position];
        if (!(D_800D2E4C[resource >> 3] & (1 << (resource & 7)))) return 0;
    }
    return 1;
}
static void setup(s32 mode, u32 count, s32 inactive) {
    u32 i; clear(entries, sizeof(entries)); clear(bits, sizeof(bits));
    second_value = -2; row.second = &second_value; row.pad = 0xA5A5A5A5;
    row.deps = deps; row.count = count;
    deps[0] = -1; deps[1] = 0; deps[2] = 1; deps[3] = 7;
    deps[4] = 8; deps[5] = 15; deps[6] = 31; deps[7] = 63;
    D_800D2E4C = bits + 8;
    for (i = 0; i < count; i++) {
        s32 value = deps[i]; D_800D2E4C[value >> 3] |= 1 << (value & 7);
    }
    if (inactive >= 0) {
        s32 value = deps[inactive]; D_800D2E4C[value >> 3] &= ~(1 << (value & 7));
    }
    D_800D2FB0 = mode == 0 ? NULL : (u8 *)entries;
    entries[4] = mode == 1 ? NULL : &row;
}
static s32 check(Query query) {
    s32 mode, outputs, inactive; u32 count;
    for (mode = 0; mode < 3; mode++) for (count = 0; count <= 8; count++)
    for (inactive = -1; inactive < (s32)count; inactive++) for (outputs = 0; outputs < 4; outputs++) {
        s32 a = 0x11111111, b = 0x22222222, x = a, y = b;
        s32 *ap = outputs & 1 ? &a : NULL, *bp = outputs & 2 ? &b : NULL;
        s32 *xp = outputs & 1 ? &x : NULL, *yp = outputs & 2 ? &y : NULL;
        s32 expected, actual;
        setup(mode, count, inactive); expected = reference(1, xp, yp);
        setup(mode, count, inactive); actual = query(-7, 1, ap, bp);
        if (actual != expected || a != x || b != y) return 0;
    }
    return 1;
}
static s32 run(void) {
    if (sizeof(void *) != 4 || sizeof(Record) != 16) return 61;
CHECKS
    return 0;
}
''' + START
    checks = []
    for index, (name, _, selected) in enumerate(rows):
        checks.append("    if (%scheck(%s)) return %d;" %
                      ("!" if selected else "", name, 70 + index))
    return (text.replace("FUNCTIONS", bodies).replace("CHECKS", "\n".join(checks)),
            len(rows))


def qualify(root, output):
    root, output = Path(root), Path(output)
    text, count = harness()
    unit = output / "native-dependency-record-status.c"
    unit.write_text(text)
    reports = []
    for profile in ("-O0", "-O2", "-O3"):
        executable = output / ("native-dependency-record-status-" + profile[1:])
        build = subprocess.run(native_command(profile) + ["-fno-strict-aliasing",
                               str(unit), "-o", str(executable)], cwd=root,
                               capture_output=True, text=True)
        if build.returncode:
            raise AssertionError((profile, build.stdout, build.stderr))
        run = subprocess.run([str(executable)], capture_output=True, timeout=60)
        if run.returncode:
            raise AssertionError((profile, run.returncode, run.stdout, run.stderr))
        reports.append({"profile": profile, "variants": count,
                        "controls": count - 1, "UBSan": True})
    return reports
