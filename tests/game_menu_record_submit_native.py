"""Native 32-bit semantics and effective controls for func_151E2404."""

from pathlib import Path
import subprocess

from tools.experiments.game_menu_record_submit_candidates import selected_body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def renamed(name, edits=()):
    body = selected_body().replace("func_151E2404", name, 1)
    for old, new in edits:
        if body.count(old) != 1:
            raise ValueError("Ambiguous menu-record control edit: %r" % (old,))
        body = body.replace(old, new, 1)
    return body


def variants():
    return (
        ("selected", renamed("selected"), True),
        ("wrong_index_stride", renamed("wrong_index_stride",
            (("[0x42] * 10", "[0x42] * 9"),)), False),
        ("wrong_record_stride", renamed("wrong_record_stride",
            (("index * 10", "index * 9"),)), False),
        ("wrong_common_source", renamed("wrong_common_source",
            (("record[1] = source[2]", "record[1] = source[1]"),)), False),
        ("wrong_pair_source", renamed("wrong_pair_source",
            (("record[6] = source[0xE]", "record[6] = source[0xF]"),)), False),
        ("wrong_group", renamed("wrong_group",
            (("case 7:", "case 6:"),)), False),
        ("wrong_tail", renamed("wrong_tail",
            (("record[9] = source[6]", "record[9] = source[5]"),)), False),
        ("missing_submit", renamed("missing_submit",
            (("    func_150076A0();\n", ""),)), False),
    )


def harness():
    rows = variants()
    bodies = "\n\n".join(body for _, body, _ in rows)
    text = r'''
typedef signed int s32; typedef signed char s8; typedef unsigned char u8;
s8 D_800E0BE0[28]; s8 *D_8008FDD4; s8 D_800AB690[40]; s8 *D_80082BBC;
static u8 state[0x80], records[160], expected[160]; static s32 submits;
void func_150076A0(void) { submits++; }
FUNCTIONS
typedef void (*Submit)(void);
static void clear(u8 *p, s32 n) { while (n--) *p++ = 0; }
static void setup(s32 index, s32 category, s32 seed) {
    s32 i; clear(state, sizeof(state)); clear(records, sizeof(records));
    for (i = 0; i < 28; i++) D_800E0BE0[i] = (s8)(i * 17 + seed * 23 + 3);
    for (i = 0; i < 40; i++) D_800AB690[i] = -7;
    for (i = 0; i < 160; i++) records[i] = expected[i] = (u8)(i * 29 + seed);
    D_8008FDD4 = (s8 *)state; D_80082BBC = (s8 *)(records + 20);
    state[0x42] = category; D_800AB690[category * 10] = (s8)index; submits = 0;
}
static void reference(s32 index) {
    s8 *record = (s8 *)(expected + 20) + index * 10; s8 *source = D_800E0BE0;
    record[0]=0; record[1]=source[2]; record[2]=source[3];
    record[3]=source[0x10]; record[4]=source[0x11];
    if (index == 0) record[5]=source[4];
    else if (index == 1 || index == 2) { record[5]=source[0xD]; record[6]=source[0xE]; }
    else if (index == 5 || index == 7) record[5]=source[0x12];
    else if (index == 8 || index == 9) { record[5]=source[7]; record[6]=source[0x13]; }
    record[8]=source[0x16]; record[9]=source[6];
}
static s32 check(Submit submit) {
    s32 index, category, seed, i;
    for (index=-2; index<=11; index++) for (category=0; category<4; category++)
    for (seed=0; seed<3; seed++) {
        setup(index,category,seed); reference(index); submit();
        if (submits != 1) return 0;
        for (i=0;i<160;i++) if (records[i] != expected[i]) return 0;
    }
    return 1;
}
static s32 run(void) {
CHECKS
    return 0;
}
''' + START
    checks = []
    for index, (name, _, selected) in enumerate(rows):
        checks.append("    if (%scheck(%s)) return %d;" %
                      ("!" if selected else "", name, 70 + index))
    return text.replace("FUNCTIONS", bodies).replace("CHECKS", "\n".join(checks)), len(rows)


def qualify(root, output):
    root, output = Path(root), Path(output)
    text, count = harness()
    unit = output / "native-menu-record-submit.c"
    unit.write_text(text)
    reports = []
    for profile in ("-O0", "-O2", "-O3"):
        executable = output / ("native-menu-record-submit-" + profile[1:])
        build = subprocess.run(native_command(profile) + ["-fno-strict-aliasing",
                               str(unit), "-o", str(executable)], cwd=root,
                               capture_output=True, text=True)
        if build.returncode:
            raise AssertionError((profile, build.stdout, build.stderr))
        run = subprocess.run([str(executable)], capture_output=True, timeout=60)
        if run.returncode:
            raise AssertionError((profile, run.returncode, run.stdout, run.stderr))
        reports.append({"profile": profile, "variants": count,
                        "controls": count - 1, "cases_per_variant": 168,
                        "UBSan": True})
    return reports
