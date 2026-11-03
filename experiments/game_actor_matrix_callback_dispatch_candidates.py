"""Screen semantic C forms for func_15132A88's actor matrix callback dispatch."""

import hashlib
import itertools
import json
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_remaining_donor_candidates import link_owner


ENTRY = 0x15132A88
ROM = 0x15FF38
WORDS = 62
FUNCTION = "func_15132A88"
SOURCE = "conker/src/game/generated_15F680.c"
OWNER = "generated_15F680"
BUILD = "conker/build/game-actor-matrix-callback-dispatch-candidates"
DECLARATIONS = """extern u8 D_800BE9C0;
typedef s32 (*ActorMatrixCallback15F680)(Mtx *, u8 *);
extern ActorMatrixCallback15F680 D_8008998C[];
s32 func_151464B8(void *);
void func_1516972C(u8 *);

typedef struct {
    u8 retained00[0x60];
    u32 flags;
    u8 retained64[8];
    void *gate;
    u8 retained70[8];
    u8 matrixCallback;
} ActorMatrixDispatch15F680;

"""
ANCHOR = "extern u8 D_800C3E90;\n"
PLACEHOLDER = """s32 func_15132A88() {
    return 0;
}"""
SELECTED = """/* Run the selected matrix callback and publish its actor status. */
void func_15132A88(ActorMatrixDispatch15F680 *actor) {
    s32 flags;
    s32 result;

    actor->flags &= ~0x200000;
    flags = actor->flags;
    if (flags & 0x20000) {
        return;
    }
    if ((flags & 0x400) && actor->gate != NULL &&
        func_151464B8(actor->gate) != 0) {
        return;
    }
    flags = actor->flags;
    if (flags & 0x80000) {
        actor->flags = flags | 0x200000;
        return;
    }
    result = D_8008998C[actor->matrixCallback](
        (Mtx *)((u8 *)actor + (D_800BE9C0 << 6) + 0x90), (u8 *)actor);
    if (result == -1) {
        func_1516972C((u8 *)actor);
        return;
    }
    if (result == 0) {
        actor->flags &= ~0x40000;
    } else {
        actor->flags |= 0x240000;
    }
}"""


def source_with(body):
    source = (ROOT / SOURCE).read_text()
    if source.count(ANCHOR) != 1 or source.count(PLACEHOLDER) != 1:
        raise ValueError("Actor matrix callback predecessor source changed")
    if DECLARATIONS in source or SELECTED in source:
        raise ValueError("Actor matrix callback declarations already installed")
    return source.replace(ANCHOR, ANCHOR + DECLARATIONS, 1).replace(
        PLACEHOLDER, body, 1)


def variants():
    yield "typed-exact", SELECTED
    yield "typed-explicit-nested", SELECTED.replace(
        "    if ((flags & 0x400) && actor->gate != NULL &&\n"
        "        func_151464B8(actor->gate) != 0) {\n"
        "        return;\n"
        "    }",
        "    if (flags & 0x400) {\n"
        "        if (actor->gate != NULL) {\n"
        "            if (func_151464B8(actor->gate) != 0) {\n"
        "                return;\n"
        "            }\n"
        "        }\n"
        "    }")
    yield "typed-detached-clear", SELECTED.replace(
        "    actor->flags &= ~0x200000;\n"
        "    flags = actor->flags;",
        "    flags = actor->flags & ~0x200000;\n"
        "    actor->flags = flags;")
    yield "typed-explicit-result-flags", SELECTED.replace(
        "    if (result == 0) {\n"
        "        actor->flags &= ~0x40000;\n"
        "    } else {\n"
        "        actor->flags |= 0x240000;\n"
        "    }",
        "    flags = actor->flags;\n"
        "    if (result == 0) {\n"
        "        flags &= ~0x40000;\n"
        "    } else {\n"
        "        flags |= 0x240000;\n"
        "    }\n"
        "    actor->flags = flags;")
    yield "typed-negative-first", SELECTED.replace(
        "    if (result == -1) {\n"
        "        func_1516972C((u8 *)actor);\n"
        "        return;\n"
        "    }\n"
        "    if (result == 0)",
        "    if (result < 0) {\n"
        "        func_1516972C((u8 *)actor);\n"
        "        return;\n"
        "    }\n"
        "    if (result == 0)")


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
    for name, body in variants():
        record = compare(name, body)
        records.append(record)
        print(record["name"], record["words"], record["differences"], flush=True)
    output = ROOT / BUILD
    (output / "measurements.json").write_text(json.dumps(records, indent=2) + "\n")
