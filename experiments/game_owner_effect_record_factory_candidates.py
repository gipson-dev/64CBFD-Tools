"""Screen semantic C shapes for the owner-bound effect-record factory."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_actor_classifier_candidates import PROFILES
from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ENTRY, ROM, WORDS = 0x15158BD0, 0x186080, 65
FUNCTION = "func_15158BD0"
SOURCE = "conker/src/game/generated_185560.c"
OWNER = "generated_185560"
BUILD = "conker/build/game-owner-effect-record-factory-candidates"
PLACEHOLDER = "s32 func_15158BD0() {\n    return 0;\n}"
DECLARATIONS = """typedef struct {
    u8 header[0x10];
    s32 active;
    s32 state;
    u8 *owner;
    u8 ownerId;
    u8 classification;
    u8 pad1E[2];
    f32 x;
    f32 y;
    f32 z;
    u8 class0;
    u8 class1;
    u8 class2;
    u8 class3;
    u8 zero;
    u8 enabled;
    u8 pad32[0x1E];
    u8 tail;
    u8 pad51[7];
} OwnerEffectRecord15158BD0;

void *func_15167A68();
s32 func_15159370();
void func_1516979C(void *);
"""

SIGNATURE = (
    "OwnerEffectRecord15158BD0 *func_15158BD0("
    "u8 *owner, u8 enabled, s32 extraBytes)"
)

TYPED_BODY = SIGNATURE + """ {
    OwnerEffectRecord15158BD0 *record;

    if (owner == NULL) {
        return NULL;
    }
    record = func_15167A68(0x2E, 0, extraBytes + 0x58, 1, 0xFF, 1);
    if (record == NULL) {
        return NULL;
    }
    record->owner = owner;
    record->class0 = 2;
    record->class1 = 2;
    record->class2 = 2;
    record->class3 = 3;
    record->zero = 0;
    record->ownerId = owner[0x3B];
    record->x = *(f32 *)(owner + 0x14);
    record->y = *(f32 *)(owner + 0x18);
    record->enabled = 0;
    record->z = *(f32 *)(owner + 0x1C);
    if (enabled != 0) {
        record->enabled = 1;
    }
    record->active = 1;
    record->state = 0;
    if (func_15159370(owner, &record->classification, record) == 0) {
        func_1516979C(record);
        return NULL;
    }
    record->tail = 0;
    return record;
}
"""

RAW_BODY = SIGNATURE + """ {
    u8 *record;

    if (owner == NULL) {
        return NULL;
    }
    record = func_15167A68(0x2E, 0, extraBytes + 0x58, 1, 0xFF, 1);
    if (record == NULL) {
        return NULL;
    }
    *(u8 **)(record + 0x18) = owner;
    record[0x2C] = 2;
    record[0x2D] = 2;
    record[0x2E] = 2;
    record[0x2F] = 3;
    record[0x30] = 0;
    record[0x1C] = owner[0x3B];
    *(f32 *)(record + 0x20) = *(f32 *)(owner + 0x14);
    *(f32 *)(record + 0x24) = *(f32 *)(owner + 0x18);
    record[0x31] = 0;
    *(f32 *)(record + 0x28) = *(f32 *)(owner + 0x1C);
    if (enabled != 0) {
        record[0x31] = 1;
    }
    *(s32 *)(record + 0x10) = 1;
    *(s32 *)(record + 0x14) = 0;
    if (func_15159370(owner, record + 0x1D, record) == 0) {
        func_1516979C(record);
        return NULL;
    }
    record[0x50] = 0;
    return (OwnerEffectRecord15158BD0 *)record;
}
"""

SELECTED = TYPED_BODY.replace(
    SIGNATURE,
    "/* Allocate and initialize an owner-bound type-0x2E effect record. */\n" + SIGNATURE,
    1,
)


def candidates():
    yield "typed", TYPED_BODY
    yield "raw", RAW_BODY
    yield "typed-no-explicit-free", TYPED_BODY
    yield "typed-class-chain", TYPED_BODY.replace(
        "    record->class0 = 2;\n"
        "    record->class1 = 2;\n"
        "    record->class2 = 2;",
        "    record->class0 = record->class1 = record->class2 = 2;",
        1,
    )
    yield "raw-class-chain", RAW_BODY.replace(
        "    record[0x2C] = 2;\n"
        "    record[0x2D] = 2;\n"
        "    record[0x2E] = 2;",
        "    record[0x2C] = record[0x2D] = record[0x2E] = 2;",
        1,
    )


ROOT = Path(__file__).resolve().parents[2]


def source_with(body):
    live = (ROOT / SOURCE).read_text()
    marker = "void func_100043B4(s32 *, u32);\n"
    if live.count(PLACEHOLDER) == 1:
        if live.count(marker) != 1 or DECLARATIONS in live or SELECTED in live:
            raise ValueError("Owner-effect factory predecessor source changed")
        return live.replace(marker, marker + "\n" + DECLARATIONS, 1).replace(
            PLACEHOLDER, body, 1
        )
    if live.count(SELECTED) == 1:
        if live.count(DECLARATIONS) != 1 or PLACEHOLDER in live:
            raise ValueError("Installed owner-effect factory source changed")
        return live.replace(SELECTED, body, 1)
    raise ValueError("Owner-effect factory source state changed")


def compare(name, body, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(
        ROOT, output, source_with(body), name, flags=flags
    )
    text, functions, relocations = parse_object(obj)
    info = functions[FUNCTION]
    start, size = info["value"], info["size"]
    object_bytes = text[start:start + size]
    bindings = {
        offset - start: rows for offset, rows in relocations.items()
        if start <= offset < start + size
    }
    linked, linked_functions = link_owner(ROOT, output, obj, OWNER)
    linked_info = linked_functions[FUNCTION]
    ours = linked[
        linked_info["value"]:linked_info["value"] + linked_info["size"]
    ]
    retail = (ROOT / "conker/conker.us.bin").read_bytes()[ROM:ROM + WORDS * 4]
    our_words = struct.unpack(">%dI" % (len(ours) // 4), ours)
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    differences = [
        {"offset": index * 4, "ours": left, "retail": right}
        for index, (left, right) in enumerate(
            itertools.zip_longest(our_words, retail_words, fillvalue=0)
        ) if left != right
    ]
    frame = next(((-word) & 0xFFFF for word in our_words
                  if word & 0xFFFF0000 == 0x27BD0000 and word & 0x8000), 0)
    return {
        "name": name,
        "flags": flags,
        "words": len(our_words),
        "frame": frame,
        "differences": len(differences),
        "difference_rows": differences,
        "diagnostics": diagnostics,
        "object_raw_sha256": hashlib.sha256(object_bytes).hexdigest(),
        "bindings": {
            "0x%03X" % offset: rows for offset, rows in sorted(bindings.items())
        },
        "raw_sha256": hashlib.sha256(ours).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=[name for name, _ in candidates()])
    parser.add_argument("--profile", choices=PROFILES, default="o2g3")
    args = parser.parse_args()
    records = []
    for name, body in candidates():
        if args.candidate is not None and name != args.candidate:
            continue
        record = compare(name + "-" + args.profile, body, PROFILES[args.profile])
        records.append(record)
        print(name, record["words"], hex(record["frame"]),
              record["differences"], flush=True)
        for row in record["difference_rows"]:
            print("+0x%03X %08X %08X" % (
                row["offset"], row["ours"], row["retail"]
            ))
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
