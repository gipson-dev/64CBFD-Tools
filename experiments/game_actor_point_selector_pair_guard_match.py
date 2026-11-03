"""Recover and qualify the paired actor-point interval selectors in EBE60."""

import csv
import io
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span)
from tools.experiments.game_four_head_lookup_match import payload
from tools.pad_generated_object import parse_object


FILENAME = "generated_EBE60"
SOURCE = "conker/src/game/generated_EBE60.c"
OBJECT = "conker/build/src/game/generated_EBE60.c.o"
ASM = "conker/asm/EBE60.s"
BUILD = "conker/build/game-actor-point-selector-pair-guard-match"
WORDS = 62
RAW_WORDS = 61
FRAME = 0x38
DECLARATIONS = """typedef struct HeightResult71820 HeightResult71820;
typedef struct HeightActor71820 HeightActor71820;
void func_15142314(u8 *, s32, f32 *);
void func_1504715C(HeightResult71820 *, HeightActor71820 *);
s32 func_15046C80(f32 *, u16, f32, HeightResult71820 *);

"""
TARGETS = {
    "func_150BE9B0": dict(entry=0x150BE9B0, rom=0xEBE60, point4=0x17,
                          point5=0x14, caller=0x150BEACC, call_rom=0xEBFAC),
    "func_150BEC30": dict(entry=0x150BEC30, rom=0xEC0E0, point4=0x19,
                          point5=0x16, caller=0x150BED4C, call_rom=0xEC22C),
}
SYMBOLS = {
    "func_15142314": 0x15142314,
    "func_1504715C": 0x1504715C,
    "func_15046C80": 0x15046C80,
}


def selected_body(name):
    spec = TARGETS[name]
    return """/* Resolve the mode-selected actor point and optionally query its vertical interval. */
s32 NAME(f32 *position, u8 * volatile actor,
        HeightResult71820 *result, u8 mode) {
    f32 start[3];
    register s32 index = 0x10;

    switch (mode) {
        case 4:
            index = POINT4;
            break;
        case 5:
            index = POINT5;
            break;
        case 6:
            index = 0xC;
            break;
        case 7:
            break;
    }
    func_15142314(*(u8 **)(actor + 0x1D4), index, position);
    if (result == 0) {
        return 1;
    }
    start[0] = position[0];
    start[1] = position[1] + 10.0f;
    start[2] = position[2];
    func_1504715C(result, (HeightActor71820 *)actor);
    return func_15046C80(start, 0, position[1] - 50.0f, result);
}
""".replace("NAME", name).replace("POINT4", hex(spec["point4"])) \
        .replace("POINT5", hex(spec["point5"]))


def recovered_owner(before):
    result = before
    if DECLARATIONS not in result:
        position = result.index("\n", result.index("#include")) + 1
        result = result[:position] + DECLARATIONS + result[position:]
    for name in TARGETS:
        start, end = function_span(result, name)
        existing = result[start:end]
        body = selected_body(name).rstrip()
        if existing != body:
            if existing != "s32 %s() {\n    return 0;\n}" % name:
                raise ValueError("Actor point selector definition changed: " + name)
            result = result[:start] + body + result[end:]
    return result


def candidate_owner(root):
    return recovered_owner((root / SOURCE).read_text())


def compile_candidate(root, output):
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(
        root, output, candidate_owner(root), "actor-point-selector-pair-compact")
    if diagnostics:
        raise ValueError("Actor point selector diagnostics changed: " + diagnostics)
    return obj


def relocation_text(relocations):
    return "-" if not relocations else ";".join(
        kind + ":" + symbol for kind, symbol in relocations)


def unrelocated(word, relocations):
    for kind, _ in relocations:
        if kind in ("R_MIPS_HI16", "R_MIPS_LO16"):
            word &= 0xFFFF0000
        elif kind == "R_MIPS_26":
            word &= 0xFC000000
        else:
            raise ValueError("Unsupported selector relocation: " + kind)
    return word


def guard_rows(root, obj, name):
    spec = TARGETS[name]
    raw, relocations = payload(obj, name)
    if len(raw) != RAW_WORDS * 4:
        raise ValueError("Actor point selector raw extent changed: " + name)
    raw_words = struct.unpack(">%dI" % RAW_WORDS, raw)
    retail = struct.unpack_from(">%dI" % WORDS,
                                (root / "conker/conker.us.bin").read_bytes(),
                                spec["rom"])
    rows = []
    for index in range(10, 30):
        retail_index = index if index <= 26 else index + 1
        bindings = tuple(relocations.get(index * 4, ()))
        expected = raw_words[index]
        replacement = unrelocated(retail[retail_index], bindings)
        if expected == replacement and index != 26:
            continue
        rows.append({
            "filename": FILENAME,
            "function": name,
            "offset": "0x%03X" % (index * 4),
            "expected": "0x%08X" % expected,
            "replacement": "0x%08X" % replacement,
            "expected_relocations": relocation_text(bindings),
            "replacement_relocations": relocation_text(bindings),
            "note": "Normalize closed actor point selector switch compiler layout",
            "insert_after": "0x%08X" % retail[27] if index == 26 else "",
            "insert_after_relocations": "-" if index == 26 else "",
            "omit": "false",
        })
    if len(rows) != 17 or sum(bool(row["insert_after"]) for row in rows) != 1:
        raise ValueError("Actor point selector guard closure changed: " + name)
    return rows


def all_rows(root, obj):
    return [row for name in TARGETS for row in guard_rows(root, obj, name)]


def write_rows(path, rows):
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]),
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def suffix_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]),
                            lineterminator="\n")
    writer.writerows(rows)
    return stream.getvalue().encode("ascii")


def function_blob(path, name):
    text, functions, relocations = parse_object(path)
    info = functions[name]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {offset - start: rows for offset, rows in relocations.items()
                if start <= offset < end}
    return text[start:end], bindings
