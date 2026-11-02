"""Qualify the extended weighted emitter's closed compiler-layout gap."""

import argparse
import csv
import io
import re
import struct
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.pad_generated_object import parse_object


FUNCTION = "func_150E9178"
FILENAME = "generated_113D60"
SOURCE = "conker/src/game/generated_113D60.c"
ENTRY = 0x150E9178
ROM = 0x116628
WORDS = 153
RAW_FRAME = 0xF8
RETAIL_FRAME = 0xF0
OFFSETS = (
    0x000, 0x004, 0x008, 0x01C, 0x050, 0x054, 0x058, 0x05C, 0x060,
    0x064, 0x068, 0x06C, 0x070, 0x074, 0x078, 0x07C, 0x080, 0x084,
    0x088, 0x08C, 0x090, 0x094, 0x09C, 0x0A8, 0x0AC, 0x0C0, 0x0C8,
    0x0D0, 0x0D8, 0x0DC, 0x0F0, 0x130, 0x134, 0x138, 0x13C, 0x144,
    0x148, 0x168, 0x174, 0x178, 0x17C, 0x180, 0x184, 0x188, 0x18C,
    0x190, 0x198, 0x1B4, 0x1C4, 0x1F8, 0x204, 0x20C, 0x210, 0x260,
)

REPLACEMENT_RELOCATIONS = {
    0x06C: (("R_MIPS_HI16", "D_800BE9A4"),),
    0x070: (("R_MIPS_LO16", "D_800BE9A4"),),
    0x074: (("R_MIPS_HI16", "D_800DCD90"),),
    0x078: (("R_MIPS_LO16", "D_800DCD90"),),
    0x088: (("R_MIPS_HI16", "D_800DCDC4"),),
    0x08C: (("R_MIPS_LO16", "D_800DCDC4"),),
    0x094: (("R_MIPS_HI16", "D_800A13B8"),),
    0x0C0: (("R_MIPS_LO16", "D_800A13B8"),),
    0x0C8: (("R_MIPS_LO16", "D_800A13BC"),),
    0x0D0: (("R_MIPS_LO16", "D_800A13C0"),),
    0x0DC: (("R_MIPS_LO16", "D_800A13C4"),),
}

SYMBOLS = {
    "D_800BE9E8": 0x800BE9E8,
    "D_800BE9A4": 0x800BE9A4,
    "D_800DCD90": 0x800DCD90,
    "D_800DCDC4": 0x800DCDC4,
    "D_800A13B8": 0x800A13B8,
    "D_800A13BC": 0x800A13BC,
    "D_800A13C0": 0x800A13C0,
    "D_800A13C4": 0x800A13C4,
    "func_15144B34": 0x15144B34,
    "func_150ADA68": 0x150ADA68,
    "func_1514470C": 0x1514470C,
    "func_150ADA20": 0x150ADA20,
    "func_15149130": 0x15149130,
    "memcpy": 0x10022EC0,
}

TYPES = (
    "typedef signed char s8; typedef unsigned char u8; typedef short s16; "
    "typedef unsigned short u16; typedef int s32; typedef unsigned int u32; "
    "typedef float f32;\n#define NULL ((void *)0)\n"
)
DECLARATIONS = """
extern f32 D_800A13B8, D_800A13BC, D_800A13C0, D_800A13C4;
extern f32 D_800BE9A4, D_800DCD90;
extern s32 D_800BE9E8;
extern u8 *D_800DCDC4;
f32 func_150ADA68(void);
s32 func_150ADA20(void);
f32 *func_15144B34(s32);
void func_1514470C(void *, void *);
void *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);
void *memcpy(void *, const void *, u32);
"""


def candidate_source(root):
    source = (root / SOURCE).read_text()
    layouts = "\n".join(
        re.search(r"typedef struct " + name + r" \{.*?\} " + name + ";", source, re.S).group(0)
        for name in (
            "EventPayload113D60",
            "WorldPosition113D60",
            "EventPositionPayload113D60",
            "ExtendedEventPositionPayload113D60",
            "EventWeightNode113D60",
        )
    )
    body = re.search(r"void " + FUNCTION + r"\([^;{}]+\) \{\n.*?\n\}", source, re.S).group(0)
    return TYPES + layouts + DECLARATIONS + body + "\n"


