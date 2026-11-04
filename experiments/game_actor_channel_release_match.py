"""Qualify func_15172D80's actor channel release dispatch as guarded C."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION = "func_15172D80"
FILENAME = "generated_1A0100"
SOURCE = "conker/src/game/generated_1A0100.c"
OBJECT = "conker/build/src/game/generated_1A0100.c.o"
ASM = "conker/asm/1A0100.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-actor-channel-release-15172D80-match"
ENTRY, ROM, WORDS = 0x15172D80, 0x1A0230, 63
SIZE = WORDS * 4
NATURAL_FRAME, RETAIL_FRAME = 0x40, 0x38
RAW_SHA256 = "282b43219ba5e54b219debc904e6ec17e711d577375df9254f06b84ca2c75f2b"
RETAIL_SHA256 = "599bac44ac0733f5129d617f0349d5bc470026efee412dcb9ae66dcb2d60df7e"
BINDINGS = {
    0x014: [("R_MIPS_HI16", "D_800DD2B0")],
    0x018: [("R_MIPS_LO16", "D_800DD2B0")],
    0x048: [("R_MIPS_HI16", "D_800CC2D0")],
    0x04C: [("R_MIPS_LO16", "D_800CC2D0")],
    0x080: [("R_MIPS_26", "func_1517EE40")],
    0x090: [("R_MIPS_26", "func_1517F40C")],
    0x0A0: [("R_MIPS_HI16", "D_800BE9F0")],
    0x0A4: [("R_MIPS_LO16", "D_800BE9F0")],
    0x0BC: [("R_MIPS_26", "func_1501C730")],
    0x0CC: [("R_MIPS_26", "func_15172CA8")],
    0x0D4: [("R_MIPS_HI16", "D_800DD2C0")],
    0x0DC: [("R_MIPS_LO16", "D_800DD2C0")],
    0x0E0: [("R_MIPS_26", "func_15172D28")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_ROWS = (
    dict(offset="0x000", expected="0x27BDFFC0", replacement="0x27BDFFC8",
         note="Normalize actor channel release frame size"),
    dict(offset="0x0F0", expected="0x27BD0040", replacement="0x27BD0038",
         note="Normalize actor channel release frame restore"),
)
PLACEHOLDER = """s32 func_15172D80() {
    return 0;
}"""
DECLARATIONS = """extern struct127 D_800CC2D0[];
void func_1501C730(s32, s32, s32, s32, s32);
s32 func_1517F40C(s32);
"""
OLD_PAYLOAD_DECLARATION = "extern s8 D_800DD2C0[];"
NEW_PAYLOAD_DECLARATION = "extern u8 D_800DD2C0[];"
SELECTED = """/* Release a channel effect and apply its pending payload to its actor. */
void func_15172D80(s32 channel) {
    s8 *slot;
    struct127 *actor;

    slot = &D_800DD2B0[channel];
    if (*slot != -1) {
        actor = &D_800CC2D0[channel];
        if (actor->health == 0) {
            *slot = -1;
            func_1517EE40(0, 0, 0, 0x32, 0, channel);
        }
        if (func_1517F40C(channel) != 0) {
            if (D_800BE9F0 != *slot) {
                func_1501C730(1, *slot, 0, 0, 0);
                return;
            }
            func_15172CA8(channel);
            func_15172D28((u8 *)actor, D_800DD2C0[channel]);
        }
    }
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    anchor = "void func_1517EE40(s32 arg0, s32 arg1, s32 arg2, s32 arg3, s8 arg4,\n                    s32 arg5);\n"
    qualified_anchor = anchor + DECLARATIONS
    if live.count(PLACEHOLDER) == 1:
        if live.count(DECLARATIONS) or SELECTED in live:
            raise ValueError("Actor channel release predecessor source changed")
        if (live.count(anchor) != 1 or
                live.count(OLD_PAYLOAD_DECLARATION) != 1 or
                NEW_PAYLOAD_DECLARATION in live):
            raise ValueError("Actor channel release declaration anchor changed")
        qualified = live.replace(
            OLD_PAYLOAD_DECLARATION, NEW_PAYLOAD_DECLARATION, 1
        ).replace(anchor, qualified_anchor, 1).replace(PLACEHOLDER, SELECTED, 1)
        return live, qualified, False
    if live.count(SELECTED) == 1:
        if (live.count(DECLARATIONS) != 1 or PLACEHOLDER in live or
                live.count(NEW_PAYLOAD_DECLARATION) != 1 or
                OLD_PAYLOAD_DECLARATION in live):
            raise ValueError("Installed actor channel release source changed")
        predecessor = live.replace(
            NEW_PAYLOAD_DECLARATION, OLD_PAYLOAD_DECLARATION, 1
        ).replace(qualified_anchor, anchor, 1).replace(SELECTED, PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Actor channel release source state changed")


def routing_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    caller = struct.unpack_from(">8I", image, 0x464D8)
    expected = (
        0x3C01800D, 0x10000002, 0xA42B3674, 0xA42C3674,
        jal, 0x02002025, 0x3C018004, 0xAC20C8E0,
    )
    source = (root / "conker/src/game_45B80.c").read_text()
    caller_text = "void func_15018F80(s16 arg0) {"
    if calls != [0x464E8] or pointers or caller != expected:
        raise ValueError("Actor channel release retail caller contract changed")
    if source.count(caller_text) != 1 or source.count("func_15172D80(arg0);") != 1:
        raise ValueError("Actor channel release semantic caller changed")
    return {
        "direct_jal_calls": ["0x464e8"],
        "aligned_pointer_literals": [],
        "caller": "func_15018F80",
        "abi": "promoted signed channel index in a0; return value ignored",
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
        "registry_evidence": routing_evidence,
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
            report["guards"] != 2 or
            report["natural_positional_differences"] != 2):
        raise ValueError("Actor channel release qualification report changed")
    report["retail_relocations"] = len(RETAIL_BINDINGS)
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
