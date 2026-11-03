"""Qualify func_151B9214's timed oscillation transition as guarded C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_timed_oscillation_transition_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1E6260.c.o"
ASM = "conker/asm/1E6260.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22E370.rodata.s"
BUILD = "conker/build/game-timed-oscillation-transition-151B9214-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME, RETAIL_FRAME = 0x28, 0x20
RAW_SHA256 = "f00d687c48b7bf5e180ad4d5da86e68af85e94edd0a6c49cb3fe79694b8dba0f"
RETAIL_SHA256 = "f4d52581d33f3d3cbc8db7f8dc7fbc284fbdedb4044654668519e9ef20d812cd"
BINDINGS = {
    0x008: [("R_MIPS_HI16", "D_800BE9A4")],
    0x00C: [("R_MIPS_LO16", "D_800BE9A4")],
    0x028: [("R_MIPS_26", "func_15144B68")],
    0x040: [("R_MIPS_26", "sinf")],
    0x050: [("R_MIPS_HI16", "D_800BE9A4")],
    0x05C: [("R_MIPS_LO16", "D_800BE9A4")],
    0x0BC: [("R_MIPS_HI16", "D_800AA564")],
    0x0C4: [("R_MIPS_LO16", "D_800AA564")],
}

PATCH_ROWS = (
    dict(offset="0x000", expected="0x27BDFFD8", replacement="0x27BDFFE0",
         note="Normalize timed oscillation callback frame size"),
    dict(offset="0x02C", expected="0xAFA40028", replacement="0xAFA40020",
         note="Normalize timed oscillation callback owner home"),
    dict(offset="0x030", expected="0x8FA40028", replacement="0x8FA40020",
         note="Normalize timed oscillation callback owner reload"),
    dict(offset="0x044", expected="0xAFA2001C", replacement="0xAFA20018",
         note="Normalize timed oscillation state-pointer home"),
    dict(offset="0x048", expected="0x8FA2001C", replacement="0x8FA20018",
         note="Normalize timed oscillation state-pointer reload"),
    dict(offset="0x054", expected="0xC44C0004", replacement="0xC4420004",
         note="Keep oscillation amplitude in retail F2"),
    dict(offset="0x058", expected="0xC4420018", replacement="0xC44C0018",
         note="Keep transition time in retail F12"),
    dict(offset="0x060", expected="0x460C0482", replacement="0x46020482",
         note="Multiply sine by the retail amplitude register"),
    dict(offset="0x064", expected="0x4602203C", replacement="0x460C203C",
         note="Compare the retail transition-time register"),
    dict(offset="0x080", expected="0x46061281", replacement="0x46066281",
         note="Subtract the live frame step from transition time"),
    dict(offset="0x0A4", expected="0x46106100", replacement="0x46101100",
         note="Add amplitude velocity through retail F2"),
    dict(offset="0x0B0", expected="0xC442000C", replacement="0xC440000C",
         note="Keep the expired-route phase rate in retail F0"),
    dict(offset="0x0C0", expected="0x46029181", replacement="0x46009181",
         note="Subtract the retail phase-rate register"),
    dict(offset="0x0C4", expected="0xC4200000", replacement="0xC42C0000",
         expected_relocations="R_MIPS_LO16:D_800AA564",
         replacement_relocations="R_MIPS_LO16:D_800AA564",
         note="Load the transition scale into retail F12"),
    dict(offset="0x0C8", expected="0x460C8101", replacement="0x46028101",
         note="Subtract the retail amplitude register"),
    dict(offset="0x0CC", expected="0x46003282", replacement="0x460C3282",
         note="Scale the phase-rate delta through retail F12"),
    dict(offset="0x0D4", expected="0x46002482", replacement="0x460C2482",
         note="Scale the amplitude delta through retail F12"),
    dict(offset="0x0D8", expected="0x460A1200", replacement="0x460A0200",
         note="Add the scaled phase-rate delta through retail F0"),
    dict(offset="0x0DC", expected="0x46126180", replacement="0x46121180",
         note="Add the scaled amplitude delta through retail F2"),
    dict(offset="0x0F0", expected="0x27BD0028", replacement="0x27BD0020",
         note="Normalize timed oscillation callback frame restore"),
)


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
    declarations = candidate.TYPES + candidate.DECLARATIONS + "\n"
    marker = "#include <ultra64.h>\n"
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED_GUARDED in live or declarations in live:
            raise ValueError("Timed oscillation transition predecessor source changed")
        qualified = live.replace(marker, marker + declarations, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED_GUARDED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED_GUARDED) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed timed oscillation transition source changed")
        predecessor = live.replace(declarations, "", 1).replace(
            candidate.SELECTED_GUARDED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Timed oscillation transition source state changed")


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_800898B0\n", 1)[1].split(
        "enddlabel D_800898B0", 1)[0]
    entries = [line for line in block.splitlines() if ".word" in line]
    if (calls or pointers != [0x22E394] or
            entries[9].split(".word", 1)[1].strip() != FUNCTION or
            block.count(FUNCTION) != 1):
        raise ValueError("Timed oscillation transition registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x22e394"],
        "registry": "D_800898B0[9]",
        "abi": "one owner pointer; callback returns one after updating the embedded oscillator",
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
    if report["raw_sha256"] != RAW_SHA256 or report["retail_sha256"] != RETAIL_SHA256:
        raise ValueError("Timed oscillation transition report hashes changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
