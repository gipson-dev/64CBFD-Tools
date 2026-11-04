"""Qualify func_15012370's active-view projection setup as guarded exact C."""

import hashlib
import json
from pathlib import Path
import struct
import sys

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools import pad_generated_object
sys.modules.setdefault("pad_generated_object", pad_generated_object)
from tools.pad_c_object import emit_padded_assembly as pad_root_object


FUNCTION = "func_15012370"
FILENAME = "game_3F820"
SOURCE = "conker/src/game_3F820.c"
OBJECT = "conker/build/src/game_3F820.c.o"
ASM = "conker/asm/nonmatchings/game_3F820/func_15012370.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/nonmatchings/game_3B920/func_1500E470.s"
BUILD = "conker/build/game-view-projection-setup-15012370-match"
ENTRY, ROM, WORDS = 0x15012370, 0x3F820, 64
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x58
RAW_SHA256 = "5730645ece6040272140a5f46ce5275c9061b7a7e34fc69347872252eff89072"
RETAIL_SHA256 = "d1f0da4ee79135b394b310b8eab130d6a545a7edd4919791c0bf7b9c777756f9"
BINDINGS = {
    0x008: [("R_MIPS_HI16", "D_80082FA0")],
    0x00C: [("R_MIPS_LO16", "D_80082FA0")],
    0x038: [("R_MIPS_HI16", "D_80096560")],
    0x040: [("R_MIPS_HI16", "D_800DCC10")],
    0x044: [("R_MIPS_LO16", "D_80096560")],
    0x054: [("R_MIPS_HI16", "D_800BE628")],
    0x05C: [("R_MIPS_LO16", "D_800BE628")],
    0x060: [("R_MIPS_LO16", "D_800DCC10")],
    0x0B4: [("R_MIPS_26", "func_151EF954")],
}
RETAIL_BINDINGS = {
    0x008: [("R_MIPS_HI16", "D_80082FA0")],
    0x00C: [("R_MIPS_LO16", "D_80082FA0")],
    0x038: [("R_MIPS_HI16", "D_80096560")],
    0x044: [("R_MIPS_LO16", "D_80096560")],
    0x054: [("R_MIPS_HI16", "D_800BE628")],
    0x058: [("R_MIPS_HI16", "D_800DCC10")],
    0x060: [("R_MIPS_LO16", "D_800DCC10")],
    0x064: [("R_MIPS_LO16", "D_800BE628")],
    0x0B4: [("R_MIPS_26", "func_151EF954")],
}
PATCH_ROWS = (
    dict(offset="0x040", expected="0x3C140000", replacement="0x24140180",
         expected_relocations="R_MIPS_HI16:D_800DCC10", replacement_relocations="-",
         note="Keep the 0x180 view stride in retail's s4 lifetime"),
    dict(offset="0x054", expected="0x3C120000", replacement="0x3C130000",
         expected_relocations="R_MIPS_HI16:D_800BE628",
         replacement_relocations="R_MIPS_HI16:D_800BE628",
         note="Keep the mutable view-base address in retail's s3 lifetime"),
    dict(offset="0x058", expected="0x4481A000", replacement="0x3C120000",
         expected_relocations="-", replacement_relocations="R_MIPS_HI16:D_800DCC10",
         note="Materialize the matrix-table address through retail's s2 lifetime"),
    dict(offset="0x05C", expected="0x26520000", replacement="0x4481A000",
         expected_relocations="R_MIPS_LO16:D_800BE628", replacement_relocations="-",
         note="Restore the independent half-scale setup schedule"),
    dict(offset="0x060", expected="0x26940000", replacement="0x26520000",
         expected_relocations="R_MIPS_LO16:D_800DCC10",
         replacement_relocations="R_MIPS_LO16:D_800DCC10",
         note="Complete the matrix-table address through s2"),
    dict(offset="0x064", expected="0x24130180", replacement="0x26730000",
         expected_relocations="-", replacement_relocations="R_MIPS_LO16:D_800BE628",
         note="Complete the mutable view-base address through s3"),
    dict(offset="0x068", expected="0x02130019", replacement="0x02140019",
         note="Multiply the wrapped view index by retail's s4 stride"),
    dict(offset="0x06C", expected="0x8E4F0000", replacement="0x8E780000",
         note="Reload the mutable view base through retail's s3 lifetime"),
    dict(offset="0x070", expected="0x0010C980", replacement="0x00107980",
         note="Scale the matrix index through retail's t7 lifetime"),
    dict(offset="0x074", expected="0x02992021", replacement="0x024F2021",
         note="Construct the matrix pointer from retail's s2 and t7 lifetimes"),
    dict(offset="0x078", expected="0x0000C012", replacement="0x0000C812",
         note="Read the view-record product through retail's t9 lifetime"),
    dict(offset="0x07C", expected="0x01F81021", replacement="0x03191021",
         note="Construct the view-record pointer through retail's t8 and t9 lifetimes"),
    dict(offset="0x084", expected="0xC4460008", replacement="0xC4480008",
         note="Load the vertical extent through retail's f8 lifetime"),
    dict(offset="0x098", expected="0x46143082", replacement="0x46144082",
         note="Scale the vertical extent through retail's f8 lifetime"),
    dict(offset="0x09C", expected="0x46000207", replacement="0x46000187",
         note="Negate the horizontal half extent through retail's f6 lifetime"),
    dict(offset="0x0A4", expected="0x44054000", replacement="0x44053000",
         note="Pass the negative horizontal extent from retail's f6 lifetime"),
)

