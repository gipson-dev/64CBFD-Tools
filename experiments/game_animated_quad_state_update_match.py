"""Qualify func_15171FC0's animated-quad state update as exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_animated_quad_state_update_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_19F150.c.o"
ASM = "conker/asm/19F150.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22FF90.rodata.s"
BUILD = "conker/build/game-animated-quad-state-update-15171FC0-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x18
RAW_SHA256 = "0e061335b82db6e05e926b51896c664298eeb5f6ede7f95da7f20cfd9dd3e122"
RETAIL_SHA256 = "0ee78838b31ef96a96d9fdb8845cdcd9fa3324b7ab0feeb9364d5ed4146244b9"
BINDINGS = {
    0x02C: [("R_MIPS_26", "func_1516972C")],
    0x05C: [("R_MIPS_HI16", "D_800BE9E4")],
    0x06C: [("R_MIPS_LO16", "D_800BE9E4")],
    0x094: [("R_MIPS_HI16", "D_8008CA4C")],
    0x0A8: [("R_MIPS_LO16", "D_8008CA4C")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_ROWS = ()


def complete_row(row):
    raise AssertionError("The direct animated-quad updater needs no word guards")


def source_states(live):
    declaration = candidate.DECLARATION
    marker = "extern u8 *D_8008CA4C[];\n"
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or declaration in live:
            raise ValueError("Animated-quad updater predecessor source changed")
        qualified = live.replace(marker, declaration + marker, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(declaration) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed animated-quad updater source changed")
        predecessor = live.replace(declaration, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Animated-quad updater source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    rows = (
        "/* 230274 8008B7B4 15171FC0 */ .word func_15171FC0",
        "/* 230D04 8008C244 15171FC0 */ .word func_15171FC0",
    )
    if calls or pointers != [0x230274, 0x230D04] or any(
            registry.count(row) != 1 for row in rows):
        raise ValueError("Animated-quad updater registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x230274", "0x230d04"],
        "registry": "two allocator-category descriptor update slots",
        "abi": "one animated-quad record pointer; no scalar return",
    }


def prepare(root, output=None):
    replacements = {
        "candidate": candidate,
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
        "RETAIL_BINDINGS": RETAIL_BINDINGS,
        "PATCH_ROWS": PATCH_ROWS,
        "complete_row": complete_row,
        "source_states": source_states,
        "registry_evidence": registry_evidence,
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
            report["natural_positional_differences"] != 0 or
            report["guards"] != 0):
        raise ValueError("Animated-quad updater qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
