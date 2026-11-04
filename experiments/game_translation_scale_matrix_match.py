"""Qualify func_15158920's translated byte-scale matrix callback as guarded C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_translation_scale_matrix_candidates as candidate


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
BUILD = "conker/build/game-translation-scale-matrix-15158920-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x60
RAW_SHA256 = "8ef471c07b23eb554036678689f0104fc172fe6e932c1301fc2444117e78dfdf"
RETAIL_SHA256 = "0e791b1d89b25c4101f93a49bf1e91321f423e4346392474aa79c5a8d916bea0"
BINDINGS = {
    0x018: [("R_MIPS_HI16", "D_8008AE18")],
    0x01C: [("R_MIPS_LO16", "D_8008AE18")],
    0x054: [("R_MIPS_HI16", "D_800A6070")],
    0x058: [("R_MIPS_LO16", "D_800A6070")],
    0x0E4: [("R_MIPS_26", "guMtxF2L")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_ROWS = (
    dict(offset="0x010", expected="0x27A40020", replacement="0x27A40018"),
    dict(offset="0x064", expected="0xC7B20020", replacement="0xC7B20018"),
    dict(offset="0x06C", expected="0xE7A80050", replacement="0xE7A80048"),
    dict(offset="0x074", expected="0xC7A60024", replacement="0xC7A6001C"),
    dict(offset="0x078", expected="0xE7AA0054", replacement="0xE7AA004C"),
    dict(offset="0x084", expected="0xC7AA0028", replacement="0xC7AA0020"),
    dict(offset="0x088", expected="0xE7B00058", replacement="0xE7B00050"),
    dict(offset="0x090", expected="0xC7B20030", replacement="0xC7B20028"),
    dict(offset="0x094", expected="0xC7A60034", replacement="0xC7A6002C"),
    dict(offset="0x09C", expected="0xE7A40020", replacement="0xE7A40018"),
    dict(offset="0x0A0", expected="0xC7AA0038", replacement="0xC7AA0030"),
    dict(offset="0x0A8", expected="0xE7A80024", replacement="0xE7A8001C"),
    dict(offset="0x0AC", expected="0xC7B20040", replacement="0xC7B20038"),
    dict(offset="0x0B4", expected="0xE7B00028", replacement="0xE7B00020"),
    dict(offset="0x0B8", expected="0xC7A60044", replacement="0xC7A6003C"),
    dict(offset="0x0C0", expected="0xE7A40030", replacement="0xE7A40028"),
    dict(offset="0x0C4", expected="0xC7AA0048", replacement="0xC7AA0040"),
    dict(offset="0x0CC", expected="0xE7A80034", replacement="0xE7A8002C"),
    dict(offset="0x0D4", expected="0xE7B00038", replacement="0xE7B00030"),
    dict(offset="0x0DC", expected="0xE7A40040", replacement="0xE7A40038"),
    dict(offset="0x0E0", expected="0xE7A80044", replacement="0xE7A8003C"),
    dict(offset="0x0E8", expected="0xE7B00048", replacement="0xE7B00040"),
)
PATCH_NOTE = "Normalize translated byte-scale matrix local workspace placement"


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
            raise ValueError("Translation-scale matrix predecessor source changed")
        qualified = live.replace(marker, marker + declarations, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED_MATCH, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED_MATCH) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed translation-scale matrix source changed")
        predecessor = live.replace(declarations, "", 1).replace(
            candidate.SELECTED_MATCH, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Translation-scale matrix source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_8008AE0C\n", 1)[1].split(
        "enddlabel D_8008AE0C", 1)[0]
    entries = [line for line in block.splitlines() if ".word" in line]
    if (calls or pointers != [0x22F8D4] or len(entries) != 3 or
            entries[2].split(".word", 1)[1].strip() != FUNCTION or
            block.count(FUNCTION) != 1):
        raise ValueError("Translation-scale matrix registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x22f8d4"],
        "registry": "D_8008AE0C[2]",
        "abi": "fixed-matrix output and state pointers; callback returns one",
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
        raise ValueError("Translation-scale matrix qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
