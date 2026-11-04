"""Qualify func_1519E464's owner-bound effect callback as guarded exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_owner_bound_effect_submit_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1CA420.c.o"
ASM = "conker/asm/1CA420.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22EF80.rodata.s"
BUILD = "conker/build/game-owner-bound-effect-submit-1519E464-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME, RETAIL_FRAME = 0x40, 0x38
RAW_SHA256 = "81123f0cb37ffdf30188869b0788820f00a2f180ac809d2f37b95755bf48b6d4"
RETAIL_SHA256 = "b6b9d29e64f59a13d8495a4c742338a7ec23986e4249ad02611f871cfab5cf43"
BINDINGS = RETAIL_BINDINGS = candidate.RETAIL_BINDINGS
NOTE = "Normalize owner-bound effect callback compiler allocation and scheduling"

PATCH_WORDS = (
    (0x000, 0x27BDFFC0, 0x27BDFFC8),
    (0x058, 0x920A000C, 0x920C000C),
    (0x05C, 0x9202000D, 0x920A000D),
    (0x068, 0xAFAA0010, 0xAFAC0010),
    (0x06C, 0x920B0001, 0x920D0001),
    (0x074, 0xA3A8003F, 0xA3A80033),
    (0x07C, 0x30470001, 0x31470001),
    (0x084, 0xAFAB0014, 0xAFAD0014),
    (0x08C, 0x93A8003F, 0x10400013),
    (0x090, 0x10400012, 0x93A80033),
    (0x094, 0xAFA20030, 0x8C6E0000),
    (0x098, 0x8C6C0000, 0x02002825),
    (0x09C, 0x02002825, 0x00003025),
    (0x0A0, 0x00003025, 0x8DC402F4),
    (0x0A4, 0x8D8402F4, 0xA3A80033),
    (0x0A8, 0xA3A8003F, 0xAFA2002C),
    (0x0B8, 0x8FA40030, 0x8FA7002C),
    (0x0C0, 0x93A8003F, 0x93A80033),
    (0x0C8, 0xA3A8003F, 0xA3A80033),
    (0x0CC, 0x24060010, 0x00E02025),
    (0x0D4, 0x00803825, 0x24060010),
    (0x0D8, 0x93A8003F, 0x93A80033),
    (0x0E4, 0x920E000D, 0x9218000D),
    (0x0E8, 0x240DFFFF, 0x240FFFFF),
    (0x0EC, 0xA60D000E, 0xA60F000E),
    (0x0F0, 0x35CF0001, 0x37190001),
    (0x0F4, 0xA20F000D, 0xA219000D),
    (0x100, 0x27BD0040, 0x27BD0038),
)
PATCH_ROWS = tuple(
    dict(
        offset="0x%03X" % offset,
        expected="0x%08X" % expected,
        replacement="0x%08X" % replacement,
        expected_relocations="-",
        replacement_relocations="-",
        note=NOTE,
    )
    for offset, expected, replacement in PATCH_WORDS
)


def complete_row(row):
    return {
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": row["offset"],
        "expected": row["expected"],
        "replacement": row["replacement"],
        "expected_relocations": row["expected_relocations"],
        "replacement_relocations": row["replacement_relocations"],
        "note": row["note"],
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }


def source_states(live):
    declarations = candidate.TYPES + candidate.INSTALL_DECLARATIONS + "\n"
    marker = "#include <ultra64.h>\n"
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or declarations in live:
            raise ValueError("Owner-bound effect submit predecessor source changed")
        qualified = live.replace(marker, marker + declarations, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1
        )
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed owner-bound effect submit source changed")
        predecessor = live.replace(declarations, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1
        )
        return predecessor, live, True
    raise ValueError("Owner-bound effect submit source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_8008A4E8\n", 1)[1].split(
        "enddlabel D_8008A4E8", 1
    )[0]
    entries = [line for line in block.splitlines() if ".word" in line]
    if (calls or pointers != [0x22EFC8] or
            entries[8].split(".word", 1)[1].strip() != FUNCTION or
            block.count(FUNCTION) != 1):
        raise ValueError("Owner-bound effect callback registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x22efc8"],
        "registry": "D_8008A4E8[8]",
        "abi": "one callback-record pointer; submits at most one owner-bound effect and returns void",
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
        raise ValueError("Owner-bound effect submit qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
