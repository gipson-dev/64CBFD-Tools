"""Qualify func_15189900's motion-effect constructor as direct exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_effect_motion_constructor_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1B6DB0.c.o"
ASM = "conker/asm/1B6DB0.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/3C740.s"
BUILD = "conker/build/game-effect-motion-constructor-15189900-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x28
RAW_SHA256 = "fe12ba0e5f5a5e45029c249c9ae69437502fcfc57ae88df1ac81f61ff6721526"
RETAIL_SHA256 = "00f32282482f3dd37d312d61773449c380709d67a1028fc232ead73172b6be4c"
BINDINGS = {
    0x030: [("R_MIPS_26", "func_15167A68")],
    0x048: [("R_MIPS_26", "memcpy")],
    0x050: [("R_MIPS_26", "func_1510F800")],
    0x090: [("R_MIPS_26", "func_1510FD20")],
}
PATCH_ROWS = ()
CALLS = [
    0x36254, 0x3BEC8, 0x3CA80, 0x3CAFC, 0x3CB78, 0x3CBF4,
    0x3CC70, 0x3CCE4, 0x3CD60, 0x3CDDC, 0x3CE58,
]


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
    marker = "#include <ultra64.h>\n"
    installed_prefix = marker + "\n" + candidate.TYPES + "\n" + candidate.DECLARATIONS
    if live.count(candidate.PLACEHOLDER) == 1:
        if (candidate.TYPES in live or candidate.DECLARATIONS in live or
                candidate.SELECTED in live):
            raise ValueError("Motion-effect constructor predecessor source changed")
        qualified = live.replace(marker, installed_prefix, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if (live.count(candidate.TYPES) == 1 and
            live.count(candidate.DECLARATIONS) == 1 and
            live.count(candidate.SELECTED) == 1 and
            candidate.PLACEHOLDER not in live):
        predecessor = live.replace(candidate.SELECTED, candidate.PLACEHOLDER, 1).replace(
            installed_prefix, marker, 1)
        return predecessor, live, True
    raise ValueError("Motion-effect constructor source state changed")


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    caller_a = (root / "conker/src/game_360A0.c").read_text()
    caller_b = (root / "conker/src/game_3BA70.c").read_text()
    caller_c = (root / "conker/asm/3C740.s").read_text()
    if (calls != CALLS or pointers or
            caller_a.count("func_15189900(&tmp, arg0->unk1B);") != 1 or
            caller_b.count("func_15189900(&tmp, 1);") != 1 or
            caller_c.count("jal        func_15189900") != 9):
        raise ValueError("Motion-effect constructor caller evidence changed")
    return {
        "direct_jal_calls": [hex(offset) for offset in CALLS],
        "aligned_pointer_literals": [],
        "callers": ["func_15008BF0", "func_1500E8C0", "func_1500F40C (nine calls)"],
        "abi": "0x50-byte motion-descriptor pointer and unsigned byte enable flag; void return",
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
        raise ValueError("Motion-effect constructor report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
