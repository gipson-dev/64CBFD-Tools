"""Qualify func_15013C38's record mode callback directly from C."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.check_game_data_layout import audit_layout
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.game_four_head_lookup_match import diagnostics, payload
from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span)
from tools.match_progress import load_elf_functions
from tools.pad_c_object import emit_padded_assembly
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = "func_15013C38"
FILENAME = "game_40490"
SOURCE = "conker/src/game_40490.c"
OBJECT = "conker/build/src/game_40490.c.o"
LAYOUT = "conker/retail_layout.us.txt"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-record-mode-callback-15013C38-match"
ENTRY, ROM, WORDS, FRAME = 0x15013C38, 0x410E8, 64, 0x18
SIZE = WORDS * 4
RAW_SHA256 = "34b2c0353824d08639866a1ada408cb75de972c80a6326015ab47a2947e387d8"
RETAIL_SHA256 = "174e01b00d44e45611c7a6f5c9dc0cb876bee4c8003600dae67a61407f21145d"
BINDINGS = {
    0x00C: [("R_MIPS_HI16", "D_800D2E4C")],
    0x01C: [("R_MIPS_LO16", "D_800D2E4C")],
    0x020: [("R_MIPS_HI16", "D_800BE9F0")],
    0x038: [("R_MIPS_LO16", "D_800BE9F0")],
    0x024: [("R_MIPS_HI16", "D_800C35EA")],
    0x050: [("R_MIPS_LO16", "D_800C35EA")],
    0x058: [("R_MIPS_HI16", "D_800C35E8")],
    0x064: [("R_MIPS_LO16", "D_800C35E8")],
    0x0A0: [("R_MIPS_HI16", "D_80082F28")],
    0x0A8: [("R_MIPS_LO16", "D_80082F28")],
    0x0D4: [("R_MIPS_HI16", "D_80096650")],
    0x0D8: [("R_MIPS_LO16", "D_80096650")],
}
MARKER = (
    "/* Non-matching C placeholders for asm/nonmatchings/game_40490/"
    "func_15013C38.s. */")
ORIGINAL = "s32 func_15013C38() {\n    return 0;\n}"
OLD_PROTOTYPE = "s32 func_15013C38();\n"
DECLARATIONS = """typedef void (*RecordModeCallback40490)(u8 *, f32);
extern RecordModeCallback40490 D_80082F28[];
extern f32 D_80096650;
extern u8 D_800C35E8;
"""
SELECTED = """/* Dispatch the record's scaled value unless the current mode suppresses it. */
s32 func_15013C38(u8 *record) {
    RecordModeCallback40490 callback;
    s32 mode;
    f32 scaled;

    record[0x16] |= 4;
    mode = *(s32 *)(record + 0x18);
    if ((((u8 *)D_800D2E4C)[0x11] & 4) && D_800BE9F0 == 0x13) {
        return 1;
    }
    if (D_800C35EA == 1 &&
        (D_800C35E8 == 0xF || D_800C35E8 == 0x10 ||
         D_800C35E8 == 0x11)) {
        return 1;
    }
    if (mode >= 6) {
        return 1;
    }
    callback = D_80082F28[mode];
    if (callback != NULL) {
        scaled = (f32)*(u32 *)(record + 0x1C) * D_80096650;
        callback(record, scaled);
    }
    return 1;
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    anchor = "extern RecordCallback40490 D_80082E30[];\n"
    old_block = MARKER + "\n" + ORIGINAL
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    if body == ORIGINAL:
        if live.count(DECLARATIONS) or live.count(SELECTED):
            raise ValueError("Record mode predecessor preamble changed")
        if live.count(anchor) != 1 or live.count(OLD_PROTOTYPE) != 1:
            raise ValueError("Record mode predecessor anchors changed")
        qualified = live.replace(anchor, anchor + DECLARATIONS, 1)
        qualified = qualified.replace(OLD_PROTOTYPE, "", 1)
        if qualified.count(old_block) != 1:
            raise ValueError("Record mode predecessor block changed")
        qualified = qualified.replace(old_block, SELECTED, 1)
        return live, qualified, False
    if body == SELECTED.split("\n", 1)[1]:
        if live.count(DECLARATIONS) != 1 or live.count(SELECTED) != 1:
            raise ValueError("Installed record mode source changed")
        predecessor = live.replace(DECLARATIONS, "", 1)
        predecessor = predecessor.replace(anchor, anchor + OLD_PROTOTYPE, 1)
        if predecessor.count(SELECTED) != 1:
            raise ValueError("Installed record mode block changed")
        predecessor = predecessor.replace(SELECTED, old_block, 1)
        return predecessor, live, True
    raise ValueError("Record mode source state changed")


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Record mode retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    for offset in BINDINGS:
        word = struct.unpack_from(">I", data, offset)[0] & 0xFFFF0000
        struct.pack_into(">I", data, offset, word)
    return bytes(data)


def checked_candidate(obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Record mode natural candidate changed")
    if bindings != BINDINGS:
        raise ValueError("Record mode bindings changed")
    words = struct.unpack(">%dI" % WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Record mode frame changed")
    return raw, bindings


def assemble_owner(root, output, compact, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(emit_padded_assembly(
        compact, root / LAYOUT, word_patches_path=root / GUARDS,
        filename=FILENAME))
    obj = owner_dir / (FILENAME + ".c.o")
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly)], check=True, capture_output=True)
    return obj


def link_image(root, output, owner, label):
    old = OBJECT.replace("conker/", "")
    new = str(owner.relative_to(root / "conker")).replace("\\", "/")
    linker = (root / LINKER).read_text()
    if linker.count(old) != 1:
        raise ValueError("Record mode linker owner reference changed")
    link_dir = output / label
    link_dir.mkdir(parents=True, exist_ok=True)
    script = link_dir / "conker.ld"
    script.write_text(linker.replace(old, new))
    elf = link_dir / "conker.us.elf"
    subprocess.run([
        "mips-linux-gnu-ld", "-T", str(script.relative_to(root / "conker")),
        "-T", "undefined_syms.us.txt", "-T", "undefined_funcs.us.txt",
        "-T", "undefined_syms_auto.txt", "-T", "undefined_funcs_auto.txt",
        "--no-check-sections", "--no-warn-mismatch", "-o",
        str(elf.relative_to(root / "conker"))], cwd=root / "conker",
        check=True, capture_output=True)
    return elf


def expected_image(predecessor, retail):
    result = bytearray(predecessor)
    offset = elf_slot_offset(predecessor, ENTRY, SIZE)
    result[offset:offset + SIZE] = retail
    rows = [(at, fields) for at, name, fields, _ in symbol_rows(predecessor)
            if name == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 12):
        raise ValueError("Record mode predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0][0] + 8, SIZE)
    return bytes(result)


def function_blob(obj, name):
    text, functions, relocations = parse_object(obj)
    info = functions[name]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {offset - start: rows for offset, rows in relocations.items()
                if start <= offset < end}
    return text[start:end], bindings


def prepare(root, output=None):
    root = Path(root).resolve()
    output = Path(output or root / BUILD).resolve()
    output.mkdir(parents=True, exist_ok=True)
    predecessor_source, qualified_source, installed = source_states(
        (root / SOURCE).read_text())
    predecessor_compact, before_diagnostics = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after_diagnostics = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostics(before_diagnostics) != diagnostics(after_diagnostics):
        raise ValueError("Record mode owner diagnostics changed")
    raw, bindings = checked_candidate(qualified_compact)
    retail = retail_bytes(root)
    retail_object = retail_object_bytes(root)
    if raw != retail_object:
        raise ValueError("Record mode natural C does not reproduce retail")

    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, "qualified-owner")
    expected_owner = qualified_owner if installed else predecessor_owner
    if expected_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Record mode selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (retail_object, bindings):
        raise ValueError("Record mode qualified owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Record mode normalized pools changed")

    predecessor_elf = link_image(
        root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(
        root, output, qualified_owner, "qualified-image")
    expected_elf = qualified_elf if installed else predecessor_elf
    if expected_elf.read_bytes() != (root / ELF).read_bytes():
        raise ValueError("Record mode selected image differs from production")
    if qualified_elf.read_bytes() != expected_image(
            predecessor_elf.read_bytes(), retail):
        raise ValueError("Record mode qualified image differs from literal prediction")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Record mode full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Record mode protected data changed")

    (output / "proposed-owner.c").write_text(qualified_source)
    report = {
        "function": FUNCTION,
        "installed": installed,
        "words": WORDS,
        "slot_words": WORDS,
        "frame": FRAME,
        "natural_differences": 0,
        "guards": 0,
        "relocations": len(bindings),
        "neighbors": neighbors,
        "raw_sha256": digest(raw),
        "retail_sha256": digest(retail),
        "qualified_owner_sha256": digest(qualified_owner.read_bytes()),
        "predecessor_elf_sha256": digest(predecessor_elf.read_bytes()),
        "qualified_elf_sha256": digest(qualified_elf.read_bytes()),
        "functions": len(new),
        "changed_bodies": changed,
        "all_addresses_fixed": True,
        "strict_exclusions": 0,
        "game_data": data,
    }
    (output / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return report, predecessor_owner, qualified_owner, predecessor_elf, qualified_elf


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)[0], indent=2))
