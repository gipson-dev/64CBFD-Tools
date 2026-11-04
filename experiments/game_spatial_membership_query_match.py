"""Qualify func_1503F800's spatial-membership query as guarded exact C."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION = "func_1503F800"
FILENAME = "generated_6CCB0"
SOURCE = "conker/src/game/generated_6CCB0.c"
OBJECT = "conker/build/src/game/generated_6CCB0.c.o"
ASM = "conker/asm/6CCB0.s"
SECOND_CALLER_ASM = "conker/asm/13D350.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = ASM
BUILD = "conker/build/game-spatial-membership-query-1503F800-match"
ENTRY, ROM, WORDS = 0x1503F800, 0x6CCB0, 65
SIZE = WORDS * 4
NATURAL_FRAME, RETAIL_FRAME = 0x20, 0x18
RAW_SHA256 = "4c8096eb757c0b230a31da2df3f133208aec0c4f5acf819c3afb03056a0fc6ce"
RETAIL_SHA256 = "3f57607ae52c1daef89705b8f1734d7b9f2fb3ed04375506c15e7438e75dde77"
BINDINGS = {
    0x02C: [("R_MIPS_26", "func_1510F800")],
    0x034: [("R_MIPS_HI16", "D_800DBE48")],
    0x038: [("R_MIPS_LO16", "D_800DBE48")],
}
RETAIL_BINDINGS = {
    0x030: [("R_MIPS_26", "func_1510F800")],
    0x038: [("R_MIPS_HI16", "D_800DBE48")],
    0x03C: [("R_MIPS_LO16", "D_800DBE48")],
}

PATCH_WORDS = (
    (0x000, 0x27BDFFE0, 0x27BDFFE8, "-", "-"),
    (0x004, 0xAFB00018, 0xAFA5001C, "-", "-"),
    (0x008, 0x00A08025, 0xAFA60020, "-", "-"),
    (0x00C, 0xAFBF001C, 0x00057400, "-", "-"),
    (0x010, 0xAFA40020, 0x0006C400, "-", "-"),
    (0x014, 0x0006C400, 0x00183403, "-", "-"),
    (0x018, 0x00107400, 0x000E2C03, "-", "-"),
    (0x01C, 0x0018CC03, 0xAFBF0014, "-", "-"),
    (0x020, 0x000E8403, 0xAFA40018, "-", "-"),
    (0x024, 0xAFB90028, 0x00002025, "-", "-"),
    (0x028, 0x00002025, 0xA7A5001E, "-", "-"),
    (0x02C, 0x0C000000, 0xA7A60022,
     "R_MIPS_26:func_1510F800", "-"),
    (0x030, 0xAFA7002C, 0x0C000000,
     "-", "R_MIPS_26:func_1510F800"),
    (0x034, 0x3C030000, 0xAFA70024,
     "R_MIPS_HI16:D_800DBE48", "-"),
    (0x038, 0x8C630000, 0x3C030000,
     "R_MIPS_LO16:D_800DBE48", "R_MIPS_HI16:D_800DBE48"),
    (0x03C, 0x8FA60028, 0x8C630000,
     "-", "R_MIPS_LO16:D_800DBE48"),
    (0x040, 0x8FA7002C, 0x87A5001E, "-", "-"),
    (0x044, 0x5060002A, 0x87A60022, "-", "-"),
    (0x048, 0x24020001, 0x10600029, "-", "-"),
    (0x04C, 0x84650008, 0x8FA70024, "-", "-"),
    (0x050, 0x94640006, 0x84640008, "-", "-"),
    (0x054, 0x00A44021, 0x94620006, "-", "-"),
    (0x058, 0x0110082A, 0x00824021, "-", "-"),
    (0x05C, 0x1420001B, 0x0105082A, "-", "-"),
    (0x060, 0x00801025, 0x1420001B, "-", "-"),
    (0x064, 0x00A44823, 0x00824823, "-", "-"),
    (0x068, 0x0209082A, 0x00A9082A, "-", "-"),
    (0x06C, 0x54200018, 0x54200019, "-", "-"),
    (0x080, 0x14200012, 0x14200013, "-", "-"),
    (0x08C, 0x54200010, 0x54200011, "-", "-"),
    (0x0A4, 0x51E00012, 0x55E00004, "-", "-"),
    (0x0A8, 0x24020001, 0x8464000C, "-", "-"),
    (0x0AC, 0x8464000C, 0x10000011, "-", "-"),
    (0x0B0, 0x10800004, 0x24020001, "-", "-"),
    (0x0B4, 0x00041400, 0x8464000C, "-", "-"),
    (0x0B8, 0x0002C403, 0x10800003, "-", "-"),
    (0x0BC, 0x10000004, 0x00000000, "-", "-"),
    (0x0C0, 0x03001025, 0x10000004, "-", "-"),
    (0x0C4, 0x1000000A, 0x00801025, "-", "-"),
    (0x0C8, 0x00001025, 0x1000000A, "-", "-"),
    (0x0CC, 0x84620004, 0x00001025, "-", "-"),
    (0x0D0, 0x50400004, 0x84620004, "-", "-"),
    (0x0D4, 0x00001825, 0x50400004, "-", "-"),
    (0x0D8, 0x10000002, 0x00001825, "-", "-"),
    (0x0DC, 0x00621821, 0x10000002, "-", "-"),
    (0x0E0, 0x00001825, 0x00621821, "-", "-"),
    (0x0E4, 0x5460FFDA, 0x00001825, "-", "-"),
    (0x0E8, 0x84650008, 0x5460FFDA, "-", "-"),
    (0x0EC, 0x24020001, 0x84640008, "-", "-"),
    (0x0F0, 0x8FBF001C, 0x24020001, "-", "-"),
    (0x0F4, 0x8FB00018, 0x8FBF0014, "-", "-"),
    (0x0F8, 0x27BD0020, 0x27BD0018, "-", "-"),
)

PATCH_ROWS = tuple(dict(
    offset="0x%03X" % offset,
    expected="0x%08X" % expected,
    replacement="0x%08X" % replacement,
    expected_relocations=expected_relocations,
    replacement_relocations=replacement_relocations,
    note="Normalize spatial-membership query compiler frame, allocation, and schedule",
) for offset, expected, replacement, expected_relocations,
    replacement_relocations in PATCH_WORDS)

PREAMBLE = """typedef struct {
    s16 unused0;
    s16 categoryMask;
    s16 siblingOffset;
    u16 radius;
    s16 centerX;
    s16 centerZ;
    s16 childOffset;
} SpatialMembershipNode1503F800;

