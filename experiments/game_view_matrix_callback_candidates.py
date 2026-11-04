"""Screen semantic C forms for the matrix-backed viewport callback."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner,
    link_owner,
)


FUNCTION = "func_150F9AB0"
OWNER = "generated_126F60"
SOURCE = "conker/src/game/generated_126F60.c"
BUILD = "conker/build/game-view-matrix-callback-150F9AB0-candidates"
ENTRY = 0x150F9AB0
ROM = 0x126F60
WORDS = 64

DECLARATIONS = """extern s32 D_80082FA4;
extern u8 *D_800BE628;

typedef struct {
    u8 pad0[0x24];
    f32 top;
    f32 bottom;
    f32 left;
    f32 right;
    u8 pad34[0x14C];
} ViewBounds150F9AB0;

void func_15110360(s32, f32 [4][4], f32, f32, f32);
Gfx *func_15110544(Gfx *, s32, s32, s32, s32, u8, u8, u8);
Gfx *func_150FB4C0(Gfx *, f32 [4][4]);
"""

PLACEHOLDER = """s32 func_150F9AB0() {
    return 0;
}"""

STRUCT_BODY = """/* Draw through the active view using the requested matrix rotation. */
Gfx *func_150F9AB0(Gfx *commands, f32 unusedX, f32 unusedY, f32 unusedZ,
                   f32 rotationX, f32 rotationY, f32 rotationZ) {
    f32 matrix[4][4];
    ViewBounds150F9AB0 *view;

    func_15110360(D_80082FA4, matrix, rotationX, rotationY, rotationZ);
    view = &((ViewBounds150F9AB0 *)D_800BE628)[D_80082FA4];
    commands = func_15110544(commands, (s32)view->left, (s32)view->top,
        (s32)(view->right - 1.0f), (s32)view->bottom, 0, 0, 0);
    commands[0].words.w0 = 0xE7000000;
    commands[0].words.w1 = 0;
    commands[1].words.w0 = 0xEF002C0F;
    commands[1].words.w1 = 0x0F0A4004;
    commands[2].words.w1 = 0xFFFFFFFF;
    commands[2].words.w0 = 0xFC357E6A;
    return func_150FB4C0(commands + 3, matrix);
}"""

MACRO_BODY = STRUCT_BODY.replace(
    "    commands[0].words.w0 = 0xE7000000;\n"
    "    commands[0].words.w1 = 0;\n"
    "    commands[1].words.w0 = 0xEF002C0F;\n"
    "    commands[1].words.w1 = 0x0F0A4004;\n"
    "    commands[2].words.w1 = 0xFFFFFFFF;\n"
    "    commands[2].words.w0 = 0xFC357E6A;\n"
    "    return func_150FB4C0(commands + 3, matrix);",
    "    gDPPipeSync(commands++);\n"
    "    gDPSetOtherMode(commands++, 0x2C0F, 0x0F0A4004);\n"
    "    gDPSetCombine(commands++, 0x357E6A, 0xFFFFFFFF);\n"
    "    return func_150FB4C0(commands, matrix);",
)

EIGHT_ARGUMENT_BODY = MACRO_BODY.replace(
    "                   f32 rotationX, f32 rotationY, f32 rotationZ) {",
    "                   f32 rotationX, f32 rotationY, f32 rotationZ,\n"
    "                   void *unusedContext) {",
)

SELECTED = EIGHT_ARGUMENT_BODY

LEGACY_BODY = """/* Draw through the active view using the requested matrix rotation. */
void func_150F9AB0(s32 commands, void *unusedX, void *unusedY, void *unusedZ,
                   s32 rotationX, s32 rotationY, f32 rotationZ) {
    f32 matrix[4][4];
    void *view;
    void *output;

    func_15110360(D_80082FA4, matrix, rotationX, rotationY, rotationZ);
    view = D_800BE628 + D_80082FA4 * 0x180;
    output = func_15110544((Gfx *)commands,
        (s32)*(f32 *)((u8 *)view + 0x2C),
        (s32)*(f32 *)((u8 *)view + 0x24),
        (s32)(*(f32 *)((u8 *)view + 0x30) - 1.0f),
        (s32)*(f32 *)((u8 *)view + 0x28), 0, 0, 0);
    *(s32 *)((u8 *)output + 0x00) = 0xE7000000;
    *(s32 *)((u8 *)output + 0x04) = 0;
    *(s32 *)((u8 *)output + 0x08) = 0xEF002C0F;
    *(s32 *)((u8 *)output + 0x0C) = 0x0F0A4004;
    *(s32 *)((u8 *)output + 0x14) = -1;
    *(s32 *)((u8 *)output + 0x10) = 0xFC357E6A;
    func_150FB4C0((Gfx *)((u8 *)output + 0x18), matrix);
}"""

BYTE_BODY = STRUCT_BODY.replace(
    "    ViewBounds150F9AB0 *view;", "    u8 *view;"
).replace(
    "    view = &((ViewBounds150F9AB0 *)D_800BE628)[D_80082FA4];",
    "    view = D_800BE628 + D_80082FA4 * 0x180;",
).replace("view->left", "*(f32 *)(view + 0x2C)").replace(
    "view->top", "*(f32 *)(view + 0x24)"
).replace("view->right", "*(f32 *)(view + 0x30)").replace(
    "view->bottom", "*(f32 *)(view + 0x28)"
)


def variants():
    yield "typed-struct", STRUCT_BODY
    yield "sdk-command-macros", MACRO_BODY
    yield "eight-argument-sdk-macros", EIGHT_ARGUMENT_BODY
    yield "legacy-decompiler-shape", LEGACY_BODY
    yield "void-macro", MACRO_BODY.replace(
        "Gfx *func_150F9AB0", "void func_150F9AB0"
    ).replace(
        "    return func_150FB4C0(commands, matrix);",
        "    func_150FB4C0(commands, matrix);",
    )
    yield "byte-offsets", BYTE_BODY
    yield "typed-local-index", STRUCT_BODY.replace(
        "    ViewBounds150F9AB0 *view;",
        "    ViewBounds150F9AB0 *views;\n    ViewBounds150F9AB0 *view;",
    ).replace(
        "    view = &((ViewBounds150F9AB0 *)D_800BE628)[D_80082FA4];",
        "    views = (ViewBounds150F9AB0 *)D_800BE628;\n"
        "    view = &views[D_80082FA4];",
    )
    yield "signed-final-word", STRUCT_BODY.replace(
        "commands[2].words.w1 = 0xFFFFFFFF;",
        "commands[2].words.w1 = -1;",
    )
    yield "return-cast", STRUCT_BODY.replace(
        "return func_150FB4C0(commands + 3, matrix);",
        "return (Gfx *)func_150FB4C0(commands + 3, matrix);",
    )


def candidate_source(before, body):
    if before.count(PLACEHOLDER) != 1:
        raise ValueError("View-matrix callback placeholder anchor changed")
    include_anchor = '#include "structs.h"\n'
    if before.count(include_anchor) != 1:
        raise ValueError("View-matrix callback include anchor changed")
    return before.replace(
        include_anchor, include_anchor + DECLARATIONS, 1
    ).replace(PLACEHOLDER, body, 1)


def retail_bytes(root):
    image = (root / "conker/conker.us.bin").read_bytes()
    return image[ROM:ROM + WORDS * 4]


def compare(actual, retail):
    actual_words = list(struct.iter_unpack(">I", actual))
    retail_words = list(struct.iter_unpack(">I", retail))
    limit = max(len(actual_words), len(retail_words))
    return [
        index for index in range(limit)
        if (actual_words[index] if index < len(actual_words) else None) !=
           (retail_words[index] if index < len(retail_words) else None)
    ]


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    before = (root / SOURCE).read_text()
    retail = retail_bytes(root)
    records = []
    for label, body in variants():
        source = candidate_source(before, body)
        obj, diagnostics = compile_owner(
            root, output, source, label + "-" + OWNER
        )
        linked, functions = link_owner(root, output, obj, OWNER)
        info = functions[FUNCTION]
        actual = linked[info["value"]:info["value"] + info["size"]]
        while len(actual) > len(retail) and actual[-4:] == b"\0\0\0\0":
            actual = actual[:-4]
        differences = compare(actual, retail)
        record = {
            "variant": label,
            "words": len(actual) // 4,
            "retail_words": WORDS,
            "differences": len(differences),
            "difference_indices": differences,
            "body_sha256": hashlib.sha256(actual).hexdigest(),
            "retail_sha256": hashlib.sha256(retail).hexdigest(),
            "diagnostics": diagnostics,
        }
        records.append(record)
        print(json.dumps({
            key: value for key, value in record.items()
            if key != "diagnostics"
        }))
    (output / "candidates.json").write_text(
        json.dumps(records, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
