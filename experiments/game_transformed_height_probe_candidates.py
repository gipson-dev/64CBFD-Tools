"""Screen semantic C forms for func_150CB0E0's transformed height probe."""

import hashlib
import itertools
import json
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x150CB0E0
ROM = 0xF8590
WORDS = 64
FUNCTION = "func_150CB0E0"
SOURCE = "conker/src/game/generated_F8590.c"
OWNER = "generated_F8590"
BUILD = "conker/build/game-transformed-height-probe-candidates"
ANCHOR = "#include \"variables.h\"\n"
DECLARATIONS = """
typedef struct HeightResult71820 HeightResult71820;
typedef struct HeightActor71820 HeightActor71820;
extern f32 D_800A05E0[];
extern f32 D_800A05EC[];
void func_15143134(f32 *, f32 *, u8 *);
void func_1504715C(HeightResult71820 *, HeightActor71820 *);
s32 func_15046C80(f32 *, u16, f32, HeightResult71820 *);
"""
PLACEHOLDER = """s32 func_150CB0E0() {
    return 0;
}"""
SELECTED = """/* Transform the selected actor offset and optionally query its height interval. */
s32 func_150CB0E0(f32 *position, u8 *actor, HeightResult71820 *result, u8 mode) {
    f32 start[3];
    f32 *point;
    u8 *matrix;

    if (mode != 1 && mode != 2) {
        return 0;
    }
    if (mode == 1) {
        point = D_800A05EC;
    } else {
        point = D_800A05E0;
    }
    if (mode == 1) {
        matrix = *(u8 **)(actor + 0x1D4) + 0xA00;
    } else {
        matrix = *(u8 **)(actor + 0x1D4) + 0xBC0;
    }
    func_15143134(point, position, matrix);
    if (result == NULL) {
        return 1;
    }
    start[0] = position[0];
    start[1] = position[1] + 100.0f;
    start[2] = position[2];
    func_1504715C(result, (HeightActor71820 *)actor);
    return func_15046C80(start, 0, position[1] - 500.0f, result);
}"""


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    if source.count(ANCHOR) != 1 or source.count(PLACEHOLDER) != 1:
        raise ValueError("Transformed height probe predecessor source changed")
    if DECLARATIONS in source or SELECTED in source:
        raise ValueError("Transformed height probe declarations already installed")
    return source.replace(ANCHOR, ANCHOR + DECLARATIONS, 1).replace(
        PLACEHOLDER, body, 1)


def variants():
    yield "separate-branches-exact", SELECTED
    yield "ternary", SELECTED.replace(
        "    if (mode == 1) {\n"
        "        point = D_800A05EC;\n"
        "    } else {\n"
        "        point = D_800A05E0;\n"
        "    }\n"
        "    if (mode == 1) {\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0xA00;\n"
        "    } else {\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0xBC0;\n"
        "    }",
        "    point = mode == 1 ? D_800A05EC : D_800A05E0;\n"
        "    matrix = *(u8 **)(actor + 0x1D4) + (mode == 1 ? 0xA00 : 0xBC0);")
    yield "combined-branches", SELECTED.replace(
        "    if (mode == 1) {\n"
        "        point = D_800A05EC;\n"
        "    } else {\n"
        "        point = D_800A05E0;\n"
        "    }\n"
        "    if (mode == 1) {\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0xA00;\n"
        "    } else {\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0xBC0;\n"
        "    }",
        "    if (mode == 1) {\n"
        "        point = D_800A05EC;\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0xA00;\n"
        "    } else {\n"
        "        point = D_800A05E0;\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0xBC0;\n"
        "    }")
    yield "inline-call", SELECTED.replace(
        "    if (mode == 1) {\n"
        "        point = D_800A05EC;\n"
        "    } else {\n"
        "        point = D_800A05E0;\n"
        "    }\n"
        "    if (mode == 1) {\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0xA00;\n"
        "    } else {\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0xBC0;\n"
        "    }\n"
        "    func_15143134(point, position, matrix);",
        "    func_15143134(mode == 1 ? D_800A05EC : D_800A05E0, position,\n"
        "        *(u8 **)(actor + 0x1D4) + (mode == 1 ? 0xA00 : 0xBC0));").replace(
            "    f32 *point;\n    u8 *matrix;\n", "")
    yield "result-before-start", SELECTED.replace(
        "    start[0] = position[0];\n"
        "    start[1] = position[1] + 100.0f;\n"
        "    start[2] = position[2];\n"
        "    func_1504715C(result, (HeightActor71820 *)actor);",
        "    func_1504715C(result, (HeightActor71820 *)actor);\n"
        "    start[0] = position[0];\n"
        "    start[1] = position[1] + 100.0f;\n"
        "    start[2] = position[2];")


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
        "linked_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


ROOT = Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    records = []
    for name, body in variants():
        record = compare(name, body)
        records.append(record)
        print(record["name"], record["words"], record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
