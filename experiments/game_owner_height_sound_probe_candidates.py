"""Screen semantic C forms for func_151AE6B0's height/sound probe."""

import hashlib
import itertools
import json
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x151AE6B0
ROM = 0x1DBB60
WORDS = 64
FUNCTION = "func_151AE6B0"
SOURCE = "conker/src/game/generated_1D92F0.c"
BUILD = "conker/build/game-owner-height-sound-probe-candidates"
DECLARATIONS = (
    "extern f32 D_800A9D70;\n"
    "s32 func_15045800(f32 *, u16, f32, void *);\n"
    "u16 func_10010FFC(s32, s32, u16, s16, u8, void *);\n"
)
PLACEHOLDER = """s32 func_151AE6B0() {
    return 0;
}"""
SELECTED = """/* Probe below the attached actor, submit an effect, and start its hit sound. */
void func_151AE6B0(u8 *input) {
    u8 *owner = input;
    f32 position[3];
    u8 *actor;

    actor = *(u8 **)(owner + 0x18);
    position[0] = *(f32 *)(actor + 0x14);
    if (D_800A9D70 < *(f32 *)(actor + 0x118)) {
        position[1] = *(f32 *)(actor + 0x118) + 100.0f;
    } else {
        position[1] = *(f32 *)(actor + 0x18) + 150.0f;
    }
    position[2] = *(f32 *)(actor + 0x1C);
    if (func_15045800(position, 0, position[1] - 300.0f, owner + 0x34)) {
        position[1] = *(f32 *)(owner + 0x34);
        func_151ABE40(position, owner + 0x34, 5, owner[0xC], owner[1]);
        func_10010FFC(0, 0x11, 0x5208, 0, 0, actor);
    }
}"""


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    if body not in source:
        if source.count(PLACEHOLDER) != 1:
            raise ValueError("Height/sound probe source state changed")
        source = source.replace(PLACEHOLDER, body)
    if DECLARATIONS not in source:
        marker = '#include <ultra64.h>\n'
        if source.count(marker) != 1:
            raise ValueError("Owner include marker changed")
        source = source.replace(marker, marker + DECLARATIONS, 1)
    return source


def variants():
    yield "selected", SELECTED
    yield "volatile-actor", SELECTED.replace(
        "    u8 *actor;", "    u8 *volatile actor;")
    yield "reload-actor", SELECTED.replace(
        "        func_10010FFC(0, 0x11, 0x5208, 0, 0, actor);",
        "        func_10010FFC(0, 0x11, 0x5208, 0, 0,\n"
        "                       *(u8 **)(owner + 0x18));")
    yield "actor-first", SELECTED.replace(
        "    u8 *owner = input;\n    f32 position[3];\n    u8 *actor;",
        "    u8 *actor;\n    u8 *owner = input;\n    f32 position[3];")


def compare(name, body, flags=("-O2", "-g3")):
    output = ROOT / BUILD
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(ROOT, output, source_with(body), name, flags=flags)
    linked, functions = link_owner(ROOT, output, obj, "generated_1D92F0")
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
    for name, body in variants():
        for label, flags in (("o2g3", ("-O2", "-g3")), ("o2", ("-O2",))):
            record = compare(name + "-" + label, body, flags)
            records.append(record)
            print(record["name"], record["words"], record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")


