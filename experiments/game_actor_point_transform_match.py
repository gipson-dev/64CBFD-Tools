"""Qualify func_151606A8's linked actor point transform as guarded C."""

import csv
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

from tools.check_game_data_layout import audit_layout
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span)
from tools.match_progress import load_elf_functions
import tools.pad_generated_object as _pad
sys.modules.setdefault("pad_generated_object", _pad)
from tools.pad_c_object import emit_padded_assembly as emit_owner
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = "func_151606A8"
FILENAME = "game_18D770"
SOURCE = "conker/src/game_18D770.c"
OBJECT = "conker/build/src/game_18D770.c.o"
ASM = "conker/asm/nonmatchings/game_18D770/func_151606A8.s"
LAYOUT = "conker/retail_layout.us.txt"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-actor-point-transform-151606A8-match"
ENTRY, ROM, WORDS, FRAME = 0x151606A8, 0x18DB58, 63, 0x88
SIZE = WORDS * 4
TABLE_ROM = 0x22FBBC
RAW_SHA256 = "66bfdbc7d75829a423e0d784bc00f79d74acc5a985e871cddc856f98d7e9f34b"
RETAIL_SHA256 = "5f113140efbdc725cc6df2e06c9d27e1bd9bd3c364319744cdd8b1160904948e"
QUALIFIED_SHA256 = "9226318efe51e802cd7ee5c94501eafda07d3796961a7517e38f8e3428c4d936"
INHERITED_GUARDS_SHA256 = "1f973e977a2fa5f0cc277b34384fe09b70683a7f7a6b2c64650a7051e9d0a9fb"
INSTALLED_GUARDS_SHA256 = "fffe1a835fb2b55e8d20d6ebb5236ce2c3e2d2a38da108c892aed29300303618"
PREDECESSOR_ELF_SHA256 = "ff7b3420a82c34f7403ef495d3adfa3293349711905403bde9b5e54f8234b23e"
NATURAL_BINDINGS = {
    0x020: [("R_MIPS_26", "func_150A8050")],
    0x02C: [("R_MIPS_HI16", "D_800A66B4")],
    0x030: [("R_MIPS_LO16", "D_800A66B4")],
    0x094: [("R_MIPS_26", "func_150A7960")],
}
QUALIFIED_BINDINGS = {
    0x020: [("R_MIPS_26", "func_150A8050")],
    0x030: [("R_MIPS_HI16", "D_800A66B4")],
    0x034: [("R_MIPS_LO16", "D_800A66B4")],
    0x098: [("R_MIPS_26", "func_150A7960")],
}

STUB = "s32 func_151606A8() {\n    return 0;\n}"
SELECTED = """s32 func_151606A8(struct225 *arg0) {
    struct227 *transform;
    struct227 **transformRef;
    f32 matrix[4][4];
    struct17 point;

    transform = arg0->unk18;
    func_150A8050(matrix, transform->unk0, transform->unk4, transform->unk8);
    transformRef = &arg0->unk18;
    matrix[3][0] = (*transformRef)->unk10;
    matrix[3][1] = *(s16 *)&(*transformRef)->pad12[0];
    matrix[3][2] = *(s16 *)&(*transformRef)->pad12[2];
    func_150A7960(matrix, D_800A66B4[0], D_800A66B4[1], D_800A66B4[2],
                  &point.unk0, &point.unk4, &point.unk8);
    arg0->unk14->unkE = point.unk0;
    arg0->unk14->unk10 = point.unk4;
    arg0->unk14->unk12 = point.unk8;
    return 1;
}"""

