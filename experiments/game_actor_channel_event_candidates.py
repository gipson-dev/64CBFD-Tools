"""Screen semantic C forms for actor channel event dispatcher func_15172E7C."""

import itertools
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler


ENTRY, ROM, WORDS = 0x15172E7C, 0x1A032C, 59
FUNCTION = "func_15172E7C"
SYMBOLS = {
    "D_800BE9F0": 0x800BE9F0,
    "D_800DD2B0": 0x800DD2B0,
    "D_800DD2C0": 0x800DD2C0,
    "func_15172D28": 0x15172D28,
    "func_1517EE40": 0x1517EE40,
}
RECORD = """typedef struct {
    u8 pad0[0x127];
    u8 channel;
    u8 pad128[0xA2];
    u8 health;
    u8 pad1CB[0x12D];
    u16 flags;
    u8 pad2FA[0x1E];
    void *camera;
    s8 *state;
} ActorChannel15172E7C;
"""
DECLARATIONS = """extern s32 D_800BE9F0;
extern s8 D_800DD2B0[];
extern u8 D_800DD2C0[];
void func_15172D28(ActorChannel15172E7C *, s32);
void func_1517EE40(s32, s32, s32, s32, s8, s32);
"""

SELECTED = """void func_15172E7C(ActorChannel15172E7C *actor, u8 selector,
                       s32 payload) {
    u8 channel = actor->channel;

    if (actor->health != 0 &&
        (actor->state == 0 || actor->state[0x23] <= 0)) {
        if (actor->camera != 0) {
            if (D_800DD2B0[channel] == -1) {
                func_1517EE40(0, 0, 0, 0xA, 1, channel);
                actor->flags |= 0x10;
                D_800DD2B0[channel] = selector;
                D_800DD2C0[channel] = payload;
            }
        } else if (selector == D_800BE9F0) {
            func_15172D28(actor, payload);
        }
    }
}"""


def candidates():
    yield "selected", SELECTED
    yield "wide-selector-channel", SELECTED.replace(
        "ActorChannel15172E7C *actor, u8 selector,",
        "ActorChannel15172E7C *actor, s32 selector,").replace(
        "    u8 channel = actor->channel;",
        "    s32 channel = actor->channel;")
    yield "nested-health", SELECTED.replace(
        "    if (actor->health != 0 &&\n"
        "        (actor->state == 0 || actor->state[0x23] <= 0)) {",
        "    if (actor->health != 0) {\n"
        "        if (actor->state != 0 && actor->state[0x23] > 0) {\n"
        "            return;\n"
        "        }")
    yield "late-channel", SELECTED.replace(
        "    u8 channel = actor->channel;\n\n"
        "    if (actor->health != 0 &&",
        "    u8 channel;\n\n"
        "    if (actor->health != 0 &&").replace(
        "        if (actor->camera != 0) {",
        "        channel = actor->channel;\n"
        "        if (actor->camera != 0) {")
    yield "cached-state", SELECTED.replace(
        "    u8 channel = actor->channel;",
        "    u8 channel = actor->channel;\n    s8 *state = actor->state;").replace(
        "(actor->state == 0 || actor->state[0x23] <= 0)",
        "(state == 0 || state[0x23] <= 0)")
    yield "flat-camera", SELECTED.replace(
        "        if (actor->camera != 0) {\n"
        "            if (D_800DD2B0[channel] == -1) {",
        "        if (actor->camera != 0 && D_800DD2B0[channel] == -1) {").replace(
        "            }\n        } else if (selector == D_800BE9F0) {",
        "        } else if (actor->camera == 0 && selector == D_800BE9F0) {")


def compile_candidate(root, output, name, body):
    output.mkdir(parents=True, exist_ok=True)
    with patch.multiple(
            compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        record, words = compiler.compile_candidate(
            root, output, name, body, "o2g3")
    retail = struct.unpack_from(
        ">%dI" % WORDS, (root / "conker/conker.us.bin").read_bytes(), ROM)
    record["differences"] = sum(
        left != right for left, right in
        itertools.zip_longest(words, retail, fillvalue=0))
    return record


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / "conker/build/game-actor-channel-event-15172E7C-match"
    records = []
    for name, body in candidates():
        record = compile_candidate(root, output, name, body)
        records.append(record)
        print(name, record["body_words"], hex(record["frame"]),
              record["differences"], flush=True)
    (output / "candidate-measurements.json").write_text(
        json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
