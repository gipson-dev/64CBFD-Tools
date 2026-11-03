"""Qualify func_15133A94's selected attached-actor matrix copy."""

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
from tools.experiments.game_four_head_lookup_match import diagnostics, payload
from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span)
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = "func_15133A94"
FILENAME = "generated_15F680"
SOURCE = "conker/src/game/generated_15F680.c"
OBJECT = "conker/build/src/game/generated_15F680.c.o"
ASM = "conker/asm/15F680.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-selected-actor-matrix-15133A94-match"
ENTRY, ROM, WORDS, FRAME = 0x15133A94, 0x160F44, 65, 0x68
SIZE = WORDS * 4
RAW_SHA256 = "da71c46b7c04743709d267e69ec7fe2aca6be435b6b0f479aea583f779c52591"
RETAIL_SHA256 = "7ddf1b2d34b59f5cf64b141c6f79c55aaa68da8a717ac423c9ce5ceaad1f0e87"
RAW_BINDINGS = {
    0x06C: [("R_MIPS_HI16", "D_800C3E90")],
    0x084: [("R_MIPS_LO16", "D_800C3E90")],
    0x0A0: [("R_MIPS_26", "memcpy")],
    0x0C0: [("R_MIPS_26", "memcpy")],
    0x0E8: [("R_MIPS_26", "guMtxF2L")],
}
RETAIL_BINDINGS = RAW_BINDINGS
GUARD_ROWS = (
    (0x0A4, 0x01832821, 0x006C2821),
    (0x0C4, 0x01C32821, 0x006E2821),
)

ORIGINAL = "s32 func_15133A94() {\n    return 0;\n}"
TYPES = """extern u8 D_800C3E90;

typedef struct {
    f32 matrix[4][4];
    u8 reserved40[8];
} MatrixWorkspace15F680;

"""
TYPE_ANCHOR = "extern u8 D_800BE616;\n"
SELECTED = """/* Copy the selected attached-actor matrix in the active representation. */
s32 func_15133A94(Mtx *output, u8 *actor) {
    MatrixWorkspace15F680 workspace;
    u8 *attached;
    u8 *matrices;

    attached = *(u8 **)(actor + 0x7C);
    if (attached == NULL || *(u32 *)attached == 0 || attached[4] == 0xFF ||
        actor[0x80] != attached[0x3B]) {
        return -1;
    }
    matrices = *(u8 **)(attached + 0x1D4);
    if (matrices == NULL) {
        return 0;
    }
    if ((attached[0x74] & 0xF) == 0xF) {
        return 0;
    }
    if (D_800C3E90 != 0) {
        memcpy(output, matrices + (actor[0x170] << 6), 0x40);
    } else {
        memcpy(workspace.matrix, matrices + (actor[0x170] << 6), 0x40);
        workspace.matrix[0][3] = 0.0f;
        workspace.matrix[1][3] = 0.0f;
        workspace.matrix[2][3] = 0.0f;
        workspace.matrix[3][3] = 1.0f;
        guMtxF2L(workspace.matrix, output);
    }
    return 1;
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    if body == ORIGINAL:
        if live.count(TYPES) or live.count(TYPE_ANCHOR) != 1:
            raise ValueError("Selected-matrix predecessor types changed")
        qualified = live.replace(TYPE_ANCHOR, TYPE_ANCHOR + TYPES, 1)
        start, end = function_span(qualified, FUNCTION)
        qualified = qualified[:start] + SELECTED + qualified[end:]
        return live, qualified, False
    if body == SELECTED.split("\n", 1)[1]:
        if live.count(TYPES) != 1 or live.count(SELECTED) != 1:
            raise ValueError("Installed selected-matrix source changed")
        predecessor = live.replace(TYPES, "", 1)
        predecessor = predecessor.replace(SELECTED, ORIGINAL, 1)
        return predecessor, live, True
    raise ValueError("Selected-matrix source state changed")


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
            raise ValueError("Installed selected-matrix guard set changed")
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
        raise ValueError("Selected-matrix guards already exist in predecessor")
    for offset, expected, replacement in GUARD_ROWS:
        rows.append({
            "filename": FILENAME, "function": FUNCTION,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % expected,
            "replacement": "0x%08X" % replacement,
            "expected_relocations": "-", "replacement_relocations": "-",
            "note": "Normalize commutative selected-matrix base and index addition",
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
        raise ValueError("Selected-matrix retail bytes changed")
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
        raise ValueError("Selected-matrix natural candidate changed")
    if bindings != RAW_BINDINGS:
        raise ValueError("Selected-matrix natural bindings changed")
    words = struct.unpack(">%dI" % WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Selected-matrix frame changed")
    return raw, bindings


def assemble_owner(root, output, compact, guards, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / "generated_15F680.c.s"
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=guards, filename=FILENAME))
    obj = owner_dir / "generated_15F680.c.o"
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
        raise ValueError("Selected-matrix linker owner reference changed")
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
        raise ValueError("Selected-matrix predecessor symbol extent changed")
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
        raise ValueError("Selected-matrix owner diagnostics changed")
    raw, bindings = checked_candidate(qualified_compact)
    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_guards,
        "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, proposed, "qualified-owner")
    expected_owner = qualified_owner if installed else predecessor_owner
    if expected_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Selected-matrix selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (
            retail_object_bytes(root), RETAIL_BINDINGS):
        raise ValueError("Selected-matrix guarded owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Selected-matrix normalized pools changed")
    predecessor_elf = link_image(
        root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    expected_elf = qualified_elf if installed else predecessor_elf
    if expected_elf.read_bytes() != (root / ELF).read_bytes():
        raise ValueError("Selected-matrix selected image differs from production")
    retail = retail_bytes(root)
    if qualified_elf.read_bytes() != expected_image(
            predecessor_elf.read_bytes(), retail):
        raise ValueError("Selected-matrix qualified image differs from literal prediction")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Selected-matrix full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Selected-matrix protected data changed")
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