def compile_candidate(root, output):
    output.mkdir(parents=True, exist_ok=True)
    source = output / "extended-weighted-emitter.c"
    obj = output / "extended-weighted-emitter.o"
    elf = output / "extended-weighted-emitter.elf"
    binary = output / "extended-weighted-emitter.bin"
    script = output / "extended-weighted-emitter.ld"
    source.write_text(candidate_source(root))
    compiler = root / "ido/ido5.3_recomp/cc"
    conker = root / "conker"
    relative_source = source.relative_to(conker)
    relative_obj = obj.relative_to(conker)
    result = subprocess.run(
        [
            str(compiler), "-c", "-32", "-G", "0", "-Xfullwarn", "-Xcpluscomm",
            "-signed", "-nostdinc", "-non_shared", "-Wab,-r4300_mul", "-mips2",
            "-o32", "-O2", "-g3", "-o", str(relative_obj), str(relative_source),
        ],
        cwd=conker,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout + result.stderr == ""
    assert obj.is_file(), "IDO reported success without producing the candidate object"
    script.write_text("SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n" % ENTRY)
    subprocess.run(
        [
            "mips-linux-gnu-ld", "-m", "elf32btsmip", "-T", str(script), "-e", FUNCTION,
            *(f"--defsym={name}=0x{value:X}" for name, value in SYMBOLS.items()),
            "-o", str(elf), str(obj),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["mips-linux-gnu-objcopy", "-O", "binary", "-j", ".text", str(elf), str(binary)],
        check=True,
        capture_output=True,
    )
    data = binary.read_bytes()
    assert len(data) >= WORDS * 4 and not any(data[WORDS * 4:])
    words = struct.unpack_from(">%dI" % WORDS, data)
    assert 0x10000 - (words[0] & 0xFFFF) == RAW_FRAME
    return obj, words


def relocation_text(relocations):
    return "-" if not relocations else "|".join(kind + ":" + symbol for kind, symbol in relocations)


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
    retail = struct.unpack_from(">%dI" % WORDS, (root / "conker/conker.us.bin").read_bytes(), ROM)
    assert tuple(i * 4 for i, pair in enumerate(zip(linked_words, retail)) if pair[0] != pair[1]) == OFFSETS
    data, functions, relocations = parse_object(obj)
    function = functions[FUNCTION]
    assert function["size"] == WORDS * 4
    base = function["value"]
    raw = struct.unpack_from(">%dI" % WORDS, data, base)
    rows = []
    for offset in OFFSETS:
        expected_relocations = tuple(relocations.get(base + offset, ()))
        replacement_relocations = REPLACEMENT_RELOCATIONS.get(offset, ())
        expected = raw[offset // 4]
        replacement = unrelocated(retail[offset // 4], replacement_relocations)
        assert expected == unrelocated(linked_words[offset // 4], expected_relocations)
        rows.append(
            {
                "filename": FILENAME,
                "function": FUNCTION,
                "offset": "0x%03X" % offset,
                "expected": "0x%08X" % expected,
                "replacement": "0x%08X" % replacement,
                "expected_relocations": relocation_text(expected_relocations),
                "replacement_relocations": relocation_text(replacement_relocations),
                "note": "Normalize extended weighted emitter frame, saved registers, locals and schedule",
                "insert_after": "",
                "insert_after_relocations": "",
                "omit": "false",
            }
        )
    normalized = list(linked_words)
    for offset in OFFSETS:
        normalized[offset // 4] = retail[offset // 4]
    assert tuple(normalized) == retail
    return rows


def write_rows(path, rows):
    fields = (
        "filename", "function", "offset", "expected", "replacement",
        "expected_relocations", "replacement_relocations", "note", "insert_after",
        "insert_after_relocations", "omit",
    )
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def suffix_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
    writer.writerows(rows)
    return stream.getvalue().encode("ascii")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="conker/build/game-extended-weighted-emitter-150E9178-guard-match",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / args.output
    obj, words = compile_candidate(root, output)
    rows = guard_rows(root, obj, words)
    write_rows(output / "isolated-guards.csv", rows)
    (output / "guard-suffix.csv").write_bytes(suffix_bytes(rows))
    print(
        {
            "words": len(words),
            "raw_frame": RAW_FRAME,
            "retail_frame": RETAIL_FRAME,
            "raw_differences": len(rows),
            "guards": len(rows),
            "relocation_words": sum(
                row["expected_relocations"] != "-" or row["replacement_relocations"] != "-"
                for row in rows
            ),
        }
    )


if __name__ == "__main__":
    main()
