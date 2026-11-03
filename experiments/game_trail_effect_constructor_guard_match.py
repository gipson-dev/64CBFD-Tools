"""Qualify func_151DA6F8's restored constructor as guarded exact C."""

import csv
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_trail_effect_constructor_candidates as candidate
from tools.match_progress import load_elf_functions


FUNCTION = "func_151DA6F8"
FILENAME = "game_2062D0"
SOURCE = "conker/src/game_2062D0.c"
OBJECT = "conker/build/src/game_2062D0.c.o"
ASM = "conker/asm/nonmatchings/game_2062D0/func_151DA6F8.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
LAYOUT_FILE = "conker/retail_layout.us.txt"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-trail-effect-constructor-151DA6F8-match"
ENTRY, ROM, WORDS = 0x151DA6F8, 0x207BA8, 144
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0xD0
RAW_SHA256 = "ee54d337ae9f2e82885f8f850fd5fa4deb6b864720e55f6c96e4c44508248df2"
RETAIL_SHA256 = "8243c037cb292d533731712cb67e82e1e559c3bae1911b22fa03734cadf99811"
NATURAL_BINDINGS = {
    0x080: [("R_MIPS_HI16", "D_800AB404")],
    0x090: [("R_MIPS_HI16", "D_800AB330")],
    0x0AC: [("R_MIPS_LO16", "D_800AB404")],
    0x0B0: [("R_MIPS_HI16", "D_800AB498")],
    0x0B4: [("R_MIPS_LO16", "D_800AB498")],
    0x0CC: [("R_MIPS_LO16", "D_800AB330")],
    0x0D0: [("R_MIPS_HI16", "D_800AB3F4")],
    0x0F8: [("R_MIPS_LO16", "D_800AB3F4")],
    0x200: [("R_MIPS_26", "func_15147DA0")],
    0x220: [("R_MIPS_26", "memcpy")],
}
BINDINGS = {
    0x080: [("R_MIPS_HI16", "D_800AB404")],
    0x090: [("R_MIPS_HI16", "D_800AB330")],
    0x094: [("R_MIPS_HI16", "D_800AB3F4")],
    0x0AC: [("R_MIPS_LO16", "D_800AB404")],
    0x0B0: [("R_MIPS_HI16", "D_800AB498")],
    0x0B4: [("R_MIPS_LO16", "D_800AB498")],
    0x0CC: [("R_MIPS_LO16", "D_800AB330")],
    0x0F4: [("R_MIPS_LO16", "D_800AB3F4")],
    0x200: [("R_MIPS_26", "func_15147DA0")],
    0x220: [("R_MIPS_26", "memcpy")],
}


def row(offset, expected, replacement, note, expected_relocations="-",
        replacement_relocations="-"):
    return dict(offset=offset, expected=expected, replacement=replacement,
                expected_relocations=expected_relocations,
                replacement_relocations=replacement_relocations, note=note)


