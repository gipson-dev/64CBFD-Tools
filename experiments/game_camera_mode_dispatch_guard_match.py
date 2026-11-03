"""Qualify func_151283B8's sparse camera-mode switch as guarded C."""

from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.check_game_data_layout import audit_layout
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span)
from tools.match_progress import load_elf_functions
from tools.pad_c_object import emit_padded_assembly
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = "func_151283B8"
FILENAME = "game_14FF90"
SOURCE = "conker/src/game_14FF90.c"
OBJECT = "conker/build/src/game_14FF90.c.o"
LAYOUT = "conker/retail_layout.us.txt"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-camera-mode-dispatch-151283B8-guard-match"
ENTRY, ROM, WORDS, FRAME = 0x151283B8, 0x155868, 67, 0x18
SIZE = WORDS * 4
RAW_SHA256 = "77549146a4d8ecae3430bed0d9a184a571fffcf850a1245c17de7decf8714fcb"
RETAIL_SHA256 = "89c4bd3301bca8b8117089b8d330743444933b89c339b91d3a96473673b83fbf"
CALL_BINDINGS = {
    0x074: [("R_MIPS_26", "func_15122440")],
    0x084: [("R_MIPS_26", "func_15129934")],
    0x094: [("R_MIPS_26", "func_15122980")],
    0x0A4: [("R_MIPS_26", "func_15121C80")],
    0x0B4: [("R_MIPS_26", "func_151220D0")],
    0x0C4: [("R_MIPS_26", "func_15122170")],
    0x0D4: [("R_MIPS_26", "func_15122980")],
    0x0E4: [("R_MIPS_26", "func_15120158")],
    0x0F4: [("R_MIPS_26", "func_1512DEA4")],
}
OLD_DECLARATION = "s32 func_151283B8(s32 arg0);"
NEW_DECLARATION = "void func_151283B8(struct108 *camera);"
HELPER_DECLARATIONS = """void func_15120158(struct108 *);
s32 func_15121C80();
void func_151220D0(struct108 *);
void func_15122170(struct108 *);
void func_15122440(struct108 *);
void func_15122980(struct108 *);
void func_15129934(struct108 *);
void func_1512DEA4(struct108 *);
"""
ORIGINAL = "s32 func_151283B8(s32 arg0) {\n    return 0;\n}"
SELECTED = """/* Dispatch the camera update selected by its sparse mode word. */
void func_151283B8(struct108 *camera) {
    switch (camera->unk2C) {
    case 0x80:
        func_15122440(camera);
        break;
    case 0x40:
        func_15129934(camera);
        break;
    case 1:
        func_15122980(camera);
        break;
    case 8:
        func_15121C80(camera, 0);
        break;
    case 2:
        func_151220D0(camera);
        break;
    case 0x400:
        func_15122170(camera);
        break;
    case 0x800:
        func_15122980(camera);
        break;
    case 0x100:
        func_15120158(camera);
        break;
    case 0x800000:
        func_1512DEA4(camera);
        break;
    case 0x2000:
        break;
    }
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostic_counts(text):
    rows = []
    for line in text.splitlines():
        match = re.match(r"cfe: Warning (\d+): .*?: (.*)", line)
        if match:
            rows.append((match.group(1), match.group(2)))
        elif line.startswith("cfe:") and "Warning" not in line:
            raise ValueError("Unexpected camera-dispatch diagnostic: " + line)
    return Counter(rows)


def source_states(live):
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    if body == ORIGINAL:
        if live.count(OLD_DECLARATION) != 1:
            raise ValueError("Camera dispatcher predecessor declaration changed")
        predecessor = live
        qualified = live[:start] + SELECTED + live[end:]
        qualified = qualified.replace(OLD_DECLARATION, NEW_DECLARATION, 1)
        marker = "/* End generated placeholder declarations. */\n"
        if qualified.count(marker) != 1:
            raise ValueError("Camera dispatcher declaration marker changed")
        qualified = qualified.replace(
            marker, marker + "\n" + HELPER_DECLARATIONS, 1)
        qualified = qualified.replace(
            "/* Non-matching C placeholders for asm/nonmatchings/game_14FF90/"
            "func_151283B8.s. */\n", "", 1)
        return predecessor, qualified, False
    installed = SELECTED.split("\n", 1)[1]
    if body == installed:
        if live.count(NEW_DECLARATION) != 1:
            raise ValueError("Installed camera dispatcher declaration changed")
        qualified = live
        predecessor = live[:start] + ORIGINAL + live[end:]
        predecessor = predecessor.replace(NEW_DECLARATION, OLD_DECLARATION, 1)
        if predecessor.count(HELPER_DECLARATIONS) != 1:
            raise ValueError("Installed camera helper declarations changed")
        predecessor = predecessor.replace(HELPER_DECLARATIONS, "", 1)
        marker = ORIGINAL + "\n"
        predecessor = predecessor.replace(
            marker,
            "/* Non-matching C placeholders for asm/nonmatchings/game_14FF90/"
            "func_151283B8.s. */\n" + marker, 1)
        return predecessor, qualified, True
    raise ValueError("Camera dispatcher source state changed")


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Camera dispatcher retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    for offset in CALL_BINDINGS:
        struct.pack_into(">I", data, offset, 0x0C000000)
    return bytes(data)


def checked_candidate(obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Camera dispatcher natural candidate changed")
    if bindings != CALL_BINDINGS:
        raise ValueError("Camera dispatcher call bindings changed")
    words = struct.unpack(">%dI" % WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Camera dispatcher frame changed")
    return raw, bindings


def guard_row():
    return {
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": "0x0A8",
        "expected": "0x00002825",
        "replacement": "0x24050000",
        "expected_relocations": "-",
        "replacement_relocations": "-",
        "note": "Normalize zero second-argument instruction selection",
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }


def row_bytes(row):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=tuple(row), lineterminator="\n")
    writer.writerow(row)
    return stream.getvalue().encode("ascii")


def guard_states(live):
    with io.StringIO(live.decode(), newline="") as stream:
        rows = [row for row in csv.DictReader(stream)
                if row["function"] == FUNCTION]
    row = guard_row()
    suffix = row_bytes(row)
    if rows:
        if rows != [row] or not live.endswith(suffix):
            raise ValueError("Installed camera dispatcher guard differs")
        return live[:-len(suffix)], live, True
    if not live.endswith((b"\n", b"\r")):
        raise ValueError("Guard table has no terminating newline")
    return live, live + suffix, False


def assemble_owner(root, output, compact, guards, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / "game_14FF90.c.s"
    assembly.write_text(emit_padded_assembly(
        compact, root / LAYOUT, FILENAME, word_patches_path=guards))
    obj = owner_dir / "game_14FF90.c.o"
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
        raise ValueError("Camera dispatcher linker owner reference changed")
    link_dir = output / label
    link_dir.mkdir(parents=True, exist_ok=True)
    script = link_dir / "conker.ld"
    script.write_text(linker.replace(old, new))
    elf = link_dir / "conker.us.elf"
    map_path = link_dir / "conker.us.map"
    subprocess.run([
        "mips-linux-gnu-ld", "-T", str(script.relative_to(root / "conker")),
        "-Map", str(map_path.relative_to(root / "conker")), "-T",
        "undefined_syms.us.txt", "-T", "undefined_funcs.us.txt", "-T",
        "undefined_syms_auto.txt", "-T", "undefined_funcs_auto.txt",
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
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 16):
        raise ValueError("Camera dispatcher predecessor symbol extent changed")
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
    predecessor_source, qualified_source, source_installed = source_states(
        (root / SOURCE).read_text())
    predecessor_guards, qualified_guards, guards_installed = guard_states(
        (root / GUARDS).read_bytes())
    if source_installed != guards_installed:
        raise ValueError("Camera dispatcher source and guard states disagree")
    predecessor_guard_path = output / "predecessor-guards.csv"
    qualified_guard_path = output / "qualified-guards.csv"
    predecessor_guard_path.write_bytes(predecessor_guards)
    qualified_guard_path.write_bytes(qualified_guards)

    predecessor_compact, before_diagnostics = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after_diagnostics = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostic_counts(before_diagnostics) != diagnostic_counts(after_diagnostics):
        raise ValueError("Camera dispatcher owner diagnostics changed")
    raw, bindings = checked_candidate(qualified_compact)
    retail = retail_bytes(root)
    retail_object = retail_object_bytes(root)
    normalized = bytearray(raw)
    struct.pack_into(">I", normalized, 0xA8, 0x24050000)
    if bytes(normalized) != retail_object:
        raise ValueError("Camera dispatcher single guard does not reproduce retail")

    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_guard_path,
        "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, qualified_guard_path,
        "qualified-owner")
    production_owner = root / OBJECT
    expected_production_owner = (qualified_owner if source_installed
                                 else predecessor_owner)
    if expected_production_owner.read_bytes() != production_owner.read_bytes():
        raise ValueError("Camera dispatcher selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (retail_object, bindings):
        raise ValueError("Camera dispatcher qualified owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if not neighbors or normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Camera dispatcher owner neighbors or pools changed")

    predecessor_elf = link_image(root, output, predecessor_owner,
                                 "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner,
                               "qualified-image")
    current_elf = (root / ELF).read_bytes()
    expected_production_elf = qualified_elf if source_installed else predecessor_elf
    if expected_production_elf.read_bytes() != current_elf:
        raise ValueError("Camera dispatcher selected image differs from production")
    predicted = expected_image(predecessor_elf.read_bytes(), retail)
    if qualified_elf.read_bytes() != predicted:
        raise ValueError("Camera dispatcher qualified image differs from literal prediction")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Camera dispatcher full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Camera dispatcher protected data changed")

    (output / "proposed-owner.c").write_text(qualified_source)
    (output / "proposed-guard-row.json").write_text(
        json.dumps(guard_row(), indent=2) + "\n")
    report = {
        "function": FUNCTION,
        "installed": source_installed,
        "words": WORDS,
        "frame": FRAME,
        "natural_differences": 1,
        "guards": 1,
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
