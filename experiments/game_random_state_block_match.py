"""Qualify func_1509C120's random state-block replacement as guarded exact C."""

import hashlib
import json
from pathlib import Path
import struct
import sys

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools import pad_generated_object

sys.modules.setdefault("pad_generated_object", pad_generated_object)
from tools.pad_c_object import emit_padded_assembly as pad_root_object


FUNCTION = "func_1509C120"
FILENAME = "game_C8950"
SOURCE = "conker/src/game_C8950.c"
OBJECT = "conker/build/src/game_C8950.c.o"
ASM = "conker/asm/nonmatchings/game_C8950/func_1509C120.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-random-state-block-1509C120-match"
ENTRY, ROM, WORDS = 0x1509C120, 0xC95D0, 66
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x50
RAW_SHA256 = "3503c3a64e8f810e7b3ffd32de5078f6b8ae90df5093187c3d79c96a577b262d"
RETAIL_SHA256 = "75cf82695ce3cb731fa3147b953390fe5fdba0b60eeb197c531559a91b87dd37"
BINDINGS = {
    0x018: [("R_MIPS_26", "func_150ADA20")],
    0x020: [("R_MIPS_HI16", "D_800D2E4C")],
    0x024: [("R_MIPS_LO16", "D_800D2E4C")],
    0x034: [("R_MIPS_26", "func_150ADA20")],
    0x06C: [("R_MIPS_26", "allocate_memory")],
    0x09C: [("R_MIPS_26", "func_10004074")],
    0x0C4: [("R_MIPS_HI16", "D_800D2E4C")],
    0x0CC: [("R_MIPS_LO16", "D_800D2E4C")],
    0x0D0: [("R_MIPS_HI16", "D_800D2E4C")],
    0x0D4: [("R_MIPS_LO16", "D_800D2E4C")],
    0x0DC: [("R_MIPS_26", "bcopy")],
    0x0E4: [("R_MIPS_26", "func_10004074")],
}
RETAIL_BINDINGS = dict(BINDINGS)

PATCH_ROWS = (
    dict(
        offset="0x030",
        expected="0xAFAE0048",
        replacement="0xAFAE0034",
        note="Preserve the old state block in retail's scalar stack slot",
    ),
    dict(
        offset="0x0B8",
        expected="0x8FAD0048",
        replacement="0x8FAE0034",
        note="Reload the old state block through retail's t6 lifetime",
    ),
    dict(
        offset="0x0C0",
        expected="0x8D820000",
        replacement="0x8D8D0000",
        note="Load the selected state block through retail's t5 lifetime",
    ),
    dict(
        offset="0x0C8",
        expected="0x11A00008",
        replacement="0x11C00008",
        note="Test the preserved old state block through retail's t6 lifetime",
    ),
    dict(
        offset="0x0CC",
        expected="0xAC220000",
        replacement="0xAC2D0000",
        expected_relocations="R_MIPS_LO16:D_800D2E4C",
        replacement_relocations="R_MIPS_LO16:D_800D2E4C",
        note="Install the selected state block through retail's t5 lifetime",
    ),
    dict(
        offset="0x0D8",
        expected="0x01A02025",
        replacement="0x01C02025",
        note="Pass the preserved old block to bcopy through retail's t6 lifetime",
    ),
    dict(
        offset="0x0E8",
        expected="0x8FA40048",
        replacement="0x8FA40034",
        note="Reload the old block from retail's scalar slot for release",
    ),
)

PREDECESSOR_BLOCK = """// need a bigger brain
/* Non-matching C placeholders for asm/nonmatchings/game_C8950/func_1509C120.s. */
void func_1509C120(void) {
}"""

SELECTED = """/* Replace the active state block through a randomized allocation slot. */
void func_1509C120(void) {
    s32 index;
    struct102 *old;
    s32 blocks[4];
    s32 i;
    s32 kept;

    index = func_150ADA20() & 3;
    old = D_800D2E4C;
    if ((old == NULL) || ((func_150ADA20() & 4) != 0)) {
        for (i = 0; i <= index; i++) {
            blocks[i] = allocate_memory(0x1B, 0xFF, 2, 0);
        }

        for (i = 0; i <= index; i++) {
            if (i != index) {
                func_10004074((void *)blocks[i]);
            }
        }

        kept = blocks[index];
        D_800D2E4C = (struct102 *)kept;
        if (old != NULL) {
            bcopy(old, D_800D2E4C, 0x1B);
            func_10004074(old);
        }
    }
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def complete_row(row):
    return {
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": row["offset"],
        "expected": row["expected"],
        "replacement": row["replacement"],
        "expected_relocations": row.get("expected_relocations", "-"),
        "replacement_relocations": row.get("replacement_relocations", "-"),
        "note": row["note"],
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }


def source_states(live):
    if live.count(PREDECESSOR_BLOCK) == 1:
        if SELECTED in live:
            raise ValueError("Random state-block predecessor source changed")
        return live, live.replace(PREDECESSOR_BLOCK, SELECTED, 1), False
    if live.count(SELECTED) == 1:
        if PREDECESSOR_BLOCK in live:
            raise ValueError("Installed random state-block source changed")
        return live.replace(SELECTED, PREDECESSOR_BLOCK, 1), live, True
    raise ValueError("Random state-block source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    jump = 0x08000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    jumps = [index * 4 for index, word in enumerate(words) if word == jump]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    expected_calls = [0x34DEC, 0x44C48, 0xC897C]
    if calls != expected_calls or jumps or pointers:
        raise ValueError("Random state-block caller evidence changed")
    return {
        "direct_jal_calls": [hex(value) for value in calls],
        "direct_jumps": [],
        "aligned_pointer_literals": [],
        "callers": ["func_15007830", "func_15017790", "func_1509B4A0"],
        "abi": "no arguments; void return",
    }


def emit_owner(obj, asm, word_patches_path=None, filename=None,
               rodata_symbol=None):
    layout = Path(asm).parents[3] / "retail_layout.us.txt"
    return pad_root_object(
        obj,
        layout,
        filename,
        rodata_symbol=rodata_symbol,
        word_patches_path=word_patches_path,
    )


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
        "emit_padded_assembly": emit_owner,
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
    if (
        report["raw_sha256"] != RAW_SHA256
        or report["retail_sha256"] != RETAIL_SHA256
        or report["guards"] != len(PATCH_ROWS)
        or report["natural_positional_differences"] != len(PATCH_ROWS)
    ):
        raise ValueError("Random state-block qualification report changed")
    report["retail_relocations"] = len(RETAIL_BINDINGS)
    destination = Path(output or Path(root) / BUILD)
    (destination / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
