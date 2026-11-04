"""Screen semantic C forms for func_15191980's owner event dispatcher."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ENTRY = 0x15191980
ROM = 0x1BEE30
WORDS = 65
FUNCTION = "func_15191980"
SOURCE = "conker/src/game/generated_1BA1D0.c"
OWNER = "generated_1BA1D0"
BUILD = "conker/build/game-owner-event-dispatch-candidates"
RETAIL_BINDINGS = {
    0x0B0: [("R_MIPS_26", "func_1516972C")],
    0x0CC: [("R_MIPS_26", "func_1516972C")],
    0x0E8: [("R_MIPS_26", "func_15169850")],
}
PLACEHOLDER = """s32 func_15191980() {
    return 0;
}"""

TYPES = """typedef struct {
    u8 retained00[0x10];
    u8 *owner;
    u8 ownerId;
    u8 retained15;
    s16 timer;
    u8 flags;
} OwnerEventRecord15191980;

typedef struct {
    u8 *owner;
    u8 ownerId;
} OwnerEvent15191980;
"""

SELECTED = """/* Apply owner-scoped event state, release, or generic forwarding.
 * The volatile parameter reads preserve the callback's retail stack homes and
 * final command-byte reload; the owner tests and state changes remain C. */
void func_15191980(OwnerEventRecord15191980 *record,
                   OwnerEvent15191980 *volatile event, s32 rawCommand) {
    if (((u8 *)&rawCommand)[3] == 0x0D) {
        if (event->owner != record->owner && event->ownerId != record->ownerId) {
            return;
        }
        record->timer = 100;
        record->flags |= 1;
        return;
    }
    if (((u8 *)&rawCommand)[3] == 0x0C ||
        ((u8 *)&rawCommand)[3] == 0x50 ||
        ((u8 *)&rawCommand)[3] == 0x0E) {
        if (event->owner != record->owner && event->ownerId != record->ownerId) {
            return;
        }
        func_1516972C(record);
        return;
    }
    if (((u8 *)&rawCommand)[3] == 0x4E) {
        func_1516972C(record);
        return;
    }
    func_15169850((s32)event, ((volatile u8 *)&rawCommand)[3],
                  (s32)&record->owner, (s32)&record->ownerId, (s32)record);
}"""


def source_with(body):
    live = (ROOT / SOURCE).read_text()
    anchor = '#include "structs.h"\n'
    declarations = TYPES + "\n"
    if live.count(anchor) != 1:
        raise ValueError("Owner event dispatcher include anchor changed")
    if live.count(PLACEHOLDER) == 1:
        if declarations in live or SELECTED in live:
            raise ValueError("Owner event dispatcher predecessor source changed")
        return live.replace(anchor, anchor + declarations, 1).replace(
            PLACEHOLDER, body, 1)
    if live.count(SELECTED) == 1 and live.count(declarations) == 1:
        return live.replace(SELECTED, body, 1)
    raise ValueError("Owner event dispatcher source state changed")


def variants():
    yield "selected", SELECTED
    yield "without-final-volatile-reload", SELECTED.replace(
        "((volatile u8 *)&rawCommand)[3]",
        "((u8 *)&rawCommand)[3]", 1)
    yield "without-event-home", SELECTED.replace(
        "OwnerEvent15191980 *volatile event",
        "OwnerEvent15191980 *event", 1)
    yield "wrong-release-order", SELECTED.replace(
        "0x0C ||\n        ((u8 *)&rawCommand)[3] == 0x50 ||\n"
        "        ((u8 *)&rawCommand)[3] == 0x0E",
        "0x0C ||\n        ((u8 *)&rawCommand)[3] == 0x0E ||\n"
        "        ((u8 *)&rawCommand)[3] == 0x50", 1)


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
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
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
        "object_differences": object_differences,
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
