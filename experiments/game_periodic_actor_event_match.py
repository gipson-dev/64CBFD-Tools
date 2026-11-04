"""Qualify func_151905BC's periodic actor event callback as exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_periodic_actor_event_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1BA1D0.c.o"
ASM = "conker/asm/1BA1D0.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/2320A0.rodata.s"
BUILD = "conker/build/game-periodic-actor-event-151905BC-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x30
RAW_SHA256 = "4c3aa56dedc13d4ff32b00112f56e2eac6180820e461361b6c50cd2c658288f6"
RETAIL_SHA256 = "52c3b3a1f21596ce6b2eb1af8db52ecb069d12f602508c640d3846ab7539a411"
BINDINGS = {
    0x020: [("R_MIPS_HI16", "D_800BE9E4")],
    0x024: [("R_MIPS_LO16", "D_800BE9E4")],
    0x048: [("R_MIPS_HI16", "D_800CC2D0")],
    0x054: [("R_MIPS_LO16", "D_800CC2D0")],
    0x09C: [("R_MIPS_26", "func_1505D024")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_ROWS = ()


def complete_row(row):
    raise AssertionError("The direct periodic actor event callback needs no word guards")


def source_states(live):
    declarations = candidate.TYPES + "\n"
    marker = '#include "structs.h"\n'
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or declarations in live:
            raise ValueError("Periodic actor event predecessor source changed")
        qualified = live.replace(marker, marker + declarations, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed periodic actor event source changed")
        predecessor = live.replace(declarations, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Periodic actor event source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    row = "/* 23213C 8008D67C 151905BC */ .word func_151905BC"
    if calls or pointers != [0x23213C] or registry.count(row) != 1:
        raise ValueError("Periodic actor event registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x23213c"],
        "registry": "D_8008D67C[0] randomized-step callback",
        "abi": "one periodic-event record pointer; returns one",
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
        raise ValueError("Periodic actor event qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
