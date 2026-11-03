"""Screen semantic C forms for func_1515858C's uniform matrix submit."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x1515858C
ROM = 0x185A3C
WORDS = 62
FUNCTION = "func_1515858C"
SOURCE = "conker/src/game/generated_185560.c"
OWNER = "generated_185560"
BUILD = "conker/build/game-uniform-matrix-submit-candidates"
DECLARATIONS = """void func_150A8050(f32 matrix[4][4], f32, f32, f32);
"""
INSTALL_TYPES = """typedef struct {
    u8 retained00[0x48];
    f32 xPosition;
    f32 yPosition;
    f32 zPosition;
    u8 retained54[0xA4];
    f32 xRotation;
    f32 yRotation;
    f32 zRotation;
    f32 uniformScale;
} UniformMatrixState1515858C;
"""
SCREEN_TYPES = """typedef struct {
    u32 retained;
    f32 values[4][4];
} MatrixWorkspace1515858C;
typedef struct {
    f32 values[4][4];
    u32 retained;
} TrailingMatrixWorkspace1515858C;
typedef struct {
    f32 values[4][4];
} MatrixOnlyWorkspace1515858C;
"""
TYPES = INSTALL_TYPES + SCREEN_TYPES
PLACEHOLDER = """s32 func_1515858C() {
    return 0;
}"""
SELECTED = """/* Build and submit the state's translated, uniformly scaled matrix. */
s32 func_1515858C(Mtx *output, UniformMatrixState1515858C *state) {
    f32 matrix[4][4];

    func_150A8050(matrix, state->xRotation, state->yRotation, state->zRotation);
    matrix[3][0] = state->xPosition;
    matrix[3][1] = state->yPosition;
    matrix[3][2] = state->zPosition;
    matrix[0][0] *= state->uniformScale;
    matrix[0][1] *= state->uniformScale;
    matrix[0][2] *= state->uniformScale;
    matrix[1][0] *= state->uniformScale;
    matrix[1][1] *= state->uniformScale;
    matrix[1][2] *= state->uniformScale;
    matrix[2][0] *= state->uniformScale;
    matrix[2][1] *= state->uniformScale;
    matrix[2][2] *= state->uniformScale;
    guMtxF2L(matrix, output);
    return 1;
}"""
SELECTED_MATCH = SELECTED.replace(
    "    f32 matrix[4][4];",
    "    MatrixWorkspace1515858C workspace;").replace(
    "matrix,", "workspace.values,").replace(
    "matrix[", "workspace.values[")
SELECTED_TRAILING = SELECTED.replace(
    "    f32 matrix[4][4];",
    "    TrailingMatrixWorkspace1515858C workspace;\n"
    "    f32 *rotation = &state->xRotation;").replace(
    "func_150A8050(matrix, state->xRotation, state->yRotation, state->zRotation);",
    "func_150A8050(workspace.values, rotation[0], rotation[1], rotation[2]);").replace(
    "matrix[", "workspace.values[").replace(
    "state->uniformScale", "rotation[3]").replace(
    "guMtxF2L(matrix, output);", "guMtxF2L(workspace.values, output);")
SELECTED_EXACT = SELECTED_TRAILING.replace(
    "TrailingMatrixWorkspace1515858C", "MatrixOnlyWorkspace1515858C")
SELECTED_POINTER = SELECTED.replace(
    "    f32 matrix[4][4];",
    "    f32 matrix[4][4];\n    f32 *rotation = &state->xRotation;").replace(
    "state->xRotation, state->yRotation, state->zRotation",
    "rotation[0], rotation[1], rotation[2]").replace(
    "state->uniformScale", "rotation[3]")
SELECTED_SCALAR_BEFORE = SELECTED_POINTER.replace(
    "    f32 matrix[4][4];",
    "    volatile u32 retained;\n    f32 matrix[4][4];")
SELECTED_SCALAR_AFTER = SELECTED_POINTER.replace(
    "    f32 matrix[4][4];",
    "    f32 matrix[4][4];\n    volatile u32 retained;")
SELECTED_POINTER_BEFORE = SELECTED_POINTER.replace(
    "    f32 matrix[4][4];\n    f32 *rotation = &state->xRotation;",
    "    f32 *rotation = &state->xRotation;\n    f32 matrix[4][4];")
SELECTED_POINTER_ASSIGN_AFTER = SELECTED_POINTER.replace(
    "    f32 *rotation = &state->xRotation;",
    "    f32 *rotation;\n\n    rotation = &state->xRotation;")
SELECTED_POINTER_ASSIGN_BEFORE = SELECTED_POINTER.replace(
    "    f32 matrix[4][4];\n    f32 *rotation = &state->xRotation;",
    "    f32 *rotation;\n    f32 matrix[4][4];\n\n    rotation = &state->xRotation;")
RAW = """/* Build and submit the state's translated, uniformly scaled matrix. */
s32 func_1515858C(Mtx *output, u8 *state) {
    f32 matrix[4][4];

    func_150A8050(matrix, *(f32 *)(state + 0xF8), *(f32 *)(state + 0xFC),
                   *(f32 *)(state + 0x100));
    matrix[3][0] = *(f32 *)(state + 0x48);
    matrix[3][1] = *(f32 *)(state + 0x4C);
    matrix[3][2] = *(f32 *)(state + 0x50);
    matrix[0][0] *= *(f32 *)(state + 0x104);
    matrix[0][1] *= *(f32 *)(state + 0x104);
    matrix[0][2] *= *(f32 *)(state + 0x104);
    matrix[1][0] *= *(f32 *)(state + 0x104);
    matrix[1][1] *= *(f32 *)(state + 0x104);
    matrix[1][2] *= *(f32 *)(state + 0x104);
    matrix[2][0] *= *(f32 *)(state + 0x104);
    matrix[2][1] *= *(f32 *)(state + 0x104);
    matrix[2][2] *= *(f32 *)(state + 0x104);
    guMtxF2L(matrix, output);
    return 1;
}"""


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    anchor = "#include <ultra64.h>\n"
    if source.count(anchor) != 1:
        raise ValueError("Uniform matrix submit include anchor changed")
    source_types = INSTALL_TYPES if body == SELECTED_POINTER_BEFORE else TYPES
    declarations = source_types + DECLARATIONS + "\n"
    if source.count(PLACEHOLDER) == 1:
        if declarations in source or SELECTED_MATCH in source:
            raise ValueError("Uniform matrix submit predecessor source changed")
        return source.replace(PLACEHOLDER, body).replace(
            anchor, anchor + declarations, 1)
    if (body == SELECTED_POINTER_BEFORE and
            source.count(SELECTED_POINTER_BEFORE) == 1 and
            source.count(declarations) == 1):
        return source
    if source.count(SELECTED_MATCH) == 1 and source.count(declarations) == 1:
        return source.replace(SELECTED_MATCH, body, 1)
    raise ValueError("Uniform matrix submit source state changed")


def variants():
    yield "typed", SELECTED
    yield "raw", RAW
    yield "typed-named-workspace", SELECTED_MATCH
    yield "typed-trailing-workspace", SELECTED_TRAILING
    yield "typed-matrix-only-workspace", SELECTED_EXACT
    yield "typed-pointer", SELECTED_POINTER
    yield "typed-scalar-before", SELECTED_SCALAR_BEFORE
    yield "typed-scalar-after", SELECTED_SCALAR_AFTER
    yield "typed-pointer-before", SELECTED_POINTER_BEFORE
    yield "typed-pointer-assign-after", SELECTED_POINTER_ASSIGN_AFTER
    yield "typed-pointer-assign-before", SELECTED_POINTER_ASSIGN_BEFORE
    aligned = SELECTED.replace(
        "    f32 matrix[4][4];",
        "    union { u64 align; f32 values[4][4]; } matrix;")
    aligned = aligned.replace("matrix,", "matrix.values,").replace(
        "matrix[", "matrix.values[")
    yield "typed-aligned", aligned
    padded = SELECTED.replace(
        "    f32 matrix[4][4];",
        "    struct { u32 retained; f32 values[4][4]; } matrix;")
    padded = padded.replace("matrix,", "matrix.values,").replace(
        "matrix[", "matrix.values[")
    yield "typed-padded", padded


def compare(name, body, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(ROOT, output, source_with(body), name,
                                     flags=flags)
    linked, functions = link_owner(ROOT, output, obj, OWNER)
    info = functions[FUNCTION]
    ours = linked[info["value"]:info["value"] + info["size"]]
    retail = (ROOT / "conker/conker.us.bin").read_bytes()[ROM:ROM + WORDS * 4]
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
        "differences": len(differences),
        "difference_rows": differences,
        "diagnostics": diagnostics,
        "raw_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


ROOT = Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    records = []
    selected = os.environ.get("CANDIDATE_FILTER")
    for name, body in variants():
        if selected and name != selected:
            continue
        for label, flags in (("o2g3", ("-O2", "-g3")), ("o2", ("-O2",))):
            record = compare(name + "-" + label, body, flags)
            records.append(record)
            print(record["name"], record["words"], record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
