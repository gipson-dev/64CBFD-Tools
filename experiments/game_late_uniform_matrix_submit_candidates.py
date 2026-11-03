"""Screen semantic C forms for func_1518A914's uniform matrix submit."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x1518A914
ROM = 0x1B7DC4
WORDS = 63
FUNCTION = "func_1518A914"
SOURCE = "conker/src/game/generated_1B7870.c"
OWNER = "generated_1B7870"
BUILD = "conker/build/game-late-uniform-matrix-submit-candidates"
DECLARATIONS = """
void func_150A8050(f32 matrix[4][4], f32, f32, f32);
"""
TYPES = """typedef struct {
    u8 retained00[0x48];
    f32 xPosition;
    f32 yPosition;
    f32 zPosition;
    u8 retained54[0xAC];
    f32 xRotation;
    f32 yRotation;
    f32 zRotation;
    f32 uniformScale;
} UniformMatrixState1518A914;
"""
PLACEHOLDER = """s32 func_1518A914() {
    return 0;
}"""
SELECTED = """/* Build and submit the state's translated, uniformly scaled matrix. */
s32 func_1518A914(Mtx *output, UniformMatrixState1518A914 *state) {
    f32 *rotation;
    f32 matrix[4][4];

    rotation = &state->xRotation;
    func_150A8050(matrix, rotation[0], rotation[1], rotation[2]);
    matrix[3][0] = state->xPosition;
    matrix[3][1] = state->yPosition;
    matrix[3][2] = state->zPosition;
    matrix[0][0] *= rotation[3];
    matrix[0][1] *= rotation[3];
    matrix[0][2] *= rotation[3];
    matrix[1][0] *= rotation[3];
    matrix[1][1] *= rotation[3];
    matrix[1][2] *= rotation[3];
    matrix[2][0] *= rotation[3];
    matrix[2][1] *= rotation[3];
    matrix[2][2] *= rotation[3];
    guMtxF2L(matrix, output);
    return 1;
}"""
INSTALL_TYPES = TYPES
SELECTED_POINTER_BEFORE = SELECTED
DIRECT = SELECTED.replace(
    "    f32 *rotation;\n    f32 matrix[4][4];\n\n    rotation = &state->xRotation;",
    "    f32 matrix[4][4];").replace(
    "rotation[0], rotation[1], rotation[2]",
    "state->xRotation, state->yRotation, state->zRotation").replace(
    "rotation[3]", "state->uniformScale")
POINTER_AFTER = SELECTED.replace(
    "    f32 *rotation;\n    f32 matrix[4][4];",
    "    f32 matrix[4][4];\n    f32 *rotation;")
POINTER_INITIALIZER = SELECTED.replace(
    "    f32 *rotation;\n    f32 matrix[4][4];\n\n    rotation = &state->xRotation;",
    "    f32 *rotation = &state->xRotation;\n    f32 matrix[4][4];")
RAW = SELECTED.replace(
    "UniformMatrixState1518A914 *state", "u8 *state").replace(
    "    f32 *rotation;\n    f32 matrix[4][4];\n\n    rotation = &state->xRotation;",
    "    f32 *rotation = (f32 *)(state + 0x100);\n    f32 matrix[4][4];").replace(
    "state->xPosition", "*(f32 *)(state + 0x48)").replace(
    "state->yPosition", "*(f32 *)(state + 0x4C)").replace(
    "state->zPosition", "*(f32 *)(state + 0x50)")


ROOT = Path(__file__).resolve().parents[2]


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    marker = "#include <ultra64.h>\n"
    declarations = TYPES + DECLARATIONS + "\n"
    if source.count(PLACEHOLDER) == 1:
        if declarations in source or SELECTED in source:
            raise ValueError("Late uniform matrix submit predecessor source changed")
        return source.replace(marker, marker + declarations, 1).replace(
            PLACEHOLDER, body, 1)
    if source.count(SELECTED) == 1 and source.count(declarations) == 1:
        return source.replace(SELECTED, body, 1)
    raise ValueError("Late uniform matrix submit source state changed")


def variants():
    yield "pointer-before", SELECTED
    yield "direct", DIRECT
    yield "pointer-after", POINTER_AFTER
    yield "pointer-initializer", POINTER_INITIALIZER
    yield "raw", RAW


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
    for name, body in variants():
        if selected and name != selected:
            continue
        for label, flags in (("o2g3", ("-O2", "-g3")), ("o2", ("-O2",))):
            record = compare(name + "-" + label, body, flags)
            records.append(record)
            print(record["name"], record["words"], record["frame"],
                  record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
