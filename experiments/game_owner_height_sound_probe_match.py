"""Qualify func_151AE6B0's height/effect/sound probe as guarded C."""

import csv
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_owner_height_sound_probe_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_four_head_lookup_match import diagnostics
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = candidate.FUNCTION
FILENAME = "generated_1D92F0"
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1D92F0.c.o"
ASM = "conker/asm/1D92F0.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22FA90.rodata.s"
BUILD = "conker/build/game-owner-height-sound-probe-151AE6B0-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
FRAME = 0x40
RAW_SHA256 = "1c74d3480ab1de4bd9dee20549fb90f529b14fb4e701ec28fc37ff213b7c1d32"
RETAIL_SHA256 = "415c4001f2f36babac49392c2059f9267a5e3a96b5374e0134b75b4779f919ac"
NATURAL_BINDINGS = {
    0x014: [("R_MIPS_HI16", "D_800A9D70")],
    0x018: [("R_MIPS_LO16", "D_800A9D70")],
    0x094: [("R_MIPS_26", "func_15045800")],
    0x0C4: [("R_MIPS_26", "func_151ABE40")],
    0x0E4: [("R_MIPS_26", "func_10010FFC")],
}
RETAIL_BINDINGS = {
    0x018: [("R_MIPS_HI16", "D_800A9D70")],
    0x01C: [("R_MIPS_LO16", "D_800A9D70")],
    0x094: [("R_MIPS_26", "func_15045800")],
    0x0C4: [("R_MIPS_26", "func_151ABE40")],
    0x0E4: [("R_MIPS_26", "func_10010FFC")],
}

PATCH_ROWS = (
    dict(offset="0x014", expected="0x3C010000", replacement="0xC4640014",
         expected_relocations="R_MIPS_HI16:D_800A9D70", replacement_relocations="-",
         note="Normalize independent height/sound probe setup schedule"),
    dict(offset="0x018", expected="0xC4260000", replacement="0x3C010000",
         expected_relocations="R_MIPS_LO16:D_800A9D70",
         replacement_relocations="R_MIPS_HI16:D_800A9D70",
         note="Normalize independent height/sound probe setup schedule"),
    dict(offset="0x01C", expected="0xC4640014", replacement="0xC4260000",
         expected_relocations="-", replacement_relocations="R_MIPS_LO16:D_800A9D70",
         note="Normalize independent height/sound probe setup schedule"),
    dict(offset="0x020", expected="0x3C014316", replacement="0xE7A40030",
         note="Normalize independent height/sound probe setup schedule"),
    dict(offset="0x024", expected="0x27A40030", replacement="0xC4600118",
         note="Normalize independent height/sound probe setup schedule"),
    dict(offset="0x028", expected="0xE7A40030", replacement="0x3C014316",
         note="Normalize independent height/sound probe setup schedule"),
    dict(offset="0x02C", expected="0xC4600118", replacement="0x27A40030",
         note="Normalize independent height/sound probe setup schedule"),
    dict(offset="0x088", expected="0xAFA3002C", replacement="0xAFA3003C",
         note="Normalize closed attached-actor spill home"),
    dict(offset="0x0A0", expected="0x8FA3002C", replacement="0x8FA3003C",
         note="Normalize closed attached-actor spill reload"),
    dict(offset="0x0BC", expected="0xAFA3002C", replacement="0xAFA3003C",
         note="Normalize closed attached-actor spill home"),
    dict(offset="0x0CC", expected="0x8FA3002C", replacement="0x8FA3003C",
         note="Normalize closed attached-actor spill reload"),
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
        "expected_relocations": row.get("expected_relocations", "-"),
        "replacement_relocations": row.get("replacement_relocations", "-"),
        "note": row["note"],
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }


