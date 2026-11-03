"""Qualify func_150E4010's actor direction submission as direct semantic C."""

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
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = "func_150E4010"
FILENAME = "generated_1104D0"
SOURCE = "conker/src/game/generated_1104D0.c"
OBJECT = "conker/build/src/game/generated_1104D0.c.o"
ASM = "conker/asm/1104D0.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-actor-direction-submission-150E4010-match"
ENTRY, ROM, WORDS, FRAME = 0x150E4010, 0x1114C0, 67, 0x38
SIZE = WORDS * 4
TABLE_ROM = 0x234694
SYMBOL = struct.Struct(">IIIBBH")
RAW_SHA256 = "1a451ac2de909a57d9b65adf6f1fc2db813355f868b2c22d25711e62bcc72923"
RETAIL_SHA256 = "0878674bf8d4503184855b6069b8b0be89528b3dcf89988135db3be44d6a9a73"
BINDINGS = {
    0x020: [("R_MIPS_26", "func_150484A0")],
    0x044: [("R_MIPS_HI16", "D_800A1050")],
    0x048: [("R_MIPS_LO16", "D_800A1050")],
    0x0F4: [("R_MIPS_26", "func_1505D1C4")],
}

STUB = "s32 func_150E4010() {\n    return 0;\n}"
GLOBAL_ANCHOR = "extern f32 D_800BE9A4;\n"
GLOBAL_DECLARATION = "extern f32 D_800A1050;\n"
PROTOTYPE_ANCHOR = (
    "void func_151C3B0C(void *, f32, f32, f32, f32, s32, s32, s32);\n")
PROTOTYPES = (
    "f32 func_150484A0(f32, f32);\n"
    "void func_1505D1C4(f32, f32, f32, s32, s32, u16, s32, s32);\n")