NOTE = "Normalize actor point transform pointer/global register cycle"
NEW_GUARDS = [
    dict(filename=FILENAME, function=FUNCTION, offset="0x028",
         expected="0x8E0E0018", replacement="0x26020018",
         expected_relocations="-", replacement_relocations="-", note=NOTE,
         insert_after="0x8C4E0000", insert_after_relocations="-", omit="false"),
    dict(filename=FILENAME, function=FUNCTION, offset="0x02C",
         expected="0x3C020000", replacement="0x3C030000",
         expected_relocations="R_MIPS_HI16:D_800A66B4",
         replacement_relocations="R_MIPS_HI16:D_800A66B4", note=NOTE,
         insert_after="", insert_after_relocations="", omit="false"),
    dict(filename=FILENAME, function=FUNCTION, offset="0x030",
         expected="0x24420000", replacement="0x24630000",
         expected_relocations="R_MIPS_LO16:D_800A66B4",
         replacement_relocations="R_MIPS_LO16:D_800A66B4", note=NOTE,
         insert_after="", insert_after_relocations="", omit="false"),
    *[dict(filename=FILENAME, function=FUNCTION, offset="0x%03X" % at,
           expected="0x%08X" % old, replacement="0x%08X" % new,
           expected_relocations="-", replacement_relocations="-", note=NOTE,
           insert_after="", insert_after_relocations="", omit="false")
      for at, old, new in (
          (0x048, 0x8C450000, 0x8C650000),
          (0x050, 0x8C460004, 0x8C660004),
          (0x054, 0x8C470008, 0x8C670008),
          (0x060, 0x8E180018, 0x8C580000),
          (0x078, 0x8E080018, 0x8C480000))],
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    if body == SELECTED:
        predecessor = live[:start] + STUB + live[end:]
        predecessor = predecessor.replace(
            "s32 func_151606A8(struct225 *arg0);", "s32 func_151606A8();", 1)
        return predecessor, live, True
    if body == STUB:
        qualified = live[:start] + SELECTED + live[end:]
        qualified = qualified.replace(
            "s32 func_151606A8();", "s32 func_151606A8(struct225 *arg0);", 1)
        return live, qualified, False
    raise ValueError("Actor point transform source state changed")


def guard_manifests(before):
    before_hash = digest(before)
    reader = csv.DictReader(io.StringIO(before.decode()))
    fields = reader.fieldnames
    rows = list(reader)
    selected = [row for row in rows if row["function"] == FUNCTION]
    stream = io.StringIO(newline="")
    csv.DictWriter(stream, fields, lineterminator="\r\n").writerows(NEW_GUARDS)
    added = stream.getvalue().encode()
    if before_hash == INSTALLED_GUARDS_SHA256:
        if selected != NEW_GUARDS or not before.endswith(added):
            raise ValueError("Installed actor point transform guards changed")
        predecessor = before[:-len(added)]
        if digest(predecessor) != INHERITED_GUARDS_SHA256:
            raise ValueError("Actor point transform guard history changed")
        return predecessor, before
    if before_hash != INHERITED_GUARDS_SHA256 or selected:
        raise ValueError("Inherited actor point transform guards changed")
    return before, before + added


def diagnostics(text):
    rows = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"cfe: Warning (\d+): .*?, line \d+: (.*)", line)
        if match:
            rows.append((match.group(1), match.group(2),
                         lines[index + 1].strip()))
    return rows


def checked_parts(raw, bindings):
    if len(raw) != SIZE - 4 or digest(raw) != RAW_SHA256:
        raise ValueError("Actor point transform natural payload changed")
    if bindings != NATURAL_BINDINGS:
        raise ValueError("Actor point transform natural bindings changed")
    return raw, bindings


def checked_natural(obj):
    return checked_parts(*payload(obj, FUNCTION))


def function_blob(obj, name):
    text, functions, relocations = parse_object(obj)
    info = functions[name]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {offset - start: rows for offset, rows in relocations.items()
                if start <= offset < end}
    return text[start:end], bindings


def assemble_owner(root, output, compact, label, guards):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(emit_owner(
        compact, root / LAYOUT, FILENAME, word_patches_path=guards))
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
        raise ValueError("Actor point transform linker owner reference changed")
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
    if digest(predecessor) != PREDECESSOR_ELF_SHA256:
        raise ValueError("Actor point transform predecessor image changed")
    result = bytearray(predecessor)
    offset = elf_slot_offset(predecessor, ENTRY, SIZE)
    result[offset:offset + SIZE] = retail
    rows = [(at, fields) for at, name, fields, _ in symbol_rows(predecessor)
            if name == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 12):
        raise ValueError("Actor point transform predecessor symbol changed")
    struct.pack_into(">I", result, rows[0][0] + 8, SIZE)
    return bytes(result)


