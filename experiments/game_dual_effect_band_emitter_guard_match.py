"""Qualify func_150C2424's dual randomized effect-band emitter."""

import csv
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.check_game_data_layout import audit_layout
from tools.experiments.game_actor_state_tick_integration import (
    SYMBOL, elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.game_four_head_lookup_match import diagnostics, payload
from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span)
from tools.match_progress import load_elf_functions
from tools.pad_c_object import emit_padded_assembly
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = "func_150C2424"
FILENAME = "game_EF410"
SOURCE = "conker/src/game_EF410.c"
OBJECT = "conker/build/src/game_EF410.c.o"
LAYOUT = "conker/retail_layout.us.txt"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-dual-effect-band-emitter-150C2424-guard-match"
ENTRY, ROM, WORDS, FRAME = 0x150C2424, 0xEF8D4, 62, 0x38
SIZE = WORDS * 4
RAW_SHA256 = "dfd09087fa42d34720069460ea30cdfee5e2ec4f65f7c58db07f4fead4f751dc"
RETAIL_SHA256 = "a14cc47b15a7b2dd207f0d7c6b4b5df4bf90c12357475dbff7d8a0c091ee9ae9"
RAW_BINDINGS = {
    0x00C: [("R_MIPS_26", "func_150ADA68")],
    0x028: [("R_MIPS_HI16", "D_800A0268")],
    0x02C: [("R_MIPS_LO16", "D_800A0268")],
    0x06C: [("R_MIPS_26", "func_1514C470")],
    0x074: [("R_MIPS_26", "func_150ADA68")],
    0x08C: [("R_MIPS_HI16", "D_800A026C")],
    0x090: [("R_MIPS_LO16", "D_800A026C")],
    0x0E0: [("R_MIPS_26", "func_1514C470")],
}
RETAIL_BINDINGS = {
    0x00C: [("R_MIPS_26", "func_150ADA68")],
    0x01C: [("R_MIPS_HI16", "D_800A0268")],
    0x020: [("R_MIPS_LO16", "D_800A0268")],
    0x06C: [("R_MIPS_26", "func_1514C470")],
    0x074: [("R_MIPS_26", "func_150ADA68")],
    0x08C: [("R_MIPS_HI16", "D_800A026C")],
    0x090: [("R_MIPS_LO16", "D_800A026C")],
    0x0E0: [("R_MIPS_26", "func_1514C470")],
}

# Four checked words rotate only the independent first-band constant/global
# setup. Relocation metadata moves with the symbolic D_800A0268 load.
GUARD_ROWS = (
    (0x01C, 0x3C01C3F5, 0x3C010000, "-", "R_MIPS_HI16:D_800A0268"),
    (0x020, 0x44817000, 0xC42C0000, "-", "R_MIPS_LO16:D_800A0268"),
    (0x028, 0x3C010000, 0x3C01C3F5, "R_MIPS_HI16:D_800A0268", "-"),
    (0x02C, 0xC42C0000, 0x44817000, "R_MIPS_LO16:D_800A0268", "-"),
)

MARKER = (
    "/* Non-matching C placeholders for asm/nonmatchings/game_EF410/"
    "func_150C2424.s. */")
