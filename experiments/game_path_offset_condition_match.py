"""Qualify func_15075938's path-offset condition as guarded exact C."""

import hashlib
import json
from pathlib import Path
import struct
import sys

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools import pad_generated_object

sys.modules.setdefault("pad_generated_object", pad_generated_object)
from tools.pad_c_object import emit_padded_assembly as pad_root_object


FUNCTION = "func_15075938"
FILENAME = "game_A28B0"
SOURCE = "conker/src/game_A28B0.c"
OBJECT = "conker/build/src/game_A28B0.c.o"
ASM = "conker/asm/nonmatchings/game_A28B0/func_15075938.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22B1F0.rodata.s"
BUILD = "conker/build/game-path-offset-condition-15075938-match"
ENTRY, ROM, WORDS = 0x15075938, 0xA2DE8, 70
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x18
RAW_SHA256 = "a2190411ec96578623e9f15a50a3a7c1240dca229587b88982765afaa9ef1418"
RETAIL_SHA256 = "1c5074ed2ea84fa4f3c3fbe507fe177e68070d3d940680714eb3cdd66e4cc7fb"
BINDINGS = {
    0x008: [("R_MIPS_HI16", "D_800D154C")],
    0x00C: [("R_MIPS_LO16", "D_800D154C")],
    0x014: [("R_MIPS_HI16", "D_800D2108")],
    0x020: [("R_MIPS_HI16", "D_800D2108")],
    0x024: [("R_MIPS_HI16", "D_800D1891")],
    0x038: [("R_MIPS_LO16", "D_800D2108")],
    0x054: [("R_MIPS_LO16", "D_800D2108")],
    0x078: [("R_MIPS_LO16", "D_800D1891")],
    0x090: [("R_MIPS_HI16", "D_800D1892")],
    0x094: [("R_MIPS_LO16", "D_800D1892")],
    0x0FC: [("R_MIPS_HI16", "D_800D1890")],
    0x100: [("R_MIPS_26", "func_15075400")],
    0x104: [("R_MIPS_LO16", "D_800D1890")],
}
RETAIL_BINDINGS = dict(BINDINGS)
RETAIL_BINDINGS.pop(0x038)
RETAIL_BINDINGS[0x034] = [("R_MIPS_LO16", "D_800D2108")]

PATCH_ROWS = (
    dict(
        offset="0x014",
        expected="0x3C190000",
        replacement="0x3C180000",
        expected_relocations="R_MIPS_HI16:D_800D2108",
        replacement_relocations="R_MIPS_HI16:D_800D2108",
        note="Materialize the negative-wrap path-count table through retail's t8 lifetime",
    ),
    dict(
        offset="0x034",
        expected="0x9078013F",
        replacement="0x8F180000",
        expected_relocations="-",
        replacement_relocations="R_MIPS_LO16:D_800D2108",
        note="Load the negative-wrap path-count table before the actor path index",
    ),
    dict(
        offset="0x038",
        expected="0x8F390000",
        replacement="0x9079013F",
        expected_relocations="R_MIPS_LO16:D_800D2108",
        replacement_relocations="-",
        note="Load the actor path index through retail's independent t9 lifetime",
    ),
)

