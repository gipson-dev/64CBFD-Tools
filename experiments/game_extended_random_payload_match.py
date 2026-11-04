"""Qualify func_1515AA84's extended random payload callback as guarded C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_extended_random_payload_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_185560.c.o"
ASM = "conker/asm/185560.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/234400.rodata.s"
BUILD = "conker/build/game-extended-random-payload-1515AA84-match"
ENTRY, ROM, WORDS = 0x1515AA84, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x80
RAW_SHA256 = "348476bfb8dc1e3916ccae5691e24920b9d2cab8974ebb4f0651fa311b8f8e35"
RETAIL_SHA256 = "6e62ce718edb8be90e7bfe301a517c46f15fe40c3967a284cbc6b9b37e113d90"
BINDINGS = {
    0x070: [("R_MIPS_26", "func_150ADA20")],
    0x0D8: [("R_MIPS_26", "func_15149130")],
    0x0EC: [("R_MIPS_26", "memcpy")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_ROWS = (
    dict(offset="0x078", expected="0x8FA30080", replacement="0x8FA80080"),
    dict(offset="0x084", expected="0x84780082", replacement="0x25030080"),
    dict(offset="0x088", expected="0x84790080", replacement="0x84780002"),
    dict(offset="0x08C", expected="0xAFAA0018", replacement="0x84790000"),
    dict(offset="0x090", expected="0x270F0001", replacement="0xAFAA0018"),
    dict(offset="0x094", expected="0x004F001B", replacement="0x270F0001"),
    dict(offset="0x098", expected="0xAFA00014", replacement="0x004F001B"),
    dict(offset="0x09C", expected="0xAFAD0010", replacement="0xAFA00014"),
    dict(offset="0x0A0", expected="0x9069000C", replacement="0xAFAD0010"),
    dict(offset="0x0A4", expected="0x00007010", replacement="0x9109000C"),
    dict(offset="0x0A8", expected="0x01D96021", replacement="0x00007010"),
    dict(offset="0x0AC", expected="0xAFA9001C", replacement="0x01D92021"),
    dict(offset="0x0B0", expected="0x90780001", replacement="0xAFA9001C"),
    dict(offset="0x0B4", expected="0x000C2400", replacement="0x91180001"),
    dict(offset="0x0B8", expected="0x15E00002", replacement="0x00046400"),
    dict(offset="0x0BC", expected="0x00000000", replacement="0x15E00002"),
    dict(offset="0x0C0", expected="0x0007000D", replacement="0x00000000"),
    dict(offset="0x0C4", expected="0x00045C03", replacement="0x0007000D"),
    dict(offset="0x0C8", expected="0x01602025", replacement="0x000C2403"),
)
PATCH_NOTE = "Normalize closed post-RNG owner and lifetime register schedule"


def complete_row(row):
    return {
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": row["offset"],
        "expected": row["expected"],
        "replacement": row["replacement"],
        "expected_relocations": "-",
        "replacement_relocations": "-",
        "note": PATCH_NOTE,
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }


def source_states(live):
    declarations = candidate.INSTALL_TYPES + candidate.DECLARATIONS + "\n"
    marker = "#include <ultra64.h>\n"
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED_MATCH in live or declarations in live:
            raise ValueError("Extended-random-payload predecessor source changed")
        qualified = live.replace(marker, marker + declarations, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED_MATCH, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED_MATCH) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed extended-random-payload source changed")
        predecessor = live.replace(declarations, "", 1).replace(
            candidate.SELECTED_MATCH, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Extended-random-payload source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_8008F970\n", 1)[1].split(
        "enddlabel D_8008F970", 1)[0]
    entries = [line for line in block.splitlines() if ".word" in line]
    if (calls or pointers != [0x234438] or len(entries) != 4 or
            entries[2].split(".word", 1)[1].strip() != FUNCTION or
            block.count(FUNCTION) != 1):
        raise ValueError("Extended-random-payload registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x234438"],
        "registry": "D_8008F970[2]",
        "abi": "owner, position, scalar and unused word; callback has no return value",
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
            report["natural_positional_differences"] != len(PATCH_ROWS) or
            report["guards"] != len(PATCH_ROWS)):
        raise ValueError("Extended-random-payload qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