def source_states(live):
    marker = '#include <ultra64.h>\n'
    if live.count(candidate.PLACEHOLDER) == 1:
        if candidate.SELECTED in live or candidate.DECLARATIONS in live:
            raise ValueError("Height/sound probe predecessor source changed")
        qualified = live.replace(marker, marker + candidate.DECLARATIONS, 1).replace(
            candidate.PLACEHOLDER, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(candidate.DECLARATIONS) != 1 or candidate.PLACEHOLDER in live:
            raise ValueError("Installed height/sound probe source changed")
        predecessor = live.replace(candidate.DECLARATIONS, "", 1).replace(
            candidate.SELECTED, candidate.PLACEHOLDER, 1)
        return predecessor, live, True
    raise ValueError("Height/sound probe source state changed")


def write_patches(path, fields, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def function_blob(obj):
    text, functions, relocations = parse_object(obj)
    info = functions[FUNCTION]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {offset - start: rows for offset, rows in relocations.items()
                if start <= offset < end}
    return text[start:end], bindings


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Height/sound probe retail bytes changed")
    return data


def retail_object_bytes(root):
    result = bytearray(retail_bytes(root))
    for offset, rows in RETAIL_BINDINGS.items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", result, offset,
                         struct.unpack_from(">I", result, offset)[0] & mask)
    return bytes(result)


def checked_candidate(root, obj):
    raw, bindings = function_blob(obj)
    if len(raw) != SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Height/sound probe natural candidate changed")
    if ((-struct.unpack_from(">I", raw)[0]) & 0xFFFF) != FRAME:
        raise ValueError("Height/sound probe frame changed")
    if bindings != NATURAL_BINDINGS:
        raise ValueError("Height/sound probe bindings changed")
    expected = retail_object_bytes(root)
    differences = [offset for offset in range(0, SIZE, 4)
                   if raw[offset:offset + 4] != expected[offset:offset + 4]]
    wanted = [int(row["offset"], 0) for row in PATCH_ROWS]
    if differences != wanted:
        raise ValueError("Height/sound probe natural difference set changed")
    return raw, bindings


def assemble_owner(root, output, compact, rows, fields, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    patch_file = owner_dir / "retail-word-patches.csv"
    write_patches(patch_file, fields, rows)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=patch_file, filename=FILENAME))
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
        raise ValueError("Height/sound probe linker owner reference changed")
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
    block = registry.split("dlabel D_8008AFD0\n", 1)[1].split(
        "enddlabel D_8008AFD0", 1)[0]
    entries = [line for line in block.splitlines() if ".word" in line]
    if calls or pointers != [0x22FAE8] or block.count(FUNCTION) != 1:
        raise ValueError("Height/sound probe registry evidence changed")
    if entries[22].split(".word", 1)[1].strip() != FUNCTION:
        raise ValueError("Height/sound probe registry slot changed")
    return {
        "direct_jal_calls": [],
        "aligned_pointer_literals": ["0x22fae8"],
        "registry": "D_8008AFD0[22]",
        "abi": "one owner pointer; callback probes its attached actor and returns void",
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
            raise ValueError("Installed height/sound probe guards changed")
    elif target_rows:
        raise ValueError("Unexpected height/sound probe guards")
    predecessor_rows = [row for row in live_rows
                        if not (row["filename"] == FILENAME and
                                row["function"] == FUNCTION)]
    qualified_rows = predecessor_rows + expected_rows

    predecessor_compact, before = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostics(before) != diagnostics(after):
        raise ValueError("Height/sound probe owner diagnostics changed")
    raw, bindings = checked_candidate(root, qualified_compact)

    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_rows, fields,
        "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, qualified_rows, fields,
        "qualified-owner")
    live_owner = qualified_owner if installed else predecessor_owner
    if live_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Height/sound probe selected owner differs from production")
    if function_blob(qualified_owner) != (retail_object_bytes(root), RETAIL_BINDINGS):
        raise ValueError("Height/sound probe qualified owner differs from retail")

    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Height/sound probe normalized pools changed")
    predecessor_elf = link_image(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    expected_live = qualified_elf if installed else predecessor_elf
    if (root / ELF).read_bytes() != expected_live.read_bytes():
        raise ValueError("Height/sound probe selected image differs from production")

    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Height/sound probe full-image closure changed: " + repr(changed))
    if new[FUNCTION] != list(struct.unpack(">%dI" % WORDS, retail_bytes(root))):
        raise ValueError("Height/sound probe linked payload differs from retail")
    data = audit_layout(qualified_elf, root / "conker")
    if (not data["exact"] or data["bytes"] != 189088 or
            data["owner_count"] != 720 or data["different_bytes"] != 0):
        raise ValueError("Height/sound probe protected data changed")

    (output / "proposed-owner.c").write_text(qualified_source)
    (output / "qualified-patches.csv").write_text(
        (output / "qualified-owner/retail-word-patches.csv").read_text())
    report = {
        "function": FUNCTION,
        "source_installed": installed,
        "words": WORDS,
        "frame": FRAME,
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


