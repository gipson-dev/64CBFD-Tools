"""Qualify func_15178C9C's record-to-actor distance query as guarded exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_record_actor_distance_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1A5440.c.o"
ASM = "conker/asm/1A5440.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/src/game_CB1C0.c"
BUILD = "conker/build/game-record-actor-distance-15178C9C-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x18
RAW_SHA256 = "ef7014d423dcd00e31dbdcc94fbfee9d8fc3840ca6395d68192348911656b487"
RETAIL_SHA256 = "18473fd35f3252a6b98c70ba4859665f62aeeccc167104c6c3980ac1d09b0e7d"
BINDINGS = {
    0x018: [("R_MIPS_26", "func_15178B98")],
    0x054: [("R_MIPS_HI16", "D_800CC2D0")],
    0x058: [("R_MIPS_LO16", "D_800CC2D0")],
}
PATCH_ROWS = (
    dict(offset="0x060", expected="0x03191821", replacement="0x03193021",
         note="Normalize record-distance actor pointer register"),
    dict(offset="0x064", expected="0xC4640014", replacement="0xC4C40014",
         note="Normalize record-distance actor X base register"),
    dict(offset="0x06C", expected="0xC4720018", replacement="0xC4D20018",
         note="Normalize record-distance actor Y base register"),
    dict(offset="0x084", expected="0x44048000", replacement="0x44038000",
         note="Normalize record-distance X delta register"),
    dict(offset="0x08C", expected="0xC470001C", replacement="0xC4D0001C",
         note="Normalize record-distance actor Z base register"),
    dict(offset="0x090", expected="0x00840019", replacement="0x00630019",
         note="Normalize record-distance X square register"),
    dict(offset="0x0A0", expected="0x00007012", replacement="0x00001812",
         note="Normalize record-distance X square result register"),
    dict(offset="0x0A8", expected="0x44055000", replacement="0x44045000",
         note="Normalize record-distance Y delta register"),
    dict(offset="0x0B0", expected="0x00A50019", replacement="0x00840019",
         note="Normalize record-distance Y square register"),
    dict(offset="0x0B8", expected="0x44064000", replacement="0x44054000",
         note="Normalize record-distance Z delta register"),
    dict(offset="0x0BC", expected="0x00007812", replacement="0x00002012",
         note="Normalize record-distance Y square result register"),
    dict(offset="0x0C0", expected="0x01CFC021", replacement="0x00647021",
         note="Normalize record-distance XY accumulator registers"),
    dict(offset="0x0C8", expected="0x00C60019", replacement="0x00A50019",
         note="Normalize record-distance Z square register"),
    dict(offset="0x0CC", expected="0x0000C812", replacement="0x00002812",
         note="Normalize record-distance Z square result register"),
    dict(offset="0x0D0", expected="0x03194021", replacement="0x01C57821",
         note="Normalize record-distance XYZ accumulator registers"),
    dict(offset="0x0D4", expected="0x44885000", replacement="0x448F5000",
         note="Normalize record-distance squared-sum register"),
)


def complete_row(row):
    return {
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": row["offset"],
        "expected": row["expected"],
        "replacement": row["replacement"],
        "expected_relocations": "-",
        "replacement_relocations": "-",
        "note": row["note"],
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }


def source_states(live):
    type_marker = "} CleanupNode;\n"
    declaration_marker = "extern CleanupNode *D_800DCF3C;\n"
    installed_types = type_marker + "\n" + candidate.TYPES
    installed_declarations = declaration_marker + candidate.DECLARATIONS
    if live.count(candidate.PLACEHOLDER) == 1:
        if (candidate.TYPES in live or candidate.DECLARATIONS in live or
                candidate.SELECTED in live):
            raise ValueError("Record actor distance predecessor source changed")
        qualified = live.replace(type_marker, installed_types, 1).replace(
            declaration_marker, installed_declarations, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if (live.count(candidate.TYPES) != 1 or
                live.count(candidate.DECLARATIONS) != 1 or
                candidate.PLACEHOLDER in live):
            raise ValueError("Installed record actor distance source changed")
        predecessor = live.replace(candidate.SELECTED, candidate.PLACEHOLDER, 1).replace(
            installed_declarations, declaration_marker, 1).replace(
            installed_types, type_marker, 1)
        return predecessor, live, True
    raise ValueError("Record actor distance source state changed")


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    caller = (root / REGISTRY).read_text()
    call_row = "return func_15178C9C(arg0 & 0xff, func_15084000(arg2->unk8 & mask));"
    if calls != [0xCB3A4] or pointers or caller.count(call_row) != 1:
        raise ValueError("Record actor distance caller evidence changed")
    return {
        "direct_jal_calls": ["0xcb3a4"],
        "aligned_pointer_literals": [],
        "caller": "func_1509DEC4",
        "abi": "unsigned byte record ID and signed actor index; signed integer distance return",
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
    if (report["raw_sha256"] != RAW_SHA256 or
            report["retail_sha256"] != RETAIL_SHA256 or
            report["guards"] != len(PATCH_ROWS)):
        raise ValueError("Record actor distance report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
