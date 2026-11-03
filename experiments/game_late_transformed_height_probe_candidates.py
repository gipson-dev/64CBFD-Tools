"""Screen semantic C forms for func_151AF5C0's transformed height probe."""

import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x151AF5C0
ROM = 0x1DCA70
WORDS = 64
FUNCTION = "func_151AF5C0"
SOURCE = "conker/src/game/generated_1DCA70.c"
OWNER = "generated_1DCA70"
BUILD = "conker/build/game-late-transformed-height-probe-candidates"
ANCHOR = '#include <ultra64.h>\n'
DECLARATIONS = """
typedef struct HeightResult71820 HeightResult71820;
typedef struct HeightActor71820 HeightActor71820;
extern f32 D_800AA0F0[];
extern f32 D_800AA0FC[];
void func_15143134(f32 *, f32 *, u8 *);
void func_1504715C(HeightResult71820 *, HeightActor71820 *);
s32 func_15046C80(f32 *, u16, f32, HeightResult71820 *);
"""
PLACEHOLDER = """s32 func_151AF5C0() {
    return 0;
}"""
SELECTED = """/* Transform the selected actor offset and optionally query its height interval. */
s32 func_151AF5C0(f32 *position, u8 *actor, HeightResult71820 *result, u8 mode) {
    f32 start[3];
    f32 *point;
    u8 *matrix;

    if (mode != 1 && mode != 2) {
        return 0;
    }
    if (mode == 1) {
        point = D_800AA0FC;
    } else {
        point = D_800AA0F0;
    }
    if (mode == 1) {
        matrix = *(u8 **)(actor + 0x1D4) + 0x800;
    } else {
        matrix = *(u8 **)(actor + 0x1D4) + 0x640;
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


ROOT = Path(__file__).resolve().parents[2]


def source_states(live):
    if live.count(PLACEHOLDER) == 1:
        if SELECTED in live or DECLARATIONS in live:
            raise ValueError("Late transformed-height predecessor source changed")
        qualified = live.replace(ANCHOR, ANCHOR + DECLARATIONS, 1).replace(
            PLACEHOLDER, SELECTED, 1)
        return live, qualified, False
    if live.count(SELECTED) == 1:
        if live.count(DECLARATIONS) != 1 or PLACEHOLDER in live:
            raise ValueError("Installed late transformed-height source changed")
        predecessor = live.replace(DECLARATIONS, "", 1).replace(
            SELECTED, PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Late transformed-height source state changed")


def source_with(body):
    predecessor, _, _ = source_states((ROOT / SOURCE).read_text())
    return predecessor.replace(ANCHOR, ANCHOR + DECLARATIONS, 1).replace(
        PLACEHOLDER, body, 1)


def variants():
    yield "separate-branches-exact", SELECTED
    yield "ternary", SELECTED.replace(
        "    if (mode == 1) {\n"
        "        point = D_800AA0FC;\n"
        "    } else {\n"
        "        point = D_800AA0F0;\n"
        "    }\n"
        "    if (mode == 1) {\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0x800;\n"
        "    } else {\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0x640;\n"
        "    }",
        "    point = mode == 1 ? D_800AA0FC : D_800AA0F0;\n"
        "    matrix = *(u8 **)(actor + 0x1D4) + (mode == 1 ? 0x800 : 0x640);")
    yield "combined-branches", SELECTED.replace(
        "    if (mode == 1) {\n"
        "        point = D_800AA0FC;\n"
        "    } else {\n"
        "        point = D_800AA0F0;\n"
        "    }\n"
        "    if (mode == 1) {\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0x800;\n"
        "    } else {\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0x640;\n"
        "    }",
        "    if (mode == 1) {\n"
        "        point = D_800AA0FC;\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0x800;\n"
        "    } else {\n"
        "        point = D_800AA0F0;\n"
        "        matrix = *(u8 **)(actor + 0x1D4) + 0x640;\n"
        "    }")
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
    obj, diagnostics = compile_owner(
        ROOT, output, source_with(body), name, flags=flags)
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
        "linked_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


if __name__ == "__main__":
    records = []
    for name, body in variants():
        record = compare(name, body)
        records.append(record)
        print(record["name"], record["words"], record["frame"],
              record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(
        json.dumps(records, indent=2) + "\n")
