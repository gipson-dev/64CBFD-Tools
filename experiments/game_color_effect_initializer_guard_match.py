"""Qualify the color-effect initializer's closed compiler scheduling gap."""

import csv
import io
import re
import struct
from pathlib import Path

from tools.experiments import game_color_effect_initializer_candidates as prior
from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


FUNCTION = prior.FUNCTION
FILENAME = prior.OWNER
SOURCE = prior.SOURCE
ENTRY = prior.ENTRY
ROM = prior.ROM
WORDS = prior.SIZE // 4
FRAME = 0x18
OFFSETS = (
    0x034, 0x038, 0x050, 0x054, 0x058, 0x05C, 0x060, 0x064, 0x068,
    0x06C, 0x070, 0x074, 0x078, 0x07C, 0x080, 0x084, 0x088, 0x08C,
    0x090, 0x094, 0x09C, 0x0A8, 0x0AC, 0x0B0, 0x0B8,
)
REPLACEMENT_RELOCATIONS = {
    0x034: (("R_MIPS_HI16", "D_800DF700"),),
    0x038: (("R_MIPS_LO16", "D_800DF700"),),
}
SYMBOLS = {
    "D_800DF7B4": 0x800DF7B4,
    "D_800DF700": 0x800DF700,
    "bzero": 0x100226F0,
}

TYPE = """typedef struct ColorEffectRecord15187EC0 {
    u8 startRed;
    u8 startGreen;
    u8 startBlue;
    u8 targetRed;
    u8 targetGreen;
    u8 targetBlue;
    u8 currentRed;
    u8 currentGreen;
    u8 currentBlue;
    u8 padding[3];
    f32 blend;
    s32 mode;
    f32 rate;
    u8 state[12];
} ColorEffectRecord15187EC0;
"""

BODY = """/* Append a color-effect record to the five-entry pool; return its index or -1. */
s32 func_15187EC0(s32 mode, f32 rate, u8 startRed, u8 startGreen,
                  u8 startBlue, u8 targetRed, u8 targetGreen, u8 targetBlue) {
    ColorEffectRecord15187EC0 *record;

    if (D_800DF7B4 < 5) {
        record = (ColorEffectRecord15187EC0 *)(D_800DF700 + D_800DF7B4 * 36);
        record->rate = rate;
        record->currentRed = startRed;
        record->startRed = startRed;
        record->currentGreen = startGreen;
        record->startGreen = startGreen;
        record->currentBlue = startBlue;
        record->startBlue = startBlue;
        record->targetRed = targetRed;
        record->targetGreen = targetGreen;
        record->targetBlue = targetBlue;
        record->mode = mode;
        bzero(record->state, 12);
        return ++D_800DF7B4 - 1;
    }
    return -1;
}
"""


def candidate_owner(root):
    source = (root / SOURCE).read_text()
    if "typedef struct ColorEffectRecord15187EC0" not in source:
        marker = "extern u8 D_800DF700[];"
        if source.count(marker) != 1:
            raise ValueError("Unknown color-effect owner declaration")
        source = source.replace(marker, TYPE + "\n" + marker, 1)
    matches = list(re.finditer(
        r"s32 func_15187EC0\([^;{}]*\) \{\n.*?\n\}", source, re.S))
    if len(matches) != 1:
        raise ValueError("Unknown color-effect initializer definition")
    current = matches[0].group(0)
    if current != BODY[BODY.index("s32 func_15187EC0"):].rstrip():
        if current != "s32 func_15187EC0() {\n    return 0;\n}":
            raise ValueError("Unknown color-effect initializer body")
        source = source[:matches[0].start()] + BODY.rstrip() + source[matches[0].end():]
    return source


def compile_candidate(root, output):
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(
        root, output, prior.HEADERS + prior.SELECTED, "raw-color-effect-initializer")
    if diagnostics:
        raise ValueError("Color-effect initializer diagnostics changed: " + diagnostics)
    data, functions = link_owner(root, output, obj, FILENAME)
    function = functions[FUNCTION]
    linked = struct.unpack_from(">52I", data, function["value"])
    return obj, linked


def relocation_text(relocations):
    return "-" if not relocations else "|".join(
        kind + ":" + symbol for kind, symbol in relocations)


def unrelocated(word, relocations):
    for kind, _ in relocations:
        if kind in ("R_MIPS_HI16", "R_MIPS_LO16"):
            word &= 0xFFFF0000
        elif kind == "R_MIPS_26":
            word &= 0xFC000000
        else:
            raise AssertionError(kind)
    return word


def guard_rows(root, obj, linked_words):
    retail = struct.unpack_from(">52I", (root / "conker/conker.us.bin").read_bytes(), ROM)
    differences = tuple(
        index * 4 for index, pair in enumerate(zip(linked_words, retail))
        if pair[0] != pair[1])
    if differences != OFFSETS:
        raise ValueError("Color-effect initializer difference set changed")
    data, functions, relocations = parse_object(obj)
    function = functions[FUNCTION]
    if function["size"] != WORDS * 4:
        raise ValueError("Color-effect initializer size changed")
    base = function["value"]
    raw = struct.unpack_from(">52I", data, base)
    rows = []
    for offset in OFFSETS:
        expected_relocations = tuple(relocations.get(base + offset, ()))
        replacement_relocations = REPLACEMENT_RELOCATIONS.get(offset, ())
        expected = raw[offset // 4]
        if expected != unrelocated(linked_words[offset // 4], expected_relocations):
            raise ValueError("Unlinked candidate word changed at 0x%X" % offset)
        rows.append({
            "filename": FILENAME,
            "function": FUNCTION,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % expected,
            "replacement": "0x%08X" % unrelocated(
                retail[offset // 4], replacement_relocations),
            "expected_relocations": relocation_text(expected_relocations),
            "replacement_relocations": relocation_text(replacement_relocations),
            "note": "Normalize color-effect initializer argument loads and store schedule",
            "insert_after": "",
            "insert_after_relocations": "",
            "omit": "false",
        })
    return rows


def write_rows(path, rows):
    fields = tuple(rows[0])
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def suffix_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
    writer.writerows(rows)
    return stream.getvalue().encode("ascii")
