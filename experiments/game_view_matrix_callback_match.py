"""Qualify func_150F9AB0's matrix-backed viewport callback as exact C."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_view_matrix_callback_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION = candidate.FUNCTION
FILENAME = "generated_126F60"
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_126F60.c.o"
ASM = "conker/asm/126F60.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22DBF0.rodata.s"
DISPATCHER = "conker/asm/13D350.s"
BUILD = "conker/build/game-view-matrix-callback-150F9AB0-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x78
RAW_SHA256 = "3e54faf09ba7dd2d8b56b6298561124c576c92b1c8dbb0b7494cc6c4944baac2"
RETAIL_SHA256 = "3d737b9109021619780f4c531185db540abfaf7e7c36724ab7f684ca6f056eef"
BINDINGS = {
    0x01C: [("R_MIPS_HI16", "D_80082FA4")],
    0x020: [("R_MIPS_LO16", "D_80082FA4")],
    0x030: [("R_MIPS_26", "func_15110360")],
    0x038: [("R_MIPS_HI16", "D_80082FA4")],
    0x03C: [("R_MIPS_LO16", "D_80082FA4")],
    0x040: [("R_MIPS_HI16", "D_800BE628")],
    0x044: [("R_MIPS_LO16", "D_800BE628")],
    0x0A4: [("R_MIPS_26", "func_15110544")],
    0x0E8: [("R_MIPS_26", "func_150FB4C0")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_ROWS = ()
COMMENT_BEFORE = "/* Non-matching placeholders for the text-only asm slice asm/126F60.s. */"
COMMENT_AFTER = "/* Restored functions and remaining placeholders for asm/126F60.s. */"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    marker = '#include "structs.h"\n'
    if live.count(candidate.PLACEHOLDER) == 1:
        if (candidate.SELECTED in live or candidate.DECLARATIONS in live or
                live.count(COMMENT_BEFORE) != 1 or COMMENT_AFTER in live):
            raise ValueError("View-matrix callback predecessor source changed")
        qualified = live.replace(
            marker, marker + candidate.DECLARATIONS, 1
        ).replace(COMMENT_BEFORE, COMMENT_AFTER, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1
        )
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if (live.count(candidate.DECLARATIONS) != 1 or
                live.count(COMMENT_AFTER) != 1 or
                candidate.PLACEHOLDER in live or COMMENT_BEFORE in live):
            raise ValueError("Installed view-matrix callback source changed")
        predecessor = live.replace(candidate.DECLARATIONS, "", 1).replace(
            COMMENT_AFTER, COMMENT_BEFORE, 1
        ).replace(candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("View-matrix callback source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(
        ">%dI" % (len(image) // 4), image[:len(image) & ~3]
    )
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]

    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_800891D8\n", 1)[1].split(
        "enddlabel D_800891D8", 1
    )[0]
    entries = [line.split(".word", 1)[1].strip()
               for line in block.splitlines() if ".word" in line]
    if calls or pointers != [0x22DC9C] or len(entries) != 5 or entries[1] != FUNCTION:
        raise ValueError("View-matrix callback registry evidence changed")

    dispatcher = (root / DISPATCHER).read_text()
    dispatch = dispatcher.split("glabel func_1510FEA0\n", 1)[1].split(
        "endlabel func_1510FEA0", 1
    )[0]
    required = (
        "13D6FC 1511024C E7B00010 */  swc1       $f16, 0x10($sp)",
        "13D700 15110250 E7A20014 */  swc1       $f2, 0x14($sp)",
        "13D704 15110254 E7A00018 */  swc1       $f0, 0x18($sp)",
        "13D708 15110258 AFA2001C */  sw         $v0, 0x1C($sp)",
        "13D720 15110270 8F3991D8 */  lw         $t9, %lo(D_800891D8)($t9)",
        "13D72C 1511027C 0320F809 */  jalr       $t9",
        "13D734 15110284 00402025 */  or         $a0, $v0, $zero",
    )
    if any(dispatch.count(text) != 1 for text in required):
        raise ValueError("View-matrix callback dispatcher ABI changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x22dc9c"],
        "registry": "D_800891D8[1]",
        "dispatcher": "func_1510FEA0 indirect callback at 0x1511027c",
        "abi": (
            "Gfx cursor plus six binary32 values and one context pointer; "
            "this callback uses the final three floats and returns the next cursor"
        ),
    }


def prepare(root, output=None):
    replacements = {
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
            report["guards"] != 0 or
            report["natural_positional_differences"] != 0 or
            report["changed_bodies"] != [FUNCTION]):
        raise ValueError("View-matrix callback qualification report changed")
    report["retail_relocations"] = len(RETAIL_BINDINGS)
    report["sdk_graphics_commands"] = 3
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
