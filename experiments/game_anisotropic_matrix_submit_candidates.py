"""Screen semantic C forms for func_151B9310's anisotropic matrix submit."""

import hashlib
import itertools
import json
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x151B9310
ROM = 0x1E67C0
WORDS = 62
FUNCTION = "func_151B9310"
SOURCE = "conker/src/game/generated_1E6260.c"
OWNER = "generated_1E6260"
BUILD = "conker/build/game-anisotropic-matrix-submit-candidates"
DECLARATIONS = """void func_150A8050(f32 matrix[4][4], f32, f32, f32);
"""
TYPES = """typedef struct {
    u8 retained00[0x18];
    f32 horizontalScale;
    f32 verticalScale;
    u8 retained20[0x18];
    f32 xPosition;
    f32 yPosition;
    f32 zPosition;
    u8 retained44[0x12C];
    f32 zRotation;
} AnisotropicMatrixState151B9310;
typedef struct {
    u32 retained;
    f32 values[4][4];
} MatrixWorkspace151B9310;
"""
PLACEHOLDER = """s32 func_151B9310() {
    return 0;
}"""
SELECTED = """/* Build and submit the state's translated, anisotropically scaled matrix. */
s32 func_151B9310(Mtx *output, AnisotropicMatrixState151B9310 *state) {
    f32 matrix[4][4];

    func_150A8050(matrix, 0.0f, 0.0f, state->zRotation);
    matrix[3][0] = state->xPosition;
    matrix[3][1] = state->yPosition;
    matrix[3][2] = state->zPosition;
    matrix[0][0] *= state->horizontalScale;
    matrix[0][1] *= state->horizontalScale;
    matrix[0][2] *= state->horizontalScale;
    matrix[1][0] *= state->verticalScale;
    matrix[1][1] *= state->verticalScale;
    matrix[1][2] *= state->verticalScale;
    matrix[2][0] *= state->horizontalScale;
    matrix[2][1] *= state->horizontalScale;
    matrix[2][2] *= state->horizontalScale;
    guMtxF2L(matrix, output);
    return 1;
}"""
SELECTED_MATCH = SELECTED.replace(
    "    f32 matrix[4][4];",
    "    MatrixWorkspace151B9310 workspace;").replace(
    "matrix,", "workspace.values,").replace(
    "matrix[", "workspace.values[")
RAW = """/* Build and submit the state's translated, anisotropically scaled matrix. */
s32 func_151B9310(Mtx *output, u8 *state) {
    f32 matrix[4][4];

    func_150A8050(matrix, 0.0f, 0.0f, *(f32 *)(state + 0x170));
    matrix[3][0] = *(f32 *)(state + 0x38);
    matrix[3][1] = *(f32 *)(state + 0x3C);
    matrix[3][2] = *(f32 *)(state + 0x40);
    matrix[0][0] *= *(f32 *)(state + 0x18);
    matrix[0][1] *= *(f32 *)(state + 0x18);
    matrix[0][2] *= *(f32 *)(state + 0x18);
    matrix[1][0] *= *(f32 *)(state + 0x1C);
    matrix[1][1] *= *(f32 *)(state + 0x1C);
    matrix[1][2] *= *(f32 *)(state + 0x1C);
    matrix[2][0] *= *(f32 *)(state + 0x18);
    matrix[2][1] *= *(f32 *)(state + 0x18);
    matrix[2][2] *= *(f32 *)(state + 0x18);
    guMtxF2L(matrix, output);
    return 1;
}"""


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    anchor = "#include <ultra64.h>\n"
    if source.count(anchor) != 1:
        raise ValueError("Anisotropic matrix submit include anchor changed")
    declarations = TYPES + DECLARATIONS + "\n"
    if source.count(PLACEHOLDER) == 1:
        if declarations in source or SELECTED_MATCH in source:
            raise ValueError("Anisotropic matrix submit predecessor source changed")
        return source.replace(PLACEHOLDER, body).replace(
            anchor, anchor + declarations, 1)
    if source.count(SELECTED_MATCH) == 1 and source.count(declarations) == 1:
        return source.replace(SELECTED_MATCH, body, 1)
    raise ValueError("Anisotropic matrix submit source state changed")


def variants():
    yield "typed", SELECTED
    yield "raw", RAW
    yield "typed-named-workspace", SELECTED_MATCH
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
    yield "typed-output-late", SELECTED.replace(
        "    f32 matrix[4][4];", "    Mtx *destination = output;\n    f32 matrix[4][4];").replace(
        "guMtxF2L(matrix, output);", "guMtxF2L(matrix, destination);")
    aligned_output_late = aligned.replace(
        "    union { u64 align; f32 values[4][4]; } matrix;",
        "    Mtx *destination = output;\n"
        "    union { u64 align; f32 values[4][4]; } matrix;").replace(
        "guMtxF2L(matrix.values, output);",
        "guMtxF2L(matrix.values, destination);")
    yield "typed-aligned-output-late", aligned_output_late
    padded_output_late = padded.replace(
        "    struct { u32 retained; f32 values[4][4]; } matrix;",
        "    Mtx *destination = output;\n"
        "    struct { u32 retained; f32 values[4][4]; } matrix;").replace(
        "guMtxF2L(matrix.values, output);",
        "guMtxF2L(matrix.values, destination);")
    yield "typed-padded-output-late", padded_output_late
    local_scales = SELECTED.replace(
        "    f32 matrix[4][4];",
        "    f32 matrix[4][4];\n    f32 horizontalScale;\n    f32 verticalScale;")
    local_scales = local_scales.replace(
        "    matrix[0][0] *= state->horizontalScale;",
        "    horizontalScale = state->horizontalScale;\n"
        "    verticalScale = state->verticalScale;\n"
        "    matrix[0][0] *= horizontalScale;")
    local_scales = local_scales.replace(
        "*= state->horizontalScale", "*= horizontalScale").replace(
        "*= state->verticalScale", "*= verticalScale")
    yield "typed-scales-local", local_scales
    yield "typed-columns", SELECTED.replace(
        "    matrix[0][1] *= state->horizontalScale;\n"
        "    matrix[0][2] *= state->horizontalScale;\n"
        "    matrix[1][0] *= state->verticalScale;\n"
        "    matrix[1][1] *= state->verticalScale;\n"
        "    matrix[1][2] *= state->verticalScale;\n"
        "    matrix[2][0] *= state->horizontalScale;\n"
        "    matrix[2][1] *= state->horizontalScale;",
        "    matrix[1][0] *= state->verticalScale;\n"
        "    matrix[2][0] *= state->horizontalScale;\n"
        "    matrix[0][1] *= state->horizontalScale;\n"
        "    matrix[1][1] *= state->verticalScale;\n"
        "    matrix[2][1] *= state->horizontalScale;\n"
        "    matrix[0][2] *= state->horizontalScale;\n"
        "    matrix[1][2] *= state->verticalScale;")


def compare(name, body, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(ROOT, output, source_with(body), name, flags=flags)
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
    for name, body in variants():
        for label, flags in (("o2g3", ("-O2", "-g3")), ("o2", ("-O2",))):
            record = compare(name + "-" + label, body, flags)
            records.append(record)
            print(record["name"], record["words"], record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
