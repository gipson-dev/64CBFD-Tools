"""Qualify func_151AB1C4's ground-effect callback as guarded exact C."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_ground_effect_callback_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1D6E80.c.o"
ASM = "conker/asm/1D6E80.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22FA90.rodata.s"
BUILD = "conker/build/game-actor-ground-effect-callback-151AB1C4-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x40
RAW_SHA256 = "d212aaf861483e1351b07c539591dbd3e2347305f496b4dde16b6fb143c702b8"
RETAIL_SHA256 = "4012796eaf4f223f8f069fe2f388dcc8ed44ca607b36533feec7242bef07f00c"
NATURAL_BINDINGS = {
    0x018: [("R_MIPS_HI16", "D_800A8FEC")],
    0x01C: [("R_MIPS_LO16", "D_800A8FEC")],
    0x094: [("R_MIPS_26", "func_15045800")],
    0x0BC: [("R_MIPS_26", "func_151ABE40")],
    0x0D8: [("R_MIPS_26", "func_10010FFC")],
    0x0E4: [("R_MIPS_26", "func_151AA264")],
}
BINDINGS = {
    0x01C: [("R_MIPS_HI16", "D_800A8FEC")],
    0x020: [("R_MIPS_LO16", "D_800A8FEC")],
    0x094: [("R_MIPS_26", "func_15045800")],
    0x0BC: [("R_MIPS_26", "func_151ABE40")],
    0x0D8: [("R_MIPS_26", "func_10010FFC")],
    0x0E4: [("R_MIPS_26", "func_151AA264")],
}
PATCH_ROWS = (
    dict(offset="0x018", expected="0x3C010000", replacement="0xC6040014",
         expected_relocations="R_MIPS_HI16:D_800A8FEC", replacement_relocations="-",
         note="Normalize independent ground-effect setup schedule"),
    dict(offset="0x01C", expected="0xC4260000", replacement="0x3C010000",
         expected_relocations="R_MIPS_LO16:D_800A8FEC",
         replacement_relocations="R_MIPS_HI16:D_800A8FEC",
         note="Normalize independent ground-effect setup schedule"),
    dict(offset="0x020", expected="0xC6040014", replacement="0xC4260000",
         expected_relocations="-", replacement_relocations="R_MIPS_LO16:D_800A8FEC",
         note="Normalize independent ground-effect setup schedule"),
    dict(offset="0x024", expected="0x3C014316", replacement="0xE7A40030",
         note="Normalize independent ground-effect setup schedule"),
    dict(offset="0x028", expected="0xE7A40030", replacement="0xC6000118",
         note="Normalize independent ground-effect setup schedule"),
    dict(offset="0x02C", expected="0xC6000118", replacement="0x3C014316",
         note="Normalize independent ground-effect setup schedule"),
    dict(offset="0x084", expected="0xAFA7002C", replacement="0xAFA70028",
         note="Normalize closed ground-result pointer spill home"),
    dict(offset="0x0A8", expected="0x8FA5002C", replacement="0x8FA50028",
         note="Normalize closed ground-result pointer spill home"),
    dict(offset="0x0E8", expected="0x8FA5002C", replacement="0x8FA50028",
         note="Normalize closed ground-result pointer spill home"),
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
    marker = '#include "structs.h"\n'
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.DECLARATIONS in live or candidate.MATCHED in live:
            raise ValueError("Ground-effect callback predecessor source changed")
        qualified = live.replace(
            marker, marker + candidate.DECLARATIONS, 1
        ).replace(candidate.PLACEHOLDER, candidate.MATCHED, 1)
        return live, qualified, False
    if live.count(candidate.MATCHED) == 1:
        if live.count(candidate.DECLARATIONS) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed ground-effect callback source changed")
        predecessor = live.replace(candidate.DECLARATIONS, "", 1).replace(
            candidate.MATCHED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Ground-effect callback source state changed")


def checked_candidate(root, obj):
    raw, bindings = harness.function_blob(obj)
    if len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        raise ValueError("Ground-effect callback natural candidate changed")
    if ((-struct.unpack_from(">I", raw)[0]) & 0xFFFF) != NATURAL_FRAME:
        raise ValueError("Ground-effect callback natural frame changed")
    if bindings != NATURAL_BINDINGS:
        raise ValueError("Ground-effect callback natural bindings changed")
    expected = harness.retail_object_bytes(root)
    differences = [offset for offset in range(0, SIZE, 4)
                   if raw[offset:offset + 4] != expected[offset:offset + 4]]
    wanted = [int(row["offset"], 0) for row in PATCH_ROWS]
    if differences != wanted:
        raise ValueError("Ground-effect callback natural difference set changed")
    return raw, bindings


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_8008AFD0\n", 1)[1].split(
        "enddlabel D_8008AFD0", 1)[0]
    entries = [line.split(".word", 1)[1].strip()
               for line in block.splitlines() if ".word" in line]
    if calls or pointers != [0x22FACC] or entries[15] != FUNCTION or entries.count(FUNCTION) != 1:
        raise ValueError("Ground-effect callback registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x22facc"],
        "registry": "D_8008AFD0[15]",
        "abi": "one owner pointer; side-effect callback with an unconditional finalizer tail",
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
        "checked_candidate": checked_candidate,
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
        raise ValueError("Ground-effect callback report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
