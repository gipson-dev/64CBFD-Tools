"""Qualify func_15158BD0's owner-bound effect-record factory as guarded C."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_owner_effect_record_factory_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_185560.c.o"
ASM = "conker/asm/185560.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = ASM
BUILD = "conker/build/game-owner-effect-record-factory-15158BD0-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x30
RAW_SHA256 = "17a8d4b286a659d93699910c73e788584b14643a86635fd5adcda36314ca18c8"
RETAIL_SHA256 = "7ed8b0367cb7731e439dff8f3b43df4a15cd0a1c15dec8536121f3625b2d5d1e"
BINDINGS = {
    0x044: [("R_MIPS_26", "func_15167A68")],
    0x0C8: [("R_MIPS_26", "func_15159370")],
    0x0D8: [("R_MIPS_26", "func_1516979C")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_NOTE = "Normalize owner-effect record factory compiler scheduling"
PATCH_ROWS = (
    dict(offset="0x05C", expected="0x24030002", replacement="0xAC500018"),
    dict(offset="0x060", expected="0x24180003", replacement="0x9218003B"),
    dict(offset="0x064", expected="0xAC500018", replacement="0x24030002"),
    dict(offset="0x068", expected="0xA043002C", replacement="0x24190003"),
    dict(offset="0x06C", expected="0xA043002D", replacement="0xA043002C"),
    dict(offset="0x070", expected="0xA043002E", replacement="0xA043002D"),
    dict(offset="0x074", expected="0xA058002F", replacement="0xA043002E"),
    dict(offset="0x078", expected="0xA0400030", replacement="0xA059002F"),
    dict(offset="0x07C", expected="0x9219003B", replacement="0xA0400030"),
    dict(offset="0x080", expected="0x24090001", replacement="0xA058001C"),
    dict(offset="0x084", expected="0x240A0001", replacement="0xC6040014"),
    dict(offset="0x088", expected="0xA059001C", replacement="0x340A0001"),
    dict(offset="0x08C", expected="0xC6040014", replacement="0x240B0001"),
    dict(offset="0x090", expected="0x02002025", replacement="0xE4440020"),
    dict(offset="0x094", expected="0x24C5001D", replacement="0xC6060018"),
    dict(offset="0x098", expected="0xE4440020", replacement="0x02002025"),
    dict(offset="0x09C", expected="0xC6060018", replacement="0x24C5001D"),
    dict(offset="0x0A0", expected="0xA0400031", replacement="0xE4460024"),
    dict(offset="0x0A4", expected="0xE4460024", replacement="0xC608001C"),
    dict(offset="0x0A8", expected="0xC608001C", replacement="0xA0400031"),
    dict(offset="0x0B8", expected="0xACCA0010", replacement="0xACCB0010"),
    dict(offset="0x0BC", expected="0xA0490031", replacement="0xA04A0031"),
    dict(offset="0x0C0", expected="0xACCA0010", replacement="0xACCB0010"),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def complete_row(row):
    return {
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": row["offset"],
        "expected": row["expected"],
        "replacement": row["replacement"],
        "expected_relocations": "-",
        "replacement_relocations": "-",
        "note": PATCH_NOTE,
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }


def source_states(live):
    declarations = candidate.DECLARATIONS + "\n"
    marker = "void func_100043B4(s32 *, u32);\n"
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or declarations in live:
            raise ValueError("Owner-effect factory predecessor source changed")
        qualified = live.replace(
            marker, marker + "\n" + declarations, 1
        ).replace(candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed owner-effect factory source changed")
        predecessor = live.replace("\n" + declarations, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1
        )
        return predecessor, live, True
    raise ValueError("Owner-effect factory source state changed")


def registry_evidence(root):
    image = (Path(root) / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    expected_calls = [
        0x9A268, 0x9A2EC, 0xA08A4,
        0x17AE64, 0x17AF14, 0x17AF80, 0x17AFDC,
    ]
    if calls != expected_calls or pointers:
        raise ValueError("Owner-effect factory caller evidence changed")
    return {
        "direct_jal_calls": ["0x%x" % value for value in calls],
        "aligned_pointer_literals": [],
        "registry": None,
        "abi": (
            "owner pointer, unsigned-byte enable flag, and trailing payload size; "
            "returns a type-0x2E record or null after allocator/classifier failure"
        ),
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
            report["natural_positional_differences"] != len(PATCH_ROWS) or
            report["guards"] != len(PATCH_ROWS) or
            report["changed_bodies"] != [FUNCTION]):
        raise ValueError("Owner-effect factory qualification report changed")
    report.update({
        "natural_words": WORDS,
        "retail_words": WORDS,
        "natural_relocations": len(BINDINGS),
        "retail_relocations": len(RETAIL_BINDINGS),
    })
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
