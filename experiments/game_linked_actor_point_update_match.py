"""Qualify func_15107924's linked-actor point update as guarded semantic C."""

import csv
import hashlib
import io
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


FUNCTION = "func_15107924"
FILENAME = "generated_133190"
SOURCE = "conker/src/game/generated_133190.c"
OBJECT = "conker/build/src/game/generated_133190.c.o"
ASM = "conker/asm/133190.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-linked-actor-point-update-15107924-match"
ENTRY, ROM, WORDS, FRAME = 0x15107924, 0x134DD4, 63, 0x40
SIZE = WORDS * 4
TABLE_ROM = 0x22D6D0
RAW_SHA256 = "636bec741ef2e2ce328130a529f68e8c61baeda92620242606cbc681a980938f"
RETAIL_SHA256 = "835b33ad801fb40a2081dccea40e19beb29da8f9798ad0e2d24346a9c59209f4"
INHERITED_GUARDS_SHA256 = "cf2019b55b64b2c6a5f6408a41bbcd195cb431b13276d895e893fc84cd2668e1"
BINDINGS = {
    0x07C: [("R_MIPS_26", "func_15107A20")],
    0x0DC: [("R_MIPS_26", "func_15107AE0")],
}

STUB = "s32 func_15107924() {\n    return 0;\n}"
DECLARATIONS = (
    "void func_1515C244(struct127 *, struct17 *, f32 *, f32 *);\n"
    "void func_15143794(s16, s16, f32, vertex *);\n")
PROTOTYPES = (
    "void func_15107A20(struct127 *, s16, s16, vertex *, struct17 *);\n"
    "void func_15107AE0(const f32 *, const f32 *, f32 *, f32 *);\n")
SELECTED = """/* Update the linked actor point and rebuild its fractional points when changed. */
s32 func_15107924(u8 *owner, u8 *changed) {
    u8 *link = *(u8 **)(owner + 0x60);
    struct127 *actor = *(struct127 **)link;
    struct17 original;
    f32 *savedPoint;
    f32 *point;

    if (*(s32 *)actor == 0 ||
            (point = (f32 *)(owner + 0x14),
             link[4] != *((u8 *)actor + 0x3B))) {
        return 0;
    }
    *changed = 0;
    original = *(struct17 *)point;
    savedPoint = point;
    func_15107A20(actor, *(s16 *)(link + 6), *(s16 *)(link + 8),
                  (vertex *)point, NULL);
    if (original.unk0 != *(f32 *)(owner + 0x14) ||
            original.unk4 != *(f32 *)(owner + 0x18) ||
            original.unk8 != *(f32 *)(owner + 0x1C)) {
        *changed = 1;
        func_15107AE0(savedPoint, (f32 *)(owner + 0x38),
                      (f32 *)(owner + 0x20), (f32 *)(owner + 0x2C));
    }
    return 1;
}"""

