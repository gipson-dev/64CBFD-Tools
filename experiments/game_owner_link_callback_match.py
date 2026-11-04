"""Qualify func_1519E1F4's owner-link callback as direct byte-exact C."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION = "func_1519E1F4"
FILENAME = "generated_1CA420"
SOURCE = "conker/src/game/generated_1CA420.c"
OBJECT = "conker/build/src/game/generated_1CA420.c.o"
ASM = "conker/asm/1CA420.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22ECC0.rodata.s"
BUILD = "conker/build/game-owner-link-callback-1519E1F4-match"
ENTRY, ROM, WORDS = 0x1519E1F4, 0x1CB6A4, 68
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x18
RAW_SHA256 = "8cbc37ae0e1bc2af2c29e86ddcee59bbdee74773b28c88514cf182104b616d45"
RETAIL_SHA256 = "3c5ce5d05c1c92beafacecfd31678146fa0cdd7884a11e3e7b558f92c3245cec"
BINDINGS = {
    0x040: [("R_MIPS_26", "func_1519CFA0")],
    0x06C: [("R_MIPS_26", "func_1519CFA0")],
    0x0A8: [("R_MIPS_26", "func_1519CFA0")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_ROWS = ()
PLACEHOLDER = """s32 func_1519E1F4() {
    return 0;
}"""
SELECTED = """/* Route matching owner-link events or retarget the bound link. */
void func_1519E1F4(u8 *record, s32 eventAddress, u8 command) {
    u8 *link;
    u8 *event;

    link = *(u8 **)(record + 0x98);
    event = (u8 *)eventAddress;
    if (command == 0) {
        if (*(s32 *)link == *(s32 *)event || link[4] == event[4]) {
            func_1519CFA0(record);
        }
    } else if (command == 6) {
        if (event[0] == link[0x4C]) {
            func_1519CFA0(record);
        }
    } else if (command == 7) {
        if (*(s32 *)link == *(s32 *)event || link[4] == event[4]) {
            func_1519CFA0(record);
        }
    } else if (command == 0x2D) {
        if (*(u8 **)event == *(u8 **)link) {
            *(u8 **)link = *(u8 **)(event + 4);
            link[4] = event[9];
        } else if (*(u8 **)(event + 4) == *(u8 **)link) {
            *(u8 **)link = *(u8 **)event;
            link[4] = event[8];
        }
    }
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    if live.count(PLACEHOLDER) == 1:
        if SELECTED in live:
            raise ValueError("Owner-link callback predecessor source changed")
        return live, live.replace(PLACEHOLDER, SELECTED, 1), False
    if live.count(SELECTED) == 1:
        if PLACEHOLDER in live:
            raise ValueError("Installed owner-link callback source changed")
        return live.replace(SELECTED, PLACEHOLDER, 1), live, True
    raise ValueError("Owner-link callback source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_8008A390\n", 1)[1].split(
        "enddlabel D_8008A390", 1)[0]
    entries = [line for line in block.splitlines() if ".word" in line]
    dispatcher = (root / "conker/src/game/generated_174BF0.c").read_text()
    if calls or pointers != [0x22EE60] or len(entries) != 20:
        raise ValueError("Owner-link callback retail registry changed")
    if entries[4].split(".word", 1)[1].strip() != FUNCTION:
        raise ValueError("Owner-link callback registry slot changed")
    if (dispatcher.count("void func_15147D1C(u8 *arg0, s32 arg1, u8 arg2)") != 1 or
            dispatcher.count("temp_v0(arg0, arg1, arg2);") != 1):
        raise ValueError("Owner-link callback semantic dispatcher changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x22ee60"],
        "registry": "D_8008A390[4] via func_15147D1C",
        "abi": "record pointer, event address, promoted unsigned command; void return",
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
            report["natural_positional_differences"] != 0):
        raise ValueError("Owner-link callback qualification report changed")
    report["retail_relocations"] = len(RETAIL_BINDINGS)
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
