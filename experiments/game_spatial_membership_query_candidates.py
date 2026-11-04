"""Screen semantic C forms for spatial-membership query func_1503F800."""

import hashlib
import itertools
import json
from pathlib import Path
import struct
import sys

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span, link_owner)
from tools.experiments.game_four_head_lookup_match import payload


SOURCE = "conker/src/game/generated_6CCB0.c"
OWNER = "generated_6CCB0"
FUNCTION = "func_1503F800"
ROM = 0x6CCB0
WORDS = 65
BUILD = "conker/build/game-spatial-membership-query-1503F800-candidates"

PREAMBLE = """typedef struct {
    s16 unused0;
    s16 categoryMask;
    s16 siblingOffset;
    u16 radius;
    s16 centerX;
    s16 centerZ;
    s16 childOffset;
} SpatialMembershipNode1503F800;

extern u8 *D_800DBE48;
void func_1510F800();

"""

SELECTED = """/* Test whether a coordinate reaches a leaf in the selected category. */
s32 func_1503F800(void *unusedQuery, s32 x, s32 z, s32 category, s32 unusedMode) {
    SpatialMembershipNode1503F800 *node;
    s16 queryX;
    s16 queryZ;
    s16 offset;

    queryX = x;
    queryZ = z;
    func_1510F800(0, queryX, queryZ);
    node = (SpatialMembershipNode1503F800 *)D_800DBE48;
    while (node != NULL) {
        if ((s32)node->centerX + node->radius >= queryX &&
            queryX >= (s32)node->centerX - node->radius &&
            (s32)node->centerZ + node->radius >= queryZ &&
            queryZ >= (s32)node->centerZ - node->radius) {
            if (!(node->categoryMask & (1 << category))) {
                return 1;
            }
            offset = node->childOffset;
            if (offset == 0) {
                return 0;
            }
        } else {
            offset = node->siblingOffset;
        }
        node = offset != 0
            ? (SpatialMembershipNode1503F800 *)((u8 *)node + offset)
            : NULL;
    }
    return 1;
}"""

DONOR_SHAPE = """/* Test whether a coordinate reaches a leaf in the selected category. */
s32 func_1503F800(void *unusedQuery, s32 x, s32 z, s32 category, s32 unusedMode) {
    s16 center;
    s16 child;
    s16 queryX;
    s16 queryZ;
    s16 offset;
    u16 radius;
    u8 *node;

    queryZ = z;
    queryX = x;
    x = queryX;
    z = queryZ;
    func_1510F800(0, queryX, queryZ);
    node = D_800DBE48;
    if (node != NULL) {
loop:
        center = *(s16 *)(node + 8);
        radius = *(u16 *)(node + 6);
        if ((s32)center + radius >= x && x >= (s32)center - radius) {
            center = *(s16 *)(node + 10);
            if ((s32)center + radius >= z && z >= (s32)center - radius) {
                if (!(*(s16 *)(node + 2) & (1 << category))) {
                    goto miss;
                }
                child = *(s16 *)(node + 12);
                if (child != 0) {
                    offset = child;
                    goto advance;
                }
                return 0;
            }
        }
        offset = *(s16 *)(node + 4);
advance:
        node = offset != 0 ? node + offset : NULL;
        if (node != NULL) {
            goto loop;
        }
    }
miss:
    return 1;
}"""

ALTERNATE_SHAPE = """/* Test whether a coordinate reaches a leaf in the selected category. */
s32 func_1503F800(void *arg0, s32 arg1, s32 arg2, s32 arg3) {
    s16 temp_a0;
    s16 temp_a0_2;
    s16 temp_a0_3;
    s16 temp_a1;
    s16 temp_a2;
    s16 var_v0;
    u16 temp_v0;
    u8 *var_v1;

    temp_a2 = arg2;
    temp_a1 = arg1;
    arg1 = temp_a1;
    arg2 = temp_a2;
    func_1510F800(0, temp_a1, temp_a2);
    var_v1 = D_800DBE48;
    if (var_v1 != NULL) {
loop_1:
        temp_a0 = *(s16 *)(var_v1 + 8);
        temp_v0 = *(u16 *)(var_v1 + 6);
        if (((temp_a0 + temp_v0) >= arg1) &&
            (arg1 >= (temp_a0 - temp_v0))) {
            temp_a0_2 = *(s16 *)(var_v1 + 10);
            if (((temp_a0_2 + temp_v0) >= arg2) &&
                (arg2 >= (temp_a0_2 - temp_v0))) {
                if (!(*(s16 *)(var_v1 + 2) & (1 << arg3))) {
                    goto block_15;
                }
                temp_a0_3 = *(s16 *)(var_v1 + 12);
                if (temp_a0_3 != 0) {
                    var_v0 = temp_a0_3;
                    goto block_11;
                }
                return 0;
            }
        }
        var_v0 = *(s16 *)(var_v1 + 4);
block_11:
        if (var_v0 != 0) {
            var_v1 += var_v0;
        } else {
            var_v1 = NULL;
        }
        if (var_v1 == NULL) {
            goto block_15;
        }
        goto loop_1;
    }
block_15:
    return 1;
}"""

