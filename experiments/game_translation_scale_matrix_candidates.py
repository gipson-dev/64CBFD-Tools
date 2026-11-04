"""Screen semantic C forms for func_15158920's translation/scale matrix callback."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x15158920
ROM = 0x185DD0
WORDS = 64
FUNCTION = "func_15158920"
SOURCE = "conker/src/game/generated_185560.c"
OWNER = "generated_185560"
BUILD = "conker/build/game-translation-scale-matrix-candidates"
DECLARATIONS = """extern f32 D_800A6070;
extern MatrixOnlyWorkspace15158920 D_8008AE18;
"""
INSTALL_TYPES = """typedef struct {
    u8 retained00[0x48];
    f32 xPosition;
    f32 yPosition;
    f32 zPosition;
    u8 retained54[0xA4];
    f32 scaleByte;
} TranslationScaleState15158920;
typedef struct {
    f32 values[4][4];
} MatrixOnlyWorkspace15158920;
"""
SCREEN_TYPES = """typedef struct {
    MatrixOnlyWorkspace15158920 matrix;
    u32 retained[2];
} TranslationScaleWorkspace15158920;
typedef struct {
    u32 retained;
    f32 values[4][4];
} LeadingMatrixWorkspace15158920;
typedef struct {
    f32 values[4][4];
    u32 retained;
} TrailingMatrixWorkspace15158920;
typedef struct {
    f32 values[16];
} FlatMatrixWorkspace15158920;
typedef struct {
    f32 m00, m01, m02, m03;
    f32 m10, m11, m12, m13;
    f32 m20, m21, m22, m23;
    f32 m30, m31, m32, m33;
} ScalarMatrixWorkspace15158920;
#pragma pack(8)
typedef struct {
    f32 values[4][4];
} Packed8MatrixWorkspace15158920;
#pragma pack(0)
#pragma pack(4)
typedef struct {
    f32 values[4][4];
} Packed4MatrixWorkspace15158920;
#pragma pack(0)
typedef union {
    u64 words[8];
    f32 values[4][4];
} Aligned8MatrixWorkspace15158920;
"""
TYPES = INSTALL_TYPES + SCREEN_TYPES
PLACEHOLDER = """s32 func_15158920() {
    return 0;
}"""
MATRIX = """    f32 matrix[4][4] = {
        {1.0f, 0.0f, 0.0f, 0.0f},
        {0.0f, 1.0f, 0.0f, 0.0f},
        {0.0f, 0.0f, 1.0f, 0.0f},
        {0.0f, 0.0f, 0.0f, 1.0f},
    };"""
BODY_TEMPLATE = """/* Build and submit the state's translated, byte-scaled matrix. */
s32 func_15158920(Mtx *output, TranslationScaleState15158920 *state) {
MATRIX
    f32 scale;

SCALE_ASSIGN
TRANSLATION
    matrix[0][0] *= scale;
    matrix[0][1] *= scale;
    matrix[0][2] *= scale;
    matrix[1][0] *= scale;
    matrix[1][1] *= scale;
    matrix[1][2] *= scale;
    matrix[2][0] *= scale;
    matrix[2][1] *= scale;
    matrix[2][2] *= scale;
    guMtxF2L(matrix, output);
    return 1;
}"""
SCALE_ASSIGN = "    scale = state->scaleByte * D_800A6070;"
TRANSLATION = """    matrix[3][0] = state->xPosition;
    matrix[3][1] = state->yPosition;
    matrix[3][2] = state->zPosition;
