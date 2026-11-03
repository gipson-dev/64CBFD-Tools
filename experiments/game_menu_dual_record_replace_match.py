"""Qualify func_150B7560's fixed dual menu-record replacement."""

import csv
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.check_game_data_layout import audit_layout
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.experiments.game_four_head_lookup_match import diagnostics, payload
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = "func_150B7560"
FILENAME = "generated_E4070"
SOURCE = "conker/src/game/generated_E4070.c"
OBJECT = "conker/build/src/game/generated_E4070.c.o"
ASM = "conker/asm/E4070.s"
RODATA_SYMBOL = "jtbl_8009FD00_game"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-menu-dual-record-replace-150B7560-match"
ENTRY, ROM, WORDS, FRAME = 0x150B7560, 0xE4A10, 63, 0x58
SIZE = WORDS * 4
RAW_SHA256 = "5677e7783af303c4029a9647447893ca4e4ccf580dc9bac47e2cbd4d69d869ea"
RETAIL_SHA256 = "f4476a36e465c88b78cc9a8faab2b241bc75847e559d38b4cecec43ceb10c6a2"
RAW_BINDINGS = {
    0x008: [("R_MIPS_HI16", "D_800D9898")],
    0x00C: [("R_MIPS_LO16", "D_800D9898")],
    0x018: [("R_MIPS_26", "func_1516972C")],
    0x020: [("R_MIPS_HI16", "D_800D9898")],
    0x024: [("R_MIPS_LO16", "D_800D9898")],
    0x02C: [("R_MIPS_HI16", "D_800D98A4")],
    0x034: [("R_MIPS_LO16", "D_800D98A4")],
    0x048: [("R_MIPS_HI16", "D_800918DC")],
    0x054: [("R_MIPS_LO16", "D_800918DC")],
    0x0C8: [("R_MIPS_26", "func_1516972C")],
    0x0D0: [("R_MIPS_26", "func_15169968")],
    0x0D8: [("R_MIPS_HI16", "D_800D98A4")],
    0x0DC: [("R_MIPS_LO16", "D_800D98A4")],
    0x0E0: [("R_MIPS_HI16", "D_800D9890")],
    0x0E8: [("R_MIPS_LO16", "D_800D9890")],
}
RETAIL_BINDINGS = RAW_BINDINGS

# The full owner gives IDO the retail scheduling context, so this body needs no
# word guards.  The isolated screening translation unit differed at 12 stores.
GUARD_ROWS = ()