ALTERNATE_KR = ALTERNATE_SHAPE.replace(
    "s32 func_1503F800(void *arg0, s32 arg1, s32 arg2, s32 arg3) {",
    "s32 func_1503F800(arg0, arg1, arg2, arg3)\n"
    "void *arg0;\n"
    "s32 arg1;\n"
    "s32 arg2;\n"
    "s32 arg3;\n"
    "{")

ALTERNATE_TYPED = ALTERNATE_SHAPE.replace(
    "s32 func_1503F800(void *arg0, s32 arg1, s32 arg2, s32 arg3) {",
    "s32 func_1503F800(void *unusedQuery, s32 x, s32 z, s32 category, s32 unusedMode) {").replace(
    "    u8 *var_v1;", "    SpatialMembershipNode1503F800 *node;").replace(
    "    temp_a2 = arg2;\n    temp_a1 = arg1;\n    arg1 = temp_a1;\n    arg2 = temp_a2;",
    "    temp_a2 = z;\n    temp_a1 = x;\n    x = temp_a1;\n    z = temp_a2;").replace(
    "func_1510F800(0, temp_a1, temp_a2);", "func_1510F800(0);").replace(
    "    var_v1 = D_800DBE48;\n    if (var_v1 != NULL) {",
    "    node = (SpatialMembershipNode1503F800 *)D_800DBE48;\n    if (node != NULL) {").replace(
    "*(s16 *)(var_v1 + 8)", "node->centerX").replace(
    "*(u16 *)(var_v1 + 6)", "node->radius").replace(
    "temp_v0) >= arg1", "temp_v0) >= x").replace(
    "arg1 >= (temp_a0 - temp_v0)", "x >= (temp_a0 - temp_v0)").replace(
    "*(s16 *)(var_v1 + 10)", "node->centerZ").replace(
    "temp_v0) >= arg2", "temp_v0) >= z").replace(
    "arg2 >= (temp_a0_2 - temp_v0)", "z >= (temp_a0_2 - temp_v0)").replace(
    "*(s16 *)(var_v1 + 2)", "node->categoryMask").replace(
    "1 << arg3", "1 << category").replace(
    "*(s16 *)(var_v1 + 12)", "node->childOffset").replace(
    "*(s16 *)(var_v1 + 4)", "node->siblingOffset").replace(
    "            var_v1 += var_v0;", "            node = (SpatialMembershipNode1503F800 *)((u8 *)node + var_v0);").replace(
    "            var_v1 = NULL;", "            node = NULL;").replace(
    "        if (var_v1 == NULL)", "        if (node == NULL)")

TARGET_FLOW_TYPED = ALTERNATE_TYPED.replace(
    "    s16 temp_a0_3;\n", "").replace(
    "                if (!(node->categoryMask & (1 << category))) {\n"
    "                    goto block_15;\n"
    "                }\n"
    "                temp_a0_3 = node->childOffset;\n"
    "                if (temp_a0_3 != 0) {\n"
    "                    var_v0 = temp_a0_3;\n"
    "                    goto block_11;\n"
    "                }\n"
    "                return 0;",
    "                if (node->categoryMask & (1 << category)) {\n"
    "                    var_v0 = node->childOffset;\n"
    "                    if (var_v0 != 0) {\n"
    "                        goto block_11;\n"
    "                    }\n"
    "                    return 0;\n"
    "                }\n"
    "                goto block_15;")

