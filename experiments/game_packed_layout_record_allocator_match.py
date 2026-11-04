"""Qualify func_15195984's packed-layout record allocator as guarded exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_packed_layout_record_allocator_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1C2C60.c.o"
ASM = "conker/asm/1C2C60.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = ASM
BUILD = "conker/build/game-packed-layout-record-allocator-15195984-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x18
RAW_SHA256 = "a79590c6d920e9375a20e45562ff18a99f1603a2c45b2a665f14d4c9806f8bf2"
RETAIL_SHA256 = "0bd6770d9f681f6353cd70092ff12e76dfb1b2595eaa0b4892202aa04dc340a5"
BINDINGS = RETAIL_BINDINGS = candidate.RETAIL_BINDINGS
NOTE = "Normalize packed-layout allocator compiler scheduling and register allocation"

PATCH_WORDS = (
    (0x030, 0x8FA9001C, 0x8FA8001C),
    (0x034, 0x8FAA0020, 0x8FA90020),
    (0x03C, 0x00404025, 0x00403825),
    (0x040, 0x24050001, 0xAC400018),
    (0x044, 0x2404FFFF, 0x00002825),
    (0x048, 0x00057040, 0x00401825),
    (0x04C, 0xAC400018, 0x2404FFFF),
    (0x050, 0xA444001C, 0x24A50001),
    (0x054, 0x004E1821, 0x28A10005),
    (0x058, 0xA464001E, 0x24630002),
    (0x05C, 0xA4640020, 0x1420FFFC),
    (0x060, 0xA4640022, 0xA464001A),
    (0x064, 0xA464001C, 0x24050001),
    (0x068, 0xA4440026, 0x00057040),
    (0x06C, 0xA444002A, 0xA4440026),
    (0x070, 0xA444002C, 0x004E1821),
    (0x074, 0xA444002E, 0xA4640028),
    (0x078, 0xA4440028, 0xA464002A),
    (0x07C, 0x8FAF0018, 0xA464002C),
    (0x080, 0x00092B03, 0xA4640026),
    (0x084, 0x30B80FFF, 0x8FAF0018),
    (0x088, 0xA44F0008, 0x00082303),
    (0x08C, 0x8FB90024, 0x30980FFF),
    (0x090, 0x31270FFF, 0xA44F0008),
    (0x094, 0x27050002, 0x8FB90024),
    (0x098, 0x24E70002, 0x31060FFF),
    (0x09C, 0x00A01825, 0x27040002),
    (0x0A0, 0x13200003, 0x24C60002),
    (0x0A4, 0x00E03025, 0x00801825),
    (0x0A8, 0x00051840, 0x13200003),
    (0x0AC, 0x00073040, 0x00C02825),
    (0x0B0, 0x000A5B03, 0x00041840),
    (0x0B4, 0x316C0FFF, 0x00062840),
    (0x0B8, 0x314D0FFF, 0x00095303),
    (0x0BC, 0xA44C000E, 0x314D0FFF),
    (0x0C0, 0xA44D0010, 0x312F0FFF),
    (0x0C4, 0x844E000E, 0xA44D000E),
    (0x0C8, 0x84580010, 0xA44F0010),
    (0x0CC, 0x240B0001, 0x000D70C0),
    (0x0D0, 0x000E78C0, 0x000FC0C0),
    (0x0D4, 0x0018C8C0, 0x24190001),
    (0x0DC, 0xA446000C, 0xA445000C),
    (0x0E0, 0xA44F000E, 0xA44E000E),
    (0x0E4, 0xA4590010, 0xA4580010),
    (0x0E8, 0xA04B0014, 0xA0590014),
    (0x0EC, 0x01001025, 0x00E01025),
)
PATCH_ROWS = tuple(
    dict(offset="0x%03X" % offset,
         expected="0x%08X" % expected,
         replacement="0x%08X" % replacement,
         expected_relocations="-",
         replacement_relocations="-",
         note=NOTE)
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
    declarations = candidate.TYPES + "\n"
    marker = "#include <ultra64.h>\n"
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or declarations in live:
            raise ValueError("Packed-layout allocator predecessor source changed")
        qualified = live.replace(marker, marker + declarations, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed packed-layout allocator source changed")
        predecessor = live.replace(declarations, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Packed-layout allocator source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    assembly = (root / ASM).read_text()
    call_line = "jal        func_15195984"
    if calls != [0x1C3038, 0x1C3394] or pointers or assembly.count(call_line) != 2:
        raise ValueError("Packed-layout allocator caller evidence changed")
    return {
        "direct_jal_calls": ["0x1c3038", "0x1c3394"],
        "aligned_pointer_literals": [],
        "callers": ["func_15195AA8", "func_15195DD4"],
        "abi": "key, packed size pair, packed scale pair, optional size doubling; returns record pointer",
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
        raise ValueError("Packed-layout allocator qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
