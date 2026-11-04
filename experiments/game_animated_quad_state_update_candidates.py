"""Screen semantic C forms for func_15171FC0's animated-quad state update."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ENTRY = 0x15171FC0
ROM = 0x19F470
WORDS = 65
FUNCTION = "func_15171FC0"
SOURCE = "conker/src/game/generated_19F150.c"
OWNER = "generated_19F150"
BUILD = "conker/build/game-animated-quad-state-update-candidates"
DECLARATION = "extern s32 D_800BE9E4;\n"
PLACEHOLDER = """s32 func_15171FC0() {
    return 0;
}"""

SELECTED = """/* Advance an animated quad's lifetime and 8.8 fixed-point image frame. */
void func_15171FC0(QuadEffect19F150 *record) {
    s32 frameCount;

    if (record->lifetime < -1) {
        record->lifetime++;
        if (record->lifetime == -1) {
            func_1516972C((struct102 *)record);
        }
    } else if (record->lifetime == 0) {
        record->lifetime = -3;
    } else if (record->lifetime != -1) {
        if ((record->flags & 4) == 0) {
            if (record->lifetime > D_800BE9E4) {
                record->lifetime = (s32)((u32)record->lifetime -
                                         (u32)D_800BE9E4);
            } else {
                record->lifetime = 0;
            }
        }
        record->frame += record->frameStep;
        frameCount = D_8008CA4C[record->imageIndex][4];
        if (record->frame / 256 >= frameCount) {
            if (record->flags & 4) {
                record->lifetime = -3;
            } else {
                record->frame = (frameCount << 8) - 256;
            }
        }
    }
}"""


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    anchor = "extern u8 *D_8008CA4C[];\n"
    if source.count(anchor) != 1:
        raise ValueError("Animated-quad table declaration anchor changed")
    if source.count(PLACEHOLDER) == 1:
        if DECLARATION in source or SELECTED in source:
            raise ValueError("Animated-quad updater predecessor source changed")
        return source.replace(anchor, DECLARATION + anchor, 1).replace(
            PLACEHOLDER, body, 1)
    if source.count(SELECTED) == 1 and source.count(DECLARATION) == 1:
        return source.replace(SELECTED, body, 1)
    raise ValueError("Animated-quad updater source state changed")


def variants():
    yield "typed", SELECTED
    yield "byte-pointer", SELECTED.replace(
        "void func_15171FC0(QuadEffect19F150 *record)",
        "void func_15171FC0(u8 *base)", 1).replace(
        "    s32 frameCount;", "    QuadEffect19F150 *record = (QuadEffect19F150 *)base;\n    s32 frameCount;", 1)
    yield "explicit-negative", SELECTED.replace(
        "record->lifetime < -1", "record->lifetime <= -2", 1)
    yield "shift-frame", SELECTED.replace(
        "record->frame / 256", "record->frame >> 8", 1)
    yield "signed-subtract", SELECTED.replace(
        "record->lifetime = (s32)((u32)record->lifetime -\n                                         (u32)D_800BE9E4);",
        "record->lifetime -= D_800BE9E4;", 1)
    yield "cached-lifetime", SELECTED.replace(
        "    s32 frameCount;", "    s32 frameCount;\n    s16 lifetime = record->lifetime;", 1).replace(
        "record->lifetime < -1", "lifetime < -1", 1)


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
