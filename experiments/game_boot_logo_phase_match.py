"""Qualify func_151DE6D4's boot-logo phase controller as direct exact C."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.pad_generated_object import emit_padded_assembly


FUNCTION = "func_151DE6D4"
FILENAME = "generated_20AE20"
SOURCE = "conker/src/game/generated_20AE20.c"
OBJECT = "conker/build/src/game/generated_20AE20.c.o"
ASM = "conker/asm/20AE20.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/234830.rodata.s"
BUILD = "conker/build/game-boot-logo-phase-151DE6D4-match"
ENTRY, ROM, WORDS = 0x151DE6D4, 0x20BB84, 64
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x20
RAW_SHA256 = "ed9c26aabf1dc42806719bc72f348bf143ed08aaf5b99affeee7803a405886ef"
RETAIL_SHA256 = "a8bf3fa92004b4cf3b093f269e5285ff24de9cfd170e3e3e14eaaff5b9899ec2"
BINDINGS = {
    0x008: [("R_MIPS_26", "func_151E530C")],
    0x010: [("R_MIPS_HI16", "D_800CC2D0")],
    0x014: [("R_MIPS_LO16", "D_800CC2D0")],
    0x02C: [("R_MIPS_HI16", "D_80000300")],
    0x034: [("R_MIPS_LO16", "D_80000300")],
    0x038: [("R_MIPS_HI16", "D_800E0A90")],
    0x03C: [("R_MIPS_LO16", "D_800E0A90")],
    0x044: [("R_MIPS_HI16", "D_800E0B9A")],
    0x04C: [("R_MIPS_HI16", "D_800E0A90")],
    0x050: [("R_MIPS_LO16", "D_800E0A90")],
    0x06C: [("R_MIPS_LO16", "D_800E0B9A")],
    0x0B8: [("R_MIPS_HI16", "D_8008FE28")],
    0x0BC: [("R_MIPS_LO16", "D_8008FE28")],
    0x0C0: [("R_MIPS_HI16", "D_800E0B94")],
    0x0C4: [("R_MIPS_LO16", "D_800E0B94")],
    0x0C8: [("R_MIPS_HI16", "D_800D2E40")],
    0x0D0: [("R_MIPS_LO16", "D_800D2E40")],
    0x0DC: [("R_MIPS_26", "func_1501C730")],
    0x0E8: [("R_MIPS_HI16", "D_800E0B96")],
    0x0EC: [("R_MIPS_LO16", "D_800E0B96")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_ROWS = ()
RODATA_SYMBOL = "jtbl_800AB9BC"
DECLARATION = "extern s32 D_80000300;\n"
PLACEHOLDER = """s32 func_151DE6D4() {
    return 0;
}"""
SELECTED = """/* Advance the boot-logo phase and request the opening scene. */
void func_151DE6D4(void) {
    s32 timer;

    func_151E530C();
    D_800CC2D0[0].unk25C |= 0x200;
    D_800CC2D0[0].y_position = 1000.0f;
    if (D_80000300 == 0) {
        D_800E0A90 = 0;
    }
    timer = D_800E0A90;
    if ((timer >= 0x14B) && (D_800E0B9A & 0x8000)) {
        if (timer < 0x1E0) {
            timer = D_800E0A90 = 0x1E0;
        }
        if ((timer >= 0x259) && (timer < 0x2D0)) {
            timer = D_800E0A90 = 0x2D0;
        }
    }
    if (timer >= 0x349) {
        D_8008FE28 = 2;
        D_800E0B94 = 1;
        D_800D2E40 = 0;
        func_1501C730(6, 0x21, 0, 0, 1);
        D_800E0B96 = 0xFF;
    }
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    marker = "extern s32 D_800E0A90;\n"
    if live.count(PLACEHOLDER) == 1:
        if SELECTED in live or DECLARATION in live:
            raise ValueError("Boot-logo phase predecessor source changed")
        qualified = live.replace(marker, marker + DECLARATION, 1).replace(
            PLACEHOLDER, SELECTED, 1)
        return live, qualified, False
    if live.count(SELECTED) == 1:
        if live.count(DECLARATION) != 1 or PLACEHOLDER in live:
            raise ValueError("Installed boot-logo phase source changed")
        predecessor = live.replace(DECLARATION, "", 1).replace(
            SELECTED, PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Boot-logo phase source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_8008FDEC\n", 1)[1].split(
        "enddlabel D_8008FDEC", 1)[0]
    entries = [line for line in block.splitlines() if ".word" in line]
    dispatcher = (root / ASM).read_text().split(
        "glabel func_151E51EC\n", 1)[1].split(
        "endlabel func_151E51EC", 1)[0]
    if calls or pointers != [0x2348D8] or len(entries) != 12:
        raise ValueError("Boot-logo phase retail registry changed")
    if entries[11].split(".word", 1)[1].strip() != FUNCTION:
        raise ValueError("Boot-logo phase registry slot changed")
    required = (
        "%hi(D_8008FDEC)", "%lo(D_8008FDEC)($t9)", "jalr       $t9")
    if any(token not in dispatcher for token in required):
        raise ValueError("Boot-logo phase indirect dispatcher changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x2348d8"],
        "registry": "D_8008FDEC[11] via func_151E51EC",
        "abi": "no arguments; void return",
    }


def emit_owner(*args, **kwargs):
    kwargs["rodata_symbol"] = RODATA_SYMBOL
    return emit_padded_assembly(*args, **kwargs)


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
            report["guards"] != 0 or
            report["natural_positional_differences"] != 0):
        raise ValueError("Boot-logo phase qualification report changed")
    report["retail_relocations"] = len(RETAIL_BINDINGS)
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
