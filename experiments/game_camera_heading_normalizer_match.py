"""Qualify func_15123070's tracked-camera heading normalization."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

from tools.experiments import game_camera_heading_normalizer_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.pad_c_object import emit_padded_assembly as emit_plain_owner


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game_14FF90.c.o"
ASM = "conker/retail_layout.us.txt"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-camera-heading-normalizer-15123070-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0x30
RAW_SHA256 = "db2db668e6374b268754e75b3c95f421c279c075b2dbba2894377d055a4ca160"
RETAIL_SHA256 = "387f279faed3c335c1d2f8f2c4a3f127bda20779bee10bcaaf8476bdc3ffdc31"
BINDINGS = {
    0x038: [("R_MIPS_26", "func_15048F90")],
    0x040: [("R_MIPS_26", "func_15048FC8")],
}
PATCH_ROWS = (
    dict(offset="0x050", expected="0xC4E4037C", replacement="0x44811000"),
    dict(offset="0x054", expected="0x46002081", replacement="0xC4E4037C"),
    dict(offset="0x058", expected="0xE4E20390", replacement="0x46002181"),
    dict(offset="0x05C", expected="0x44811000", replacement="0xE4E60390"),
    dict(offset="0x06C", expected="0xC4E8037C", replacement="0xC4EA037C"),
    dict(offset="0x074", expected="0xC5E60040", replacement="0xC5E80040"),
    dict(offset="0x078", expected="0x44818000", replacement="0x44819000"),
    dict(offset="0x080", expected="0x46083281", replacement="0x460A4401"),
    dict(offset="0x088", expected="0x46105001", replacement="0x46128001"),
    dict(offset="0x0E0", expected="0x46020480", replacement="0x46020100"),
    dict(offset="0x0E4", expected="0xE4F20390", replacement="0xE4E40390"),
    dict(offset="0x0F8", expected="0x46020480", replacement="0x46020100"),
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
        "note": "Normalize camera heading float-register scheduling",
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }


def source_states(live):
    predecessor_block = candidate.PREDECESSOR_BLOCK
    if live.count(predecessor_block) == 1:
        if (candidate.SELECTED in live or candidate.LOOSE_VECTOR_INCLUDE in live or
                live.count(candidate.DECLARATION) != 1):
            raise ValueError("Camera heading normalizer predecessor source changed")
        qualified = live.replace(
            candidate.FUNCTIONS_INCLUDE, candidate.LOOSE_VECTOR_INCLUDE, 1
        ).replace(candidate.DECLARATION, candidate.TYPED_DECLARATION, 1).replace(
            predecessor_block, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if (live.count(candidate.LOOSE_VECTOR_INCLUDE) != 1 or
                live.count(candidate.TYPED_DECLARATION) != 1 or
                predecessor_block in live):
            raise ValueError("Installed camera heading normalizer source changed")
        predecessor = live.replace(
            candidate.LOOSE_VECTOR_INCLUDE, candidate.FUNCTIONS_INCLUDE, 1
        ).replace(candidate.TYPED_DECLARATION, candidate.DECLARATION, 1).replace(
            candidate.SELECTED, predecessor_block, 1)
        return predecessor, live, True
    raise ValueError("Camera heading normalizer source state changed")


def function_blob(obj):
    text, functions, relocations = harness.parse_object(obj)
    info = functions[FUNCTION]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {
        offset - start: rows for offset, rows in relocations.items()
        if start <= offset < end
    }
    return text[start:end], bindings


def retail_bytes(root):
    data = (Path(root) / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or hashlib.sha256(data).hexdigest() != RETAIL_SHA256:
        raise ValueError("Camera heading normalizer retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    for offset, rows in BINDINGS.items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", data, offset,
                         struct.unpack_from(">I", data, offset)[0] & mask)
    return bytes(data)


def checked_candidate(root, obj):
    raw, bindings = function_blob(obj)
    if len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        raise ValueError("Camera heading normalizer natural candidate changed")
    if ((-struct.unpack_from(">I", raw)[0]) & 0xFFFF) != NATURAL_FRAME:
        raise ValueError("Camera heading normalizer natural frame changed")
    if bindings != BINDINGS:
        raise ValueError("Camera heading normalizer bindings changed")
    expected = retail_object_bytes(root)
    differences = [offset for offset in range(0, SIZE, 4)
                   if raw[offset:offset + 4] != expected[offset:offset + 4]]
    if differences != [int(row["offset"], 0) for row in PATCH_ROWS]:
        raise ValueError("Camera heading normalizer difference set changed")
    return raw, bindings


def assemble_owner(root, output, compact, rows, fields, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    patch_file = owner_dir / "retail-word-patches.csv"
    harness.write_patches(patch_file, fields, rows)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(emit_plain_owner(
        compact, root / ASM, word_patches_path=patch_file,
        filename=FILENAME))
    obj = owner_dir / (FILENAME + ".c.o")
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly)], check=True, capture_output=True)
    return obj


def routing_evidence(root):
    image = (Path(root) / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    raw_hits = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    calls = [0xEBE08, 0xF5404, 0x135504, 0x14FA94]
    collisions = [0x32E84, 0x150424, 0x1504D8]
    if raw_hits != [0x32E84, *calls, 0x150424, 0x1504D8] or pointers:
        raise ValueError("Camera heading normalizer routing evidence changed")
    return {
        "direct_jal_calls": [hex(offset) for offset in calls],
        "aligned_pointer_literals": [],
        "same_word_non_calls": [hex(offset) for offset in collisions],
        "callers": ["func_150BE83C", "func_150C7E08",
                    "func_15107FE0", "func_15122440"],
        "abi": "one camera pointer; void heading update",
    }


def prepare(root, output=None):
    replacements = {
        "candidate": candidate, "FUNCTION": FUNCTION, "FILENAME": FILENAME,
        "SOURCE": SOURCE, "OBJECT": OBJECT, "ASM": ASM, "GUARDS": GUARDS,
        "ELF": ELF, "LINKER": LINKER, "ROM_IMAGE": ROM_IMAGE, "BUILD": BUILD,
        "ENTRY": ENTRY, "ROM": ROM, "WORDS": WORDS, "SIZE": SIZE,
        "NATURAL_FRAME": NATURAL_FRAME, "RETAIL_FRAME": RETAIL_FRAME,
        "RAW_SHA256": RAW_SHA256, "RETAIL_SHA256": RETAIL_SHA256,
        "BINDINGS": BINDINGS, "PATCH_ROWS": PATCH_ROWS,
        "complete_row": complete_row, "source_states": source_states,
        "registry_evidence": routing_evidence,
        "checked_candidate": checked_candidate, "assemble_owner": assemble_owner,
        "function_blob": function_blob, "retail_bytes": retail_bytes,
        "retail_object_bytes": retail_object_bytes,
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
            report["guards"] != len(PATCH_ROWS) or
            report["natural_positional_differences"] != len(PATCH_ROWS)):
        raise ValueError("Camera heading normalizer qualification report changed")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
