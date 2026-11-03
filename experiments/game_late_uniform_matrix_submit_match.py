"""Qualify func_1518A914's padded uniform matrix submit as direct exact C."""

import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_late_uniform_matrix_submit_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1B7870.c.o"
ASM = "conker/asm/1B7870.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22F8C0.rodata.s"
BUILD = "conker/build/game-late-uniform-matrix-submit-1518A914-match"
ENTRY, ROM = candidate.ENTRY, candidate.ROM
COMPACT_WORDS = 62
COMPACT_SIZE = COMPACT_WORDS * 4
WORDS = candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x68
RAW_SHA256 = "e748b3ac61b5c1a2604161bc7a47119fc1f502c5348823c6ac6f1a46ac31cf5d"
COMPACT_RETAIL_SHA256 = "a9a4eeb3733fa67f590e0598d471d24d2db449b91f6477888fbe2c6c35a76731"
RETAIL_SHA256 = "7484f27bae35efb02afac8e7e95f175253579746834a652ae93d957aa3380169"
BINDINGS = {
    0x020: [("R_MIPS_26", "func_150A8050")],
    0x0D8: [("R_MIPS_26", "guMtxF2L")],
}
PATCH_ROWS = ()


def complete_row(row):
    raise AssertionError("Direct late uniform matrix submit must not create guards")


def source_states(live):
    declarations = candidate.TYPES + candidate.DECLARATIONS + "\n"
    marker = "#include <ultra64.h>\n"
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or declarations in live:
            raise ValueError("Late uniform matrix submit predecessor source changed")
        qualified = live.replace(marker, marker + declarations, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed late uniform matrix submit source changed")
        predecessor = live.replace(declarations, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Late uniform matrix submit source state changed")


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_8008AE0C\n", 1)[1].split(
        "enddlabel D_8008AE0C", 1)[0]
    entries = [line.split(".word", 1)[1].strip()
               for line in block.splitlines() if ".word" in line]
    if calls or pointers != [0x22F8D0] or entries != [
            "func_1515858C", FUNCTION, "func_15158920"]:
        raise ValueError("Late uniform matrix submit registry evidence changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x22f8d0"],
        "registry": "D_8008AE0C[1]",
        "abi": "fixed-matrix output and state pointers; callback returns one after conversion",
    }


def prepare(root, output=None):
    original_loader = harness.load_elf_functions

    def compact_loader(*args, **kwargs):
        functions, symbols, addresses = original_loader(*args, **kwargs)
        words = functions.get(FUNCTION)
        if words is not None:
            if len(words) != WORDS or words[-1] != 0:
                raise ValueError("Late uniform matrix submit retail pad changed")
            functions[FUNCTION] = words[:-1]
        return functions, symbols, addresses

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
        "WORDS": COMPACT_WORDS,
        "SIZE": COMPACT_SIZE,
        "NATURAL_FRAME": NATURAL_FRAME,
        "RETAIL_FRAME": RETAIL_FRAME,
        "RAW_SHA256": RAW_SHA256,
        "RETAIL_SHA256": COMPACT_RETAIL_SHA256,
        "BINDINGS": BINDINGS,
        "PATCH_ROWS": PATCH_ROWS,
        "complete_row": complete_row,
        "source_states": source_states,
        "registry_evidence": registry_evidence,
        "load_elf_functions": compact_loader,
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
    qualified, _, _ = original_loader(
        str(result["qualified_elf"]), "mips-linux-gnu-objdump")
    retail = (Path(root) / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if (len(retail) != SIZE or
            qualified[FUNCTION] != list(struct.unpack(">%dI" % WORDS, retail)) or
            retail[-4:] != b"\0\0\0\0"):
        raise ValueError("Late uniform matrix submit padded linked slot changed")
    if (report["raw_sha256"] != RAW_SHA256 or
            report["retail_sha256"] != COMPACT_RETAIL_SHA256 or
            report["guards"] != 0):
        raise ValueError("Late uniform matrix submit compact report changed")
    report["words"] = WORDS
    report["compact_words"] = COMPACT_WORDS
    report["trailing_pad_words"] = WORDS - COMPACT_WORDS
    report["compact_retail_sha256"] = COMPACT_RETAIL_SHA256
    report["retail_sha256"] = RETAIL_SHA256
    report_path = Path(root) / BUILD / "qualification.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