TYPE = """typedef struct {
    f32 unused0;
    f32 horizontalExtent;
    f32 verticalExtent;
    u8 opaqueC[0x174];
} ViewProjectionSetup15012370;

"""
PLACEHOLDER = """/* Non-matching C placeholders for asm/nonmatchings/game_3F820/func_15012370.s. */
s32 func_15012370() {
    return 0;
}"""
DRAFT = """// void func_15012370(void) {
//     f32 temp_f0;
//     f32 temp_f2;
//     u8 i;
//
//     f32 foo = D_80096560; // 20000.0f
//     f32 **tmp = D_800BE628;
//
//     for (i = 0; i <= D_80082FA0; i++) {
//         temp_f0 = tmp[i][1] * 0.5f;
//         temp_f2 = tmp[i][2] * 0.5f;
//         func_151EF954(D_800DCC10[i], -temp_f0, temp_f0, -temp_f2, temp_f2, 1.0f, foo, 1.0f);
//     }
// }"""
PREDECESSOR_BLOCK = PLACEHOLDER + "\n" + DRAFT
SELECTED = """/* Rebuild each active view's projection matrix from its half extents. */
void func_15012370(void) {
    f32 halfWidth;
    f32 halfHeight;
    u8 index;
    f32 farPlane;

    index = 0;
    if (D_80082FA0 >= 0) {
        farPlane = D_80096560;
        do {
            halfWidth = ((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index].horizontalExtent * 0.5f;
            halfHeight = ((ViewProjectionSetup15012370 *)(u32)D_800BE628)[index].verticalExtent * 0.5f;
            func_151EF954(((f32 (*)[4][4])D_800DCC10)[index],
                -halfWidth, halfWidth, -halfHeight, halfHeight,
                1.0f, farPlane, 1.0f);
            index++;
        } while (index <= D_80082FA0);
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
    marker = "/* Generated placeholder declarations. */\n"
    old_declaration = "s32 func_15012370();"
    new_declaration = "void func_15012370(void);"
    if live.count(PREDECESSOR_BLOCK) == 1:
        if SELECTED in live or TYPE in live or new_declaration in live:
            raise ValueError("View-projection setup predecessor source changed")
        qualified = live.replace(marker, TYPE + marker, 1).replace(
            old_declaration, new_declaration, 1).replace(
            PREDECESSOR_BLOCK, SELECTED, 1)
        return live, qualified, False
    if live.count(SELECTED) == 1:
        if (live.count(TYPE) != 1 or live.count(new_declaration) != 1 or
                PREDECESSOR_BLOCK in live or old_declaration in live):
            raise ValueError("Installed view-projection setup source changed")
        predecessor = live.replace(TYPE, "", 1).replace(
            new_declaration, old_declaration, 1).replace(
            SELECTED, PREDECESSOR_BLOCK, 1)
        return predecessor, live, True
    raise ValueError("View-projection setup source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    caller = (root / REGISTRY).read_text()
    required = ("glabel func_1500E470", "jal        func_15012370",
                "endlabel func_1500E470")
    if calls != [0x3B9A4] or pointers or any(item not in caller for item in required):
        raise ValueError("View-projection setup caller evidence changed")
    return {
        "direct_jal_calls": ["0x3b9a4"],
        "aligned_pointer_literals": [],
        "caller": "func_1500E470",
        "abi": "no arguments; void return",
    }


def emit_owner(obj, asm, word_patches_path=None, filename=None,
               rodata_symbol=None):
    layout = Path(asm).parents[3] / "retail_layout.us.txt"
    return pad_root_object(
        obj, layout, filename, rodata_symbol=rodata_symbol,
        word_patches_path=word_patches_path)


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
    if (report["raw_sha256"] != RAW_SHA256 or
            report["retail_sha256"] != RETAIL_SHA256 or
            report["guards"] != len(PATCH_ROWS) or
            report["natural_positional_differences"] != len(PATCH_ROWS)):
        raise ValueError("View-projection setup qualification report changed")
    report["retail_relocations"] = len(RETAIL_BINDINGS)
    destination = Path(output or Path(root) / BUILD)
    (destination / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
