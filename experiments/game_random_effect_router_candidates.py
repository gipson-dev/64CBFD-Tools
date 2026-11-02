"""Screen semantic C forms for func_151AE890 without editing production."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner,
    function_span,
    link_owner,
)
from tools.pad_generated_object import parse_object


OWNER = "generated_1D92F0"
FUNCTION = "func_151AE890"
SOURCE = "conker/src/game/generated_1D92F0.c"
BUILD = "conker/build/game-random-effect-router-151AE890-candidates"
ROM = 0x1DBD40
SIZE = 0xF4

DECLARATIONS = """extern f32 D_800A9D84, D_800A9D88;
f32 func_150ADA68(void);
s32 func_151AE984();
s32 func_151AEAB4();
"""
PLACEHOLDER = "s32 func_151AE890() {\n    return 0;\n}"

SELECTED = """/* Randomly route a position to one of two effect constructors. */
void func_151AE890(f32 x, f32 y, f32 z, f32 value0, f32 value1,
                   f32 value2, u8 *actor) {
    f32 position[3];
    f32 sample;

    position[0] = x;
    position[1] = y;
    position[2] = z;
    sample = func_150ADA68();
    if (sample < D_800A9D84) {
        return;
    }
    if (sample < 0.25f) {
        func_151AEAB4(position, 0.0f < func_150ADA68(), actor[0xC]);
    } else {
        func_151AE984(position, value0, value1, value2,
                      D_800A9D88 < func_150ADA68(), actor[0xC]);
    }
}"""

PRODUCTION = """/* Route a position and raw effect payload through a random constructor. */
void func_151AE890(f32 x, f32 y, f32 z, s32 effect_arg0_bits,
                   s32 effect_arg1_bits, s32 effect_arg2_bits, u8 *actor) {
    f32 position[3];
    f32 sample;

    position[0] = x;
    position[1] = y;
    position[2] = z;
    sample = func_150ADA68();
    if (sample < D_800A9D84) {
        return;
    }
    if (sample < 0.25f) {
        func_151AEAB4(position,
                      0.0f < func_150ADA68() ? 1 : 0, actor[0xC]);
    } else {
        s32 flag = D_800A9D88 < func_150ADA68() ? 1 : 0;
        func_151AE984(position, effect_arg0_bits, effect_arg1_bits,
                      effect_arg2_bits, flag, actor[0xC]);
    }
}"""
PRODUCTION_DEFINITION = PRODUCTION.split("\n", 1)[1]


def recovered_owner(before, body=SELECTED):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != PLACEHOLDER:
        raise ValueError("Unknown random-effect router predecessor")
    anchor = "#include <ultra64.h>\n"
    if before.count(anchor) != 1:
        raise ValueError("Unknown random-effect router declaration anchor")
    return (before[:lo] + body + before[hi:]).replace(
        anchor, anchor + DECLARATIONS, 1)


def production_source(source):
    lo, hi = function_span(source, FUNCTION)
    current = source[lo:hi]
    if current == PRODUCTION_DEFINITION:
        if source.count(DECLARATIONS) != 1:
            raise ValueError("Installed random-effect router declarations changed")
        return source, True
    if current != PLACEHOLDER:
        raise ValueError("Unknown random-effect router source state")
    return recovered_owner(source, PRODUCTION), False


def forms():
    yield "raw-word-payload", PRODUCTION
    yield "selected", SELECTED
    yield "ternary-first-flag", SELECTED.replace(
        "func_151AEAB4(position, 0.0f < func_150ADA68(), actor[0xC]);",
        "func_151AEAB4(position,\n"
        "                      0.0f < func_150ADA68() ? 1 : 0, actor[0xC]);")
    yield "ternary-both-flags", SELECTED.replace(
        "func_151AEAB4(position, 0.0f < func_150ADA68(), actor[0xC]);",
        "func_151AEAB4(position,\n"
        "                      0.0f < func_150ADA68() ? 1 : 0, actor[0xC]);").replace(
        "D_800A9D88 < func_150ADA68(), actor[0xC]);",
        "D_800A9D88 < func_150ADA68() ? 1 : 0, actor[0xC]);")
    yield "ternary-first-branch-local-second", SELECTED.replace(
        "func_151AEAB4(position, 0.0f < func_150ADA68(), actor[0xC]);",
        "func_151AEAB4(position,\n"
        "                      0.0f < func_150ADA68() ? 1 : 0, actor[0xC]);").replace(
        "        func_151AE984(position, value0, value1, value2,\n"
        "                      D_800A9D88 < func_150ADA68(), actor[0xC]);",
        "        s32 flag = 0;\n"
        "        if (D_800A9D88 < func_150ADA68()) {\n"
        "            flag = 1;\n"
        "        }\n"
        "        func_151AE984(position, value0, value1, value2, flag, actor[0xC]);")
    yield "ternary-first-local-ternary-second", SELECTED.replace(
        "func_151AEAB4(position, 0.0f < func_150ADA68(), actor[0xC]);",
        "func_151AEAB4(position,\n"
        "                      0.0f < func_150ADA68() ? 1 : 0, actor[0xC]);").replace(
        "        func_151AE984(position, value0, value1, value2,\n"
        "                      D_800A9D88 < func_150ADA68(), actor[0xC]);",
        "        s32 flag = D_800A9D88 < func_150ADA68() ? 1 : 0;\n"
        "        func_151AE984(position, value0, value1, value2, flag, actor[0xC]);")
    yield "selected-first-ternary-second", SELECTED.replace(
        "D_800A9D88 < func_150ADA68(), actor[0xC]);",
        "D_800A9D88 < func_150ADA68() ? 1 : 0, actor[0xC]);")
    yield "branch-local-first-flag", SELECTED.replace(
        "        func_151AEAB4(position, 0.0f < func_150ADA68(), actor[0xC]);",
        "        s32 flag = 0;\n"
        "        if (0.0f < func_150ADA68()) {\n"
        "            flag = 1;\n"
        "        }\n"
        "        func_151AEAB4(position, flag, actor[0xC]);")
    yield "branch-local-both-flags", SELECTED.replace(
        "        func_151AEAB4(position, 0.0f < func_150ADA68(), actor[0xC]);",
        "        s32 flag = 0;\n"
        "        if (0.0f < func_150ADA68()) {\n"
        "            flag = 1;\n"
        "        }\n"
        "        func_151AEAB4(position, flag, actor[0xC]);").replace(
        "        func_151AE984(position, value0, value1, value2,\n"
        "                      D_800A9D88 < func_150ADA68(), actor[0xC]);",
        "        s32 flag = 0;\n"
        "        if (D_800A9D88 < func_150ADA68()) {\n"
        "            flag = 1;\n"
        "        }\n"
        "        func_151AE984(position, value0, value1, value2, flag, actor[0xC]);")
    yield "no-sample-local", SELECTED.replace(
        "    f32 sample;\n\n", "\n").replace(
        "    sample = func_150ADA68();\n"
        "    if (sample < D_800A9D84) {",
        "    if (func_150ADA68() < D_800A9D84) {").replace(
        "    if (sample < 0.25f) {", "    if (func_150ADA68() < 0.25f) {")
    yield "explicit-first-flag", SELECTED.replace(
        "    f32 sample;", "    f32 sample;\n    s32 flag;").replace(
        "        func_151AEAB4(position, 0.0f < func_150ADA68(), actor[0xC]);",
        "        flag = 0;\n        if (0.0f < func_150ADA68()) {\n"
        "            flag = 1;\n        }\n"
        "        func_151AEAB4(position, flag, actor[0xC]);")
    yield "explicit-both-flags", SELECTED.replace(
        "    f32 sample;", "    f32 sample;\n    s32 flag;").replace(
        "        func_151AEAB4(position, 0.0f < func_150ADA68(), actor[0xC]);",
        "        flag = 0;\n        if (0.0f < func_150ADA68()) {\n"
        "            flag = 1;\n        }\n"
        "        func_151AEAB4(position, flag, actor[0xC]);").replace(
        "        func_151AE984(position, value0, value1, value2,\n"
        "                      D_800A9D88 < func_150ADA68(), actor[0xC]);",
        "        flag = 0;\n        if (D_800A9D88 < func_150ADA68()) {\n"
        "            flag = 1;\n        }\n"
        "        func_151AE984(position, value0, value1, value2, flag, actor[0xC]);")


def measure(root, output, label, body):
    obj, diagnostics = compile_owner(
        root, output, recovered_owner((root / SOURCE).read_text(), body), label)
    if diagnostics:
        raise ValueError("Random-effect router compiler diagnostics: " + diagnostics)
    linked, functions = link_owner(root, output, obj, OWNER)
    info = functions[FUNCTION]
    candidate = linked[info["value"]:info["value"] + info["size"]]
    retail = (root / "conker/conker.us.bin").read_bytes()[ROM:ROM + SIZE]
    aligned = min(len(candidate), len(retail)) // 4
    candidate_words = struct.unpack_from(">%dI" % aligned, candidate)
    retail_words = struct.unpack_from(">%dI" % aligned, retail)
    rows = [
        (index * 4, expected, actual)
        for index, (expected, actual) in enumerate(zip(retail_words, candidate_words))
        if expected != actual
    ]
    _, _, relocations = parse_object(obj)
    result = {
        "label": label,
        "words": len(candidate) // 4,
        "retail_words": SIZE // 4,
        "extent_gap": len(candidate) - SIZE,
        "differences": len(rows) + abs(len(candidate) - SIZE) // 4,
        "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
        "retail_sha256": hashlib.sha256(retail).hexdigest(),
        "relocations": sum(
            len(items) for offset, items in relocations.items()
            if info["value"] <= offset < info["value"] + info["size"]),
        "difference_rows": [
            {"offset": offset, "retail": expected, "candidate": actual}
            for offset, expected, actual in rows
        ],
    }
    (output / (label + "-audit.json")).write_text(
        json.dumps(result, indent=2) + "\n")
    return result


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    output.mkdir(parents=True, exist_ok=True)
    rows = [measure(root, output, label, body) for label, body in forms()]
    rows.sort(key=lambda row: (row["differences"], abs(row["extent_gap"]), row["label"]))
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
