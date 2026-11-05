"""Qualify func_151C86AC's owner event-state dispatcher as direct exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_owner_event_state_dispatch_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1F4650.c.o"
ASM = "conker/asm/1F4650.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22E730.rodata.s"
BUILD = "conker/build/game-owner-event-state-dispatch-151C86AC-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x18
RAW_SHA256 = "cd22afb41cc9617da662a270199edbab25ea6902758bfdb82da4f15c72d69e61"
RETAIL_SHA256 = "aec69e41677220ab8f52285c6c06ed15f3a0d156593353319cd958b65f9cb8c5"
BINDINGS = RETAIL_BINDINGS = candidate.RETAIL_BINDINGS
PATCH_ROWS = ()


def complete_row(row):
    raise AssertionError("The owner event-state dispatcher needs no word guards")


def source_states(live):
    marker = "#include <ultra64.h>\n"
    declarations = candidate.DECLARATIONS
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or declarations in live:
            raise ValueError("Owner event-state dispatcher predecessor source changed")
        qualified = live.replace(marker, marker + declarations, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed owner event-state dispatcher source changed")
        predecessor = live.replace(declarations, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Owner event-state dispatcher source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_80089F64\n", 1)[1].split(
        "enddlabel D_80089F64", 1)[0]
    entries = [line for line in block.splitlines() if ".word" in line]
    if calls or pointers != [0x22EA30] or len(entries) != 11:
        raise ValueError("Owner event-state dispatcher registry evidence changed")
    if entries[3].split(".word", 1)[1].strip() != FUNCTION:
        raise ValueError("Owner event-state dispatcher registry slot changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x22ea30"],
        "registry": "D_80089F64[3]",
        "abi": (
            "owner pointer, event pointer, unsigned byte event code; updates "
            "the owner state or forwards one action request and returns void"
        ),
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
        raise ValueError("Owner event-state dispatcher report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
