"""Screen semantic C forms for func_15195984's packed-layout allocator."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.pad_generated_object import parse_object


ENTRY = 0x15195984
ROM = 0x1C2E34
WORDS = 64
FUNCTION = "func_15195984"
SOURCE = "conker/src/game/generated_1C2C60.c"
OWNER = "generated_1C2C60"
BUILD = "conker/build/game-packed-layout-record-allocator-candidates"
RETAIL_BINDINGS = {
    0x028: [("R_MIPS_26", "func_151957B0")],
    0x018: [("R_MIPS_HI16", "D_800E08E8")],
    0x024: [("R_MIPS_LO16", "D_800E08E8")],
    0x01C: [("R_MIPS_HI16", "D_800E08EC")],
    0x020: [("R_MIPS_LO16", "D_800E08EC")],
}
PLACEHOLDER = """s32 func_15195984() {
    return 0;
}"""

TYPES = """typedef struct {
    u8 retained00[0x08];
    s16 key;
    s16 width;
    s16 height;
    s16 scaledX;
    s16 scaledY;
    u8 retained12[0x02];
    u8 active;
    u8 retained15[0x03];
    s32 link;
    s16 primary[5];
    s16 secondary0;
    s16 secondary1;
    s16 secondary2;
    s16 secondary3;
    s16 secondary4;
    u8 retained30[0x0C];
} PackedLayoutRecord15195984;
"""

SELECTED = """/* Allocate and initialize a record from two packed 12-bit pairs. */
PackedLayoutRecord15195984 *func_15195984(s32 key, s32 packedSize,
                                          s32 packedScale, s32 doubleSize) {
    PackedLayoutRecord15195984 *record;
    s32 index;
    s32 width;
    s32 height;

    record = (PackedLayoutRecord15195984 *)func_151957B0(
        0x3C, (u8 *)&D_800E08E8, (u8 *)&D_800E08EC);
    if (record != NULL) {
        record->link = 0;
        for (index = 0; index < 5; index++) {
            record->primary[index] = -1;
        }
        record->secondary0 = -1;
        record->secondary2 = -1;
        record->secondary3 = -1;
        record->secondary4 = -1;
        record->secondary1 = -1;
        record->key = key;
        width = ((packedSize >> 12) & 0xFFF) + 2;
        height = (packedSize & 0xFFF) + 2;
        if (doubleSize != 0) {
            width *= 2;
            height *= 2;
        }
        record->scaledX = (packedScale >> 12) & 0xFFF;
        record->scaledY = packedScale & 0xFFF;
        record->width = width;
        record->height = height;
        record->scaledX *= 8;
        record->scaledY *= 8;
        record->active = 1;
    }
    return record;
}"""

POINTER_SHAPE = """/* Allocate and initialize a record from two packed 12-bit pairs. */
void *func_15195984(s32 key, s32 packedSize, s32 packedScale, s32 doubleSize) {
    s16 widthBase;
    s16 heightBase;
    s16 scaledX;
    s16 scaledY;
    s16 width;
    s16 height;
    s32 index;
    u8 *record;
    u8 *secondary;
    u8 *cursor;

    record = (u8 *)func_151957B0(
        0x3C, (u8 *)&D_800E08E8, (u8 *)&D_800E08EC);
    if (record != NULL) {
        *(s32 *)(record + 0x18) = 0;
        index = 0;
        cursor = record;
        do {
            index += 1;
            cursor += 2;
            *(s16 *)(cursor + 0x1A) = -1;
        } while (index < 5);
        *(s16 *)(record + 0x26) = -1;
        secondary = record + 2;
        *(s16 *)(secondary + 0x28) = -1;
        *(s16 *)(secondary + 0x2A) = -1;
        *(s16 *)(secondary + 0x2C) = -1;
        *(s16 *)(secondary + 0x26) = -1;
        *(s16 *)(record + 0x08) = key;
        widthBase = ((packedSize >> 12) & 0xFFF) + 2;
        heightBase = (packedSize & 0xFFF) + 2;
        width = widthBase;
        height = heightBase;
        if (doubleSize != 0) {
            width = widthBase * 2;
            height = heightBase * 2;
        }
        scaledX = (packedScale >> 12) & 0xFFF;
        scaledY = packedScale & 0xFFF;
        *(s16 *)(record + 0x0E) = scaledX;
        *(s16 *)(record + 0x10) = scaledY;
        *(s16 *)(record + 0x0A) = width;
        *(s16 *)(record + 0x0C) = height;
        *(s16 *)(record + 0x0E) = scaledX * 8;
        *(s16 *)(record + 0x10) = scaledY * 8;
        record[0x14] = 1;
    }
    return record;
}"""


def source_with(body):
    live = (ROOT / SOURCE).read_text()
    anchor = "#include <ultra64.h>\n"
    declarations = TYPES + "\n"
    if live.count(anchor) != 1:
        raise ValueError("Packed-layout allocator include anchor changed")
    if live.count(PLACEHOLDER) == 1:
        if declarations in live or SELECTED in live:
            raise ValueError("Packed-layout allocator predecessor source changed")
        return live.replace(anchor, anchor + declarations, 1).replace(
            PLACEHOLDER, body, 1)
    if live.count(SELECTED) == 1 and live.count(declarations) == 1:
        return live.replace(SELECTED, body, 1)
    raise ValueError("Packed-layout allocator source state changed")


def variants():
    yield "pointer-shape", POINTER_SHAPE
    yield "selected", SELECTED
    yield "assign-scaled-last", SELECTED.replace(
        "        record->scaledX = (packedScale >> 12) & 0xFFF;\n"
        "        record->scaledY = packedScale & 0xFFF;\n"
        "        record->width = width;\n"
        "        record->height = height;\n",
        "        record->width = width;\n"
        "        record->height = height;\n"
        "        record->scaledX = (packedScale >> 12) & 0xFFF;\n"
        "        record->scaledY = packedScale & 0xFFF;\n", 1)
    yield "secondary-linear", SELECTED.replace(
        "        record->secondary0 = -1;\n"
        "        record->secondary2 = -1;\n"
        "        record->secondary3 = -1;\n"
        "        record->secondary4 = -1;\n"
        "        record->secondary1 = -1;\n",
        "        record->secondary0 = -1;\n"
        "        record->secondary1 = -1;\n"
        "        record->secondary2 = -1;\n"
        "        record->secondary3 = -1;\n"
        "        record->secondary4 = -1;\n", 1)


def compare(name, body, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(ROOT, output, source_with(body), name,
                                     flags=flags)
    text, object_functions, relocations = parse_object(obj)
    object_info = object_functions[FUNCTION]
    object_start = object_info["value"]
    object_bytes = text[object_start:object_start + object_info["size"]]
    bindings = {
        offset - object_start: rows for offset, rows in relocations.items()
        if object_start <= offset < object_start + object_info["size"]
    }
    linked, functions = link_owner(ROOT, output, obj, OWNER)
    info = functions[FUNCTION]
    ours = linked[info["value"]:info["value"] + info["size"]]
    retail = (ROOT / "conker/conker.us.bin").read_bytes()[ROM:ROM + WORDS * 4]
    our_words = struct.unpack(">%dI" % (len(ours) // 4), ours)
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    retail_object = bytearray(retail)
    for offset, rows in RETAIL_BINDINGS.items():
        kind = rows[0][0]
        mask = 0xFC000000 if kind == "R_MIPS_26" else 0xFFFF0000
        word = struct.unpack_from(">I", retail_object, offset)[0] & mask
        struct.pack_into(">I", retail_object, offset, word)
    object_padded = object_bytes.ljust(WORDS * 4, b"\0")[:WORDS * 4]
    object_words = struct.unpack(">%dI" % WORDS, object_padded)
    retail_object_words = struct.unpack(">%dI" % WORDS, retail_object)
    object_differences = [
        {
            "offset": index * 4,
            "expected": left,
            "replacement": right,
            "expected_relocations": bindings.get(index * 4, []),
            "replacement_relocations": RETAIL_BINDINGS.get(index * 4, []),
        }
        for index, (left, right) in enumerate(zip(object_words, retail_object_words))
        if left != right or bindings.get(index * 4, []) != RETAIL_BINDINGS.get(index * 4, [])
    ]
    differences = [
        {"offset": index * 4, "ours": left, "retail": right}
        for index, (left, right) in enumerate(
            itertools.zip_longest(our_words, retail_words, fillvalue=0))
        if left != right
    ]
    frame = 0
    if our_words and our_words[0] >> 16 == 0x27BD:
        frame = (-our_words[0]) & 0xFFFF
    return {
        "name": name, "flags": flags, "words": len(our_words), "frame": frame,
        "differences": len(differences), "difference_rows": differences,
        "object_differences": object_differences, "diagnostics": diagnostics,
        "object_raw_sha256": hashlib.sha256(object_bytes).hexdigest(),
        "bindings": {"0x%03X" % offset: rows
                     for offset, rows in sorted(bindings.items())},
        "raw_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


ROOT = Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    records = []
    selected = os.environ.get("CANDIDATE_FILTER")
    profiles = (("o2g3", ("-O2", "-g3")), ("o2", ("-O2",)))
    for name, body in variants():
        if selected and name != selected:
            continue
        for label, flags in profiles:
            record = compare(name + "-" + label, body, flags)
            records.append(record)
            print(record["name"], record["words"], record["frame"],
                  record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
