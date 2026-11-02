"""Screen semantic C forms for func_15131DEC without editing production."""
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


OWNER = "generated_15D730"
FUNCTION = "func_15131DEC"
SOURCE = "conker/src/game/generated_15D730.c"
BUILD = "conker/build/game-curve-timer-15131DEC-candidates"
ROM = 0x15F29C
SIZE = 0xF8

DECLARATIONS = "extern f32 D_800BE9A4;\n"
PLACEHOLDER = "s32 func_15131DEC() {\n    return 0;\n}"

SELECTED = """/* Update the paired scale, curve byte, and bounded timer. */
s32 func_15131DEC(u8 *record, s32 event) {
    f32 scale;
    f32 time;

    scale = sqrtf(*(f32 *)(record + 0xA8)) * *(f32 *)(record + 0xB0);
    *(f32 *)(record + 0x3C) = scale;
    *(f32 *)(record + 0x38) = scale;
    time = *(f32 *)(record + 0xA8);
    record[0x2B] = (u32)(*(f32 *)(record + 0xB4) -
                         *(f32 *)(record + 0xB8) * time * time);
    *(f32 *)(record + 0xA8) += D_800BE9A4;
    if (*(f32 *)(record + 0xAC) < *(f32 *)(record + 0xA8)) {
        return 0;
    }
    return 1;
}"""
SELECTED_DEFINITION = SELECTED.split("\n", 1)[1]


def recovered_owner(before, body=SELECTED):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != PLACEHOLDER:
        raise ValueError("Unknown curve-timer predecessor")
    anchor = "#include <ultra64.h>\n"
    if before.count(anchor) != 1:
        raise ValueError("Unknown curve-timer declaration anchor")
    return (before[:lo] + body + before[hi:]).replace(
        anchor, anchor + DECLARATIONS, 1)


def production_source(source):
    lo, hi = function_span(source, FUNCTION)
    current = source[lo:hi]
    if current == SELECTED_DEFINITION:
        if DECLARATIONS not in source:
            raise ValueError("Installed curve-timer declaration missing")
        return source, True
    if current != PLACEHOLDER:
        raise ValueError("Unknown curve-timer source state")
    return recovered_owner(source), False


def forms():
    yield "selected", SELECTED
    yield "inline-time", SELECTED.replace(
        "    f32 time;\n", "").replace(
        "    time = *(f32 *)(record + 0xA8);\n", "").replace(
        "*(f32 *)(record + 0xB8) * time * time",
        "*(f32 *)(record + 0xB8) * *(f32 *)(record + 0xA8) * "
        "*(f32 *)(record + 0xA8)")
    yield "chained-scale", SELECTED.replace(
        "    f32 scale;\n", "").replace(
        "    scale = sqrtf(*(f32 *)(record + 0xA8)) * *(f32 *)(record + 0xB0);\n"
        "    *(f32 *)(record + 0x3C) = scale;\n"
        "    *(f32 *)(record + 0x38) = scale;",
        "    *(f32 *)(record + 0x38) = *(f32 *)(record + 0x3C) =\n"
        "        sqrtf(*(f32 *)(record + 0xA8)) * *(f32 *)(record + 0xB0);")
    yield "direct-result", SELECTED.replace(
        "    if (*(f32 *)(record + 0xAC) < *(f32 *)(record + 0xA8)) {\n"
        "        return 0;\n"
        "    }\n"
        "    return 1;",
        "    return !(*(f32 *)(record + 0xAC) < *(f32 *)(record + 0xA8));")


def measure(root, out, label, body):
    before = (root / SOURCE).read_text()
    obj, diagnostics = compile_owner(
        root, out, recovered_owner(before, body), label)
    if diagnostics:
        raise ValueError("Curve-timer compiler diagnostics: " + diagnostics)
    linked, functions = link_owner(root, out, obj, OWNER)
    info = functions[FUNCTION]
    candidate = linked[info["value"]:info["value"] + info["size"]]
    retail = (root / "conker/conker.us.bin").read_bytes()[ROM:ROM + SIZE]
    aligned = min(len(candidate), len(retail)) // 4
    candidate_words = struct.unpack_from(">%dI" % aligned, candidate)
    retail_words = struct.unpack_from(">%dI" % aligned, retail)
    text, _, relocations = parse_object(obj)
    rows = [
        (index * 4, expected, actual)
        for index, (expected, actual) in enumerate(zip(retail_words, candidate_words))
        if expected != actual
    ]
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
    (out / (label + "-audit.json")).write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    out.mkdir(parents=True, exist_ok=True)
    rows = [measure(root, out, label, body) for label, body in forms()]
    rows.sort(key=lambda row: (row["differences"], abs(row["extent_gap"]), row["label"]))
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
