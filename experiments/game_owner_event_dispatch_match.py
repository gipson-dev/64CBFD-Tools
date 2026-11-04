"""Qualify func_15191980's owner-event dispatcher as guarded exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_owner_event_dispatch_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1BA1D0.c.o"
ASM = "conker/asm/1BA1D0.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22FF90.rodata.s"
BUILD = "conker/build/game-owner-event-dispatch-15191980-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x28
RAW_SHA256 = "29108e69524af3a9317cdfc225d863e083db157f492c9d5a10a6558dbd10e27f"
RETAIL_SHA256 = "802a9b01279fd08f0a8a7bff60d857fcc40a7dca93fa04d86b3890e50bd4c738"
BINDINGS = {
    0x0AC: [("R_MIPS_26", "func_1516972C")],
    0x0C8: [("R_MIPS_26", "func_1516972C")],
    0x0E8: [("R_MIPS_26", "func_15169850")],
}
RETAIL_BINDINGS = candidate.RETAIL_BINDINGS

PATCH_ROWS = (
    dict(offset="0x020",
         expected="0x54410012",
         replacement="0x8FAF002C",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x024",
         expected="0x2401000C",
         replacement="0x54410012",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x028",
         expected="0x8FAF002C",
         replacement="0x2401000C",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x034",
         expected="0x51D80007",
         replacement="0x8FA8002C",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x038",
         expected="0x920B0018",
         replacement="0x51D80006",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x03C",
         expected="0x8FA8002C",
         replacement="0x920A0018",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x050",
         expected="0x920B0018",
         replacement="0x920A0018",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x054",
         expected="0x240A0064",
         replacement="0x240C0064",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x058",
         expected="0xA60A0016",
         replacement="0xA60C0016",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x05C",
         expected="0x356C0001",
         replacement="0x354B0001",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x060",
         expected="0x10000023",
         replacement="0xA20B0018",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x064",
         expected="0xA20C0018",
         replacement="0x10000023",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x068",
         expected="0x2401000C",
         replacement="0x8FBF0024",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x06C",
         expected="0x10410005",
         replacement="0x2401000C",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x070",
         expected="0x24010050",
         replacement="0x10410006",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x074",
         expected="0x10410003",
         replacement="0x8FAF002C",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x078",
         expected="0x2401000E",
         replacement="0x24010050",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x07C",
         expected="0x54410010",
         replacement="0x10410003",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x080",
         expected="0x2401004E",
         replacement="0x2401000E",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x084",
         expected="0x8FAF002C",
         replacement="0x5441000F",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x088",
         expected="0x8E0D0010",
         replacement="0x2401004E",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x08C",
         expected="0x8DEE0000",
         replacement="0x8E0D0010",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x090",
         expected="0x11AE0006",
         replacement="0x8DEE0000",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x094",
         expected="0x00000000",
         replacement="0x8FA8002C",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x098",
         expected="0x8FA8002C",
         replacement="0x11AE0005",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x09C",
         expected="0x92180014",
         replacement="0x00000000",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0A0",
         expected="0x91190004",
         replacement="0x92180014",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0A4",
         expected="0x57190013",
         replacement="0x91190004",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0A8",
         expected="0x8FBF0024",
         replacement="0x57190012",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0AC",
         expected="0x0C000000",
         replacement="0x8FBF0024",
         expected_relocations="R_MIPS_26:func_1516972C",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0B0",
         expected="0x02002025",
         replacement="0x0C000000",
         expected_relocations="-",
         replacement_relocations="R_MIPS_26:func_1516972C",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0B4",
         expected="0x1000000F",
         replacement="0x02002025",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0B8",
         expected="0x8FBF0024",
         replacement="0x1000000E",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0BC",
         expected="0x2401004E",
         replacement="0x8FBF0024",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0C0",
         expected="0x14410005",
         replacement="0x2401004E",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0C4",
         expected="0x27A90030",
         replacement="0x14410005",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0C8",
         expected="0x0C000000",
         replacement="0x8FA4002C",
         expected_relocations="R_MIPS_26:func_1516972C",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0CC",
         expected="0x02002025",
         replacement="0x0C000000",
         expected_relocations="-",
         replacement_relocations="R_MIPS_26:func_1516972C",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0D0",
         expected="0x10000008",
         replacement="0x02002025",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0D4",
         expected="0x8FBF0024",
         replacement="0x10000007",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0D8",
         expected="0x8FA4002C",
         replacement="0x8FBF0024",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0DC",
         expected="0x91250003",
         replacement="0x93A50033",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0E0",
         expected="0xAFB00010",
         replacement="0x26060010",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0E4",
         expected="0x26060010",
         replacement="0x26070014",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
    dict(offset="0x0EC",
         expected="0x26070014",
         replacement="0xAFB00010",
         expected_relocations="-",
         replacement_relocations="-",
         note="Normalize owner-event dispatcher compiler scheduling and register allocation"),
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
    marker = '#include "structs.h"\n'
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or declarations in live:
            raise ValueError("Owner-event dispatcher predecessor source changed")
        qualified = live.replace(marker, marker + declarations, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed owner-event dispatcher source changed")
        predecessor = live.replace(declarations, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Owner-event dispatcher source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    row = "/* 230604 8008BB44 15191980 */ .word func_15191980"
    if calls or pointers != [0x230604] or registry.count(row) != 1:
        raise ValueError("Owner-event dispatcher registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x230604"],
        "registry": "D_8008B4D4 descriptor callback slot at 0x8008BB44",
        "abi": "record pointer, owner event pointer, command byte; no scalar return",
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
        raise ValueError("Owner-event dispatcher qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))

