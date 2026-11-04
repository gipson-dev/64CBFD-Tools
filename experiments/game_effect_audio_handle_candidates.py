"""Screen semantic C forms for the effect-and-audio handle constructor."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner,
    function_span,
    link_owner,
)


FUNCTION = "func_150E3414"
OWNER = "generated_1104D0"
SOURCE = "conker/src/game/generated_1104D0.c"
BUILD = "conker/build/game-effect-audio-handle-150E3414-candidates"
ENTRY = 0x150E3414
ROM = 0x1108C4
WORDS = 64

DECLARATION = (
    "u16 func_1000FA64(u16, s16, s16, s16, s32, u16, s16, s32, "
    "void *, s32, s32, s32);\n"
)

PLACEHOLDER = """s32 func_150E3414() {
    return 0;
}"""

INTEGER_BODY = """/* Create an effect with an attached positional sound and return its slot. */
s32 func_150E3414(s32 soundX, s32 soundY, s32 soundZ,
                  s32 x, s32 y, s32 z, s32 context, s32 kind, f32 step) {
    s32 effect;

    effect = func_150E3020(x, y, z, 0, 0, 0, kind, step, context,
                           (f32)soundX, (f32)soundY, (f32)soundZ, 0, -99);
    if (effect != 0) {
        *(u16 *)(effect + 0x4A) = func_1000FA64(
            0x2D0, (s16)soundX, (s16)soundY, (s16)soundZ,
            0x5DC0, 0x1770, 0x3E8, (s32)func_150E33CC,
            NULL, 0, 0, 0);
        return *(u8 *)(effect + 0x48) + 1;
    }
    return 0;
}"""

SELECTED = INTEGER_BODY

POINTER_BODY = INTEGER_BODY.replace(
    "    s32 effect;", "    u8 *effect;"
).replace(
    "    effect = func_150E3020(", "    effect = (u8 *)func_150E3020("
).replace(
    "effect != 0", "effect != NULL"
).replace(
    "*(u16 *)(effect + 0x4A)", "*(u16 *)(effect + 0x4A)"
).replace(
    "*(u8 *)(effect + 0x48)", "effect[0x48]"
)


def variants():
    yield "integer", INTEGER_BODY
    yield "pointer", POINTER_BODY
    yield "integer-bare-callback", INTEGER_BODY.replace(
        "(s32)func_150E33CC", "func_150E33CC"
    )
    yield "pointer-bare-callback", POINTER_BODY.replace(
        "(s32)func_150E33CC", "func_150E33CC"
    )
    yield "integer-temp-result", INTEGER_BODY.replace(
        "    s32 effect;", "    s32 effect;\n    u16 sound;"
    ).replace(
        "        *(u16 *)(effect + 0x4A) = func_1000FA64(\n",
        "        sound = func_1000FA64(\n",
    ).replace(
        "            NULL, 0, 0, 0);\n        return",
        "            NULL, 0, 0, 0);\n        *(u16 *)(effect + 0x4A) = sound;\n"
        "        return",
    )


def candidate_source(before, body):
    anchor = PLACEHOLDER
    if before.count(anchor) != 1:
        raise ValueError("Effect-audio placeholder anchor changed")
    result = before.replace(anchor, body)
    declaration_anchor = "s32 func_150AD9A0(s32, s32, s32);\n"
    if result.count(declaration_anchor) != 1:
        raise ValueError("Effect-audio declaration anchor changed")
    return result.replace(
        declaration_anchor, declaration_anchor + DECLARATION, 1
    )


def retail_bytes(root):
    image = (root / "conker/conker.us.bin").read_bytes()
    return image[ROM:ROM + WORDS * 4]


def compare(actual, retail):
    actual_words = list(struct.iter_unpack(">I", actual))
    retail_words = list(struct.iter_unpack(">I", retail))
    limit = max(len(actual_words), len(retail_words))
    return [
        index for index in range(limit)
        if (actual_words[index] if index < len(actual_words) else None) !=
           (retail_words[index] if index < len(retail_words) else None)
    ]


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    before = (root / SOURCE).read_text()
    retail = retail_bytes(root)
    records = []
    for label, body in variants():
        source = candidate_source(before, body)
        obj, diagnostics = compile_owner(
            root, output, source, label + "-" + OWNER
        )
        linked, functions = link_owner(root, output, obj, OWNER)
        info = functions[FUNCTION]
        actual = linked[info["value"]:info["value"] + info["size"]]
        while len(actual) > len(retail) and actual[-4:] == b"\0\0\0\0":
            actual = actual[:-4]
        differences = compare(actual, retail)
        record = {
            "variant": label,
            "words": len(actual) // 4,
            "retail_words": WORDS,
            "differences": len(differences),
            "difference_indices": differences,
            "body_sha256": hashlib.sha256(actual).hexdigest(),
            "retail_sha256": hashlib.sha256(retail).hexdigest(),
            "diagnostics": diagnostics,
        }
        records.append(record)
        print(json.dumps({
            key: value for key, value in record.items()
            if key != "diagnostics"
        }))
    (output / "candidates.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
