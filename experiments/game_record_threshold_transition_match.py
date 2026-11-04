"""Qualify func_1512B630's threshold transition as exact semantic C."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_record_threshold_transition_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_157840.c.o"
ASM = "conker/asm/157840.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = ASM
BUILD = "conker/build/game-record-threshold-transition-1512B630-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x20
RAW_SHA256 = "3786acad0df74e808ca73353073c46b140c3221709733038540586fb4ad6a29c"
RETAIL_SHA256 = "140e3fe26d7be7fdf9ddb1795c643e152e070e610e79ca3b10af89d2ba0838c5"
BINDINGS = {
    0x024: [("R_MIPS_HI16", "D_800DC204")],
    0x03C: [("R_MIPS_LO16", "D_800DC204")],
    0x048: [("R_MIPS_HI16", "D_800DC206")],
    0x05C: [("R_MIPS_LO16", "D_800DC206")],
    0x098: [("R_MIPS_26", "func_1512B5FC")],
    0x0C8: [("R_MIPS_26", "func_1512B5FC")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_ROWS = ()
COMMENT_BEFORE = "/* Non-matching placeholders for the text-only asm slice asm/157840.s. */"
COMMENT_AFTER = "/* Restored functions and remaining placeholders for asm/157840.s. */"


def source_states(live):
    marker = '#include "structs.h"\n'
    if live.count(candidate.PLACEHOLDER) == 1:
        if (candidate.SELECTED in live or candidate.DECLARATIONS in live or
                live.count(COMMENT_BEFORE) != 1 or COMMENT_AFTER in live):
            raise ValueError("Threshold-transition predecessor source changed")
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
            raise ValueError("Installed threshold-transition source changed")
        predecessor = live.replace(candidate.DECLARATIONS, "", 1).replace(
            COMMENT_AFTER, COMMENT_BEFORE, 1
        ).replace(candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Threshold-transition source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    if calls != [0x15886C, 0x158998] or pointers:
        raise ValueError("Threshold-transition retail registry changed")

    assembly = (root / ASM).read_text()
    caller = assembly.split("glabel func_1512B1B8\n", 1)[1].split(
        "endlabel func_1512B1B8", 1
    )[0]
    required = (
        "158868 1512B3B8 AFAB0010 */  sw         $t3, 0x10($sp)",
        "15886C 1512B3BC 0D44AD8C */  jal        func_1512B630",
        "158870 1512B3C0 AFA00014 */   sw        $zero, 0x14($sp)",
        "158874 1512B3C4 50400003 */  beql       $v0, $zero, .L1512B3D4",
        "158994 1512B4E4 AFB90010 */  sw         $t9, 0x10($sp)",
        "158998 1512B4E8 0D44AD8C */  jal        func_1512B630",
        "15899C 1512B4EC AFA00014 */   sw        $zero, 0x14($sp)",
        "1589A0 1512B4F0 50400003 */  beql       $v0, $zero, .L1512B500",
    )
    if any(caller.count(text) != 1 for text in required):
        raise ValueError("Threshold-transition caller ABI changed")
    return {
        "direct_jal_calls": ["0x15886c", "0x158998"],
        "aligned_pointer_literals": [],
        "callers": ["func_1512B1B8 at 0x1512B3BC", "func_1512B1B8 at 0x1512B4E8"],
        "abi": (
            "actor pointer, transition record, signed threshold and value pair, "
            "signed comparison peer, and alternate-table selector; returns zero or one"
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
        raise ValueError("Threshold-transition qualification report changed")
    report["retail_relocations"] = len(RETAIL_BINDINGS)
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
