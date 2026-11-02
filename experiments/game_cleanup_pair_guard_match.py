"""Qualify the twin resource-cleanup callbacks and their closed register gap."""

import csv
import io
from pathlib import Path
import struct

from tools.experiments.game_cleanup_pair_candidates import (
    OWNER, SOURCE, TARGETS, WORDS, body)
from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span, link_owner)
from tools.pad_generated_object import parse_object


ASM = "conker/asm/1F4650.s"
OFFSETS = (0x020, 0x040, 0x044, 0x048)
SYMBOLS = {
    "func_1516972C": 0x1516972C,
    "func_151C87AC": 0x151C87AC,
    "func_1000FD38": 0x1000FD38,
    "func_1513CA6C": 0x1513CA6C,
    "func_1513CAA0": 0x1513CAA0,
}


def selected_bodies():
    return {name: body(name, finalizer, "reload_owner")
            for name, _, _, finalizer in TARGETS}


def candidate_owner(root):
    source = (Path(root) / SOURCE).read_text()
    selected = selected_bodies()
    if all(value in source for value in selected.values()):
        return source
    for name, _, _, _ in TARGETS:
        lo, hi = function_span(source, name)
        predecessor = source[lo:hi]
        if predecessor != "s32 %s() {\n    return 0;\n}" % name:
            raise ValueError("Unknown cleanup-pair predecessor for " + name)
        source = source[:lo] + selected[name] + source[hi:]
    return source


def compile_candidate(root, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(
        Path(root), output, candidate_owner(root), "cleanup-pair")
    if diagnostics:
        raise ValueError("Cleanup-pair compiler diagnostics changed: " + diagnostics)
    data, functions = link_owner(Path(root), output, obj, OWNER)
    linked = {}
    for name, _, _, _ in TARGETS:
        info = functions[name]
        if info["size"] != WORDS * 4:
            raise ValueError("Cleanup-pair extent changed for " + name)
        linked[name] = struct.unpack_from(">%dI" % WORDS, data, info["value"])
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


def guard_rows(root, obj, linked):
    root = Path(root)
    rom = (root / "conker/conker.us.bin").read_bytes()
    text, functions, relocations = parse_object(obj)
    rows = []
    for name, _, rom_offset, _ in TARGETS:
        retail = struct.unpack_from(">%dI" % WORDS, rom, rom_offset)
        differences = tuple(index * 4 for index, pair in enumerate(zip(linked[name], retail))
                            if pair[0] != pair[1])
        if differences != OFFSETS:
            raise ValueError("Cleanup-pair difference set changed for %s: %r" %
                             (name, differences))
        info = functions[name]
        base = info["value"]
        raw = struct.unpack_from(">%dI" % WORDS, text, base)
        for offset in OFFSETS:
            expected_relocations = tuple(relocations.get(base + offset, ()))
            expected = raw[offset // 4]
            if expected != unrelocated(linked[name][offset // 4], expected_relocations):
                raise ValueError("Unlinked cleanup-pair word changed at 0x%X" % offset)
            rows.append({
                "filename": OWNER,
                "function": name,
                "offset": "0x%03X" % offset,
                "expected": "0x%08X" % expected,
                "replacement": "0x%08X" % unrelocated(
                    retail[offset // 4], expected_relocations),
                "expected_relocations": relocation_text(expected_relocations),
                "replacement_relocations": relocation_text(expected_relocations),
                "note": "Normalize cleanup callback owner reload register allocation",
                "insert_after": "",
                "insert_after_relocations": "",
                "omit": "false",
            })
    return rows


def write_rows(path, rows):
    path = Path(path)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def suffix_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
    writer.writerows(rows)
    return stream.getvalue().encode("ascii")
