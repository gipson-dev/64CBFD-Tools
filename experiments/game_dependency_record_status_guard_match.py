"""Qualify the indexed dependency-record status query and its closed register gap."""

import csv
import io
from pathlib import Path
import struct
import subprocess
import sys

from tools.experiments.game_dependency_record_status_candidates import (
    ENTRY, GUARD_OWNER, OWNER, ROM_OFFSET, SOURCE, TARGET, WORDS,
    candidate_source as install_candidate)
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.pad_generated_object import parse_object


ASM = "conker/asm/C9EC0.s"
OFFSETS = (0x014, 0x094, 0x098, 0x09C, 0x0B0, 0x0B4,
           0x0B8, 0x0BC, 0x0C0, 0x0C4, 0x0C8, 0x0D4)
SYMBOLS = {
    "D_800D2FB0": 0x800D2FB0,
    "D_800D2E4C": 0x800D2E4C,
}


def candidate_owner(root):
    return install_candidate((Path(root) / SOURCE).read_text())


def compile_profile_owner(root, output, source, name):
    """Compile with generated_C9EC0's actual no-loop-unroll Make profile."""
    root, output = Path(root), Path(output)
    raw, processed, obj = (output / (name + suffix)
                           for suffix in (".c", "-processed.c", ".o"))
    raw.write_text(source)
    processor = [sys.executable, str(root / "tools/asm-processor/asm_processor.py"),
                 "-O2", "-g3", str(raw.relative_to(root / "conker"))]
    preprocess = subprocess.run(processor, cwd=root / "conker",
                                capture_output=True, text=True, check=True)
    if preprocess.stderr:
        raise ValueError(preprocess.stderr)
    processed.write_text(preprocess.stdout)
    includes = (".", "include", "include/2.0L", "include/2.0L/PR", "include/libc",
                "src/libultra/os", "src/libultra/audio", "src/libultra/io")
    command = [str(root / "ido/ido5.3_recomp/cc"), "-c", "-32", "-G", "0",
               "-Xfullwarn", "-Xcpluscomm", "-signed", "-nostdinc", "-non_shared",
               "-Wab,-r4300_mul", "-D_LANGUAGE_C", "-D_FINALROM", "-DF3DEX_GBI_2",
               "-D_MIPS_SZLONG=32", "-woff", "649,838",
               *(flag for path in includes for flag in ("-I", path)),
               "-O2", "-g3", "-Wo,-loopunroll,0", "-mips2", "-o32",
               "-o", str(obj.relative_to(root / "conker")),
               str(processed.relative_to(root / "conker"))]
    result = subprocess.run(command, cwd=root / "conker", capture_output=True, text=True)
    diagnostics = result.stdout + result.stderr
    (output / (name + "-diagnostics.txt")).write_text(diagnostics)
    if result.returncode:
        raise ValueError(diagnostics)
    subprocess.run([*processor, "--post-process", str(obj.relative_to(root / "conker")),
                    "--assembler",
                    "mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include",
                    "--asm-prelude", "include/asm_processor_prelude.inc"],
                   cwd=root / "conker", capture_output=True, text=True, check=True)
    return obj, diagnostics


def compile_candidate(root, output):
    root, output = Path(root), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_profile_owner(
        root, output, candidate_owner(root), "dependency-record-status")
    if diagnostics:
        raise ValueError("Dependency-record status diagnostics changed: " + diagnostics)
    data, functions = link_owner(root, output, obj, OWNER)
    info = functions[TARGET]
    if info["size"] != WORDS * 4:
        raise ValueError("Dependency-record status extent changed: %d" % info["size"])
    words = struct.unpack_from(">%dI" % WORDS, data, info["value"])
    return obj, words


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
    retail = struct.unpack_from(">%dI" % WORDS,
                                (root / "conker/conker.us.bin").read_bytes(),
                                ROM_OFFSET)
    differences = tuple(index * 4 for index, pair in enumerate(zip(linked, retail))
                        if pair[0] != pair[1])
    if differences != OFFSETS:
        raise ValueError("Dependency-record status difference set changed: %r" %
                         (differences,))
    text, functions, relocations = parse_object(obj)
    info = functions[TARGET]
    base = info["value"]
    raw = struct.unpack_from(">%dI" % WORDS, text, base)
    rows = []
    for offset in OFFSETS:
        expected_relocations = tuple(relocations.get(base + offset, ()))
        if expected_relocations:
            raise ValueError("Unexpected guarded relocation at 0x%X" % offset)
        expected = raw[offset // 4]
        if expected != unrelocated(linked[offset // 4], expected_relocations):
            raise ValueError("Unlinked dependency-record status word changed at 0x%X" %
                             offset)
        rows.append({
            "filename": GUARD_OWNER,
            "function": TARGET,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % expected,
            "replacement": "0x%08X" % retail[offset // 4],
            "expected_relocations": "-",
            "replacement_relocations": "-",
            "note": ("Normalize dependency status address operand order and closed "
                     "loop register allocation"),
            "insert_after": "",
            "insert_after_relocations": "",
            "omit": "false",
        })
    return rows


def write_rows(path, rows):
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def suffix_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
    writer.writerows(rows)
    return stream.getvalue().encode("ascii")
