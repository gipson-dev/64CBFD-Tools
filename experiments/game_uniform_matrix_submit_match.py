"""Qualify func_1515858C's uniform matrix submit as direct byte-exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_uniform_matrix_submit_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_185560.c.o"
ASM = "conker/asm/185560.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22F8C0.rodata.s"
BUILD = "conker/build/game-uniform-matrix-submit-1515858C-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x68
RAW_SHA256 = "a2b2aed67410b24442f948dad6945ead9f2c3f17e78f61b8e58df9fa1b8624e3"
RETAIL_SHA256 = "d4ac8544f180d34ce45b665bf4541a61563a031139e4b2c71a311151975e759d"
BINDINGS = {
    0x020: [("R_MIPS_26", "func_150A8050")],
    0x0D8: [("R_MIPS_26", "guMtxF2L")],
}
PATCH_ROWS = ()


def complete_row(row):
    raise AssertionError("Direct uniform matrix submit must not create guards")


def source_states(live):
    declarations = candidate.INSTALL_TYPES + candidate.DECLARATIONS + "\n"
    marker = "#include <ultra64.h>\n"
    selected = candidate.SELECTED_POINTER_BEFORE
    if live.count(candidate.PLACEHOLDER) == 1:
        if selected in live or declarations in live:
            raise ValueError("Uniform matrix submit predecessor source changed")
        qualified = live.replace(marker, marker + declarations, 1).replace(
            candidate.PLACEHOLDER, selected, 1)
        return live, qualified, False
    if live.count(selected) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed uniform matrix submit source changed")
        predecessor = live.replace(declarations, "", 1).replace(
            selected, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Uniform matrix submit source state changed")


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_8008AE0C\n", 1)[1].split(
        "enddlabel D_8008AE0C", 1)[0]
    entries = [line for line in block.splitlines() if ".word" in line]
    if (calls or pointers != [0x22F8CC] or
            entries[0].split(".word", 1)[1].strip() != FUNCTION or
            block.count(FUNCTION) != 1):
        raise ValueError("Uniform matrix submit registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x22f8cc"],
        "registry": "D_8008AE0C[0]",
        "abi": "fixed-matrix output and state pointers; callback returns one after conversion",
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
            report["retail_sha256"] != RETAIL_SHA256 or report["guards"] != 0):
        raise ValueError("Uniform matrix submit report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
