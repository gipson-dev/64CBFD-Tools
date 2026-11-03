"""Qualify func_151B1828's embedded dual-phase planar position update as guarded C."""

import csv
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_embedded_dual_phase_position_update_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_four_head_lookup_match import diagnostics
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = candidate.FUNCTION
FILENAME = "generated_1DD500"
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1DD500.c.o"
ASM = "conker/asm/1DD500.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22E730.rodata.s"
BUILD = "conker/build/game-embedded-dual-phase-position-update-151B1828-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME, RETAIL_FRAME = 0x20, 0x30
RAW_SHA256 = "b5c046431d39dd4c77a3bc03aca9f5851056df1fe2c969c0f28391a8fad73928"
RETAIL_SHA256 = "6b4ac0b0f10c883b55eabac9151fa77e5e24d00cd3589e6483245a3eb6a0fcda"
BINDINGS = {
    0x004: [("R_MIPS_HI16", "D_800BE9E4")],
    0x008: [("R_MIPS_LO16", "D_800BE9E4")],
    0x058: [("R_MIPS_26", "func_151423D8")],
    0x07C: [("R_MIPS_26", "func_151423D8")],
}

PATCH_ROWS = (
    dict(offset="0x000", expected="0x27BDFFE0", replacement="0x27BDFFD0",
         note="Normalize embedded dual-phase callback frame size"),
    dict(offset="0x05C", expected="0xAFA50020", replacement="0xAFA50030",
         note="Normalize embedded dual-phase callback owner home"),
    dict(offset="0x060", expected="0x8FA50020", replacement="0x8FA50030",
         note="Normalize embedded dual-phase callback owner reload"),
    dict(offset="0x064", expected="0xE7A00018", replacement="0xE7A00024",
         note="Normalize first trigonometric sample home"),
    dict(offset="0x088", expected="0xC7A60018", replacement="0xC7A60024",
         note="Normalize first trigonometric sample reload"),
    dict(offset="0x08C", expected="0x8FA50020", replacement="0x8FA50030",
         note="Normalize post-call owner reload"),
    dict(offset="0x0BC", expected="0x46022180", replacement="0x46041180",
         note="Normalize first commutative smoothing addition"),
    dict(offset="0x0DC", expected="0x460C3200", replacement="0x46066200",
         note="Normalize second commutative smoothing addition"),
    dict(offset="0x0EC", expected="0x27BD0020", replacement="0x27BD0030",
         note="Normalize embedded dual-phase callback frame restore"),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def complete_row(row):
    return {
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": row["offset"],
        "expected": row["expected"],
        "replacement": row["replacement"],
        "expected_relocations": "-",
        "replacement_relocations": "-",
        "note": row["note"],
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }


def source_states(live):
    marker = '#include "structs.h"\n'
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or candidate.DECLARATIONS in live:
            raise ValueError("Embedded dual-phase position predecessor source changed")
        qualified = live.replace(
            marker, marker + candidate.DECLARATIONS, 1
        ).replace(candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(candidate.DECLARATIONS) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed embedded dual-phase position source changed")
        predecessor = live.replace(candidate.DECLARATIONS, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Embedded dual-phase position source state changed")


def write_patches(path, fields, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def function_blob(obj):
    text, functions, relocations = parse_object(obj)
    info = functions[FUNCTION]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {
        offset - start: rows for offset, rows in relocations.items()
        if start <= offset < end
    }
    return text[start:end], bindings


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Embedded dual-phase position retail bytes changed")
    return data


def retail_object_bytes(root):
    result = bytearray(retail_bytes(root))
    for offset, rows in BINDINGS.items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", result, offset,
                         struct.unpack_from(">I", result, offset)[0] & mask)
    return bytes(result)


def checked_candidate(root, obj):
    raw, bindings = function_blob(obj)
    if len(raw) != SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Embedded dual-phase position natural candidate changed")
    if ((-struct.unpack_from(">I", raw)[0]) & 0xFFFF) != NATURAL_FRAME:
        raise ValueError("Embedded dual-phase position natural frame changed")
    if bindings != BINDINGS:
        raise ValueError("Embedded dual-phase position bindings changed")
    expected = retail_object_bytes(root)
    differences = [
        offset for offset in range(0, SIZE, 4)
        if raw[offset:offset + 4] != expected[offset:offset + 4]
    ]
    wanted = [int(row["offset"], 0) for row in PATCH_ROWS]
    if differences != wanted:
        raise ValueError("Embedded dual-phase position natural difference set changed")
    return raw, bindings


def assemble_owner(root, output, compact, rows, fields, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    patch_file = owner_dir / "retail-word-patches.csv"
    write_patches(patch_file, fields, rows)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=patch_file,
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
        raise ValueError("Embedded dual-phase position linker owner reference changed")
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


def registry_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    registry = (root / REGISTRY).read_text()
    block = registry.split("dlabel D_80089CB8\n", 1)[1].split(
        "enddlabel D_80089CB8", 1)[0]
    if calls or pointers != [0x22E7BC] or block.count("func_151B1828") != 1:
        raise ValueError("Embedded dual-phase position registry evidence changed")
    entries = [line for line in block.splitlines() if ".word" in line]
    if entries[17].split(".word", 1)[1].strip() != FUNCTION:
        raise ValueError("Embedded dual-phase position registry slot changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x22e7bc"],
        "registry": "D_80089CB8[17]",
        "abi": "one state pointer; callback returns one after updating both planar coordinates",
    }


def prepare(root, output=None):
    root = Path(root).resolve()
    output = Path(output or root / BUILD).resolve()
    output.mkdir(parents=True, exist_ok=True)
    predecessor_source, qualified_source, installed = source_states(
        (root / SOURCE).read_text())

    with (root / GUARDS).open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        live_rows = list(reader)
    target_rows = [row for row in live_rows
                   if row["filename"] == FILENAME and row["function"] == FUNCTION]
    expected_rows = [complete_row(row) for row in PATCH_ROWS]
    if installed:
        if target_rows != expected_rows:
            raise ValueError("Installed embedded dual-phase position guards changed")
    elif target_rows:
        raise ValueError("Unexpected embedded dual-phase position guards")
    predecessor_rows = [row for row in live_rows
                        if not (row["filename"] == FILENAME and
                                row["function"] == FUNCTION)]
    qualified_rows = predecessor_rows + expected_rows

    predecessor_compact, before = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostics(before) != diagnostics(after):
        raise ValueError("Embedded dual-phase position owner diagnostics changed")
    raw, bindings = checked_candidate(root, qualified_compact)

    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_rows, fields,
        "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, qualified_rows, fields,
        "qualified-owner")
    live_owner = qualified_owner if installed else predecessor_owner
    if live_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Embedded dual-phase position selected owner differs from production")
    if function_blob(qualified_owner) != (retail_object_bytes(root), BINDINGS):
        raise ValueError("Embedded dual-phase position qualified owner differs from retail")

    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Embedded dual-phase position normalized pools changed")
    predecessor_elf = link_image(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    expected_live = qualified_elf if installed else predecessor_elf
    if (root / ELF).read_bytes() != expected_live.read_bytes():
        raise ValueError("Embedded dual-phase position selected image differs from production")

    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Embedded dual-phase position full-image closure changed: " + repr(changed))
    if new[FUNCTION] != list(struct.unpack(">%dI" % WORDS, retail_bytes(root))):
        raise ValueError("Embedded dual-phase position linked payload differs from retail")
    data = audit_layout(qualified_elf, root / "conker")
    if (not data["exact"] or data["bytes"] != 189088 or
            data["owner_count"] != 720 or data["different_bytes"] != 0):
        raise ValueError("Embedded dual-phase position protected data changed")

    (output / "proposed-owner.c").write_text(qualified_source)
    (output / "qualified-patches.csv").write_text(
        (output / "qualified-owner/retail-word-patches.csv").read_text())
    report = {
        "function": FUNCTION,
        "source_installed": installed,
        "words": WORDS,
        "natural_frame": NATURAL_FRAME,
        "retail_frame": RETAIL_FRAME,
        "natural_positional_differences": len(PATCH_ROWS),
        "guards": len(PATCH_ROWS),
        "relocations": len(bindings),
        "neighbors": neighbors,
        "raw_sha256": digest(raw),
        "retail_sha256": digest(retail_bytes(root)),
        "qualified_owner_sha256": digest(qualified_owner.read_bytes()),
        "predecessor_elf_sha256": digest(predecessor_elf.read_bytes()),
        "qualified_elf_sha256": digest(qualified_elf.read_bytes()),
        "functions": len(new),
        "changed_bodies": changed,
        "all_addresses_fixed": True,
        "strict_exclusions": 0,
        "registry": registry_evidence(root),
        "game_data": data,
    }
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return {
        "report": report,
        "predecessor_owner": predecessor_owner,
        "qualified_owner": qualified_owner,
        "predecessor_elf": predecessor_elf,
        "qualified_elf": qualified_elf,
        "fields": fields,
        "predecessor_rows": predecessor_rows,
        "qualified_rows": qualified_rows,
        "qualified_compact": qualified_compact,
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)["report"], indent=2))

