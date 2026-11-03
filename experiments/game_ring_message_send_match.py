"""Qualify func_15043BB8's length-prefixed ring writer as direct C."""

from collections import Counter
import hashlib
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


FUNCTION = "func_15043BB8"
FILENAME = "game_70200"
SOURCE = "conker/src/game_70200.c"
HEADER = "conker/include/functions.h"
OBJECT = "conker/build/src/game_70200.c.o"
LAYOUT = "conker/retail_layout.us.txt"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-ring-message-send-15043BB8-match"
ENTRY, ROM, WORDS, FRAME = 0x15043BB8, 0x71068, 59, 0x28
SIZE = WORDS * 4
RAW_SHA256 = "db6a3f24d611a017f1fb1d1105d0f976ef2a7729512431b7951ad729b0490fad"
RETAIL_SHA256 = "643d92a8336b6c69082799e9b9314b74f80c3b812c85e0705b86a53c8323df92"
CALL_BINDINGS = {
    0x0AC: [("R_MIPS_26", "func_15043A20")],
    0x0C8: [("R_MIPS_26", "func_15043A20")],
}
OLD_PROTOTYPE = "void func_15043BB8(struct105* arg0, void *arg1, s32 arg2);"
NEW_PROTOTYPE = "s32 func_15043BB8(struct105 *queue, u8 *input, s32 length);"
ORIGINAL = "void func_15043BB8(struct105* arg0, void *arg1, s32 arg2) {\n}"
SELECTED = """/* Write one aligned length-prefixed message when the ring has room. */
s32 func_15043BB8(struct105 *queue, u8 *input, s32 length) {
    s32 cursor;

    if (length != 0 && input != 0) {
        length += 4;
        length = (length + 3) & ~3;
        cursor = queue->unkC;
        if (cursor < queue->unk8) {
            if (cursor + length >= queue->unk8) {
                return 1;
            }
        } else if (cursor + length - queue->unk4 >= queue->unk8) {
            return 1;
        }
        length -= 4;
        cursor = func_15043A20((u8 *)queue->unk0, queue->unk4, cursor,
                              (u8 *)&length, 4);
        cursor = func_15043A20((u8 *)queue->unk0, queue->unk4, cursor,
                              input, length);
        queue->unkC = cursor;
    }
    return 0;
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
            raise ValueError("Unexpected ring-writer diagnostic: " + line)
    return Counter(rows)


def source_states(live):
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    placeholder = ("/* Non-matching C placeholders for asm/nonmatchings/"
                   "game_70200/func_15043BB8.s. */\n")
    if body == ORIGINAL:
        qualified = live[:start] + SELECTED + live[end:]
        if qualified.count(placeholder) != 1:
            raise ValueError("Ring writer placeholder marker changed")
        return live, qualified.replace(placeholder, "", 1), False
    installed = SELECTED.split("\n", 1)[1]
    if body == installed:
        predecessor = live[:start] + ORIGINAL + live[end:]
        purpose = SELECTED.split("\n", 1)[0] + "\n"
        if predecessor.count(purpose) != 1:
            raise ValueError("Installed ring writer purpose comment changed")
        return predecessor.replace(purpose, placeholder, 1), live, True
    raise ValueError("Ring writer source state changed")


def header_states(live):
    old_count, new_count = live.count(OLD_PROTOTYPE), live.count(NEW_PROTOTYPE)
    if (old_count, new_count) == (1, 0):
        return live, live.replace(OLD_PROTOTYPE, NEW_PROTOTYPE, 1), False
    if (old_count, new_count) == (0, 1):
        return live.replace(NEW_PROTOTYPE, OLD_PROTOTYPE, 1), live, True
    raise ValueError("Ring writer public prototype state changed")


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Ring writer retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    for offset in CALL_BINDINGS:
        struct.pack_into(">I", data, offset, 0x0C000000)
    return bytes(data)


def checked_candidate(obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Ring writer natural candidate changed")
    if bindings != CALL_BINDINGS:
        raise ValueError("Ring writer call bindings changed")
    words = struct.unpack(">%dI" % WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Ring writer frame changed")
    return raw, bindings


def compile_state(root, output, source, header, label):
    (output / "functions.h").write_text(header)
    return compile_owner(root, output, source, label)


def assemble_owner(root, output, compact, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / "game_70200.c.s"
    assembly.write_text(emit_padded_assembly(
        compact, root / LAYOUT, FILENAME,
        word_patches_path=root / GUARDS))
    obj = owner_dir / "game_70200.c.o"
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
        raise ValueError("Ring writer linker owner reference changed")
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
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 20):
        raise ValueError("Ring writer predecessor symbol extent changed")
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
    predecessor_header, qualified_header, header_installed = header_states(
        (root / HEADER).read_text())
    if source_installed != header_installed:
        raise ValueError("Ring writer source and public prototype disagree")

    predecessor_compact, before_diagnostics = compile_state(
        root, output, predecessor_source, predecessor_header,
        "predecessor-compact")
    qualified_compact, after_diagnostics = compile_state(
        root, output, qualified_source, qualified_header,
        "qualified-compact")
    if diagnostic_counts(before_diagnostics) != diagnostic_counts(after_diagnostics):
        raise ValueError("Ring writer owner diagnostics changed")
    raw, bindings = checked_candidate(qualified_compact)
    retail = retail_bytes(root)
    retail_object = retail_object_bytes(root)
    if raw != retail_object:
        raise ValueError("Ring writer natural C does not reproduce retail")

    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, "qualified-owner")
    expected_owner = qualified_owner if source_installed else predecessor_owner
    if expected_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Ring writer selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (retail_object, bindings):
        raise ValueError("Ring writer qualified owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if neighbors != 15 or normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Ring writer owner neighbors or pools changed")

    predecessor_elf = link_image(
        root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(
        root, output, qualified_owner, "qualified-image")
    current_elf = (root / ELF).read_bytes()
    expected_elf = qualified_elf if source_installed else predecessor_elf
    if expected_elf.read_bytes() != current_elf:
        raise ValueError("Ring writer selected image differs from production")
    if qualified_elf.read_bytes() != expected_image(
            predecessor_elf.read_bytes(), retail):
        raise ValueError("Ring writer qualified image differs from literal prediction")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Ring writer full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Ring writer protected data changed")

    (output / "proposed-owner.c").write_text(qualified_source)
    (output / "proposed-functions.h").write_text(qualified_header)
    report = {
        "function": FUNCTION,
        "installed": source_installed,
        "words": WORDS,
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
