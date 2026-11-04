"""Qualify func_151B6320's actor-position effect factory as direct exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_actor_position_effect_factory_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1E37D0.c.o"
ASM = "conker/asm/1E37D0.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/src/game/generated_97AA0.c"
BUILD = "conker/build/game-actor-position-effect-factory-151B6320-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x90
RAW_SHA256 = "fb4fc0ac22b7031bca52f48601446d2d3dd62faeb421c1225b1db5cfc047a06f"
RETAIL_SHA256 = "c4525273cad4a8e76fcf60658e3f63eb946d81e5f29209f02808026926d2532c"
BINDINGS = RETAIL_BINDINGS = candidate.RETAIL_BINDINGS
PATCH_ROWS = ()


def complete_row(row):
    raise AssertionError("The actor-position effect factory needs no word guards")


def source_states(live):
    marker = "#include <ultra64.h>\n"
    declarations = candidate.DECLARATIONS + "\n"
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or declarations in live:
            raise ValueError("Actor-position effect factory predecessor source changed")
        qualified = live.replace(marker, marker + declarations, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1
        )
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed actor-position effect factory source changed")
        predecessor = live.replace(declarations, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1
        )
        return predecessor, live, True
    raise ValueError("Actor-position effect factory source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    caller = (root / REGISTRY).read_text()
    call = "func_151B6320(arg0, 0xFF, 1);"
    if calls != [0x97EE0] or pointers or caller.count(call) != 1:
        raise ValueError("Actor-position effect factory caller evidence changed")
    return {
        "direct_jal_calls": ["0x97ee0"],
        "aligned_pointer_literals": [],
        "caller": "func_1506AA08",
        "abi": (
            "actor pointer, unsigned byte channel, signed context; creates one "
            "position-effect record and returns void"
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
            report["natural_positional_differences"] != 0 or
            report["guards"] != 0):
        raise ValueError("Actor-position effect factory report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
