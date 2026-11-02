"""Screen semantic C forms for func_15179CB0 without editing production."""
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


OWNER = "generated_1A6360"
FUNCTION = "func_15179CB0"
SOURCE = "conker/src/game/generated_1A6360.c"
BUILD = "conker/build/game-distance-opacity-15179CB0-candidates"
ROM = 0x1A7160
SIZE = 0x100

DECLARATIONS = "extern u8 *D_800DBFF0;\n"
PLACEHOLDER = "s32 func_15179CB0() {\n    return 0;\n}"

SELECTED = """/* Derive the record opacity byte from planar viewer distance. */
void func_15179CB0(u8 *record) {
    f32 dx;
    f32 dz;
    f32 distance;
    u8 *viewer;

    viewer = D_800DBFF0;
    dx = (f32)*(s16 *)(record + 0xA0) - *(f32 *)(viewer + 0x300);
    dz = (f32)*(s16 *)(record + 0x9C) - *(f32 *)(viewer + 0x2F8);
    distance = sqrtf(dx * dx + dz * dz);
    record[0xB4] = (u32)(255.0f - distance * 160.0f / 1000.0f);
}"""
SELECTED_DEFINITION = SELECTED.split("\n", 1)[1]


def recovered_owner(before, body=SELECTED):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != PLACEHOLDER:
        raise ValueError("Unknown distance-opacity predecessor")
    anchor = "#include <ultra64.h>\n"
    if before.count(anchor) != 1:
        raise ValueError("Unknown distance-opacity declaration anchor")
    return (before[:lo] + body + before[hi:]).replace(
        anchor, anchor + DECLARATIONS, 1)


def production_source(source):
    lo, hi = function_span(source, FUNCTION)
    current = source[lo:hi]
    if current == SELECTED_DEFINITION:
        if DECLARATIONS not in source:
            raise ValueError("Installed distance-opacity declaration missing")
        return source, True
    if current != PLACEHOLDER:
        raise ValueError("Unknown distance-opacity source state")
    return recovered_owner(source), False


def forms():
    yield "selected", SELECTED
    yield "inline-distance", SELECTED.replace(
        "    f32 distance;\n", "").replace(
        "    distance = sqrtf(dx * dx + dz * dz);\n",
        "").replace("distance * 160.0f", "sqrtf(dx * dx + dz * dz) * 160.0f")
    yield "s16-record", SELECTED.replace(
        "void func_15179CB0(u8 *record)",
        "void func_15179CB0(s16 *record)").replace(
        "*(s16 *)(record + 0xA0)", "record[0x50]").replace(
        "*(s16 *)(record + 0x9C)", "record[0x4E]").replace(
        "record[0xB4] =", "*((u8 *)record + 0xB4) =")
    yield "direct-global", SELECTED.replace(
        "    u8 *viewer;\n\n", "").replace(
        "    viewer = D_800DBFF0;\n", "").replace("viewer +", "D_800DBFF0 +")
    yield "divide-first", SELECTED.replace(
        "distance * 160.0f / 1000.0f", "(distance / 1000.0f) * 160.0f")
    yield "multiply-parenthesized", SELECTED.replace(
        "distance * 160.0f / 1000.0f", "(distance * 160.0f) / 1000.0f")
    yield "direct-byte-cast", SELECTED.replace(
        "record[0xB4] = (u32)", "record[0xB4] = (u8)")
    yield "signed-cast", SELECTED.replace(
        "record[0xB4] = (u32)", "record[0xB4] = (s32)")


def measure(root, out, label, body):
    before = (root / SOURCE).read_text()
    obj, diagnostics = compile_owner(root, out, recovered_owner(before, body), label)
    if diagnostics:
        raise ValueError("Distance-opacity compiler diagnostics: " + diagnostics)
    linked, functions = link_owner(root, out, obj, OWNER)
    info = functions[FUNCTION]
    candidate = linked[info["value"]:info["value"] + info["size"]]
    retail = (root / "conker/conker.us.bin").read_bytes()[ROM:ROM + SIZE]
    aligned = min(len(candidate), len(retail)) // 4
    candidate_words = struct.unpack_from(">%dI" % aligned, candidate)
    retail_words = struct.unpack_from(">%dI" % aligned, retail)
    _, _, relocations = parse_object(obj)
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
