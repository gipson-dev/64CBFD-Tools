"""Qualify func_1515BAE0's timed packet callback as guarded byte-exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_timed_packet_callback_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_188F90.c.o"
ASM = "conker/asm/188F90.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22FF90.rodata.s"
BUILD = "conker/build/game-timed-packet-callback-1515BAE0-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x28
RAW_SHA256 = "7bc36c213ea35d0ff56e589c55e331778c866338bc64bd4dc0878f462250616d"
RETAIL_SHA256 = "25311acc5110ab6cab187ee93422a646099b3da0b0dcdd76378fed0b7b255da0"
BINDINGS = {
    0x018: [("R_MIPS_HI16", "D_800BE9E4")],
    0x02C: [("R_MIPS_LO16", "D_800BE9E4")],
    0x058: [("R_MIPS_HI16", "D_8008B078")],
    0x068: [("R_MIPS_LO16", "D_8008B078")],
    0x0A0: [("R_MIPS_26", "func_1514401C")],
    0x0BC: [("R_MIPS_HI16", "D_8008B07C")],
    0x0CC: [("R_MIPS_LO16", "D_8008B07C")],
    0x0E4: [("R_MIPS_26", "func_1516972C")],
    0x0F4: [("R_MIPS_26", "func_1516972C")],
}
PATCH_ROWS = (
    dict(offset="0x070", expected="0xAFA30024", replacement="0xA3A30023",
         note="Normalize timed packet completion flag spill width"),
    dict(offset="0x080", expected="0x8FA30024", replacement="0x93A30023",
         note="Normalize timed packet completion flag reload width"),
)


def complete_row(row):
    return {
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": row["offset"],
        "expected": row["expected"],
        "replacement": row["replacement"],
        "expected_relocations": "-",
        "replacement_relocations": "-",
        "note": row["note"],
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }


def source_states(live):
    declarations = candidate.INSTALL_TYPES + candidate.DECLARATIONS + "\n"
    marker = '#include "structs.h"\n'
    selected = candidate.SELECTED_MATCH
    if live.count(candidate.PLACEHOLDER) == 1:
        if selected in live or declarations in live:
            raise ValueError("Timed packet callback predecessor source changed")
        qualified = live.replace(marker, marker + "\n" + declarations, 1).replace(
            candidate.PLACEHOLDER, selected, 1)
        return live, qualified, False
    if live.count(selected) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed timed packet callback source changed")
        predecessor = live.replace("\n" + declarations, "", 1).replace(
            selected, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Timed packet callback source state changed")


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    row = "/* 23131C 8008C85C 1515BAE0 */ .word func_1515BAE0"
    if calls or pointers != [0x23131C] or registry.count(row) != 1:
        raise ValueError("Timed packet callback registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x23131c"],
        "registry": "anonymous descriptor at 0x8008C858, callback field +0x04",
        "abi": "one timed-packet record pointer; no return value",
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
            report["retail_sha256"] != RETAIL_SHA256 or report["guards"] != 2):
        raise ValueError("Timed packet callback report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