ORIGINAL = "s32 func_150B7560() {\n    return 0;\n}"
OLD_PROTOTYPE = "s32 func_150B7560(void);\n"
NEW_PROTOTYPE = "void func_150B7560(void);\n"
SELECTED = """/* Replace both fixed menu records, then select state 3. */
void func_150B7560(void) {
    MenuRecordDescriptorE4070 descriptor;

    if (*(void **)D_800D9898 != NULL) {
        func_1516972C(*(void **)D_800D9898);
        *(void **)D_800D9898 = NULL;
    }
    descriptor.field18 = 77;
    descriptor.field31 = 15;
    descriptor.field14 = 0;
    descriptor.field16 = 0;
    descriptor.field2C = 88;
    descriptor.field2E = 88;
    descriptor.field30 = 0;
    descriptor.asset = D_800918DC;
    descriptor.field24 = 0;
    descriptor.field26 = 0;
    descriptor.field32 = 255;
    descriptor.field33 = 0;
    descriptor.field34 = 0;
    descriptor.field35 = 255;
    descriptor.field36 = 7;
    descriptor.field37 = 17;
    descriptor.field38 = 1;
    descriptor.field39 = 0;
    descriptor.field28 = 4096;
    descriptor.field2A = 4096;
    descriptor.field1C = 60.0f;
    descriptor.field20 = 60.0f;
    if (*(void **)D_800D98A4 != NULL) {
        func_1516972C(*(void **)D_800D98A4);
    }
    *(void **)D_800D98A4 = func_15169968(&descriptor);
    D_800D9890 = 3;
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    if body == ORIGINAL:
        if live.count(OLD_PROTOTYPE) != 1 or live.count(NEW_PROTOTYPE):
            raise ValueError("Dual-record predecessor prototype changed")
        qualified = live.replace(OLD_PROTOTYPE, NEW_PROTOTYPE, 1)
        start, end = function_span(qualified, FUNCTION)
        qualified = qualified[:start] + SELECTED + qualified[end:]
        return live, qualified, False
    if body == SELECTED.split("\n", 1)[1]:
        if live.count(NEW_PROTOTYPE) != 1 or live.count(SELECTED) != 1:
            raise ValueError("Installed dual-record source changed")
        predecessor = live.replace(NEW_PROTOTYPE, OLD_PROTOTYPE, 1)
        predecessor = predecessor.replace(SELECTED, ORIGINAL, 1)
        return predecessor, live, True
    raise ValueError("Dual-record source state changed")


def proposed_guards(root, output, installed):
    source = root / GUARDS
    proposed = output / "proposed-guards.csv"
    with source.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames, rows = reader.fieldnames, list(reader)
    selected = [row for row in rows if row["filename"] == FILENAME and
                row["function"] == FUNCTION]
    if installed:
        if len(selected) != len(GUARD_ROWS):
            raise ValueError("Installed dual-record guard set changed")
        proposed.write_bytes(source.read_bytes())
        rows = [row for row in rows if not
                (row["filename"] == FILENAME and row["function"] == FUNCTION)]
        predecessor = output / "predecessor-guards.csv"
        with predecessor.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames,
                                    lineterminator="\n")
            writer.writeheader(); writer.writerows(rows)
        return predecessor, proposed
    if selected:
        raise ValueError("Dual-record guards already exist in predecessor")
    for offset, expected, replacement in GUARD_ROWS:
        rows.append({
            "filename": FILENAME, "function": FUNCTION,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % expected,
            "replacement": "0x%08X" % replacement,
            "expected_relocations": "-", "replacement_relocations": "-",
            "note": "Normalize independent dual menu-record descriptor store schedule",
            "insert_after": "", "insert_after_relocations": "", "omit": "false",
        })
    with proposed.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames,
                                lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    return source, proposed


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Dual-record retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    for offset, rows in RETAIL_BINDINGS.items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", data, offset,
                         struct.unpack_from(">I", data, offset)[0] & mask)
    return bytes(data)


def checked_candidate(obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Dual-record natural candidate changed")
    if bindings != RAW_BINDINGS:
        raise ValueError("Dual-record natural bindings changed")
    words = struct.unpack(">%dI" % WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Dual-record frame changed")
    return raw, bindings


def assemble_owner(root, output, compact, guards, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / "generated_E4070.c.s"
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=guards, filename=FILENAME,
        rodata_symbol=RODATA_SYMBOL))
    obj = owner_dir / "generated_E4070.c.o"
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
        raise ValueError("Dual-record linker owner reference changed")
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
        raise ValueError("Dual-record predecessor symbol extent changed")
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
    predecessor_guards, proposed = proposed_guards(root, output, installed)
    predecessor_compact, before = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostics(before) != diagnostics(after):
        raise ValueError("Dual-record owner diagnostics changed")
    raw, bindings = checked_candidate(qualified_compact)
    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_guards,
        "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, proposed, "qualified-owner")
    expected_owner = qualified_owner if installed else predecessor_owner
    if expected_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Dual-record selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (
            retail_object_bytes(root), RETAIL_BINDINGS):
        raise ValueError("Dual-record guarded owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Dual-record normalized pools changed")
    predecessor_elf = link_image(
        root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    expected_elf = qualified_elf if installed else predecessor_elf
    if expected_elf.read_bytes() != (root / ELF).read_bytes():
        raise ValueError("Dual-record selected image differs from production")
    retail = retail_bytes(root)
    if qualified_elf.read_bytes() != expected_image(
            predecessor_elf.read_bytes(), retail):
        raise ValueError("Dual-record qualified image differs from literal prediction")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Dual-record full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Dual-record protected data changed")
    (output / "proposed-owner.c").write_text(qualified_source)
    report = {
        "function": FUNCTION, "installed": installed, "words": WORDS,
        "slot_words": WORDS, "frame": FRAME,
        "natural_positional_differences": sum(
            left != right for left, right in zip(
                struct.unpack(">%dI" % WORDS, raw),
                struct.unpack(">%dI" % WORDS, retail_object_bytes(root)))),
        "guards": len(GUARD_ROWS), "relocations": len(bindings),
        "neighbors": neighbors, "raw_sha256": digest(raw),
        "retail_sha256": digest(retail),
        "qualified_owner_sha256": digest(qualified_owner.read_bytes()),
        "predecessor_elf_sha256": digest(predecessor_elf.read_bytes()),
        "qualified_elf_sha256": digest(qualified_elf.read_bytes()),
        "functions": len(new), "changed_bodies": changed,
        "all_addresses_fixed": True, "strict_exclusions": 0,
        "game_data": data,
    }
    (output / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return report, predecessor_owner, qualified_owner, predecessor_elf, qualified_elf


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)[0], indent=2))
