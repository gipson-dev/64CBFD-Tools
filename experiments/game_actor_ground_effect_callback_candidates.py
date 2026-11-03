"""Screen semantic C forms for func_151AB1C4's ground-effect callback."""

import hashlib
import itertools
import json
import os
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner


ENTRY = 0x151AB1C4
ROM = 0x1D8674
WORDS = 64
FUNCTION = "func_151AB1C4"
SOURCE = "conker/src/game/generated_1D6E80.c"
OWNER = "generated_1D6E80"
BUILD = "conker/build/game-actor-ground-effect-callback-candidates"
DECLARATIONS = """extern f32 D_800A8FEC;
void func_151AA264(u8 *, f32 *);
"""
PLACEHOLDER = """s32 func_151AB1C4() {
    return 0;
}"""
SELECTED = """/* Probe below the attached actor, submit the hit effect and sound, then finalize it. */
void func_151AB1C4(u8 *owner) {
    f32 position[3];
    u8 *actor;

    actor = *(u8 **)(owner + 0x18);
    position[0] = *(f32 *)(actor + 0x14);
    if (D_800A8FEC < *(f32 *)(actor + 0x118)) {
        position[1] = *(f32 *)(actor + 0x118) + 100.0f;
    } else {
        position[1] = *(f32 *)(actor + 0x18) + 150.0f;
    }
    position[2] = *(f32 *)(actor + 0x1C);
    if (func_15045800(position, 0, position[1] - 300.0f, owner + 0x34)) {
        position[1] = *(f32 *)(owner + 0x34);
        func_151ABE40(position, owner + 0x34, 3, owner[0xC], owner[1]);
        func_10010FFC(0, 0x11, 0x5208, 0, 0, actor);
    }
    func_151AA264(actor, (f32 *)(owner + 0x34));
}"""
OWNER_ALIAS = SELECTED.replace(
    "    f32 position[3];\n    u8 *actor;",
    "    u8 *input = owner;\n    f32 position[3];\n    u8 *actor;").replace(
    "owner +", "input +").replace("owner[", "input[")
ACTOR_FIRST = SELECTED.replace(
    "    f32 position[3];\n    u8 *actor;",
    "    u8 *actor;\n    f32 position[3];")
VOID_POINTER_FINAL = SELECTED.replace(
    "func_151AA264(actor, (f32 *)(owner + 0x34));",
    "func_151AA264(actor, owner + 0x34);")
MATCHED = ACTOR_FIRST


ROOT = Path(__file__).resolve().parents[2]


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    marker = '#include "structs.h"\n'
    if source.count(PLACEHOLDER) == 1:
        if DECLARATIONS in source or SELECTED in source:
            raise ValueError("Actor ground-effect callback predecessor source changed")
        return source.replace(marker, marker + DECLARATIONS, 1).replace(
            PLACEHOLDER, body, 1)
    if source.count(MATCHED) == 1 and source.count(DECLARATIONS) == 1:
        return source.replace(MATCHED, body, 1)
    raise ValueError("Actor ground-effect callback source state changed")


def variants():
    yield "typed-void", SELECTED
    yield "owner-alias", OWNER_ALIAS
    yield "actor-first", ACTOR_FIRST
    yield "void-pointer-final", VOID_POINTER_FINAL


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
        "frame": (-our_words[0] & 0xFFFF) if our_words else 0,
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
            print(record["name"], record["words"], record["frame"],
                  record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