GUARD_WORDS = (
    (0x000, 0x27BDFFB8, 0x27BDFFC0),
    (0x010, 0xAFA5004C, 0xAFA50044),
    (0x01C, 0xAFAE0040, 0xAFAE0038),
    (0x034, 0x8FA9004C, 0x8FA90044),
    (0x054, 0x27AA0034, 0x27AA002C),
    (0x080, 0x8FA40040, 0x8FA40038),
    (0x084, 0xC7A40034, 0xC7A4002C),
    (0x08C, 0xC7A80038, 0xC7A80030),
    (0x098, 0x8FAE004C, 0x8FAE0044),
    (0x0B0, 0xC7B0003C, 0xC7B00034),
    (0x0F0, 0x27BD0048, 0x27BD0040),
)
NEW_GUARDS = [
    {
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": f"0x{offset:03X}",
        "expected": f"0x{expected:08X}",
        "replacement": f"0x{replacement:08X}",
        "expected_relocations": "-",
        "replacement_relocations": "-",
        "note": "Normalize linked-actor point updater stack frame and local slots",
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }
    for offset, expected, replacement in GUARD_WORDS
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    predecessor_block = STUB + "\n\n" + DECLARATIONS
    qualified_block = DECLARATIONS + PROTOTYPES + "\n" + SELECTED
    if predecessor_block in live:
        if PROTOTYPES in live or SELECTED in live:
            raise ValueError("Linked-actor point predecessor declarations changed")
        if live.count(predecessor_block) != 1:
            raise ValueError("Linked-actor point predecessor block changed")
        return live, live.replace(predecessor_block, qualified_block, 1), False
    if qualified_block in live:
        if live.count(qualified_block) != 1:
            raise ValueError("Installed linked-actor point source changed")
        return live.replace(qualified_block, predecessor_block, 1), live, True
    raise ValueError("Linked-actor point source state changed")


def guard_manifest(before):
    if digest(before) != INHERITED_GUARDS_SHA256:
        raise ValueError("Inherited guard manifest changed")
    reader = csv.DictReader(io.StringIO(before.decode()))
    fields = reader.fieldnames
    rows = list(reader)
    if any(row["function"] == FUNCTION for row in rows):
        raise ValueError("Linked-actor point guards already present")
    extra = io.StringIO(newline="")
    writer = csv.DictWriter(extra, fields, lineterminator="\r\n")
    writer.writerows(NEW_GUARDS)
    return before + extra.getvalue().encode()


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Linked-actor point retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    for offset in BINDINGS:
        struct.pack_into(">I", data, offset,
                         struct.unpack_from(">I", data, offset)[0] & 0xFC000000)
    return bytes(data)


def checked_candidate(root, obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Linked-actor point natural candidate changed")
    if bindings != BINDINGS:
        raise ValueError("Linked-actor point natural bindings changed")
    normalized = bytearray(raw)
    for offset, expected, replacement in GUARD_WORDS:
        if struct.unpack_from(">I", normalized, offset)[0] != expected:
            raise ValueError("Linked-actor point natural guard word changed")
        struct.pack_into(">I", normalized, offset, replacement)
    if bytes(normalized) != retail_object_bytes(root):
        raise ValueError("Linked-actor point normalized words differ from retail")
    return raw, bindings


def assemble_owner(root, output, compact, label, guards):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=guards,
        filename=FILENAME, rodata_symbol="D_800A2420"))
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
        raise ValueError("Linked-actor point linker owner reference changed")
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
        raise ValueError("Linked-actor point predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0][0] + 8, SIZE)
    return bytes(result)


def check_image(predecessor, actual, retail):
    if actual != expected_image(predecessor, retail):
        raise ValueError("Linked-actor point image differs from literal prediction")


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
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    direct_calls = sum(word == jal_target for word in words)
    pointers = [at for at in range(0, len(image) - 3, 4)
                if struct.unpack_from(">I", image, at)[0] == ENTRY]
    if pointer != ENTRY or pointers != [TABLE_ROM] or direct_calls != 0:
        raise ValueError("Linked-actor point callback registration changed")
    return {"table": "D_80088C10", "table_rom": hex(TABLE_ROM),
            "aligned_pointers": [hex(at) for at in pointers],
            "direct_jal_calls": direct_calls}


def prepare(root, output=None):
    root = Path(root).resolve()
    output = Path(output or root / BUILD).resolve()
    output.mkdir(parents=True, exist_ok=True)
    inherited_guards = (root / GUARDS).read_bytes()
    proposed = guard_manifest(inherited_guards)
    proposed_path = output / "proposed-guards.csv"
    proposed_path.write_bytes(proposed)
    predecessor_source, qualified_source, installed = source_states(
        (root / SOURCE).read_text())
    predecessor_compact, before = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostics(before) != diagnostics(after):
        raise ValueError("Linked-actor point owner diagnostics changed")
    raw, bindings = checked_candidate(root, qualified_compact)
    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, "predecessor-owner", root / GUARDS)
    qualified_owner = assemble_owner(
        root, output, qualified_compact, "qualified-owner", proposed_path)
    expected_owner = qualified_owner if installed else predecessor_owner
    if expected_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Linked-actor point selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (
            retail_object_bytes(root), BINDINGS):
        raise ValueError("Linked-actor point guarded owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Linked-actor point normalized pools changed")
    predecessor_elf = link_image(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    expected_elf = qualified_elf if installed else predecessor_elf
    if expected_elf.read_bytes() != (root / ELF).read_bytes():
        raise ValueError("Linked-actor point selected image differs from production")
    retail = retail_bytes(root)
    check_image(predecessor_elf.read_bytes(), qualified_elf.read_bytes(), retail)
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Linked-actor point full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Linked-actor point protected data changed")
    (output / "proposed-owner.c").write_text(qualified_source)
    report = {
        "function": FUNCTION, "installed": installed, "words": WORDS,
        "frame": FRAME, "natural_frame": 0x48,
        "natural_positional_differences": len(GUARD_WORDS),
        "guards": len(GUARD_WORDS), "relocations": len(bindings),
        "neighbors": neighbors, "raw_sha256": digest(raw),
        "retail_sha256": digest(retail),
        "qualified_owner_sha256": digest(qualified_owner.read_bytes()),
        "predecessor_elf_sha256": digest(predecessor_elf.read_bytes()),
        "qualified_elf_sha256": digest(qualified_elf.read_bytes()),
        "guard_manifest_sha256": digest(proposed),
        "functions": len(new), "changed_bodies": changed,
        "all_addresses_fixed": True, "strict_exclusions": 0,
        "registry": registry_evidence(root), "game_data": data,
    }
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report, predecessor_owner, qualified_owner, predecessor_elf, qualified_elf


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)[0], indent=2))