NARROW_SELECTED = """/* Test whether a coordinate reaches a leaf in the selected category. */
s32 func_1503F800(void *unusedQuery, s16 x, s16 z, s32 category, s32 unusedMode) {
    u8 *node;
    s16 center;
    s16 offset;
    u16 radius;

    func_1510F800(0);
    node = D_800DBE48;
    while (node != NULL) {
        center = *(s16 *)(node + 8);
        radius = *(u16 *)(node + 6);
        if ((s32)center + radius < x || x < (s32)center - radius) {
            offset = *(s16 *)(node + 4);
        } else {
            center = *(s16 *)(node + 10);
            if ((s32)center + radius < z || z < (s32)center - radius) {
                offset = *(s16 *)(node + 4);
            } else {
                if (!(*(s16 *)(node + 2) & (1 << category))) {
                    return 1;
                }
                offset = *(s16 *)(node + 12);
                if (offset == 0) {
                    return 0;
                }
            }
        }
        node = offset != 0 ? node + offset : NULL;
    }
    return 1;
}"""

NARROW_KR = NARROW_SELECTED.replace(
    "s32 func_1503F800(void *unusedQuery, s16 x, s16 z, s32 category, s32 unusedMode) {",
    "s32 func_1503F800(unusedQuery, x, z, category)\n"
    "void *unusedQuery;\n"
    "s16 x;\n"
    "s16 z;\n"
    "s32 category;\n"
    "{")

DIRECT_NARROW = NARROW_SELECTED.replace(
    "s32 func_1503F800(void *unusedQuery, s16 x, s16 z, s32 category, s32 unusedMode) {",
    "s32 func_1503F800(void *unusedQuery, s32 x, s32 z, s32 category, s32 unusedMode) {").replace(
    "    func_1510F800(0);",
    "    x = (s16)x;\n"
    "    z = (s16)z;\n"
    "    func_1510F800(0, x, z);")

VOLATILE_CAPTURED = NARROW_SELECTED.replace(
    "s16 x, s16 z", "volatile s16 x, volatile s16 z").replace(
    "    s16 center;\n    s16 offset;",
    "    s16 center;\n    s16 offset;\n    s16 queryX;\n    s16 queryZ;").replace(
    "    func_1510F800(0);\n    node = D_800DBE48;",
    "    func_1510F800(0, x, z);\n"
    "    node = D_800DBE48;\n"
    "    queryX = x;\n"
    "    queryZ = z;").replace(
    "radius < x || x < (s32)center - radius",
    "radius < queryX || queryX < (s32)center - radius").replace(
    "radius < z || z < (s32)center - radius",
    "radius < queryZ || queryZ < (s32)center - radius")


def variants():
    yield "target-flow-typed", TARGET_FLOW_TYPED
    yield "alternate-typed", ALTERNATE_TYPED
    yield "volatile-captured", VOLATILE_CAPTURED
    yield "direct-narrow", DIRECT_NARROW
    yield "volatile-narrow", NARROW_SELECTED.replace(
        "s16 x, s16 z", "volatile s16 x, volatile s16 z")
    yield "volatile-narrow-three-arg", NARROW_SELECTED.replace(
        "s16 x, s16 z", "volatile s16 x, volatile s16 z").replace(
        "func_1510F800(0);", "func_1510F800(0, x, z);")
    yield "narrow-five", NARROW_SELECTED
    yield "narrow-five-three-arg-init", NARROW_SELECTED.replace(
        "func_1510F800(0);", "func_1510F800(0, x, z);")
    yield "narrow-kr-four", NARROW_KR
    yield "narrow-kr-three-arg-init", NARROW_KR.replace(
        "func_1510F800(0);", "func_1510F800(0, x, z);")
    yield "alternate-kr-one-arg-init", ALTERNATE_KR.replace(
        "func_1510F800(0, temp_a1, temp_a2);", "func_1510F800(0);")
    yield "alternate-kr-three-arg-init", ALTERNATE_KR
    yield "alternate-five-args", ALTERNATE_SHAPE.replace(
        "s32 arg2, s32 arg3)",
        "s32 arg2, s32 arg3, s32 unusedMode)")
    yield "alternate-five-one-arg-init", ALTERNATE_SHAPE.replace(
        "s32 arg2, s32 arg3)",
        "s32 arg2, s32 arg3, s32 unusedMode)").replace(
        "func_1510F800(0, temp_a1, temp_a2);", "func_1510F800(0);")
    yield "structured", SELECTED
    yield "donor-shape", DONOR_SHAPE
    yield "donor-query-order", DONOR_SHAPE.replace(
        "    queryZ = z;\n    queryX = x;",
        "    queryX = x;\n    queryZ = z;")
    yield "donor-one-arg-init", DONOR_SHAPE.replace(
        "func_1510F800(0, queryX, queryZ);", "func_1510F800(0);")
    yield "structured-one-arg-init", SELECTED.replace(
        "func_1510F800(0, queryX, queryZ);", "func_1510F800(0);")
    yield "structured-goto-miss", SELECTED.replace(
        "                return 1;", "                goto miss;", 1).replace(
        "    return 1;\n}", "miss:\n    return 1;\n}")