extern u8 *D_800DBE48;
void func_1510F800(s32 context);

"""

PLACEHOLDER = """s32 func_1503F800() {
    return 0;
}"""

SELECTED = """/* Return zero only when the coordinate reaches a selected leaf. */
s32 func_1503F800(void *unusedQuery, s32 x, s32 z, s32 category, s32 unusedMode) {
    s16 centerX;
    s16 centerZ;
    s16 childOffset;
    s16 queryX;
    s16 queryZ;
    s16 offset;
    u16 radius;
    SpatialMembershipNode1503F800 *node;

    queryZ = z;
    queryX = x;
    x = queryX;
    z = queryZ;
    func_1510F800(0);
    node = (SpatialMembershipNode1503F800 *)D_800DBE48;
    if (node != NULL) {
loop:
        centerX = node->centerX;
        radius = node->radius;
        if (((centerX + radius) >= x) && (x >= (centerX - radius))) {
            centerZ = node->centerZ;
            if (((centerZ + radius) >= z) && (z >= (centerZ - radius))) {
                if (!(node->categoryMask & (1 << category))) {
                    goto miss;
                }
                childOffset = node->childOffset;
                if (childOffset != 0) {
                    offset = childOffset;
                    goto advance;
                }
                return 0;
            }
        }
        offset = node->siblingOffset;
advance:
        if (offset != 0) {
            node = (SpatialMembershipNode1503F800 *)((u8 *)node + offset);
        } else {
            node = NULL;
        }
        if (node == NULL) {
            goto miss;
        }
        goto loop;
    }
miss:
    return 1;
}"""


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
    marker = "/* Recovered and remaining routines from the text-only asm slice asm/6CCB0.s. */\n\n"
    if live.count(PLACEHOLDER) == 1:
        if SELECTED in live or PREAMBLE in live:
            raise ValueError("Spatial-membership query predecessor source changed")
        qualified = live.replace(marker, marker + PREAMBLE, 1).replace(
            PLACEHOLDER, SELECTED, 1)
        return live, qualified, False
    if live.count(SELECTED) == 1:
        if live.count(PREAMBLE) != 1 or PLACEHOLDER in live:
            raise ValueError("Installed spatial-membership query source changed")
        predecessor = live.replace(PREAMBLE, "", 1).replace(
            SELECTED, PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Spatial-membership query source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    wrapper_source = (root / REGISTRY).read_text()
    gameplay_source = (root / SECOND_CALLER_ASM).read_text()
    wrapper_required = ("glabel func_1503F904", "jal        func_1503F800",
                        "endlabel func_1503F904")
    gameplay_required = ("glabel func_15112A80", "jal        func_1503F800",
                         "endlabel func_15112A80")
    if (calls != [0x6CDFC, 0x1400E8] or pointers or
            any(item not in wrapper_source for item in wrapper_required) or
            any(item not in gameplay_source for item in gameplay_required)):
        raise ValueError("Spatial-membership query caller evidence changed")
    return {
        "direct_jal_calls": ["0x6cdfc", "0x1400e8"],
        "aligned_pointer_literals": [],
        "callers": ["func_1503F904", "func_15112A80"],
        "abi": ("query pointer, signed X/Z words, category bit, and an unused "
                "fifth caller word; returns zero only for an accepted leaf"),
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
            report["guards"] != len(PATCH_ROWS) or
            report["natural_positional_differences"] != len(PATCH_ROWS)):
        raise ValueError("Spatial-membership query qualification report changed")
    report["retail_relocations"] = len(RETAIL_BINDINGS)
    destination = Path(output or Path(root) / BUILD)
    (destination / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