TABLE = "Normalize constructor table and register allocation schedule"
LAYOUT = "Normalize constructor payload, render, and stack layout"
OUTGOING = "Normalize constructor outgoing argument allocation"
RESULT = "Normalize constructor result and payload-copy schedule"
PATCH_ROWS = (
    row("0x094", "0x01E67821", "0x3C190000", TABLE,
        replacement_relocations="R_MIPS_HI16:D_800AB3F4"),
    row("0x0A0", "0x240D00FF", "0x01E67821", TABLE),
    row("0x0A4", "0x27A50090", "0x0326C821", TABLE),
    row("0x0D0", "0x3C0A0000", "0x00001025", TABLE,
        expected_relocations="R_MIPS_HI16:D_800AB3F4"),
    row("0x0D4", "0x00001025", "0x240A00FF", TABLE),
    row("0x0DC", "0x01465021", "0x27A50090", TABLE),
    row("0x0EC", "0x03035825", "0x03032025", TABLE),
    row("0x0F0", "0x356C0040", "0x93B800EF", TABLE),
    row("0x0F4", "0x93AB00EF", "0x93390000", TABLE,
        replacement_relocations="R_MIPS_LO16:D_800AB3F4"),
    row("0x0F8", "0x914A0000", "0x93AD00E3", TABLE,
        expected_relocations="R_MIPS_LO16:D_800AB3F4"),
    row("0x0FC", "0x93AE00E3", "0x87AE0106", TABLE),
    row("0x100", "0x87AF0106", "0x87AF010A", TABLE),
    row("0x104", "0x87B8010A", "0x348B0040", TABLE),
    row("0x108", "0x319900FF", "0x316C00FF", TABLE),
    row("0x10C", "0x03202025", "0x01802025", TABLE),
    row("0x110", "0xA3AD00AA", "0xA3AA00AA", TABLE),
    row("0x114", "0xA3AA00A9", "0xA3B900A9", TABLE),
    row("0x118", "0xA3AE00AB", "0xA3AD00AB", TABLE),
    row("0x11C", "0xA7AF00AC", "0xA7AE00AC", TABLE),
    row("0x120", "0x11600006", "0x13000006", TABLE),
    row("0x124", "0xA7B800AE", "0xA7AF00AE", TABLE),
    row("0x128", "0x372C0003", "0x358B0003", TABLE),
    row("0x130", "0xA3AC00A8", "0xA3AB00A8", TABLE),
    row("0x148", "0x93B900FB", "0xC7A800F0", LAYOUT),
    row("0x14C", "0xC7A800F0", "0xC7AA00F4", LAYOUT),
    row("0x150", "0xC7AA00F4", "0xA3A6008C", LAYOUT),
    row("0x154", "0x3C0A0022", "0xE7A80084", LAYOUT),
    row("0x158", "0x3C0D0005", "0xE7AA0088", LAYOUT),
    row("0x15C", "0x354A0005", "0x93AC00FB", LAYOUT),
    row("0x160", "0x35AD0600", "0x3C190022", LAYOUT),
    row("0x164", "0x240E0003", "0x3C0A0005", LAYOUT),
    row("0x168", "0x240F0046", "0x37390005", LAYOUT),
    row("0x16C", "0x24180080", "0x354A0600", LAYOUT),
    row("0x170", "0x240B0020", "0x240D0003", LAYOUT),
    row("0x174", "0x240C000C", "0x240E0046", LAYOUT),
    row("0x178", "0xA3A6008C", "0x240F0080", LAYOUT),
    row("0x17C", "0xAFA00064", "0x24180020", LAYOUT),
    row("0x180", "0xAFAA0068", "0x240B000C", LAYOUT),
    row("0x184", "0xAFAD006C", "0xAFA00054", LAYOUT),
    row("0x188", "0xAFAE0070", "0xAFB90058", LAYOUT),
    row("0x18C", "0xAFAF0074", "0xAFAA005C", LAYOUT),
    row("0x190", "0xAFB80078", "0xAFAD0060", LAYOUT),
    row("0x194", "0xAFAB007C", "0xAFAE0064", LAYOUT),
    row("0x198", "0xA3A00080", "0xAFAF0068", LAYOUT),
    row("0x19C", "0xA3AC0081", "0xAFB8006C", LAYOUT),
    row("0x1A0", "0xE7A80084", "0xA3A00070", LAYOUT),
    row("0x1A4", "0x13200004", "0x11800004", LAYOUT),
    row("0x1A8", "0xE7AA0088", "0xA3AB0071", LAYOUT),
    row("0x1C0", "0x8FAD0100", "0x8FAA0100", LAYOUT),
    row("0x1C4", "0x93AE0113", "0x93AD0113", LAYOUT),
    row("0x1C8", "0x8FAF0114", "0x8FAE0114", LAYOUT),
    row("0x1CC", "0x27AA0064", "0x27B90054", LAYOUT),
    row("0x1D0", "0xAFAA002C", "0xAFB9002C", LAYOUT),
    row("0x1F8", "0xAFAD0030", "0xAFAA0030", OUTGOING),
    row("0x1FC", "0xAFAE0034", "0xAFAD0034", OUTGOING),
    row("0x204", "0xAFAF0038", "0xAFAE0038", OUTGOING),
    row("0x208", "0x10400008", "0x00401825", RESULT),
    row("0x20C", "0x00401825", "0x10400007", RESULT),
    row("0x210", "0x8C440098", "0x27A50084", RESULT),
    row("0x214", "0xAFA200CC", "0x8C640098", RESULT),
    row("0x218", "0x27A50084", "0xAFA300CC", RESULT),
)


