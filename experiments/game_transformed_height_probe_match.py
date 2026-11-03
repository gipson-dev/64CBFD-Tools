"""Qualify func_150CB0E0's transformed height probe as direct exact C."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_transformed_height_probe_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_F8590.c.o"
ASM = "conker/asm/F8590.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-transformed-height-probe-150CB0E0-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x38
RAW_SHA256 = "862a9af6d07f9c08a190a0a189353d58ccfb32d28cae3ce30f5628ff5b4fb789"
RETAIL_SHA256 = "7842a0d1c596d002e2fab875d5e660b2b8ab8eeb55ef85a3d2473d020ddf5e73"
BINDINGS = {
    0x048: [("R_MIPS_HI16", "D_800A05E0")],
    0x04C: [("R_MIPS_HI16", "D_800A05EC")],
    0x054: [("R_MIPS_LO16", "D_800A05EC")],
    0x058: [("R_MIPS_LO16", "D_800A05E0")],
    0x07C: [("R_MIPS_26", "func_15143134")],
    0x0BC: [("R_MIPS_26", "func_1504715C")],
    0x0E4: [("R_MIPS_26", "func_15046C80")],
}
PATCH_ROWS = ()


def complete_row(row):
    raise AssertionError("Direct transformed height probe must not create guards")


def source_states(live):
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or candidate.DECLARATIONS in live:
            raise ValueError("Transformed height probe predecessor source changed")
        qualified = live.replace(
            candidate.ANCHOR, candidate.ANCHOR + candidate.DECLARATIONS, 1
        ).replace(candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if (live.count(candidate.DECLARATIONS) != 1 or
                candidate.PLACEHOLDER in live):
            raise ValueError("Installed transformed height probe source changed")
        predecessor = live.replace(candidate.DECLARATIONS, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Transformed height probe source state changed")


def routing_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    if calls != [0xF86D4] or pointers:
        raise ValueError("Transformed height probe routing evidence changed")
    caller = struct.unpack_from(">8I", image, 0xF86B8)
    if caller != (
            0x8FAE0130, 0x27A40124, 0x8FA50130, 0x8DCF01D4,
            0x27A60100, 0x51E00168, 0x8FBF0044, jal):
        raise ValueError("Transformed height probe caller contract changed")
    return {
        "direct_jal_calls": ["0xf86d4"],
        "aligned_pointer_literals": [],
        "caller": "func_150CB1F4",
        "abi": "position output, actor, optional height result, unsigned mode",
    }


def function_blob(obj):
    text, functions, relocations = harness.parse_object(obj)
    info = functions[FUNCTION]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {
        offset - start: rows for offset, rows in relocations.items()
        if start <= offset < end
    }
    return text[start:end], bindings


def retail_object_bytes(root):
    data = bytearray((Path(root) / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE])
    if len(data) != SIZE or hashlib.sha256(data).hexdigest() != RETAIL_SHA256:
        raise ValueError("Transformed height probe retail bytes changed")
    for offset, rows in BINDINGS.items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", data, offset,
                         struct.unpack_from(">I", data, offset)[0] & mask)
    return bytes(data)


def checked_payload(root, raw, bindings):
    """Accept only the complete natural payload and its exact relocations."""
    if len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        raise ValueError("Transformed height probe natural candidate changed")
    if bindings != BINDINGS:
        raise ValueError("Transformed height probe relocation bindings changed")
    if raw != retail_object_bytes(root):
        raise ValueError("Transformed height probe natural candidate differs from retail")
    return raw, bindings


def checked_candidate(root, obj):
    return checked_payload(root, *function_blob(obj))


def assemble_owner(root, output, compact, rows, fields, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    patch_file = owner_dir / "retail-word-patches.csv"
    harness.write_patches(patch_file, fields, rows)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(harness.emit_padded_assembly(
        compact, root / ASM, word_patches_path=patch_file,
        filename=FILENAME))
    obj = owner_dir / (FILENAME + ".c.o")
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly),
    ], check=True, capture_output=True)
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
        "registry_evidence": routing_evidence,
        "checked_candidate": checked_candidate,
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
            report["retail_sha256"] != RETAIL_SHA256 or
            report["guards"] != 0 or
            report["natural_positional_differences"] != 0):
        raise ValueError("Transformed height probe qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
