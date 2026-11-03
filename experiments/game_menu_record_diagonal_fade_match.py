"""Qualify func_150B709C's diagonal menu-record update as direct exact C."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_menu_record_diagonal_fade_candidates as candidate
from tools.experiments.game_active_record_lookup_match import (
    compile_owner as no_unroll_compile_owner,
)


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_E4070.c.o"
ASM = "conker/asm/E4070.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22FF90.rodata.s"
BUILD = "conker/build/game-menu-record-diagonal-fade-150B709C-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0
RAW_SHA256 = "773d5996f50c8bc8cc1733e3ebf5ec83665f5f41f0ceeec29c2b6e6ed4e5a114"
RETAIL_SHA256 = "3d7561b59f27e10330e521fa0d371a77a238cf9216ed7df6587223c665530745"
BINDINGS = {
    0x008: [("R_MIPS_HI16", "D_800BE9E4")],
    0x014: [("R_MIPS_HI16", "D_800BE9E4")],
    0x018: [("R_MIPS_LO16", "D_800BE9E4")],
    0x03C: [("R_MIPS_LO16", "D_800BE9E4")],
}
PATCH_ROWS = ()


def complete_row(row):
    raise AssertionError("Direct diagonal menu-record update must not create guards")


def source_states(live):
    marker = "#include <ultra64.h>\n"
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or candidate.TYPES in live:
            raise ValueError("Diagonal menu-record predecessor source changed")
        qualified = live.replace(marker, marker + candidate.TYPES, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(candidate.TYPES) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed diagonal menu-record source changed")
        predecessor = live.replace(candidate.TYPES, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Diagonal menu-record source state changed")


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_8008CA20\n", 1)[1].split(
        "enddlabel D_8008CA20", 1)[0]
    entries = [line for line in block.splitlines() if ".word" in line]
    if (calls or pointers != [0x231500] or
            entries[8].split(".word", 1)[1].strip() != FUNCTION or
            block.count(FUNCTION) != 1):
        raise ValueError("Diagonal menu-record registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x231500"],
        "registry": "D_8008CA20[8]",
        "abi": "one record pointer; void phase callback updates progress, position and opacity",
    }


def checked_candidate(root, obj):
    raw, bindings = harness.function_blob(obj)
    if len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        raise ValueError("Diagonal menu-record natural candidate changed")
    if bindings != BINDINGS:
        raise ValueError("Diagonal menu-record relocation bindings changed")
    if raw != harness.retail_object_bytes(root):
        raise ValueError("Diagonal menu-record natural candidate differs from retail")
    return raw, bindings


def assemble_owner(root, output, compact, rows, fields, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    patch_file = owner_dir / "retail-word-patches.csv"
    harness.write_patches(patch_file, fields, rows)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(harness.emit_padded_assembly(
        compact, root / ASM, word_patches_path=patch_file,
        filename=FILENAME, rodata_symbol="jtbl_8009FD00_game"))
    obj = owner_dir / (FILENAME + ".c.o")
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly),
    ], check=True, capture_output=True)
    return obj


def prepare(root, output=None):
    replacements = {
        "candidate": candidate,
        "compile_owner": no_unroll_compile_owner,
        "FUNCTION": FUNCTION,
        "FILENAME": FILENAME,
        "SOURCE": SOURCE,
        "OBJECT": OBJECT,
        "ASM": ASM,
        "GUARDS": GUARDS,
        "ELF": ELF,
        "LINKER": LINKER,
        "ROM_IMAGE": ROM_IMAGE,
        "REGISTRY": REGISTRY,
        "BUILD": BUILD,
        "ENTRY": ENTRY,
        "ROM": ROM,
        "WORDS": WORDS,
        "SIZE": SIZE,
        "NATURAL_FRAME": NATURAL_FRAME,
        "RETAIL_FRAME": RETAIL_FRAME,
        "RAW_SHA256": RAW_SHA256,
        "RETAIL_SHA256": RETAIL_SHA256,
        "BINDINGS": BINDINGS,
        "PATCH_ROWS": PATCH_ROWS,
        "complete_row": complete_row,
        "source_states": source_states,
        "registry_evidence": registry_evidence,
        "checked_candidate": checked_candidate,
        "assemble_owner": assemble_owner,
    }
    saved = {name: getattr(harness, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(harness, name, value)
        result = harness.prepare(root, output or Path(root) / BUILD)
    finally:
        for name, value in saved.items():
            setattr(harness, name, value)
    report = result["report"]
    if (report["raw_sha256"] != RAW_SHA256 or
            report["retail_sha256"] != RETAIL_SHA256 or
            report["guards"] != 0 or
            report["natural_positional_differences"] != 0):
        raise ValueError("Diagonal menu-record qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