def complete_row(value):
    return {
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": value["offset"],
        "expected": value["expected"],
        "replacement": value["replacement"],
        "expected_relocations": value["expected_relocations"],
        "replacement_relocations": value["replacement_relocations"],
        "note": value["note"],
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }


def source_states(live):
    if live.count(candidate.SELECTED) != 1:
        raise ValueError("Installed trail-effect constructor source changed")
    root = Path(__file__).resolve().parents[2]
    with (root / GUARDS).open(newline="") as stream:
        target_rows = [value for value in csv.DictReader(stream)
                       if value["filename"] == FILENAME and
                       value["function"] == FUNCTION]
    return live, live, bool(target_rows)


def checked_candidate(root, obj):
    raw, bindings = harness.function_blob(obj)
    if len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        raise ValueError("Trail-effect constructor natural candidate changed")
    if ((-struct.unpack_from(">I", raw)[0]) & 0xFFFF) != NATURAL_FRAME:
        raise ValueError("Trail-effect constructor natural frame changed")
    if bindings != NATURAL_BINDINGS:
        raise ValueError("Trail-effect constructor natural bindings changed")
    expected = harness.retail_object_bytes(root)
    differences = [offset for offset in range(0, SIZE, 4)
                   if raw[offset:offset + 4] != expected[offset:offset + 4]]
    wanted = [int(value["offset"], 0) for value in PATCH_ROWS]
    if differences != wanted:
        raise ValueError("Trail-effect constructor natural difference set changed")
    return raw, bindings


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    pattern_offsets = [index * 4 for index, value in enumerate(words) if value == jal]
    pointers = [index * 4 for index, value in enumerate(words) if value == ENTRY]
    expected_patterns = [0xE9660, 0xE9DD8, 0x109CF4, 0x1636C0, 0x164864,
                         0x181378, 0x181618, 0x1BFA0C, 0x1DC138, 0x1DD64C,
                         0x1F2EE0]
    functions, _, addresses = load_elf_functions(
        str(root / ELF), "mips-linux-gnu-objdump")
    callers = [(name, addresses[name] + index * 4)
               for name, body in functions.items()
               for index, value in enumerate(body) if value == jal]
    expected_callers = [
        ("func_15135DD0", 0x15136210),
        ("func_15136F50", 0x151373B4),
        ("func_15153CCC", 0x15153EC8),
        ("func_15153F18", 0x15154168),
        ("func_151C577C", 0x151C5A30),
    ]
    if pattern_offsets != expected_patterns or pointers or callers != expected_callers:
        raise ValueError("Trail-effect constructor caller evidence changed")
    return {
        "direct_callers": [{"function": name, "call": hex(address)}
                           for name, address in callers],
        "rom_jal_pattern_offsets": [hex(value) for value in pattern_offsets],
        "aligned_pointer_literals": [],
        "abi": "18 O32 arguments; returns the created effect pointer or null",
    }


def assemble_owner(root, output, compact, rows, fields, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    patch_file = owner_dir / "retail-word-patches.csv"
    harness.write_patches(patch_file, fields, rows)
    assembly = owner_dir / (FILENAME + ".c.s")
    subprocess.run([
        sys.executable, str(root / "tools/pad_c_object.py"), str(compact),
        str(root / LAYOUT_FILE), FILENAME, str(assembly),
        "--word-patches", str(patch_file),
    ], check=True, capture_output=True)
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
        "REGISTRY": SOURCE,
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
        "checked_candidate": checked_candidate,
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
    guards_installed = report["source_installed"]
    report["source_installed"] = True
    report["guards_installed"] = guards_installed
    if (report["raw_sha256"] != RAW_SHA256 or
            report["retail_sha256"] != RETAIL_SHA256 or
            report["guards"] != len(PATCH_ROWS) or
            report["changed_bodies"] != [FUNCTION]):
        raise ValueError("Trail-effect constructor report changed")
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))
