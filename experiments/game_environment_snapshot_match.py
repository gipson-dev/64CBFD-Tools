"""Qualify func_151732E0's environment snapshot setup as guarded exact C."""

import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_environment_snapshot_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1A0790.c.o"
ASM = "conker/asm/1A0790.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/nonmatchings/game_3B920/func_1500E470.s"
BUILD = "conker/build/game-environment-snapshot-151732E0-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x20
RAW_SHA256 = "a0b439002fae7517273c67a54579e28038e6c662dbebbf121f91c83b61114ddf"
RETAIL_SHA256 = "b851f41c56fa0253132495248588db0227794f2a624efe5e29ca642db21d492b"
BINDINGS = {
    0x00C: [("R_MIPS_HI16", "D_800B0DF0")],
    0x010: [("R_MIPS_LO16", "D_800B0DF0")],
    0x03C: [("R_MIPS_HI16", "D_800B0DF0")],
    0x040: [("R_MIPS_LO16", "D_800B0DF0")],
    0x048: [("R_MIPS_HI16", "D_8008CC70")],
    0x04C: [("R_MIPS_LO16", "D_8008CC70")],
    0x0B4: [("R_MIPS_HI16", "D_800DD2E0")],
    0x0B8: [("R_MIPS_LO16", "D_800DD2E0")],
    0x0C8: [("R_MIPS_26", "func_151733E4")],
    0x0D8: [("R_MIPS_HI16", "D_800DD2E0")],
    0x0DC: [("R_MIPS_LO16", "D_800DD2E0")],
    0x0E0: [("R_MIPS_26", "func_151733E4")],
}
PATCH_ROWS = (
    dict(offset="0x028", expected="0x544E0007", replacement="0x55C20007",
         note="Normalize environment range comparison operand order"),
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
    declarations = candidate.DECLARATIONS + "\n"
    if live.count(candidate.OLD_TYPES) == 1 and live.count(candidate.PLACEHOLDER) == 1:
        if (candidate.INSTALL_TYPES in live or declarations in live or
                candidate.SELECTED in live):
            raise ValueError("Environment snapshot predecessor source changed")
        qualified = live.replace(
            candidate.OLD_TYPES, candidate.INSTALL_TYPES, 1).replace(
            "extern Generated1A0790State *D_800B0DF0;\n",
            "extern Generated1A0790State *D_800B0DF0;\n" + declarations,
            1).replace(candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.INSTALL_TYPES) == 1 and live.count(candidate.SELECTED) == 1:
        if live.count(declarations) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed environment snapshot source changed")
        predecessor = live.replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1).replace(
            "extern Generated1A0790State *D_800B0DF0;\n" + declarations,
            "extern Generated1A0790State *D_800B0DF0;\n", 1).replace(
            candidate.INSTALL_TYPES, candidate.OLD_TYPES, 1)
        return predecessor, live, True
    raise ValueError("Environment snapshot source state changed")


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    first = (root / "conker/asm/nonmatchings/game_34F20/func_15007B3C.s").read_text()
    second = (root / REGISTRY).read_text()
    first_row = "/* 352A4 15007DF4 0D45CCB8 */  jal        func_151732E0"
    second_row = "/* 3B9B4 1500E504 0D45CCB8 */  jal        func_151732E0"
    if (calls != [0x352A4, 0x3B9B4] or pointers or
            first.count(first_row) != 1 or second.count(second_row) != 1):
        raise ValueError("Environment snapshot caller evidence changed")
    return {
        "direct_jal_calls": ["0x352a4", "0x3b9b4"],
        "aligned_pointer_literals": [],
        "callers": ["func_15007B3C", "func_1500E470"],
        "abi": "one signed context value; no return value",
    }


def assemble_owner(root, output, compact, rows, fields, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    patch_file = owner_dir / "retail-word-patches.csv"
    harness.write_patches(patch_file, fields, rows)
    predecessor, qualified, _ = source_states((root / SOURCE).read_text())
    nodebug_source = qualified if label == "qualified-owner" else predecessor
    nodebug, diagnostics = candidate.compile_owner(
        root, owner_dir, nodebug_source, label + "-nodebug", flags=("-O2",))
    if diagnostics:
        raise ValueError("Environment snapshot nodebug owner diagnostics changed")
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(harness.emit_padded_assembly(
        compact, root / ASM,
        function_objects={"func_151733D8": nodebug},
        word_patches_path=patch_file, filename=FILENAME))
    obj = owner_dir / (FILENAME + ".c.o")
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly)], check=True, capture_output=True)
    return obj


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
        "assemble_owner": assemble_owner,
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
            report["retail_sha256"] != RETAIL_SHA256 or report["guards"] != 1):
        raise ValueError("Environment snapshot report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
