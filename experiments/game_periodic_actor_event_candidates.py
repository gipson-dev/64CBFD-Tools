"""Screen semantic C forms for func_151905BC's periodic actor event callback."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ENTRY = 0x151905BC
ROM = 0x1BDA6C
WORDS = 66
FUNCTION = "func_151905BC"
SOURCE = "conker/src/game/generated_1BA1D0.c"
OWNER = "generated_1BA1D0"
BUILD = "conker/build/game-periodic-actor-event-candidates"
PLACEHOLDER = """s32 func_151905BC() {
    return 0;
}"""

FLAT_TYPE = """typedef struct {
    u8 retained00[0x10];
    struct127 *owner;
    u8 retained14[0x7C];
    s32 period;
    s32 elapsed;
    struct127 *eventTarget;
} PeriodicActorEvent151905BC;
"""

TYPES = """typedef struct {
    s32 period;
    s32 elapsed;
    struct127 *eventTarget;
} PeriodicActorEventClock151905BC;

typedef struct {
    u8 retained00[0x10];
    struct127 *owner;
    u8 retained14[0x7C];
    PeriodicActorEventClock151905BC clock;
} PeriodicActorEventNested151905BC;

s32 func_1505D024(struct127 *, s32, u16, s32);
extern struct127 D_800CC2D0[];
"""

FLAT = """/* Emit one actor event per elapsed period and refresh the attached target. */
s32 func_151905BC(PeriodicActorEvent151905BC *record) {
    struct126 *attached;

    record->elapsed += D_800BE9E4;
    while (record->elapsed >= record->period) {
        func_1505D024(record->owner, 0x60021, 0,
                      ((s32)record->eventTarget - (s32)D_800CC2D0) /
                          (s32)sizeof(struct127));
        record->elapsed -= record->period;
    }
    attached = record->owner->unk31C;
    if (attached != NULL && ((u8 *)attached)[0x84] == 0) {
        *(s16 *)((u8 *)attached + 0x46) = 1000;
    }
    return 1;
}"""

EXPLICIT = """/* Emit one actor event per elapsed period and refresh the attached target. */
s32 func_151905BC(PeriodicActorEventNested151905BC *record) {
    PeriodicActorEventClock151905BC *clock = &record->clock;
    struct127 *base;
    s32 eventCode;
    s32 stride;
    struct126 *attached;

    clock->elapsed += D_800BE9E4;
    if (clock->elapsed >= clock->period) {
        @ASSIGNMENTS@
        do {
            func_1505D024(record->owner, eventCode, 0,
                          ((s32)clock->eventTarget - (s32)base) / stride);
            clock->elapsed -= clock->period;
        } while (clock->elapsed >= clock->period);
    }
    attached = record->owner->unk31C;
    if (attached != NULL && ((u8 *)attached)[0x84] == 0) {
        *(s16 *)((u8 *)attached + 0x46) = 1000;
    }
    return 1;
}"""

QUALIFIED = EXPLICIT.replace(
    "@ASSIGNMENTS@",
    "base = D_800CC2D0;\n        eventCode = 0x60021;\n"
    "        stride = sizeof(struct127);",
)

DEFINED = QUALIFIED.replace(
    "clock->elapsed += D_800BE9E4;",
    "clock->elapsed = (s32)((u32)clock->elapsed + (u32)D_800BE9E4);",
).replace(
    "((s32)clock->eventTarget - (s32)base) / stride",
    "(s32)((u32)clock->eventTarget - (u32)base) / stride",
).replace(
    "clock->elapsed -= clock->period;",
    "clock->elapsed = (s32)((u32)clock->elapsed - (u32)clock->period);",
)

SELECTED = DEFINED


def source_with(body):
    live = (ROOT / SOURCE).read_text()
    anchor = '#include "structs.h"\n'
    selected_declarations = TYPES + "\n"
    declarations = (FLAT_TYPE if "PeriodicActorEvent151905BC" in body else "") + TYPES + "\n"
    if live.count(anchor) != 1:
        raise ValueError("Periodic actor event include anchor changed")
    if live.count(PLACEHOLDER) == 1:
        if selected_declarations in live or SELECTED in live:
            raise ValueError("Periodic actor event predecessor source changed")
        source = live
    elif live.count(SELECTED) == 1 and live.count(selected_declarations) == 1:
        source = live.replace(selected_declarations, "", 1).replace(
            SELECTED, PLACEHOLDER, 1)
    else:
        raise ValueError("Periodic actor event source state changed")
    return source.replace(anchor, anchor + declarations, 1).replace(
            PLACEHOLDER, body, 1)


def variants():
    yield "selected", SELECTED
    yield "typed", FLAT
    yield "byte-pointer", FLAT.replace(
        "s32 func_151905BC(PeriodicActorEvent151905BC *record)",
        "s32 func_151905BC(u8 *base)", 1).replace(
        "    struct126 *attached;",
        "    PeriodicActorEvent151905BC *record = (PeriodicActorEvent151905BC *)base;\n"
        "    struct126 *attached;", 1)
    yield "typed-pointer-difference", FLAT.replace(
        "((s32)record->eventTarget - (s32)D_800CC2D0) /\n"
        "                          (s32)sizeof(struct127)",
        "record->eventTarget - D_800CC2D0", 1)
    yield "cached-owner", FLAT.replace(
        "    struct126 *attached;",
        "    struct127 *owner = record->owner;\n    struct126 *attached;", 1).replace(
        "func_1505D024(record->owner,", "func_1505D024(owner,", 1).replace(
        "attached = record->owner->unk31C;", "attached = owner->unk31C;", 1)
    yield "nested-clock", """/* Emit one actor event per elapsed period and refresh the attached target. */
s32 func_151905BC(PeriodicActorEventNested151905BC *record) {
    PeriodicActorEventClock151905BC *clock = &record->clock;
    struct126 *attached;

    clock->elapsed += D_800BE9E4;
    while (clock->elapsed >= clock->period) {
        func_1505D024(record->owner, 0x60021, 0,
                      ((s32)clock->eventTarget - (s32)D_800CC2D0) /
                          (s32)sizeof(struct127));
        clock->elapsed -= clock->period;
    }
    attached = record->owner->unk31C;
    if (attached != NULL && ((u8 *)attached)[0x84] == 0) {
        *(s16 *)((u8 *)attached + 0x46) = 1000;
    }
    return 1;
}"""
    assignments = {
        "b": "base = D_800CC2D0;",
        "c": "eventCode = 0x60021;",
        "s": "stride = sizeof(struct127);",
    }
    for order in ("bcs", "bsc", "cbs", "csb", "sbc", "scb"):
        block = "\n        ".join(assignments[key] for key in order)
        yield "explicit-" + order, EXPLICIT.replace("@ASSIGNMENTS@", block)
    yield "for-loop", FLAT.replace(
        "    while (record->elapsed >= record->period) {",
        "    for (; record->elapsed >= record->period;\n"
        "         record->elapsed -= record->period) {", 1).replace(
        "        record->elapsed -= record->period;\n", "", 1)


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
    frame = 0
    if our_words and our_words[0] >> 16 == 0x27BD:
        frame = (-our_words[0]) & 0xFFFF
    return {
        "name": name,
        "flags": flags,
        "words": len(our_words),
        "frame": frame,
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
        for label, flags in (("o2g3", ("-O2", "-g3")),
                             ("o2", ("-O2",))):
            record = compare(name + "-" + label, body, flags)
            records.append(record)
            print(record["name"], record["words"], record["frame"],
                  record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
