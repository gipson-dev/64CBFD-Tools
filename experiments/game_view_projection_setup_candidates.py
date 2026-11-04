"""Screen semantic C forms for view-projection setup func_15012370."""

import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span, link_owner)


SOURCE = "conker/src/game_3F820.c"
OWNER = "game_3F820"
FUNCTION = "func_15012370"
ROM = 0x3F820
WORDS = 64
BUILD = "conker/build/game-view-projection-setup-15012370-candidates"
PROTOTYPE = "void func_15012370(void);"
TYPE = """typedef struct {
    f32 unused0;
    f32 horizontalExtent;
    f32 verticalExtent;
    u8 opaqueC[0x174];
} ViewProjectionSetup15012370;

"""

SELECTED = """/* Rebuild each active view's projection matrix from its half extents. */
void func_15012370(void) {
    f32 halfWidth;
    f32 halfHeight;
    u8 index;
    f32 farPlane = D_80096560;

    for (index = 0; index <= D_80082FA0; index++) {
        halfWidth = ((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index].horizontalExtent * 0.5f;
        halfHeight = ((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index].verticalExtent * 0.5f;
        func_151EF954(((f32 (*)[4][4])D_800DCC10)[index],
            -halfWidth, halfWidth, -halfHeight, halfHeight,
            1.0f, farPlane, 1.0f);
    }
}"""


