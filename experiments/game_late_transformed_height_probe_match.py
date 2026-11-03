"""Qualify func_151AF5C0's transformed height probe as direct exact C."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_late_transformed_height_probe_candidates as candidate


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1DCA70.c.o"
ASM = "conker/asm/1DCA70.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-late-transformed-height-probe-151AF5C0-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x38
RAW_SHA256 = "d8a8c47c3e87f1329ddde3ad5f2d1fe857cc14661f97e491243ed6567227e0e8"
RETAIL_SHA256 = "6ca039999591d943e14da27d3a7da11c812440b87bd19b0770263231ecdc5fc9"
BINDINGS = {
    0x048: [("R_MIPS_HI16", "D_800AA0F0")],
    0x04C: [("R_MIPS_HI16", "D_800AA0FC")],
    0x054: [("R_MIPS_LO16", "D_800AA0FC")],
    0x058: [("R_MIPS_LO16", "D_800AA0F0")],
    0x07C: [("R_MIPS_26", "func_15143134")],
    0x0BC: [("R_MIPS_26", "func_1504715C")],
    0x0E4: [("R_MIPS_26", "func_15046C80")],
}
PATCH_ROWS = ()


def complete_row(row):
    raise AssertionError("Direct late transformed-height probe must not create guards")


def source_states(live):
    return candidate.source_states(live)


def routing_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    if calls != [0x1DCBBC] or pointers:
        raise ValueError("Late transformed-height routing evidence changed")
    caller = struct.unpack_from(">8I", image, 0x1DCBA8)
    if caller != (
            0x8DF801D4, 0x27A40124, 0x8FA50130, 0x1300012F,
            0x27A60100, jal, 0x93A70137, 0x1040012B):
        raise ValueError("Late transformed-height caller contract changed")
    return {
        "direct_jal_calls": ["0x1dcbbc"],
        "aligned_pointer_literals": [],
        "caller": "func_151AF6D4",
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
        raise ValueError("Late transformed-height retail bytes changed")
    for offset, rows in BINDINGS.items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", data, offset,
                         struct.unpack_from(">I", data, offset)[0] & mask)
    return bytes(data)


def checked_payload(root, raw, bindings):
    if len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        raise ValueError("Late transformed-height natural candidate changed")
    if bindings != BINDINGS:
        raise ValueError("Late transformed-height relocation bindings changed")
    if raw != retail_object_bytes(root):
        raise ValueError("Late transformed-height natural candidate differs from retail")
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
        "REGISTRY": "conker/asm/1DCA70.s",
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
        raise ValueError("Late transformed-height qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