SELECTED = """/* Submit this actor's position and direction as object slot 25. */
void func_150E4010(u8 *actor) {
    u8 *extension;

    extension = actor + 0x110;
    if (*(s32 *)(actor + 0x1B4) != 0) {
        func_1505D1C4(*(f32 *)(extension + 0x30),
                      *(f32 *)(extension + 0x34),
                      *(f32 *)(extension + 0x38),
                      *(s32 *)(extension + 0xA4) | 0x60000,
                      -1,
                      (((u32)(func_150484A0(*(f32 *)(extension + 0x60),
                                            *(f32 *)(extension + 0x64)) *
                                D_800A1050) & 0xFFFF) - 0x4000) | 1,
                      0, 0);
    }
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    if body == STUB:
        if any(block in live for block in
               (GLOBAL_DECLARATION, PROTOTYPES, SELECTED)):
            raise ValueError("Direction-submission predecessor declarations changed")
        if live.count(GLOBAL_ANCHOR) != 1 or live.count(PROTOTYPE_ANCHOR) != 1:
            raise ValueError("Direction-submission predecessor anchors changed")
        qualified = live.replace(
            GLOBAL_ANCHOR, GLOBAL_ANCHOR + GLOBAL_DECLARATION, 1)
        qualified = qualified.replace(
            PROTOTYPE_ANCHOR, PROTOTYPE_ANCHOR + PROTOTYPES, 1)
        qstart, qend = function_span(qualified, FUNCTION)
        qualified = qualified[:qstart] + SELECTED + qualified[qend:]
        return live, qualified, False
    if body == SELECTED.split("\n", 1)[1]:
        if (live.count(GLOBAL_DECLARATION) != 1 or
                live.count(PROTOTYPES) != 1 or live.count(SELECTED) != 1):
            raise ValueError("Installed direction-submission source changed")
        predecessor = live.replace(GLOBAL_DECLARATION, "", 1)
        predecessor = predecessor.replace(PROTOTYPES, "", 1)
        predecessor = predecessor.replace(SELECTED, STUB, 1)
        return predecessor, live, True
    raise ValueError("Direction-submission source state changed")


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Direction-submission retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    for offset, rows in BINDINGS.items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", data, offset,
                         struct.unpack_from(">I", data, offset)[0] & mask)
    return bytes(data)


def checked_candidate(root, obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Direction-submission natural candidate changed")
    if bindings != BINDINGS or raw != retail_object_bytes(root):
        raise ValueError("Direction-submission natural bindings or words changed")
    words = struct.unpack(">%dI" % WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Direction-submission frame changed")
    return raw, bindings


def assemble_owner(root, output, compact, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=root / GUARDS,
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
        raise ValueError("Direction-submission linker owner reference changed")
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
        raise ValueError("Direction-submission predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0][0] + 8, SIZE)
    # Adding this owner's first D_800A1050 reference changes one bounded GNU-ld
    # hash collision. The equal-length symbols exchange adjacent .symtab and
    # .strtab slots without changing either definition.
    entries = {name: (at, fields, string_at)
               for at, name, fields, string_at in symbol_rows(predecessor)}
    names = ("D_800A1050", "D_800A92A0")
    first, second = (entries[name] for name in names)
    literals = tuple(name.encode() + b"\0" for name in names)
    if (second[0] != first[0] + SYMBOL.size or
            second[2] != first[2] + len(literals[0]) or
            predecessor[first[2]:second[2] + len(literals[1])] !=
            literals[0] + literals[1]):
        raise ValueError("Direction-submission symbol-order cycle changed")
    strings_base = first[2] - first[1][0]
    for slot, source, literal in (
            (first, second, literals[1]), (second, first, literals[0])):
        fields = list(source[1])
        fields[0] = slot[2] - strings_base
        SYMBOL.pack_into(result, slot[0], *fields)
        result[slot[2]:slot[2] + len(literal)] = literal
    return bytes(result)


def check_image(predecessor, actual, retail):
    if actual != expected_image(predecessor, retail):
        raise ValueError("Direction-submission image differs from literal prediction")


def function_blob(obj, name):
    text, functions, relocations = parse_object(obj)
    info = functions[name]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {offset - start: rows for offset, rows in relocations.items()
                if start <= offset < end}
    return text[start:end], bindings


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    pointer = struct.unpack_from(">I", image, TABLE_ROM)[0]
    jal_target = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    direct_calls = sum(word == jal_target for word in
                       struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3]))
    pointers = [at for at in range(0, len(image) - 3, 4)
                if struct.unpack_from(">I", image, at)[0] == ENTRY]
    if pointer != ENTRY or pointers != [TABLE_ROM] or direct_calls != 0:
        raise ValueError("Direction-submission callback registration changed")
    return {"table": "D_8008FBD0", "table_rom": hex(TABLE_ROM),
            "aligned_pointers": [hex(at) for at in pointers],
            "direct_jal_calls": direct_calls}


def prepare(root, output=None):
    root = Path(root).resolve()
    output = Path(output or root / BUILD).resolve()
    output.mkdir(parents=True, exist_ok=True)
    predecessor_source, qualified_source, installed = source_states(
        (root / SOURCE).read_text())
    predecessor_compact, before = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostics(before) != diagnostics(after):
        raise ValueError("Direction-submission owner diagnostics changed")
    raw, bindings = checked_candidate(root, qualified_compact)
    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, "qualified-owner")
    expected_owner = qualified_owner if installed else predecessor_owner
    if expected_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Direction-submission selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (
            retail_object_bytes(root), BINDINGS):
        raise ValueError("Direction-submission owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Direction-submission normalized pools changed")
    predecessor_elf = link_image(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    expected_elf = qualified_elf if installed else predecessor_elf
    if expected_elf.read_bytes() != (root / ELF).read_bytes():
        raise ValueError("Direction-submission selected image differs from production")
    retail = retail_bytes(root)
    check_image(predecessor_elf.read_bytes(), qualified_elf.read_bytes(), retail)
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Direction-submission full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Direction-submission protected data changed")
    (output / "proposed-owner.c").write_text(qualified_source)
    (output / "proposed-guards.csv").write_bytes((root / GUARDS).read_bytes())
    report = {
        "function": FUNCTION, "installed": installed, "words": WORDS,
        "frame": FRAME, "natural_positional_differences": 0,
        "guards": 0, "relocations": len(bindings), "neighbors": neighbors,
        "raw_sha256": digest(raw), "retail_sha256": digest(retail),
        "qualified_owner_sha256": digest(qualified_owner.read_bytes()),
        "predecessor_elf_sha256": digest(predecessor_elf.read_bytes()),
        "qualified_elf_sha256": digest(qualified_elf.read_bytes()),
        "functions": len(new), "changed_bodies": changed,
        "all_addresses_fixed": True, "strict_exclusions": 0,
        "registry": registry_evidence(root), "game_data": data,
    }
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report, predecessor_owner, qualified_owner, predecessor_elf, qualified_elf


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)[0], indent=2))
