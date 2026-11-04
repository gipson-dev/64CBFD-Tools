"""Qualify func_150E3414's positional effect-and-audio handle as exact C."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_effect_audio_handle_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION = candidate.FUNCTION
FILENAME = "generated_1104D0"
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1104D0.c.o"
ASM = "conker/asm/1104D0.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/C9EC0.s"
BUILD = "conker/build/game-effect-audio-handle-150E3414-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x48
RAW_SHA256 = "0ab13fb3ed75394d1abee20045a9e3222c6419d1f1d7abc13ce7165efb2b27ee"
RETAIL_SHA256 = "8dc372cb9b7454b5316acbc8f24fcaf95235656415ab68b1e2f13a0221204e99"
BINDINGS = {
    0x080: [("R_MIPS_26", "func_150E3020")],
    0x090: [("R_MIPS_HI16", "func_150E33CC")],
    0x094: [("R_MIPS_LO16", "func_150E33CC")],
    0x0D0: [("R_MIPS_26", "func_1000FA64")],
}
RETAIL_BINDINGS = BINDINGS
PATCH_ROWS = ()
COMMENT_BEFORE = "/* Non-matching placeholders for the text-only asm slice asm/1104D0.s. */"
COMMENT_AFTER = "/* Restored functions and remaining placeholders for asm/1104D0.s. */"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    marker = "s32 func_150AD9A0(s32, s32, s32);\n"
    if live.count(candidate.PLACEHOLDER) == 1:
        if (candidate.SELECTED in live or candidate.DECLARATION in live or
                live.count(COMMENT_BEFORE) != 1 or COMMENT_AFTER in live):
            raise ValueError("Effect-audio handle predecessor source changed")
        qualified = live.replace(
            marker, marker + candidate.DECLARATION, 1).replace(
            COMMENT_BEFORE, COMMENT_AFTER, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if (live.count(candidate.DECLARATION) != 1 or
                live.count(COMMENT_AFTER) != 1 or
                candidate.PLACEHOLDER in live or COMMENT_BEFORE in live):
            raise ValueError("Installed effect-audio handle source changed")
        predecessor = live.replace(candidate.DECLARATION, "", 1).replace(
            COMMENT_AFTER, COMMENT_BEFORE, 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Effect-audio handle source state changed")


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(
        ">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    assembly = (root / REGISTRY).read_text()
    caller_block = assembly.split("glabel func_1509D180\n", 1)[1].split(
        "endlabel func_1509D180", 1)[0]
    caller_source = (root / "conker/src/game/generated_C9EC0.c").read_text()
    if (calls != [0xCAB04] or pointers or
            caller_block.count("jal        func_150E3414") != 1 or
            caller_block.count("/* CAB04 1509D654") != 1 or
            caller_source.count(
                "s32 func_1509D180() {\n    return 0;\n}") != 1):
        raise ValueError("Effect-audio handle caller evidence changed")
    return {
        "direct_jal_calls": ["0xcab04"],
        "direct_callers": [
            {"function": "func_1509D180", "call": "0x1509d654"}],
        "caller_source": "retail assembly retained; current C parent is a placeholder",
        "aligned_pointer_literals": [],
        "callback": "func_150E33CC passed to func_1000FA64",
        "abi": "nine O32 arguments; returns zero or a one-based unsigned-byte slot",
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
            report["natural_positional_differences"] != 0 or
            report["changed_bodies"] != [FUNCTION]):
        raise ValueError("Effect-audio handle qualification report changed")
    report["retail_relocations"] = len(RETAIL_BINDINGS)
    report["callback_relocation_words"] = 2
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
