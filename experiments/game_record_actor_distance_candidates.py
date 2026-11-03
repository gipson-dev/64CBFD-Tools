"""Screen semantic C forms for func_15178C9C's record-to-actor distance query."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x15178C9C
ROM = 0x1A614C
WORDS = 66
FUNCTION = "func_15178C9C"
SOURCE = "conker/src/game/generated_1A5440.c"
OWNER = "generated_1A5440"
BUILD = "conker/build/game-record-actor-distance-candidates"
PLACEHOLDER = """s32 func_15178C9C() {
    return 0;
}"""
TYPES = """typedef struct {
    u8 retained00[0x18];
    s32 positionX;
    s32 positionY;
    s32 positionZ;
} DistanceRecord15178C9C;

typedef struct {
    u8 retained00[0x14];
    f32 positionX;
    f32 positionY;
    f32 positionZ;
    u8 retained20[0x30C];
} DistanceActor15178C9C;
"""
DECLARATIONS = """extern DistanceActor15178C9C D_800CC2D0[];
f32 sqrtf(f32 value);
"""
SELECTED = """/* Return the integer distance from a selected record to an actor position. */
s32 func_15178C9C(u8 recordId, s32 actorIndex) {
    DistanceRecord15178C9C *record;
    s32 deltaX;
    s32 deltaY;
    s32 deltaZ;

    record = (DistanceRecord15178C9C *)func_15178B98(recordId);
    if (record == NULL) {
        return 1;
    }
    deltaX = (s32)(D_800CC2D0[actorIndex].positionX - (f32)record->positionX);
    deltaY = (s32)(D_800CC2D0[actorIndex].positionY - (f32)record->positionY);
    deltaZ = (s32)(D_800CC2D0[actorIndex].positionZ - (f32)record->positionZ);
    return (s32)sqrtf((f32)((deltaX * deltaX + deltaY * deltaY) +
                            deltaZ * deltaZ));
}"""
SELECTED_EARLY_RETURN = SELECTED
SELECTED_CACHED_ACTOR = SELECTED.replace(
    "    s32 deltaZ;\n\n",
    "    s32 deltaZ;\n    DistanceActor15178C9C *actor;\n\n").replace(
    "    deltaX = (s32)(D_800CC2D0[actorIndex].positionX",
    "    actor = &D_800CC2D0[actorIndex];\n"
    "    deltaX = (s32)(actor->positionX", 1).replace(
    "D_800CC2D0[actorIndex].positionY", "actor->positionY", 1).replace(
    "D_800CC2D0[actorIndex].positionZ", "actor->positionZ", 1)
SELECTED_LINEAR_SUM = SELECTED.replace(
    "(f32)((deltaX * deltaX + deltaY * deltaY) +\n"
    "                            deltaZ * deltaZ)",
    "(f32)(deltaX * deltaX + deltaY * deltaY + deltaZ * deltaZ)")
SELECTED_UNSIGNED_SUM = SELECTED.replace(
    "    s32 deltaZ;\n\n",
    "    s32 deltaZ;\n    u32 squaredDistance;\n\n").replace(
    "    return (s32)sqrtf((f32)((deltaX * deltaX + deltaY * deltaY) +\n"
    "                            deltaZ * deltaZ));",
    "    squaredDistance = deltaX * deltaX + deltaY * deltaY;\n"
    "    squaredDistance += deltaZ * deltaZ;\n"
    "    return (s32)sqrtf((f32)squaredDistance);")
SELECTED_POSITIVE_IF = SELECTED.replace(
    "    if (record == NULL) {\n"
    "        return 1;\n"
    "    }\n"
    "    deltaX = (s32)(D_800CC2D0[actorIndex].positionX - (f32)record->positionX);\n"
    "    deltaY = (s32)(D_800CC2D0[actorIndex].positionY - (f32)record->positionY);\n"
    "    deltaZ = (s32)(D_800CC2D0[actorIndex].positionZ - (f32)record->positionZ);\n"
    "    return (s32)sqrtf((f32)((deltaX * deltaX + deltaY * deltaY) +\n"
    "                            deltaZ * deltaZ));",
    "    if (record != NULL) {\n"
    "        deltaX = (s32)(D_800CC2D0[actorIndex].positionX - (f32)record->positionX);\n"
    "        deltaY = (s32)(D_800CC2D0[actorIndex].positionY - (f32)record->positionY);\n"
    "        deltaZ = (s32)(D_800CC2D0[actorIndex].positionZ - (f32)record->positionZ);\n"
    "        return (s32)sqrtf((f32)((deltaX * deltaX + deltaY * deltaY) +\n"
    "                                deltaZ * deltaZ));\n"
    "    }\n"
    "    return 1;")
SELECTED_POSITIVE_CACHED = SELECTED_POSITIVE_IF.replace(
    "    DistanceRecord15178C9C *record;\n",
    "    DistanceRecord15178C9C *record;\n"
    "    DistanceActor15178C9C *actor;\n", 1).replace(
    "    if (record != NULL) {\n"
    "        deltaX = (s32)(D_800CC2D0[actorIndex].positionX",
    "    if (record != NULL) {\n"
    "        actor = &D_800CC2D0[actorIndex];\n"
    "        deltaX = (s32)(actor->positionX", 1).replace(
    "D_800CC2D0[actorIndex].positionY", "actor->positionY", 1).replace(
    "D_800CC2D0[actorIndex].positionZ", "actor->positionZ", 1)
SELECTED_POSITIVE_RAW_ACTOR = SELECTED_POSITIVE_CACHED.replace(
    "    DistanceActor15178C9C *actor;\n",
    "    u8 *actor;\n", 1).replace(
    "        actor = &D_800CC2D0[actorIndex];\n",
    "        actor = (u8 *)&D_800CC2D0[actorIndex];\n", 1).replace(
    "actor->positionX", "*(f32 *)(actor + 0x14)", 1).replace(
    "actor->positionY", "*(f32 *)(actor + 0x18)", 1).replace(
    "actor->positionZ", "*(f32 *)(actor + 0x1C)", 1)
SELECTED_POSITIVE_ACTOR_LAST = SELECTED_POSITIVE_CACHED.replace(
    "    DistanceRecord15178C9C *record;\n"
    "    DistanceActor15178C9C *actor;\n"
    "    s32 deltaX;\n"
    "    s32 deltaY;\n"
    "    s32 deltaZ;",
    "    DistanceRecord15178C9C *record;\n"
    "    s32 deltaX;\n"
    "    s32 deltaY;\n"
    "    s32 deltaZ;\n"
    "    DistanceActor15178C9C *actor;", 1)
SELECTED_POSITIVE_ACTOR_FIRST = SELECTED_POSITIVE_CACHED.replace(
    "    DistanceRecord15178C9C *record;\n"
    "    DistanceActor15178C9C *actor;",
    "    DistanceActor15178C9C *actor;\n"
    "    DistanceRecord15178C9C *record;", 1)
SELECTED = SELECTED_POSITIVE_IF


ROOT = Path(__file__).resolve().parents[2]


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    marker = "} CleanupNode;\n"
    if source.count(marker) != 1:
        raise ValueError("CleanupNode declaration marker changed")
    declarations = "extern CleanupNode *D_800DCF3C;\n" + DECLARATIONS
    if source.count(PLACEHOLDER) == 1:
        if TYPES in source or DECLARATIONS in source or SELECTED in source:
            raise ValueError("Record actor distance predecessor source changed")
        source = source.replace(marker, marker + "\n" + TYPES, 1)
        source = source.replace("extern CleanupNode *D_800DCF3C;\n",
                                declarations, 1)
        return source.replace(PLACEHOLDER, body, 1)
    if (source.count(TYPES) == 1 and source.count(DECLARATIONS) == 1 and
            source.count(SELECTED) == 1 and PLACEHOLDER not in source):
        return source.replace(SELECTED, body, 1)
    raise ValueError("Record actor distance source state changed")


def variants():
    yield "typed-positive-if", SELECTED_POSITIVE_IF
    yield "typed-positive-cached", SELECTED_POSITIVE_CACHED
    yield "typed-positive-raw-actor", SELECTED_POSITIVE_RAW_ACTOR
    yield "typed-positive-actor-last", SELECTED_POSITIVE_ACTOR_LAST
    yield "typed-positive-actor-first", SELECTED_POSITIVE_ACTOR_FIRST
    yield "typed-direct", SELECTED_EARLY_RETURN
    yield "typed-cached-actor", SELECTED_CACHED_ACTOR
    yield "typed-linear-sum", SELECTED_LINEAR_SUM
    yield "typed-unsigned-sum", SELECTED_UNSIGNED_SUM


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
            print(record["name"], record["words"], record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