def check_image(predecessor, actual, retail):
    if actual != expected_image(predecessor, retail):
        raise ValueError("Actor point transform image differs from literal prediction")


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    pointer = struct.unpack_from(">I", image, TABLE_ROM)[0]
    jal_target = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    direct_calls = sum(word == jal_target for word in words)
    pointers = [at for at in range(0, len(image) - 3, 4)
                if struct.unpack_from(">I", image, at)[0] == ENTRY]
    if pointer != ENTRY or pointers != [TABLE_ROM] or direct_calls != 0:
        raise ValueError("Actor point transform callback registration changed")
    return {"table": "D_8008B0F0", "table_rom": hex(TABLE_ROM),
            "aligned_pointers": [hex(at) for at in pointers],
            "direct_jal_calls": direct_calls}


def prepare(root, output=None):
    root = Path(root).resolve()
    output = Path(output or root / BUILD).resolve()
    output.mkdir(parents=True, exist_ok=True)
    predecessor_guards, proposed = guard_manifests((root / GUARDS).read_bytes())
    predecessor_path = output / "predecessor-guards.csv"
    proposed_path = output / "proposed-guards.csv"
    predecessor_path.write_bytes(predecessor_guards)
    proposed_path.write_bytes(proposed)
    predecessor_source, qualified_source, selected = source_states(
        (root / SOURCE).read_text())
    predecessor_compact, before_diag = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after_diag = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostics(before_diag) != diagnostics(after_diag):
        raise ValueError("Actor point transform owner diagnostics changed")
    raw, natural_bindings = checked_natural(qualified_compact)
    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, "predecessor-owner", predecessor_path)
    qualified_owner = assemble_owner(
        root, output, qualified_compact, "qualified-owner", proposed_path)
    body, qualified_bindings = function_blob(qualified_owner, FUNCTION)
    retail = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if (len(retail), digest(retail), digest(body), qualified_bindings) != (
            SIZE, RETAIL_SHA256, QUALIFIED_SHA256, QUALIFIED_BINDINGS):
        raise ValueError("Actor point transform guarded payload changed")
    normalized = bytearray(retail)
    for offset, rows in QUALIFIED_BINDINGS.items():
        word = struct.unpack_from(">I", normalized, offset)[0]
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", normalized, offset, word & mask)
    if body != bytes(normalized):
        raise ValueError("Actor point transform guarded body differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Actor point transform normalized pools changed")
    predecessor_elf = link_image(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    check_image(predecessor_elf.read_bytes(), qualified_elf.read_bytes(), retail)
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Actor point transform full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Actor point transform protected data changed")
    (output / "proposed-owner.c").write_text(qualified_source)
    report = {
        "function": FUNCTION, "selected_source": selected, "words": WORDS,
        "natural_words": (SIZE - 4) // 4, "frame": FRAME,
        "guards": len(NEW_GUARDS), "insertions": 1,
        "relocations": len(qualified_bindings), "neighbors": neighbors,
        "raw_sha256": digest(raw), "retail_sha256": digest(retail),
        "qualified_owner_sha256": digest(qualified_owner.read_bytes()),
        "predecessor_elf_sha256": digest(predecessor_elf.read_bytes()),
        "qualified_elf_sha256": digest(qualified_elf.read_bytes()),
        "guard_manifest_sha256": digest(proposed), "functions": len(new),
        "changed_bodies": changed, "all_addresses_fixed": True,
        "strict_exclusions": 0, "registry": registry_evidence(root),
        "game_data": data,
    }
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report, predecessor_owner, qualified_owner, predecessor_elf, qualified_elf


if __name__ == "__main__":
    print(json.dumps(prepare(Path(__file__).resolve().parents[2])[0], indent=2))