ORIGINAL = "s32 func_150C2424() {\n    return 0;\n}"
OLD_PROTOTYPE = "s32 func_150C2424();\n"
PROTOTYPE_ANCHOR = "s32 func_150C2290();\n"
DECLARATIONS = """extern f32 D_800A0268;
extern f32 D_800A026C;
void func_1514C470(f32, f32, f32, f32, f32, f32, f32, s32, s32, f32, void *, u8);
"""
SELECTED = """/* Emit both randomized effect bands used by event 0x2E. */
void func_150C2424(u8 channel) {
    func_1514C470(D_800A0268, -490.0f, -328.0f, D_800A0268,
                 -490.0f, 328.0f, func_150ADA68() * 8.0f + 8.0f,
                 1, 0, 0.0f, NULL, channel);
    func_1514C470(D_800A026C, -560.0f, -580.0f, 8117.0f,
                 -560.0f, -580.0f, func_150ADA68() * 3.0f + 4.0f,
                 3, 0, 0.0f, NULL, channel);
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    anchor = "extern f32 D_800A0284;\n"
    old_block = MARKER + "\n" + ORIGINAL
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    if body == ORIGINAL:
        if live.count(DECLARATIONS) or live.count(SELECTED):
            raise ValueError("Dual-band predecessor declarations changed")
        if live.count(anchor) != 1 or live.count(OLD_PROTOTYPE) != 1:
            raise ValueError("Dual-band predecessor anchors changed")
        qualified = live.replace(anchor, anchor + DECLARATIONS, 1)
        qualified = qualified.replace(OLD_PROTOTYPE, "", 1)
        if qualified.count(old_block) != 1:
            raise ValueError("Dual-band predecessor block changed")
        qualified = qualified.replace(old_block, SELECTED, 1)
        return live, qualified, False
    if body == SELECTED.split("\n", 1)[1]:
        if live.count(DECLARATIONS) != 1 or live.count(SELECTED) != 1:
            raise ValueError("Installed dual-band source changed")
        predecessor = live.replace(DECLARATIONS, "", 1)
        predecessor = predecessor.replace(
            PROTOTYPE_ANCHOR, PROTOTYPE_ANCHOR + OLD_PROTOTYPE, 1)
        predecessor = predecessor.replace(SELECTED, old_block, 1)
        return predecessor, live, True
    raise ValueError("Dual-band source state changed")


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
            raise ValueError("Installed dual-band guard set changed")
        proposed.write_bytes(source.read_bytes())
        prior = [row for row in rows if not
                 (row["filename"] == FILENAME and row["function"] == FUNCTION)]
        predecessor = output / "predecessor-guards.csv"
        with predecessor.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames,
                                    lineterminator="\n")
            writer.writeheader(); writer.writerows(prior)
        return predecessor, proposed
    if selected:
        raise ValueError("Dual-band guards already exist in predecessor")
    for offset, expected, replacement, expected_rel, replacement_rel in GUARD_ROWS:
        rows.append({
            "filename": FILENAME, "function": FUNCTION,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % expected,
            "replacement": "0x%08X" % replacement,
            "expected_relocations": expected_rel,
            "replacement_relocations": replacement_rel,
            "note": "Normalize dual effect-band first-call constant and global schedule",
            "insert_after": "", "insert_after_relocations": "", "omit": "false",
        })
    with proposed.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    return source, proposed


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Dual-band retail bytes changed")
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
        raise ValueError("Dual-band natural candidate changed: %d %s" %
                         (len(raw), digest(raw)))
    if bindings != RAW_BINDINGS:
        raise ValueError("Dual-band natural bindings changed")
    words = struct.unpack(">%dI" % WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Dual-band frame changed")
    return raw, bindings


def assemble_owner(root, output, compact, guards, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(emit_padded_assembly(
        compact, root / LAYOUT, word_patches_path=guards,
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
        raise ValueError("Dual-band linker owner reference changed")
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
        raise ValueError("Dual-band predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0][0] + 8, SIZE)
    # Adding D_800A026C to this owner changes one deterministic GNU-ld hash
    # collision: it swaps this symbol with D_80096A6C in both .symtab and
    # .strtab. Predict the complete closed metadata cycle rather than
    # excluding non-allocated ELF bytes from the image proof.
    entries = {name: (at, fields, string_at)
               for at, name, fields, string_at in symbol_rows(predecessor)}
    names = ("D_800A026C", "D_80096A6C")
    first, second = (entries[name] for name in names)
    literals = tuple(name.encode() + b"\0" for name in names)
    if (second[0] != first[0] + SYMBOL.size or
            second[2] != first[2] + len(literals[0]) or
            predecessor[first[2]:second[2] + len(literals[1])] !=
            literals[0] + literals[1]):
        raise ValueError("Dual-band bounded symbol-order cycle changed")
    strings_base = first[2] - first[1][0]
    for slot, source, literal in (
            (first, second, literals[1]), (second, first, literals[0])):
        fields = list(source[1])
        fields[0] = slot[2] - strings_base
        SYMBOL.pack_into(result, slot[0], *fields)
        result[slot[2]:slot[2] + len(literal)] = literal
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
        raise ValueError("Dual-band owner diagnostics changed")
    raw, bindings = checked_candidate(qualified_compact)
    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_guards, "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, proposed, "qualified-owner")
    expected_owner = qualified_owner if installed else predecessor_owner
    if expected_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Dual-band selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (
            retail_object_bytes(root), RETAIL_BINDINGS):
        raise ValueError("Dual-band guarded owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Dual-band normalized pools changed")
    predecessor_elf = link_image(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    expected_elf = qualified_elf if installed else predecessor_elf
    if expected_elf.read_bytes() != (root / ELF).read_bytes():
        raise ValueError("Dual-band selected image differs from production")
    retail = retail_bytes(root)
    if qualified_elf.read_bytes() != expected_image(
            predecessor_elf.read_bytes(), retail):
        raise ValueError("Dual-band qualified image differs from literal prediction")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Dual-band full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Dual-band protected data changed")
    (output / "proposed-owner.c").write_text(qualified_source)
    report = {
        "function": FUNCTION, "installed": installed, "words": WORDS,
        "frame": FRAME,
        "natural_positional_differences": sum(
            a != b for a, b in zip(struct.unpack(">%dI" % WORDS, raw),
                                   struct.unpack(">%dI" % WORDS,
                                                 retail_object_bytes(root)))),
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
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report, predecessor_owner, qualified_owner, predecessor_elf, qualified_elf


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)[0], indent=2))