def variants():
    yield "typed-direct", SELECTED
    addressed = SELECTED.replace(
        "    f32 farPlane = D_80096560;",
        "    ViewProjectionSetup15012370 **views;\n"
        "    f32 (*matrices)[4][4];\n"
        "    f32 farPlane = D_80096560;\n\n"
        "    views = (ViewProjectionSetup15012370 **)&D_800BE628;\n"
        "    matrices = (f32 (*)[4][4])D_800DCC10;").replace(
        "((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index]",
        "(*views)[index]").replace(
        "((f32 (*)[4][4])D_800DCC10)[index]", "matrices[index]")
    yield "addressed-views", addressed
    yield "addressed-matrices-first", addressed.replace(
        "    ViewProjectionSetup15012370 **views;\n"
        "    f32 (*matrices)[4][4];",
        "    f32 (*matrices)[4][4];\n"
        "    ViewProjectionSetup15012370 **views;").replace(
        "    views = (ViewProjectionSetup15012370 **)&D_800BE628;\n"
        "    matrices = (f32 (*)[4][4])D_800DCC10;",
        "    matrices = (f32 (*)[4][4])D_800DCC10;\n"
        "    views = (ViewProjectionSetup15012370 **)&D_800BE628;")
    yield "addressed-view-only", SELECTED.replace(
        "    f32 farPlane = D_80096560;",
        "    ViewProjectionSetup15012370 **views;\n"
        "    f32 farPlane = D_80096560;\n\n"
        "    views = (ViewProjectionSetup15012370 **)&D_800BE628;").replace(
        "((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index]",
        "(*views)[index]")
    guarded = SELECTED.replace(
        "    f32 farPlane = D_80096560;",
        "    f32 farPlane;").replace(
        "    for (index = 0; index <= D_80082FA0; index++) {",
        "    index = 0;\n"
        "    if (D_80082FA0 >= 0) {\n"
        "        farPlane = D_80096560;\n"
        "        do {").replace(
        "            1.0f, farPlane, 1.0f);\n    }\n}",
        "            1.0f, farPlane, 1.0f);\n"
        "            index++;\n"
        "        } while (index <= D_80082FA0);\n"
        "    }\n"
        "}")
    yield "guarded-init", guarded
    extents = guarded.replace(
        "    f32 halfWidth;\n    f32 halfHeight;",
        "    f32 halfWidth;\n    f32 halfHeight;\n"
        "    f32 horizontalExtent;\n    f32 verticalExtent;").replace(
        "        halfWidth = ((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index].horizontalExtent * 0.5f;\n"
        "        halfHeight = ((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index].verticalExtent * 0.5f;",
        "        horizontalExtent = ((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index].horizontalExtent;\n"
        "        verticalExtent = ((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index].verticalExtent;\n"
        "        halfWidth = horizontalExtent * 0.5f;\n"
        "        halfHeight = verticalExtent * 0.5f;")
    yield "guarded-loaded-extents", extents
    yield "guarded-reversed-half-declarations", guarded.replace(
        "    f32 halfWidth;\n    f32 halfHeight;",
        "    f32 halfHeight;\n    f32 halfWidth;")
    stride = guarded.replace(
        "    f32 farPlane;",
        "    s32 stride;\n    f32 farPlane;").replace(
        "    index = 0;\n    if (D_80082FA0 >= 0) {",
        "    index = 0;\n    stride = sizeof(ViewProjectionSetup15012370);\n"
        "    if (D_80082FA0 >= 0) {").replace(
        "((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index].horizontalExtent",
        "((ViewProjectionSetup15012370 *)((u8 *)(u32)D_800BE628 + "
        "(u32)index * stride))->horizontalExtent").replace(
        "((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index].verticalExtent",
        "((ViewProjectionSetup15012370 *)((u8 *)(u32)D_800BE628 + "
        "(u32)index * stride))->verticalExtent")
    yield "guarded-explicit-stride", stride
    yield "guarded-u32-stride", stride.replace("    s32 stride;", "    u32 stride;")
    yield "guarded-stride-after-far", stride.replace(
        "    s32 stride;\n    f32 farPlane;",
        "    f32 farPlane;\n    s32 stride;")
    declarations = {
        "stride": "    s32 stride;",
        "view": "    volatile s32 *viewBaseAddress;",
        "matrix": "    u8 *matrixBase;",
    }
    for order in itertools.permutations(declarations):
        explicit = """/* Rebuild each active view's projection matrix from its half extents. */
void func_15012370(void) {
    f32 halfWidth;
    f32 halfHeight;
    u8 index;
%s
    f32 farPlane;

    index = 0;
    stride = sizeof(ViewProjectionSetup15012370);
    if (D_80082FA0 >= 0) {
        farPlane = D_80096560;
        viewBaseAddress = &D_800BE628;
        matrixBase = (u8 *)D_800DCC10;
        do {
            halfWidth = ((ViewProjectionSetup15012370 *)((u8 *)(u32)*viewBaseAddress + (u32)index * stride))->horizontalExtent * 0.5f;
            halfHeight = ((ViewProjectionSetup15012370 *)((u8 *)(u32)*viewBaseAddress + (u32)index * stride))->verticalExtent * 0.5f;
            func_151EF954((f32 (*)[4])(matrixBase + (u32)index * 0x40),
                -halfWidth, halfWidth, -halfHeight, halfHeight,
                1.0f, farPlane, 1.0f);
            index++;
        } while (index <= D_80082FA0);
    }
}""" % "\n".join(declarations[name] for name in order)
        yield "explicit-" + "-".join(order), explicit
    yield "byte-matrix", SELECTED.replace(
        "((f32 (*)[4][4])D_800DCC10)[index]",
        "(f32 (*)[4])((u8 *)D_800DCC10 + (u32)index * 0x40)")
    yield "byte-view", SELECTED.replace(
        "((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index].horizontalExtent",
        "*(f32 *)((u8 *)(u32)D_800BE628 + (u32)index * 0x180 + 4)").replace(
        "((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index].verticalExtent",
        "*(f32 *)((u8 *)(u32)D_800BE628 + (u32)index * 0x180 + 8)")
    yield "separate-far-plane", SELECTED.replace(
        "    f32 farPlane = D_80096560;",
        "    f32 farPlane;\n\n    farPlane = D_80096560;")
    yield "do-while", SELECTED.replace(
        "    for (index = 0; index <= D_80082FA0; index++) {",
        "    index = 0;\n    if (D_80082FA0 >= 0) {\n        do {").replace(
        "            1.0f, farPlane, 1.0f);\n    }\n}",
        "            1.0f, farPlane, 1.0f);\n            index++;\n        } while (index <= D_80082FA0);\n    }\n}")
    yield "signed-index", SELECTED.replace("    u8 index;", "    s32 index;")
    yield "cached-view-base", SELECTED.replace(
        "    f32 farPlane = D_80096560;",
        "    ViewProjectionSetup15012370 *views;\n"
        "    f32 farPlane = D_80096560;\n\n"
        "    views = (ViewProjectionSetup15012370 *)(u32)D_800BE628;").replace(
        "((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index]",
        "views[index]")


def candidate_source(before, body):
    start, end = function_span(before, FUNCTION)
    predecessor = before[start:end]
    if predecessor != "s32 func_15012370() {\n    return 0;\n}":
        raise ValueError("View-projection setup predecessor changed")
    marker = "/* Generated placeholder declarations. */\n"
    if before.count(marker) != 1:
        raise ValueError("View-projection setup type anchor changed")
    before = before.replace(marker, TYPE + marker, 1)
    start, end = function_span(before, FUNCTION)
    before = before[:start] + body + before[end:]
    declaration = "s32 func_15012370();"
    if before.count(declaration) != 1:
        raise ValueError("View-projection setup declaration changed")
    before = before.replace(declaration, PROTOTYPE, 1)
    comment = (
        "/* Non-matching C placeholders for "
        "asm/nonmatchings/game_3F820/func_15012370.s. */\n")
    if before.count(comment) != 1:
        raise ValueError("View-projection setup placeholder comment changed")
    return before.replace(comment, "", 1)


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    before = (root / SOURCE).read_text()
    retail = (root / "conker/conker.us.bin").read_bytes()[
        ROM:ROM + WORDS * 4]
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    records = []
    for label, body in variants():
        obj, diagnostics = compile_owner(
            root, output, candidate_source(before, body), label)
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


if __name__ == "__main__":
    main()