def candidate_source(before, body):
    start, end = function_span(before, FUNCTION)
    predecessor = before[start:end]
    if predecessor != "s32 func_1503F800() {\n    return 0;\n}":
        raise ValueError("Spatial-membership query predecessor changed")
    marker = "/* Recovered and remaining routines from the text-only asm slice asm/6CCB0.s. */\n\n"
    if before.count(marker) != 1:
        raise ValueError("Spatial-membership query declaration anchor changed")
    before = before.replace(marker, marker + PREAMBLE, 1)
    start, end = function_span(before, FUNCTION)
    return before[:start] + body + before[end:]


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    before = (root / SOURCE).read_text()
    retail = (root / "conker/conker.us.bin").read_bytes()[
        ROM:ROM + WORDS * 4]
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    records = []
    screens = []
    for label, body in variants():
        screens.append((label, body, ("-O2", "-g3")))
        if label in ("volatile-narrow", "volatile-narrow-three-arg",
                     "narrow-five", "narrow-five-three-arg-init",
                     "alternate-five-one-arg-init"):
            screens.extend((label + "-" + profile, body, flags) for
                profile, flags in (
                    ("o2", ("-O2",)),
                    ("o1", ("-O1",)),
                    ("g", ("-g",)),
                ))
    for label, body, flags in screens:
        obj, diagnostics = compile_owner(
            root, output, candidate_source(before, body), label, flags=flags)
        linked, functions = link_owner(root, output, obj, OWNER)
        info = functions[FUNCTION]
        actual = linked[info["value"]:info["value"] + info["size"]]
        actual_words = struct.unpack(">%dI" % (len(actual) // 4), actual)
        differences = [
            index * 4 for index, (left, right) in enumerate(
                itertools.zip_longest(
                    actual_words, retail_words, fillvalue=0))
            if left != right
        ]
        record = {
            "variant": label,
            "words": len(actual_words),
            "frame": (-actual_words[0] & 0xFFFF) if actual_words else 0,
            "differences": len(differences),
            "difference_offsets": differences,
            "raw_sha256": hashlib.sha256(actual).hexdigest(),
            "retail_sha256": hashlib.sha256(retail).hexdigest(),
            "diagnostics": diagnostics,
        }
        records.append(record)
        print(label, record["words"], hex(record["frame"]),
              record["differences"], flush=True)
    (output / "candidate-measurements.json").write_text(
        json.dumps(records, indent=2) + "\n")


def print_selected_details():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    raw, bindings = payload(output / "alternate-typed.o", FUNCTION)
    retail = (root / "conker/conker.us.bin").read_bytes()[
        ROM:ROM + WORDS * 4]
    actual_words = struct.unpack(">%dI" % WORDS, raw)
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    retail_bindings = {
        0x030: [("R_MIPS_26", "func_1510F800")],
        0x038: [("R_MIPS_HI16", "D_800DBE48")],
        0x03C: [("R_MIPS_LO16", "D_800DBE48")],
    }
    def relocation_spec(rows):
        return "-" if not rows else ";".join(
            kind + ":" + symbol for kind, symbol in rows)
    print(json.dumps({
        "words": WORDS,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
        "bindings": {hex(offset): rows for offset, rows in bindings.items()},
        "retail_bindings": {
            hex(offset): rows for offset, rows in retail_bindings.items()},
        "differences": sum(left != right for left, right in
                           zip(actual_words, retail_words)),
    }, indent=2))
    for index, (actual, expected) in enumerate(
            zip(actual_words, retail_words)):
        if actual == expected:
            continue
        offset = index * 4
        print(
            'dict(offset="0x%03X", expected="0x%08X", '
            'replacement="0x%08X", expected_relocations="%s", '
            'replacement_relocations="%s"),' % (
                offset, actual, expected,
                relocation_spec(bindings.get(offset, [])),
                relocation_spec(retail_bindings.get(offset, []))))


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--details":
        print_selected_details()
    else:
        main()
