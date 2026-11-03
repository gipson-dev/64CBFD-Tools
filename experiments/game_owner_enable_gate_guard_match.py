"""Qualify func_1514E920's owner enable gate as guarded semantic C."""

from collections import Counter
import csv
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
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = "func_1514E920"
WRAPPER = "func_1514E9DC"
FILENAME = "generated_179F30"
SOURCE = "conker/src/game/generated_179F30.c"
OBJECT = "conker/build/src/game/generated_179F30.c.o"
ASM = "conker/asm/179F30.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-owner-enable-gate-1514E920-guard-match"
ENTRY, ROM, WORDS, FRAME = 0x1514E920, 0x17BDD0, 47, 0x18
SIZE = WORDS * 4
RAW_WORDS = 44
RAW_SHA256 = "e246d24a1783d7cabf1d658de33a8d1dabfd8294f7b82a88174f9a10576c50fc"
RETAIL_SHA256 = "e48659cef02f008661fb30cf57f7c67ac90547a1f449edf680974ec261d0df58"
RAW_BINDINGS = {0x08C: [("R_MIPS_26", "func_1514E89C")]}
RETAIL_BINDINGS = {0x098: [("R_MIPS_26", "func_1514E89C")]}

# Offsets refer to the natural 44-word compiler output. Insertions are emitted
# after their checked source word, so later words and the JAL relocation move
# into their retail positions without any unchecked byte editing.
GUARD_ROWS = (
    (0x008, 0x10A00007, 0x10A00008, 0x24870110),
    (0x010, 0x10A1001A, 0x10A1001C, None),
    (0x018, 0x50A10011, 0x50A10012, None),
    (0x020, 0x1000001A, 0x1000001C, None),
    (0x02C, 0x306E0001, 0x2401FFFE, None),
    (0x030, 0x11C00008, 0x306E0001, None),
    (0x034, 0x34780001, 0x11C00008, None),
    (0x038, 0x8C820154, 0x34780001, None),
    (0x03C, 0x2401FFFE, 0x00617824, None),
    (0x040, 0x00617824, 0xAC8F0010, None),
    (0x044, 0x10400015, 0x8CE20044, None),
    (0x048, 0xAC8F0010, 0x50400017, 0x24020001),
    (0x04C, 0x10000013, 0x10000014, None),
    (0x054, 0x10000011, 0x10000012, None),
    (0x060, 0x8C820154, 0x2401FFFE, None),
    (0x064, 0x2401FFFE, 0x03214024, None),
    (0x068, 0x03214024, 0xAC880010, None),
    (0x06C, 0x1040000B, 0x8CE20044, None),
    (0x070, 0xAC880010, 0x5040000C, 0x24020001),
)

