"""Screen semantic C forms for actor channel release dispatcher func_15172D80."""

import argparse
import itertools
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler


ENTRY, ROM, WORDS = 0x15172D80, 0x1A0230, 63
FUNCTION = "func_15172D80"
SYMBOLS = {
    "D_800BE9F0": 0x800BE9F0,
    "D_800CC2D0": 0x800CC2D0,
    "D_800DD2B0": 0x800DD2B0,
    "D_800DD2C0": 0x800DD2C0,
    "func_1501C730": 0x1501C730,
    "func_15172CA8": 0x15172CA8,
    "func_15172D28": 0x15172D28,
    "func_1517EE40": 0x1517EE40,
    "func_1517F40C": 0x1517F40C,
}
RECORD = """typedef struct {
    u8 pad0[0x1CA];
    u8 health;
    u8 pad1CB[0x161];
} ActorChannel15172D80;
"""
DECLARATIONS = """extern s32 D_800BE9F0;
extern ActorChannel15172D80 D_800CC2D0[];
extern s8 D_800DD2B0[];
extern u8 D_800DD2C0[];
void func_1501C730(s32, s32, s32, s32, s32);
void func_15172CA8(s32);
void func_15172D28(ActorChannel15172D80 *, s32);
void func_1517EE40(s32, s32, s32, s32, s8, s32);
s32 func_1517F40C(s32);
"""

SELECTED = """void func_15172D80(s32 channel) {
    s8 *slot;
    ActorChannel15172D80 *actor;

    slot = &D_800DD2B0[channel];
    if (*slot != -1) {
        actor = &D_800CC2D0[channel];
        if (actor->health == 0) {
            *slot = -1;
            func_1517EE40(0, 0, 0, 0x32, 0, channel);
        }
        if (func_1517F40C(channel) != 0) {
            if (D_800BE9F0 != *slot) {
                func_1501C730(1, *slot, 0, 0, 0);
                return;
            }
            func_15172CA8(channel);
            func_15172D28(actor, D_800DD2C0[channel]);
        }
    }
}"""


def candidates():
    yield "selected", SELECTED
    yield "actor-declared-first", SELECTED.replace(
        "    s8 *slot;\n    ActorChannel15172D80 *actor;",
        "    ActorChannel15172D80 *actor;\n    s8 *slot;")
    yield "slot-initializer", SELECTED.replace(
        "    s8 *slot;", "    s8 *slot = &D_800DD2B0[channel];").replace(
        "\n    slot = &D_800DD2B0[channel];", "")
    yield "actor-block-declaration", SELECTED.replace(
        "    ActorChannel15172D80 *actor;\n\n", "\n").replace(
        "    if (*slot != -1) {\n        actor = &D_800CC2D0[channel];",
        "    if (*slot != -1) {\n"
        "        ActorChannel15172D80 *actor = &D_800CC2D0[channel];")
    yield "actor-block-separate", SELECTED.replace(
        "    ActorChannel15172D80 *actor;\n\n", "\n").replace(
        "    if (*slot != -1) {\n        actor = &D_800CC2D0[channel];",
        "    if (*slot != -1) {\n"
        "        ActorChannel15172D80 *actor;\n\n"
        "        actor = &D_800CC2D0[channel];")
    yield "unused-word-before", SELECTED.replace(
        "    s8 *slot;", "    s32 unused;\n    s8 *slot;")
    yield "unused-word-between", SELECTED.replace(
        "    ActorChannel15172D80 *actor;",
        "    s32 unused;\n    ActorChannel15172D80 *actor;")
    yield "unused-pointer-before", SELECTED.replace(
        "    s8 *slot;", "    void *unused;\n    s8 *slot;")
    yield "unused-byte-before", SELECTED.replace(
        "    s8 *slot;", "    s8 unused;\n    s8 *slot;")
    yield "unused-array-before", SELECTED.replace(
        "    s8 *slot;", "    u8 unused[8];\n    s8 *slot;")
    yield "index-first", SELECTED.replace(
        "    slot = &D_800DD2B0[channel];\n",
        "    actor = &D_800CC2D0[channel];\n"
        "    slot = &D_800DD2B0[channel];\n").replace(
        "        actor = &D_800CC2D0[channel];\n", "", 1)
    yield "flat-first-gate", SELECTED.replace(
        "    if (*slot != -1) {", "    if (*slot == -1) {\n        return;\n    }\n    {")
    yield "cached-selector", SELECTED.replace(
        "    ActorChannel15172D80 *actor;", 
        "    ActorChannel15172D80 *actor;\n    s8 selector;").replace(
        "        if (func_1517F40C(channel) != 0) {\n"
        "            if (D_800BE9F0 != *slot) {\n"
        "                func_1501C730(1, *slot, 0, 0, 0);",
        "        if (func_1517F40C(channel) != 0) {\n"
        "            selector = *slot;\n"
        "            if (D_800BE9F0 != selector) {\n"
        "                func_1501C730(1, selector, 0, 0, 0);")
    yield "signed-payload", SELECTED.replace(
        "extern u8 D_800DD2C0[];", "extern s8 D_800DD2C0[];")
    yield "actor-bytes", SELECTED.replace(
        "ActorChannel15172D80 *actor;", "u8 *actor;").replace(
        "actor = &D_800CC2D0[channel];", 
        "actor = (u8 *)&D_800CC2D0[channel];").replace(
        "actor->health", "actor[0x1CA]").replace(
        "func_15172D28(actor,", 
        "func_15172D28((ActorChannel15172D80 *)actor,")


def compile_candidate(root, output, name, body, profile="o2g3"):
    output.mkdir(parents=True, exist_ok=True)
    with patch.multiple(
            compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        record, words = compiler.compile_candidate(
            root, output, name, body, profile)
    retail = struct.unpack_from(
        ">%dI" % WORDS, (root / "conker/conker.us.bin").read_bytes(), ROM)
    record["differences"] = sum(
        left != right for left, right in
        itertools.zip_longest(words, retail, fillvalue=0))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / "conker/build/game-actor-channel-release-15172D80-match"
    records = []
    for name, body in candidates():
        profiles = compiler.PROFILES if args.profiles else ("o2g3",)
        for profile in profiles:
            record = compile_candidate(
                root, output, name + "-" + profile, body, profile)
            records.append(record)
            print(name, profile, record["body_words"], hex(record["frame"]),
                  record["differences"], flush=True)
    (output / "candidate-measurements.json").write_text(
        json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
