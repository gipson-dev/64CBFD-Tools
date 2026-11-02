"""Qualify func_150DFCA8's closed floating-register allocation gap."""

import csv
import io
import struct
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


FUNCTION = "func_150DFCA8"
FILENAME = "generated_10CD70"
SOURCE = "conker/src/game/generated_10CD70.c"
ASM = "conker/asm/10CD70.s"
ENTRY = 0x150DFCA8
ROM = 0x10D158
WORDS = 63
OFFSETS = (
    0x00C, 0x010, 0x018, 0x01C, 0x024, 0x028, 0x02C, 0x030,
    0x034, 0x040, 0x058, 0x060, 0x070, 0x078, 0x098, 0x09C,
    0x0A0, 0x0A4, 0x0A8, 0x0D0, 0x0D4, 0x0D8, 0x0DC, 0x0E0,
)
SYMBOLS = {
    "D_800A0FA0": 0x800A0FA0,
    "D_800A0FA4": 0x800A0FA4,
    "D_800A0FA8": 0x800A0FA8,
    "D_800A0FAC": 0x800A0FAC,
    "D_800BE9E4": 0x800BE9E4,
}

DECLARATIONS = (
    "extern f32 D_800A0FA0, D_800A0FA4, D_800A0FA8, D_800A0FAC;\n"
    "extern s32 D_800BE9E4;\n"
)
TYPE = """typedef struct MotionTargetState150DFCA8 {
    f32 field0;
    f32 position;
    u8 reserved08[0x5C];
    f32 velocity;
    u8 reserved68[0x14];
    f32 targetVelocity;
} MotionTargetState150DFCA8;
"""
BODY = """/* Integrate vertical motion and approach the region-selected velocity. */
void func_150DFCA8(MotionTargetState150DFCA8 *state) {
    f32 target;

    state->position += state->velocity * (f32)D_800BE9E4;
    if (state->position < 11.0f) {
        target = D_800A0FA0;
        state->targetVelocity = target;
    } else if (55.0f < state->position) {
        target = -D_800A0FA4;
        state->targetVelocity = target;
    } else {
        target = state->targetVelocity;
    }

    if (state->velocity < target) {
        state->velocity += D_800A0FA8;
        if (target < state->velocity) {
            state->velocity = target;
        }
    } else if (target < state->velocity) {
        state->velocity -= D_800A0FAC;
        if (state->velocity < target) {
            state->velocity = target;
        }
    }
}
"""
PLACEHOLDER = "s32 func_150DFCA8() {\n    return 0;\n}"
BLOCK = """#ifdef RETAIL_FUNC_150DFCA8
%s%s
%s#else
%s
#endif""" % (DECLARATIONS, TYPE, BODY, PLACEHOLDER)


def candidate_owner(root, enabled=False):
    source = (Path(root) / SOURCE).read_text()
    if BLOCK not in source:
        if source.count(PLACEHOLDER) != 1:
            raise ValueError("Unknown motion-target predecessor")
        source = source.replace(PLACEHOLDER, BLOCK, 1)
    if enabled:
        source = "#define RETAIL_FUNC_150DFCA8 1\n" + source
    return source


def compile_candidate(root, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(
        Path(root), output, candidate_owner(root, enabled=True), "motion-target-clamp")
    if diagnostics:
        raise ValueError("Motion-target compiler diagnostics changed: " + diagnostics)
    data, functions = link_owner(Path(root), output, obj, FILENAME)
    info = functions[FUNCTION]
    if info["size"] != WORDS * 4:
        raise ValueError("Motion-target extent changed")
    return obj, struct.unpack_from(">%dI" % WORDS, data, info["value"])


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
    root = Path(root)
    retail = struct.unpack_from(">%dI" % WORDS,
                                (root / "conker/conker.us.bin").read_bytes(), ROM)
    differences = tuple(index * 4 for index, pair in enumerate(zip(linked_words, retail))
                        if pair[0] != pair[1])
    if differences != OFFSETS:
        raise ValueError("Motion-target difference set changed: %r" % (differences,))
    text, functions, relocations = parse_object(obj)
    info = functions[FUNCTION]
    if info["size"] != WORDS * 4:
        raise ValueError("Motion-target raw extent changed")
    base = info["value"]
    raw = struct.unpack_from(">%dI" % WORDS, text, base)
    rows = []
    for offset in OFFSETS:
        expected_relocations = tuple(relocations.get(base + offset, ()))
        expected = raw[offset // 4]
        if expected != unrelocated(linked_words[offset // 4], expected_relocations):
            raise ValueError("Unlinked candidate word changed at 0x%X" % offset)
        rows.append({
            "filename": FILENAME,
            "function": FUNCTION,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % expected,
            "replacement": "0x%08X" % unrelocated(
                retail[offset // 4], expected_relocations),
            "expected_relocations": relocation_text(expected_relocations),
            "replacement_relocations": relocation_text(expected_relocations),
            "note": "Normalize motion-target clamp floating-register allocation",
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