PLACEHOLDER = """/* Non-matching C placeholders for asm/nonmatchings/game_A28B0/func_15075938.s. */
s32 func_15075938() {
    return 0;
}"""
DRAFT = """// NON-MATCHING: 2nd half ok, 1st is a mystery
// void func_15075938(void) {
//     u8 tmp;
//     u8 changed;
//     s32 temp_a0;
//     s32 phi_v1;
//     u8 temp_v0;
//
//     changed = 0;
//
//     temp_a0 = D_800D154C->unk21E - D_800D154C->unk221;
//     if (temp_a0 < 0) {
//         temp_v0 = D_800D154C->unk13F + D_800D2108;
//         temp_a0 = (temp_a0 + temp_v0) - 1;
//     } else {
//         temp_v0 = D_800D154C->unk13F + D_800D2108;
//         if ((temp_v0 - 1) <= temp_a0) {
//             temp_a0 = (temp_a0 - temp_v0) + 1;
//         }
//     }
//
//     if (D_800D1891 == 0xFF) {
//         phi_v1 = temp_v0 - 2;
//     } else {
//         phi_v1 = D_800D1891;
//     }
//
//     if (D_800D1892 == 0) {
//         if (phi_v1 == temp_a0) {
//             changed = 1;
//         }
//     } else if (D_800D1892 == 1) {
//         if (phi_v1 != temp_a0) {
//             changed = 1;
//         }
//     } else if (D_800D1892 == 2) {
//         if (phi_v1 < temp_a0) {
//             changed = 1;
//         }
//     } else {
//         if (phi_v1 > temp_a0) {
//             changed = 1;
//         }
//     }
//
//     if (changed) {
//         func_15075400(D_800D1890);
//     }
// }"""
PREDECESSOR_BLOCK = PLACEHOLDER + "\n" + DRAFT

SELECTED = """/* Test the wrapped path offset against the script condition. */
void func_15075938(void) {
    s32 changed;
    s32 current;
    s32 target;
    s32 pathCount;

    changed = 0;
    current = D_800D154C->unk21E - D_800D154C->unk221;
    if (current < 0) {
        pathCount = D_800D2108[D_800D154C->unk13F];
        current = current + pathCount - 1;
    } else {
        pathCount = D_800D2108[D_800D154C->unk13F];
        if (current >= pathCount - 1) {
            current = current - pathCount + 1;
        }
    }

    if (D_800D1891 == 0xFF) {
        target = pathCount - 2;
    } else {
        target = D_800D1891;
    }

    if (D_800D1892 == 0) {
        if (target == current) {
            changed = 1;
        }
    } else if (D_800D1892 == 1) {
        if (target != current) {
            changed = 1;
        }
    } else if (D_800D1892 == 2) {
        if (target < current) {
            changed = 1;
        }
    } else if (target > current) {
        changed = 1;
    }

    if (changed != 0) {
        func_15075400(D_800D1890);
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
    old_declaration = "s32 func_15075938();"
    new_declaration = "void func_15075938(void);"
    if live.count(PREDECESSOR_BLOCK) == 1:
        if SELECTED in live or new_declaration in live:
            raise ValueError("Path-offset condition predecessor source changed")
        qualified = live.replace(
            old_declaration, new_declaration, 1
        ).replace(PREDECESSOR_BLOCK, SELECTED, 1)
        return live, qualified, False
    if live.count(SELECTED) == 1:
        if (
            live.count(new_declaration) != 1
            or PREDECESSOR_BLOCK in live
            or old_declaration in live
        ):
            raise ValueError("Installed path-offset condition source changed")
        predecessor = live.replace(
            new_declaration, old_declaration, 1
        ).replace(SELECTED, PREDECESSOR_BLOCK, 1)
        return predecessor, live, True
    raise ValueError("Path-offset condition source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[: len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    jump = 0x08000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    jumps = [index * 4 for index, word in enumerate(words) if word == jump]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    required = (
        "dlabel D_80086730",
        "/* 22B430 80086970 15075938 */ .word func_15075938",
    )
    if (
        calls
        or jumps
        or pointers != [0x22B430]
        or any(item not in registry for item in required)
    ):
        raise ValueError("Path-offset condition registry evidence changed")
    return {
        "direct_jal_calls": [],
        "direct_jumps": [],
        "aligned_pointer_literals": ["0x22b430"],
        "dispatch_table": "D_80086730",
        "dispatch_row": 144,
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
        raise ValueError("Path-offset condition qualification report changed")
    report["retail_relocations"] = len(RETAIL_BINDINGS)
    destination = Path(output or Path(root) / BUILD)
    (destination / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
