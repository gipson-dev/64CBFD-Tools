"""Qualify func_151E2404 and its closed a0/v1 allocation cycle."""

import csv
import io
from pathlib import Path
import struct

from tools.experiments import game_menu_record_submit_candidates as candidate
from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


FUNCTION = candidate.TARGET
FILENAME = "generated_20AE20"
SOURCE = candidate.SOURCE
ASM = "conker/asm/20AE20.s"
ENTRY = 0x151E2404
ROM = candidate.ROM_OFFSET
WORDS = candidate.WORDS
FRAME = 0x18
RODATA_SYMBOL = "jtbl_800AB9BC"
OFFSETS = (
    0x004, 0x008, 0x01C, 0x034, 0x038, 0x03C, 0x040, 0x044,
    0x054, 0x05C, 0x064, 0x06C, 0x08C, 0x098, 0x0A0, 0x0AC,
    0x0B8, 0x0C0, 0x0C8, 0x0D0,
)
SYMBOLS = {
    "D_800E0BE0": 0x800E0BE0,
    "D_8008FDD4": 0x8008FDD4,
    "D_800AB690": 0x800AB690,
    "D_80082BBC": 0x80082BBC,
    RODATA_SYMBOL: 0x800AB9BC,
    "func_150076A0": 0x150076A0,
}


def candidate_owner(root):
    source = (root / SOURCE).read_text()
    return candidate.candidate_source(source, candidate.selected_body())


def compile_candidate(root, output):
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(
        root, output, candidate_owner(root), "raw-menu-record-submit")
    if diagnostics:
        raise ValueError("Menu record submitter diagnostics changed: " + diagnostics)
    data, functions = link_owner(root, output, obj, candidate.OWNER)
    function = functions[FUNCTION]
    if function["size"] != WORDS * 4:
        raise ValueError("Menu record submitter extent changed")
    linked = list(struct.unpack_from(">%dI" % WORDS, data, function["value"]))
    retail = struct.unpack_from(">%dI" % WORDS,
                                (root / "conker/conker.us.bin").read_bytes(), ROM)
    # The private owner link places compact .rodata beside .text. Production
    # anchors the same table at its retained retail symbol.
    linked[0x078 // 4] = retail[0x078 // 4]
    linked[0x080 // 4] = retail[0x080 // 4]
    return obj, tuple(linked)


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
    retail = struct.unpack_from(">%dI" % WORDS,
                                (root / "conker/conker.us.bin").read_bytes(), ROM)
    differences = tuple(index * 4 for index, pair in enumerate(zip(linked_words, retail))
                        if pair[0] != pair[1])
    if differences != OFFSETS:
        raise ValueError("Menu record submitter allocation cycle changed: %r" %
                         (differences,))
    text, functions, relocations = parse_object(obj)
    function = functions[FUNCTION]
    base = function["value"]
    raw = struct.unpack_from(">%dI" % WORDS, text, base)
    rows = []
    for offset in OFFSETS:
        bindings = tuple(relocations.get(base + offset, ()))
        expected = raw[offset // 4]
        if expected != unrelocated(linked_words[offset // 4], bindings):
            raise ValueError("Unlinked menu record word changed at 0x%X" % offset)
        rows.append({
            "filename": FILENAME,
            "function": FUNCTION,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % expected,
            "replacement": "0x%08X" % unrelocated(retail[offset // 4], bindings),
            "expected_relocations": relocation_text(bindings),
            "replacement_relocations": relocation_text(bindings),
            "note": "Normalize complete menu source/index a0-v1 allocation cycle",
            "insert_after": "",
            "insert_after_relocations": "",
            "omit": "false",
        })
    return rows


def write_rows(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def suffix_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
    writer.writerows(rows)
    return stream.getvalue().encode("ascii")