"""


def body(matrix=MATRIX, scale_before=True, inline=False, raw=False):
    text = BODY_TEMPLATE.replace("MATRIX", matrix)
    assignment = SCALE_ASSIGN
    translation = TRANSLATION
    if not scale_before:
        assignment, translation = translation.rstrip(), assignment + "\n"
    text = text.replace("SCALE_ASSIGN", assignment).replace(
        "TRANSLATION", translation)
    if inline:
        text = text.replace("    f32 scale;\n\n", "").replace(
            "    scale = state->scaleByte * D_800A6070;\n", "").replace(
            "*= scale", "*= state->scaleByte * D_800A6070")
    if raw:
        text = text.replace("TranslationScaleState15158920 *state", "u8 *state")
        text = text.replace("state->scaleByte", "*(f32 *)(state + 0xF8)")
        text = text.replace("state->xPosition", "*(f32 *)(state + 0x48)")
        text = text.replace("state->yPosition", "*(f32 *)(state + 0x4C)")
        text = text.replace("state->zPosition", "*(f32 *)(state + 0x50)")
    return text


def workspace_body(workspace_type):
    matrix = MATRIX.replace(
        "f32 matrix[4][4] = {",
        workspace_type + " workspace = {{").replace(
            "    };", "    }};")
    return body(matrix=matrix).replace(
        "matrix[", "workspace.values[").replace(
            "guMtxF2L(matrix, output);",
            "guMtxF2L(workspace.values, output);")


def flat_workspace_body(workspace_type, scalar=False):
    values = ["1.0f" if index in (0, 5, 10, 15) else "0.0f"
              for index in range(16)]
    matrix = "    %s workspace = {%s};" % (
        workspace_type, ", ".join(values))
    text = body(matrix=matrix)
    for row in range(4):
        for column in range(4):
            replacement = ("workspace.m%d%d" % (row, column) if scalar else
                           "workspace.values[%d]" % (row * 4 + column))
            text = text.replace(
                "matrix[%d][%d]" % (row, column), replacement)
    return text.replace(
        "guMtxF2L(matrix, output);",
        "guMtxF2L((f32 (*)[4])&workspace, output);")


def retained_local_body(count, before=False):
    text = SELECTED
    declaration = "    f32 retained[%d];\n" % count
    if before:
        return text.replace(MATRIX, declaration + MATRIX, 1)
    return text.replace("    f32 scale;", declaration + "    f32 scale;", 1)


def retained_declaration_body(declaration, before=False):
    text = SELECTED
    declaration = "    " + declaration + "\n"
    if before:
        return text.replace(MATRIX, declaration + MATRIX, 1)
    return text.replace("    f32 scale;", declaration + "    f32 scale;", 1)


def aligned8_workspace_body():
    matrix = """    Aligned8MatrixWorkspace15158920 workspace = {{
        0x3F80000000000000ULL, 0x0000000000000000ULL,
        0x000000003F800000ULL, 0x0000000000000000ULL,
        0x0000000000000000ULL, 0x3F80000000000000ULL,
        0x0000000000000000ULL, 0x000000003F800000ULL,
    }};"""
    return body(matrix=matrix).replace(
        "matrix[", "workspace.values[").replace(
            "guMtxF2L(matrix, output);",
            "guMtxF2L(workspace.values, output);")


def template_workspace_body():
    matrix = ("    MatrixOnlyWorkspace15158920 workspace = "
              "D_8008AE18;")
    return body(matrix=matrix).replace(
        "matrix[", "workspace.values[").replace(
            "guMtxF2L(matrix, output);",
            "guMtxF2L(workspace.values, output);")


def word_array_body():
    values = ["0x3F800000" if index in (0, 5, 10, 15) else "0"
              for index in range(16)]
    matrix = "    u32 words[16] = {%s};\n    f32 *matrix = (f32 *)words;" % (
        ", ".join(values))
    text = body(matrix=matrix)
    for row in range(4):
        for column in range(4):
            text = text.replace(
                "matrix[%d][%d]" % (row, column),
                "matrix[%d]" % (row * 4 + column))
    return text.replace(
        "guMtxF2L(matrix, output);",
        "guMtxF2L((f32 (*)[4])matrix, output);")


SELECTED = body()
SELECTED_MATCH = template_workspace_body()
ROOT = Path(__file__).resolve().parents[2]


def source_with(candidate):
    source = (ROOT / SOURCE).read_text()
    anchor = "#include <ultra64.h>\n"
    install_declarations = INSTALL_TYPES + DECLARATIONS + "\n"
    declarations = TYPES + DECLARATIONS + "\n"
    if source.count(PLACEHOLDER) == 1:
        if declarations in source or SELECTED in source:
            raise ValueError("Translation-scale matrix predecessor source changed")
        return source.replace(anchor, anchor + declarations, 1).replace(
            PLACEHOLDER, candidate, 1)
    if (source.count(SELECTED_MATCH) == 1 and
            source.count(install_declarations) == 1):
        if candidate == SELECTED_MATCH:
            return source
        return source.replace(
            install_declarations, declarations, 1).replace(
                SELECTED_MATCH, candidate, 1)
    raise ValueError("Translation-scale matrix source state changed")


def variants():
    yield "typed-scale-before", SELECTED
    yield "typed-matrix-only-workspace", workspace_body(
        "MatrixOnlyWorkspace15158920")
    yield "typed-trailing-workspace", workspace_body(
        "TrailingMatrixWorkspace15158920")
    yield "typed-flat-workspace", flat_workspace_body(
        "FlatMatrixWorkspace15158920")
    yield "typed-scalar-workspace", flat_workspace_body(
        "ScalarMatrixWorkspace15158920", scalar=True)
    yield "typed-packed8-workspace", workspace_body(
        "Packed8MatrixWorkspace15158920")
    yield "typed-packed4-workspace", workspace_body(
        "Packed4MatrixWorkspace15158920")
    yield "typed-aligned8-workspace", aligned8_workspace_body()
    yield "typed-template-workspace", template_workspace_body()
    yield "typed-word-array", word_array_body()
    yield "typed-retained-one-after", retained_local_body(1)
    yield "typed-retained-two-after", retained_local_body(2)
    yield "typed-retained-one-before", retained_local_body(1, before=True)
    yield "typed-retained-two-before", retained_local_body(2, before=True)
    yield "typed-retained-double-after", retained_declaration_body(
        "f64 retained;")
    yield "typed-retained-scalars-after", retained_declaration_body(
        "f32 retained0; f32 retained1;")
    yield "typed-retained-double-before", retained_declaration_body(
        "f64 retained;", before=True)
    yield "typed-retained-scalars-before", retained_declaration_body(
        "f32 retained0; f32 retained1;", before=True)
    yield "typed-scale-after", body(scale_before=False)
    yield "raw-scale-before", body(raw=True)
    yield "raw-scale-after", body(scale_before=False, raw=True)
    yield "typed-inline", body(inline=True)
    yield "raw-inline", body(inline=True, raw=True)


def compare(name, candidate, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(
        ROOT, output, source_with(candidate), name, flags=flags)
    linked, functions = link_owner(ROOT, output, obj, OWNER)
    info = functions[FUNCTION]
    ours = linked[info["value"]:info["value"] + info["size"]]
    retail = (ROOT / "conker/conker.us.bin").read_bytes()[
        ROM:ROM + WORDS * 4]
    our_words = struct.unpack(">%dI" % (len(ours) // 4), ours)
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    differences = [
        {"offset": index * 4, "ours": left, "retail": right}
        for index, (left, right) in enumerate(
            itertools.zip_longest(our_words, retail_words, fillvalue=0))
        if left != right
    ]
    return {
        "name": name,
        "flags": flags,
        "words": len(our_words),
        "frame": (-our_words[0] & 0xFFFF) if our_words else 0,
        "differences": len(differences),
        "difference_rows": differences,
        "diagnostics": diagnostics,
        "raw_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


if __name__ == "__main__":
    records = []
    selected = os.environ.get("CANDIDATE_FILTER")
    for name, candidate in variants():
        if selected and name != selected:
            continue
        for label, flags in (("o2g3", ("-O2", "-g3")),
                             ("o2", ("-O2",))):
            record = compare(name + "-" + label, candidate, flags)
            records.append(record)
            print(record["name"], record["words"], record["frame"],
                  record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(
        json.dumps(records, indent=2) + "\n")
