"""Qualify func_1504A620's natural-logarithm approximation as guarded C."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_logarithm_approximation_candidates as candidate
from tools.pad_generated_object import parse_object


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game_77AD0.c.o"
ASM = "conker/retail_layout.us.txt"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/778B0.s"
BUILD = "conker/build/game-logarithm-approximation-1504A620-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_SIZE = 65 * 4
NATURAL_FRAME = RETAIL_FRAME = 0
RAW_SHA256 = "6773ad789c97dbd36e75e2748d30735eccb25871d945cd3797a6edc7d16e0cbb"
RETAIL_SHA256 = "5ea84c1d30ac4dba44ae3ef6b79c082ebd45000ace9a0c7a4d369a2c708bb40c"
NOTE = "Normalize logarithm approximation compiler allocation and schedule"
PREDECESSOR_MARKER = (
    "// NON-MATCHING: ported from ects_proto (ECTS ROM build), "
    "not yet byte-verified for us\n"
    "f32 func_1504A620(f32 arg0) {"
)
QUALIFIED_MARKER = (
    "// MATCHING: semantic natural-logarithm approximation; retail allocation "
    "and scheduling use checked guards.\n"
    "f32 func_1504A620(f32 arg0) {"
)
NATURAL_BINDINGS = {
    0x048: [("R_MIPS_HI16", "D_800990B0")],
    0x054: [("R_MIPS_LO16", "D_800990B0")],
    0x084: [("R_MIPS_HI16", "D_800990B4")],
    0x098: [("R_MIPS_LO16", "D_800990B4")],
}
RETAIL_BINDINGS = {
    0x048: [("R_MIPS_HI16", "D_800990B0")],
    0x05C: [("R_MIPS_LO16", "D_800990B0")],
    0x084: [("R_MIPS_HI16", "D_800990B4")],
    0x088: [("R_MIPS_LO16", "D_800990B4")],
}


# Offsets are in the unpadded 65-word compiler body. Insertions move subsequent
# output words, which is why the final relocation offsets differ above.
_PATCH_DATA = (
    ("0x000", "0x44807000", "0x44800000", "-", "-", ""),
    ("0x008", "0x460E603C", "0x4600603C", "-", "-", ""),
    ("0x010", "0x45020004", "0x45020005", "-", "-", ""),
    ("0x014", "0x460E6032", "0x46006032", "-", "-", "0x44800000"),
    ("0x01C", "0x46007006", "0x00000000", "-", "-", ""),
    ("0x020", "0x460E6032", "0x46006032", "-", "-", ""),
    ("0x028", "0x45020004", "0x45020005", "-", "-", ""),
    ("0x02C", "0x44818000", "0x44817000", "-", "-", "0x44800000"),
    ("0x034", "0x46007006", "0x00000000", "-", "-", ""),
    ("0x038", "0x44818000", "0x44817000", "-", "-", ""),
    ("0x03C", "0x46006006", "0x46000086", "-", "-", ""),
    ("0x040", "0x46007086", "0x3C010000", "-", "R_MIPS_HI16:D_800990B0", ""),
    ("0x044", "0x460C803E", "0x460C703E", "-", "-", ""),
    ("0x048", "0x3C010000", "0x00000000", "R_MIPS_HI16:D_800990B0", "-", ""),
    ("0x04C", "0x4502000C", "0x4500000B", "-", "-", ""),
    ("0x050", "0x3C013F80", "0x00000000", "-", "-", ""),
    ("0x054", "0xC42C0000", "0xC4300000", "R_MIPS_LO16:D_800990B0", "R_MIPS_LO16:D_800990B0", ""),
    ("0x05C", "0x44817000", "0x44810000", "-", "-", ""),
    ("0x064", "0x460E0002", "0x46006302", "-", "-", ""),
    ("0x068", "0x460C1080", "0x46101080", "-", "-", ""),
    ("0x06C", "0x4600803E", "0x460C703E", "-", "-", ""),
    ("0x07C", "0x3C013F80", "0x3C010000", "-", "R_MIPS_HI16:D_800990B4", ""),
    ("0x080", "0x44819000", "0xC4300000", "-", "R_MIPS_LO16:D_800990B4", ""),
    ("0x084", "0x3C010000", "0x3C013F80", "R_MIPS_HI16:D_800990B4", "-", ""),
    ("0x088", "0x4612003C", "0x44819000", "-", "-", ""),
    ("0x090", "0x45020009", "0x4612603C", "-", "-", ""),
    ("0x094", "0x46120101", "0x00000000", "-", "-", ""),
    ("0x098", "0xC42C0000", "0x45020008", "R_MIPS_LO16:D_800990B4", "-", ""),
    ("0x09C", "0x46000000", "0x46126101", "-", "-", ""),
    ("0x0A0", "0x460C1081", "0x460C6300", "-", "-", ""),
    ("0x0A4", "0x4612003C", "0x46101081", "-", "-", "0x4612603C"),
    ("0x0B0", "0x46000000", "0x460C6300", "-", "-", ""),
    ("0x0B4", "0x46120101", "0x46126101", "-", "-", ""),
    ("0x0BC", "0x46120180", "0x46126180", "-", "-", ""),
    ("0x0C0", "0x46062303", "0x46062383", "-", "-", ""),
    ("0x0C4", "0x460C6382", "0x460E7402", "-", "-", ""),
    ("0x0C8", "0x460C6400", "0x460E7000", "-", "-", ""),
    ("0x0D0", "0x46001006", "0x46001306", "-", "-", ""),
    ("0x0DC", "0x460A8103", "0x460A0103", "-", "-", ""),
    ("0x0E0", "0x460E8402", "0x46100002", "-", "-", ""),
    ("0x0E8", "0x46001032", "0x460C1032", "-", "-", ""),
)


PATCH_ROWS = tuple({
    "offset": offset,
    "expected": expected,
    "replacement": replacement,
    "expected_relocations": expected_relocations,
    "replacement_relocations": replacement_relocations,
    "note": NOTE,
    "insert_after": insert_after,
    "insert_after_relocations": "-" if insert_after else "",
    "omit": "false",
} for (offset, expected, replacement, expected_relocations,
       replacement_relocations, insert_after) in _PATCH_DATA)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def complete_row(row):
    return dict(row, filename=FILENAME, function=FUNCTION)


def source_states(live):
    if live.count(PREDECESSOR_MARKER) == 1:
        if QUALIFIED_MARKER in live:
            raise ValueError("Logarithm approximation predecessor marker changed")
        return live, live.replace(PREDECESSOR_MARKER, QUALIFIED_MARKER, 1), False
    if live.count(QUALIFIED_MARKER) == 1:
        if PREDECESSOR_MARKER in live:
            raise ValueError("Installed logarithm approximation marker changed")
        return live.replace(QUALIFIED_MARKER, PREDECESSOR_MARKER, 1), live, True
    raise ValueError("Logarithm approximation source state changed")


def function_blob(obj):
    text, functions, relocations = parse_object(obj)
    info = functions[FUNCTION]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {
        offset - start: rows for offset, rows in relocations.items()
        if start <= offset < end
    }
    return text[start:end], bindings


def retail_bytes(root):
    data = (Path(root) / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Logarithm approximation retail bytes changed")
    return data


def retail_object_bytes(root):
    result = bytearray(retail_bytes(root))
    for offset, rows in RETAIL_BINDINGS.items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", result, offset,
                         struct.unpack_from(">I", result, offset)[0] & mask)
    return bytes(result)


def checked_payload(root, raw, bindings):
    if len(raw) != NATURAL_SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Logarithm approximation natural candidate changed")
    if bindings != NATURAL_BINDINGS:
        raise ValueError("Logarithm approximation natural bindings changed")
    return raw, bindings


def checked_candidate(root, obj):
    return checked_payload(root, *function_blob(obj))


def assemble_owner(root, output, compact, rows, fields, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    patch_file = owner_dir / "retail-word-patches.csv"
    harness.write_patches(patch_file, fields, rows)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(pad_c_object.emit_padded_assembly(
        compact, root / ASM, FILENAME, word_patches_path=patch_file))
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
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    caller = struct.unpack_from(">8I", image, 0x77990)
    if calls != [0x77994] or pointers or caller != (
            0x4600A306, jal, 0xE7AE0024, 0xC7AE0024,
            0x460E0302, 0x0D4128AC, 0x00000000, 0x1000002F):
        raise ValueError("Logarithm approximation retail caller contract changed")
    assembly = (Path(root) / REGISTRY).read_text()
    call_text = (
        "mov.s      $f12, $f20\n"
        "    /* 77994 1504A4E4 0D412988 */  jal        func_1504A620\n"
        "    /* 77998 1504A4E8 E7AE0024 */   swc1      $f14, 0x24($sp)\n"
        "    /* 7799C 1504A4EC C7AE0024 */  lwc1       $f14, 0x24($sp)\n"
        "    /* 779A0 1504A4F0 460E0302 */  mul.s      $f12, $f0, $f14"
    )
    if call_text not in assembly:
        raise ValueError("Logarithm approximation assembly caller evidence changed")
    return {
        "direct_jal_calls": ["0x77994"],
        "aligned_pointer_literals": [],
        "caller": "func_1504A400 (retail raw assembly)",
        "current_linked_caller": "zero-return placeholder; no live-call claim",
        "abi": "binary32 input in f12; binary32 result in f0 is multiplied by saved f14",
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
        "BINDINGS": NATURAL_BINDINGS,
        "RETAIL_BINDINGS": RETAIL_BINDINGS,
        "PATCH_ROWS": PATCH_ROWS,
        "complete_row": complete_row,
        "source_states": source_states,
        "registry_evidence": routing_evidence,
        "checked_candidate": checked_candidate,
        "assemble_owner": assemble_owner,
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
            report["guards"] != 41 or
            report["natural_positional_differences"] != 41):
        raise ValueError("Logarithm approximation qualification report changed")
    report["compiler_words"] = 65
    report["insertions"] = 3
    report["omissions"] = 0
    report["retail_relocations"] = len(RETAIL_BINDINGS)
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
