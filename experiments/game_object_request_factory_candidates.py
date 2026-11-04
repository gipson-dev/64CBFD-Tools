"""Screen semantic C forms for func_1515BE50's object-request factory."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ENTRY = 0x1515BE50
ROM = 0x189300
WORDS = 64
FUNCTION = "func_1515BE50"
SOURCE = "conker/src/game/generated_188F90.c"
OWNER = "generated_188F90"
BUILD = "conker/build/game-object-request-factory-candidates"
PLACEHOLDER = """s32 func_1515BE50() {
    return 0;
}"""

TYPES = """typedef struct {
    u8 retained00[0x14];
    f32 x;
    f32 y;
    f32 z;
} RequestedObject1515BE50;

typedef struct {
    RequestedObject1515BE50 *object;
    u8 uniqueId;
    u8 retained05;
    u16 size;
} ObjectRequest1515BE50;

typedef struct {
    u8 retained00[0x10];
    s32 active;
    s32 state;
    ObjectRequest1515BE50 request;
    f32 currentX;
    f32 currentY;
    f32 currentZ;
    f32 previousX;
    f32 previousY;
    f32 previousZ;
    f32 velocityX;
    f32 velocityY;
    f32 velocityZ;
    s32 listState;
    s32 listIndex;
} ObjectFollowRecord1515BE50;

void *func_15167A68(s32, s32, s32, s32, u8, u8);
"""

SELECTED = """/* Allocate a tracking record for an object request and seed both positions. */
ObjectFollowRecord1515BE50 *func_1515BE50(ObjectRequest1515BE50 *request,
                                          s32 extraBytes, u8 channel,
                                          s32 context) {
    ObjectFollowRecord1515BE50 *record;

    if (request->object == NULL) {
        return NULL;
    }
    record = func_15167A68(0x32, context, extraBytes + 0x50, 1, channel, 1);
    if (record == NULL) {
        return NULL;
    }
    memcpy(&record->request, request, sizeof(*request));
    record->currentX = request->object->x;
    record->currentY = request->object->y;
    record->currentZ = request->object->z;
    record->previousX = request->object->x;
    record->previousY = request->object->y;
    record->previousZ = request->object->z;
    record->listState = 0;
    record->listIndex = -1;
    record->active = 1;
    record->state = 0;
    record->velocityX = 0.0f;
    record->velocityY = 0.0f;
    record->velocityZ = 0.0f;
    return record;
}"""


def source_with(body, types=TYPES):
    source = (ROOT / SOURCE).read_text()
    anchor = '#include "structs.h"\n'
    declarations = types + "\n"
    if source.count(anchor) != 1:
        raise ValueError("Object-request factory include anchor changed")
    if source.count(PLACEHOLDER) == 1:
        if declarations in source or SELECTED in source:
            raise ValueError("Object-request factory predecessor source changed")
        return source.replace(anchor, anchor + "\n" + declarations, 1).replace(
            PLACEHOLDER, body, 1)
    if source.count(SELECTED) == 1 and source.count(declarations) == 1:
        return source.replace(SELECTED, body, 1)
    raise ValueError("Object-request factory source state changed")


def variants():
    yield "typed", SELECTED
    yield "typed-void-return", SELECTED.replace(
        "ObjectFollowRecord1515BE50 *func_1515BE50", "void *func_1515BE50", 1)
    yield "typed-s32-return", SELECTED.replace(
        "ObjectFollowRecord1515BE50 *func_1515BE50", "s32 func_1515BE50", 1).replace(
        "        return NULL;", "        return 0;", 2).replace(
        "    return record;", "    return (s32)record;", 1)
    yield "explicit-eight", SELECTED.replace(
        "memcpy(&record->request, request, sizeof(*request));",
        "memcpy(&record->request, request, 8);")
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
        "frame": (-struct.unpack_from(">I", ours)[0]) & 0xFFFF,
        "differences": len(differences),
        "difference_rows": differences,
        "diagnostics": diagnostics,
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
    for name, body in variants():
        if selected and name != selected:
            continue
        for label, flags in (("o2g3", ("-O2", "-g3")), ("o2", ("-O2",))):
            record = compare(name + "-" + label, body, flags)
            records.append(record)
            print(record["name"], record["words"], record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
