"""Screen semantic C forms for func_150B709C's diagonal menu-record update."""

import hashlib
import itertools
import json
import struct
from pathlib import Path

from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.experiments.game_remaining_donor_candidates import link_owner


ENTRY = 0x150B709C
ROM = 0xE454C
WORDS = 67
FUNCTION = "func_150B709C"
SOURCE = "conker/src/game/generated_E4070.c"
OWNER = "generated_E4070"
BUILD = "conker/build/game-menu-record-diagonal-fade-candidates"
TYPES = """typedef struct {
    u8 retained00[0x18];
    s32 progress;
    u8 retained1C[0x10];
    f32 xPosition;
    f32 yPosition;
    u8 retained34[0x11];
    u8 opacity;
} DiagonalMenuRecord150B709C;
typedef struct {
    u8 retained00[0x18];
    s32 progress;
    u8 retained1C[0x10];
    volatile f32 xPosition;
    volatile f32 yPosition;
    u8 retained34[0x11];
    u8 opacity;
} VolatileDiagonalMenuRecord150B709C;
"""
PLACEHOLDER = """s32 func_150B709C() {
    return 0;
}"""
SELECTED = """/* Advance the diagonal menu entry and pulse its terminal opacity. */
void func_150B709C(DiagonalMenuRecord150B709C *record) {
    s32 progress = record->progress;

    if (progress == 30) {
        s32 opacity = record->opacity;

        opacity += D_800BE9E4 * 8;
        if (opacity >= 256) {
            opacity = 0;
        }
        record->opacity = opacity;
    }
    progress += D_800BE9E4 * 2;
    if (progress >= 31) {
        progress = 30;
    }
    record->progress = progress;
    record->xPosition = (f32)((progress * -84) / 30 + 230);
    record->yPosition = (f32)((progress * -50) / 30 + 170);
}"""
RAW = """/* Advance the diagonal menu entry and pulse its terminal opacity. */
void func_150B709C(u8 *record) {
    s32 progress = *(s32 *)(record + 0x18);

    if (progress == 30) {
        s32 opacity = record[0x45] + D_800BE9E4 * 8;
        if (opacity >= 256) {
            opacity = 0;
        }
        record[0x45] = opacity;
    }
    progress += D_800BE9E4 * 2;
    if (progress >= 31) {
        progress = 30;
    }
    *(s32 *)(record + 0x18) = progress;
    *(f32 *)(record + 0x2C) = (f32)((-progress * 84) / 30 + 230);
    *(f32 *)(record + 0x30) = (f32)((-progress * 50) / 30 + 170);
}"""


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    anchor = "#include <ultra64.h>\n"
    if source.count(anchor) != 1:
        raise ValueError("Diagonal menu-record include anchor changed")
    if source.count(PLACEHOLDER) == 1:
        if TYPES in source or SELECTED in source:
            raise ValueError("Diagonal menu-record predecessor source changed")
        return source.replace(anchor, anchor + TYPES, 1).replace(
            PLACEHOLDER, body, 1)
    if source.count(SELECTED) == 1 and source.count(TYPES) == 1:
        return source.replace(SELECTED, body, 1)
    raise ValueError("Diagonal menu-record source state changed")


def variants():
    yield "typed-exact", SELECTED
    yield "raw", RAW
    yield "typed-combined-opacity", SELECTED.replace(
        "        s32 opacity = record->opacity;\n\n"
        "        opacity += D_800BE9E4 * 8;",
        "        s32 opacity = record->opacity + D_800BE9E4 * 8;")
    yield "typed-shared-negation", SELECTED.replace(
        "progress * -84", "-progress * 84").replace(
        "progress * -50", "-progress * 50")
    yield "typed-negative-products", SELECTED.replace(
        "progress * -84", "-(progress * 84)").replace(
        "progress * -50", "-(progress * 50)")
    yield "typed-leading-negative-constants", SELECTED.replace(
        "progress * -84", "-84 * progress").replace(
        "progress * -50", "-50 * progress")
    yield "typed-base-first", SELECTED.replace(
        "(progress * -84) / 30 + 230", "230 + (progress * -84) / 30").replace(
        "(progress * -50) / 30 + 170", "170 + (progress * -50) / 30")
    yield "typed-subtractive", SELECTED.replace(
        "(progress * -84) / 30 + 230", "230 - (progress * 84) / 30").replace(
        "(progress * -50) / 30 + 170", "170 - (progress * 50) / 30")
    yield "typed-outer-opacity", SELECTED.replace(
        "    s32 progress = record->progress;",
        "    s32 opacity;\n    s32 progress = record->progress;").replace(
        "        s32 opacity = record->opacity;", "        opacity = record->opacity;")
    yield "typed-volatile-positions", SELECTED.replace(
        "DiagonalMenuRecord150B709C *record",
        "VolatileDiagonalMenuRecord150B709C *record")


def compare(name, body, flags=("-O2", "-g3", "-Wo,-loopunroll,0")):
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
    for name, body in variants():
        record = compare(name, body)
        records.append(record)
        print(record["name"], record["words"], record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
