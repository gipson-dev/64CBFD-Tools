"""Screen semantic C forms for func_1515BAE0's timed packet callback."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x1515BAE0
ROM = 0x188F90
WORDS = 68
FUNCTION = "func_1515BAE0"
SOURCE = "conker/src/game/generated_188F90.c"
OWNER = "generated_188F90"
BUILD = "conker/build/game-timed-packet-callback-candidates"
DECLARATIONS = """typedef s32 (*TimedPacketCallback1515BAE0)(void *);
extern TimedPacketCallback1515BAE0 D_8008B078[];
extern TimedPacketCallback1515BAE0 D_8008B07C[];
extern s32 D_800BE9E4;
s32 func_1514401C(u8, s32 *, s32 *, u8);
void func_1516972C(void *);
"""
INSTALL_TYPES = """typedef struct {
    u8 retained00[0x10];
    u8 mode;
    u8 flags;
    u8 command;
    u8 retained13;
    s16 timer;
    u8 retained16[2];
    s32 cursor;
    s32 packet;
    u8 retained20[0x18];
    s8 updateCallback;
    s8 removeCallback;
} TimedPacketRecord1515BAE0;
"""
PLACEHOLDER = """s32 func_1515BAE0() {
    return 0;
}"""
SELECTED = """/* Advance a timed packet and remove it when its callbacks request completion. */
void func_1515BAE0(TimedPacketRecord1515BAE0 *record) {
    u8 remove = 0;
    s8 callbackIndex;

    if ((record->flags & 1) != 0) {
        record->timer -= D_800BE9E4;
        if (record->timer < 0) {
            remove = 1;
        }
    }
    if (remove == 0) {
        callbackIndex = record->updateCallback;
        if (callbackIndex != -1) {
            if (D_8008B078[callbackIndex](record) == 0) {
                remove = 1;
            }
        }
        if (record->packet != 0) {
            remove = func_1514401C(record->mode, &record->packet,
                                  &record->cursor, record->command) & 0xFF;
        }
    }
    if (remove != 0) {
        callbackIndex = record->removeCallback;
        if (callbackIndex != -1) {
            if (D_8008B07C[callbackIndex](record) != 0) {
                func_1516972C(record);
            }
        } else {
            func_1516972C(record);
        }
    }
}"""


def replace_type(body, old, new):
    return body.replace("    " + old + " remove = 0;", "    " + new + " remove = 0;", 1)


SELECTED_MATCH = replace_type(SELECTED, "u8", "s32")


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    anchor = '#include "structs.h"\n'
    declarations = INSTALL_TYPES + DECLARATIONS + "\n"
    if source.count(anchor) != 1:
        raise ValueError("Timed packet callback include anchor changed")
    if source.count(PLACEHOLDER) == 1:
        if declarations in source or SELECTED in source:
            raise ValueError("Timed packet callback predecessor source changed")
        return source.replace(anchor, anchor + "\n" + declarations, 1).replace(
            PLACEHOLDER, body, 1)
    if source.count(SELECTED_MATCH) == 1 and source.count(declarations) == 1:
        return source.replace(SELECTED_MATCH, body, 1)
    raise ValueError("Timed packet callback source state changed")


def variants():
    yield "typed-u8", SELECTED
    yield "typed-s32", SELECTED_MATCH
    yield "typed-s8", replace_type(SELECTED, "u8", "s8")
    yield "callback-first", SELECTED.replace(
        "    u8 remove = 0;\n    s8 callbackIndex;",
        "    s8 callbackIndex;\n    u8 remove = 0;", 1)
    yield "combined-update", SELECTED.replace(
        "        if (callbackIndex != -1) {\n"
        "            if (D_8008B078[callbackIndex](record) == 0) {\n"
        "                remove = 1;\n"
        "            }\n"
        "        }",
        "        if ((callbackIndex != -1) &&\n"
        "            (D_8008B078[callbackIndex](record) == 0)) {\n"
        "            remove = 1;\n"
        "        }", 1)
    yield "combined-remove", SELECTED.replace(
        "        if (callbackIndex != -1) {\n"
        "            if (D_8008B07C[callbackIndex](record) != 0) {\n"
        "                func_1516972C(record);\n"
        "            }\n"
        "        } else {",
        "        if ((callbackIndex != -1) &&\n"
        "            (D_8008B07C[callbackIndex](record) != 0)) {\n"
        "            func_1516972C(record);\n"
        "        } else if (callbackIndex == -1) {", 1)


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
