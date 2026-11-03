"""Qualify func_15132A88's actor matrix callback dispatch as direct exact C."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_actor_matrix_callback_dispatch_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_15F680.c.o"
ASM = "conker/asm/15F680.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-actor-matrix-callback-dispatch-15132A88-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x18
RAW_SHA256 = "d8369d118c0bfd39199a9304ee94072be81bca54bb86d543d63be37666263029"
RETAIL_SHA256 = "ae72b23bedc2985367c742e841bedf5ff2ca9283b87d065a45d578f2e4eafd43"
BINDINGS = {
    0x040: [("R_MIPS_26", "func_151464B8")],
    0x058: [("R_MIPS_HI16", "D_800BE9C0")],
    0x078: [("R_MIPS_LO16", "D_800BE9C0")],
    0x07C: [("R_MIPS_HI16", "D_8008998C")],
    0x088: [("R_MIPS_LO16", "D_8008998C")],
    0x0A8: [("R_MIPS_26", "func_1516972C")],
}
PATCH_ROWS = ()


def complete_row(row):
    raise AssertionError("Direct actor matrix dispatch must not create guards")


def source_states(live):
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or candidate.DECLARATIONS in live:
            raise ValueError("Actor matrix dispatch predecessor source changed")
        qualified = live.replace(
            candidate.ANCHOR, candidate.ANCHOR + candidate.DECLARATIONS, 1
        ).replace(candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if (live.count(candidate.DECLARATIONS) != 1 or
                candidate.PLACEHOLDER in live):
            raise ValueError("Installed actor matrix dispatch source changed")
        predecessor = live.replace(candidate.DECLARATIONS, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Actor matrix dispatch source state changed")


def routing_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    if calls or pointers != [0x230488, 0x230E14]:
        raise ValueError("Actor matrix dispatch routing evidence changed")
    owner_asm = (root / ASM).read_text()
    if owner_asm.count("glabel " + FUNCTION) != 1:
        raise ValueError("Actor matrix dispatch retail owner label changed")
    registry = (root / "conker/asm/data/22FF90.rodata.s").read_text()
    if registry.count(".word " + FUNCTION) != 2:
        raise ValueError("Actor matrix dispatch descriptor entries changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x230488", "0x230e14"],
        "registry": "D_8008B4D4 descriptor slots +0x4F4 and +0xE80",
        "abi": "one actor pointer; void update dispatches a selected matrix callback",
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
        raise ValueError("Actor matrix dispatch retail bytes changed")
    for offset, rows in BINDINGS.items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", data, offset,
                         struct.unpack_from(">I", data, offset)[0] & mask)
    return bytes(data)


def checked_candidate(root, obj):
    raw, bindings = function_blob(obj)
    if len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        raise ValueError("Actor matrix dispatch natural candidate changed")
    if bindings != BINDINGS:
        raise ValueError("Actor matrix dispatch relocation bindings changed")
    if raw != retail_object_bytes(root):
        raise ValueError("Actor matrix dispatch natural candidate differs from retail")
    return raw, bindings


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
        raise ValueError("Actor matrix dispatch qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
