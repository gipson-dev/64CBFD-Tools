"""Qualify func_1515BE50's object-request tracking factory as exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_object_request_factory_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_188F90.c.o"
ASM = "conker/asm/188F90.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/179F30.s"
BUILD = "conker/build/game-object-request-factory-1515BE50-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x30
RAW_SHA256 = "54392dd2d00cc7c415a70a98efd211fb09903f4171cb8ebea65544af189efa03"
RETAIL_SHA256 = "54ef22a94c688b9fa29fc0eca45c961712630d1a1ae00303367dec8a81e750e5"
BINDINGS = {
    0x04C: [("R_MIPS_26", "func_15167A68")],
    0x070: [("R_MIPS_26", "memcpy")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_ROWS = ()


def complete_row(row):
    raise AssertionError("The direct object-request factory needs no word guards")


def source_states(live):
    declarations = candidate.TYPES + "\n"
    marker = '#include "structs.h"\n'
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or declarations in live:
            raise ValueError("Object-request factory predecessor source changed")
        qualified = live.replace(marker, marker + "\n" + declarations, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed object-request factory source changed")
        predecessor = live.replace("\n" + declarations, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Object-request factory source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    caller = (root / REGISTRY).read_text()
    call_line = "/* 17C354 1514EEA4 0D456F94 */  jal        func_1515BE50"
    if calls != [0x17C354] or pointers or caller.count(call_line) != 1:
        raise ValueError("Object-request factory caller evidence changed")
    return {
        "direct_jal_calls": ["0x17c354"],
        "aligned_pointer_literals": [],
        "caller": "func_1514EE70",
        "abi": "request pointer, extra bytes, byte channel, context; returns tracking record or null",
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
            report["natural_positional_differences"] != 0 or
            report["guards"] != 0):
        raise ValueError("Object-request factory qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