ORIGINAL = "s32 func_1514E920() {\n    return 0;\n}"
ORIGINAL_WRAPPER = """void func_1514E9DC(u8 *arg0, s32 arg1) {
    func_1514E920(arg0, arg1);
}"""
SELECTED = """/* Toggle, enable, or disable an owner and clear its attached enable byte. */
s32 func_1514E920(u8 *owner, s32 mode, s32 context) {
    u8 *extension;
    u8 *attached;

    extension = owner + 0x110;
    switch (mode) {
        case 0:
            if ((*(s32 *)(owner + 0x10) & 1) != 0) {
                *(s32 *)(owner + 0x10) &= ~1;
                attached = *(u8 **)(extension + 0x44);
                if (attached != NULL) {
                    attached[0x30] = 0;
                }
            } else {
                *(s32 *)(owner + 0x10) |= 1;
            }
            break;
        case 2:
            *(s32 *)(owner + 0x10) &= ~1;
            attached = *(u8 **)(extension + 0x44);
            if (attached != NULL) {
                attached[0x30] = 0;
            }
            break;
        case 1:
            *(s32 *)(owner + 0x10) |= 1;
            break;
        default:
            return func_1514E89C(owner, mode, context);
    }
    return 1;
}"""
SELECTED_WRAPPER = """/* Forward the complete operation callback context to the enable gate. */
void func_1514E9DC(u8 *owner, s32 mode, s32 context) {
    func_1514E920(owner, mode, context);
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
            raise ValueError("Unexpected enable-gate diagnostic: " + line)
    return Counter(rows)


def source_states(live):
    old_present = ORIGINAL in live and ORIGINAL_WRAPPER in live
    new_present = SELECTED in live and SELECTED_WRAPPER in live
    if old_present and not new_present:
        qualified = live.replace(ORIGINAL, SELECTED, 1)
        qualified = qualified.replace(ORIGINAL_WRAPPER, SELECTED_WRAPPER, 1)
        return live, qualified, False
    if new_present and not old_present:
        predecessor = live.replace(SELECTED, ORIGINAL, 1)
        predecessor = predecessor.replace(SELECTED_WRAPPER, ORIGINAL_WRAPPER, 1)
        return predecessor, live, True
    raise ValueError("Enable-gate source state changed")


def proposed_guards(root, output, installed):
    source = root / GUARDS
    proposed = output / "proposed-guards.csv"
    with source.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        rows = list(reader)
    selected = [row for row in rows if row["filename"] == FILENAME and
                row["function"] == FUNCTION]
    if installed:
        if len(selected) != len(GUARD_ROWS):
            raise ValueError("Installed enable-gate guard set changed")
        proposed.write_bytes(source.read_bytes())
        rows = [row for row in rows if not
                (row["filename"] == FILENAME and row["function"] == FUNCTION)]
        predecessor = output / "predecessor-guards.csv"
        with predecessor.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames,
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        return predecessor, proposed
    if selected:
        raise ValueError("Enable-gate guards already exist in predecessor")
    for offset, expected, replacement, inserted in GUARD_ROWS:
        rows.append({
            "filename": FILENAME,
            "function": FUNCTION,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % expected,
            "replacement": "0x%08X" % replacement,
            "expected_relocations": "-",
            "replacement_relocations": "-",
            "note": "Normalize owner enable-gate compiler control flow and schedule",
            "insert_after": "" if inserted is None else "0x%08X" % inserted,
            "insert_after_relocations": "",
            "omit": "false",
        })
    with proposed.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames,
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return source, proposed


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Enable-gate retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    word = struct.unpack_from(">I", data, 0x098)[0] & 0xFC000000
    struct.pack_into(">I", data, 0x098, word)
    return bytes(data)


def checked_candidate(obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != RAW_WORDS * 4 or digest(raw) != RAW_SHA256:
        raise ValueError("Enable-gate natural candidate changed: %d %s" %
                         (len(raw), digest(raw)))
    if bindings != RAW_BINDINGS:
        raise ValueError("Enable-gate natural bindings changed")
    words = struct.unpack(">%dI" % RAW_WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Enable-gate frame changed")
    return raw, bindings


def assemble_owner(root, output, compact, guards, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=guards, filename=FILENAME))
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
        raise ValueError("Enable-gate linker owner reference changed")
    link_dir = output / label
    link_dir.mkdir(parents=True, exist_ok=True)
    script = link_dir / "conker.ld"
    script.write_text(linker.replace(old, new))
    elf = link_dir / "conker.us.elf"
    subprocess.run([
        "mips-linux-gnu-ld", "-T", str(script.relative_to(root / "conker")),
        "-Map", str((link_dir / "conker.us.map").relative_to(root / "conker")),
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
        raise ValueError("Enable-gate predecessor symbol extent changed")
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
    predecessor_compact, before_diagnostics = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after_diagnostics = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostic_counts(before_diagnostics) != diagnostic_counts(after_diagnostics):
        raise ValueError("Enable-gate owner diagnostics changed")
    raw, bindings = checked_candidate(qualified_compact)

    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_guards,
        "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, proposed, "qualified-owner")
    expected_owner = qualified_owner if installed else predecessor_owner
    if expected_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Enable-gate selected owner differs from production")
    retail = retail_bytes(root)
    if function_blob(qualified_owner, FUNCTION) != (
            retail_object_bytes(root), RETAIL_BINDINGS):
        raise ValueError("Enable-gate guarded owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Enable-gate normalized pools changed")

    predecessor_elf = link_image(
        root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(
        root, output, qualified_owner, "qualified-image")
    expected_elf = qualified_elf if installed else predecessor_elf
    if expected_elf.read_bytes() != (root / ELF).read_bytes():
        raise ValueError("Enable-gate selected image differs from production")
    if qualified_elf.read_bytes() != expected_image(
            predecessor_elf.read_bytes(), retail):
        raise ValueError("Enable-gate qualified image differs from literal prediction")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Enable-gate full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Enable-gate protected data changed")

    (output / "proposed-owner.c").write_text(qualified_source)
    report = {
        "function": FUNCTION,
        "wrapper": WRAPPER,
        "installed": installed,
        "words": WORDS,
        "natural_words": RAW_WORDS,
        "frame": FRAME,
        "natural_positional_differences": sum(
            left != right for left, right in zip(
                struct.unpack(">%dI" % RAW_WORDS, raw),
                struct.unpack(">%dI" % WORDS, retail_object_bytes(root)))),
        "guards": len(GUARD_ROWS),
        "insertions": sum(row[3] is not None for row in GUARD_ROWS),
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
