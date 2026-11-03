"""Qualify func_1515EB84's linked point-record search as guarded C."""

import csv
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_point_record_search_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_four_head_lookup_match import diagnostics
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = candidate.FUNCTION
FILENAME = "generated_18A8F0"
SOURCE = candidate.SOURCE
OBJECT = "conker/build/src/game/generated_18A8F0.c.o"
ASM = "conker/asm/18A8F0.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
BUILD = "conker/build/game-point-record-search-1515EB84-match"
ENTRY, ROM, WORDS, FRAME = candidate.ENTRY, candidate.ROM, candidate.WORDS, candidate.FRAME
SIZE = WORDS * 4
RAW_SHA256 = "d11e4f45a3d99c989d91924585621a0ddda78043fef2b6aada1066ad41eb9591"
RETAIL_SHA256 = "b1a1865fd83d62120ed64b5299d3affc6b97b7def9ab4e0c2da5fb128ac46780"
BINDINGS = candidate.BINDINGS

PATCH_ROWS = (
    dict(offset="0x020", expected="0x44852000", replacement="0x44853000",
         note="Convert Y through retail temporary F6"),
    dict(offset="0x024", expected="0x44843000", replacement="0x44842000",
         note="Convert X through retail temporary F4"),
    dict(offset="0x02C", expected="0x46802020", replacement="0x46803020",
         note="Complete the Y conversion from retail F6"),
    dict(offset="0x038", expected="0x468030A0", replacement="0x468020A0",
         note="Complete the X conversion from retail F4"),
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
    if live.count(candidate.STUB) == 1:
        if candidate.SELECTED in live or candidate.DECLARATION in live:
            raise ValueError("Point-record-search predecessor source changed")
        qualified = live.replace(
            candidate.ANCHOR, candidate.ANCHOR + candidate.DECLARATION, 1
        ).replace(candidate.STUB, candidate.SELECTED, 1)
        return live, qualified, False
    if live.count(candidate.SELECTED) == 1:
        if live.count(candidate.DECLARATION) != 1 or candidate.STUB in live:
            raise ValueError("Installed point-record-search source changed")
        predecessor = live.replace(candidate.DECLARATION, "", 1).replace(
            candidate.SELECTED, candidate.STUB, 1
        )
        return predecessor, live, True
    raise ValueError("Point-record-search source state changed")


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
    data = (root / candidate.ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Point-record-search retail bytes changed")
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
        raise ValueError("Point-record-search natural candidate changed")
    if ((-struct.unpack_from(">I", raw)[0]) & 0xFFFF) != FRAME:
        raise ValueError("Point-record-search frame changed")
    if bindings != BINDINGS:
        raise ValueError("Point-record-search helper binding changed")
    expected = retail_object_bytes(root)
    differences = [
        offset for offset in range(0, SIZE, 4)
        if raw[offset:offset + 4] != expected[offset:offset + 4]
    ]
    if differences != [0x20, 0x24, 0x2C, 0x38]:
        raise ValueError("Point-record-search natural difference set changed")
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
        raise ValueError("Point-record-search linker owner reference changed")
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


def caller_evidence(root):
    image = (root / candidate.ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    proof = {
        0x18B748: 0x8FA40060,
        0x18B74C: 0x8FA50064,
        0x18B750: 0x8FA60068,
        0x18B754: 0x8FA7006C,
        0x18B758: jal,
        0x18B75C: 0xAFAE0010,
        0x18B900: 0x00003825,
        0x18B904: jal,
        0x18B908: 0xAFAE0010,
    }
    if calls != [0x18B758, 0x18B904] or pointers or any(
            struct.unpack_from(">I", image, offset)[0] != word
            for offset, word in proof.items()):
        raise ValueError("Point-record-search caller evidence changed")
    return {
        "direct_jal_calls": [hex(offset) for offset in calls],
        "aligned_pointer_literals": [],
        "callers": ["func_1515E278", "func_1515E43C"],
        "abi": "five arguments; both callers consume the returned record pointer",
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
            raise ValueError("Installed point-record-search guards changed")
    elif target_rows:
        raise ValueError("Unexpected point-record-search guards")
    predecessor_rows = [row for row in live_rows
                        if not (row["filename"] == FILENAME and
                                row["function"] == FUNCTION)]
    qualified_rows = predecessor_rows + expected_rows

    predecessor_compact, before = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostics(before) != diagnostics(after):
        raise ValueError("Point-record-search owner diagnostics changed")
    raw, bindings = checked_candidate(root, qualified_compact)

    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_rows, fields,
        "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, qualified_rows, fields,
        "qualified-owner")
    live_owner = qualified_owner if installed else predecessor_owner
    if live_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Point-record-search selected owner differs from production")
    if function_blob(qualified_owner) != (retail_object_bytes(root), BINDINGS):
        raise ValueError("Point-record-search qualified owner differs from retail")

    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Point-record-search normalized pools changed")
    predecessor_elf = link_image(
        root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    live_elf = root / ELF
    expected_live = qualified_elf if installed else predecessor_elf
    if live_elf.read_bytes() != expected_live.read_bytes():
        raise ValueError("Point-record-search selected image differs from production")

    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Point-record-search full-image closure changed: " + repr(changed))
    if new[FUNCTION] != list(struct.unpack(">%dI" % WORDS, retail_bytes(root))):
        raise ValueError("Point-record-search linked payload differs from retail")
    data = audit_layout(qualified_elf, root / "conker")
    if (not data["exact"] or data["bytes"] != 189088 or
            data["owner_count"] != 720 or data["different_bytes"] != 0):
        raise ValueError("Point-record-search protected data changed")

    (output / "proposed-owner.c").write_text(qualified_source)
    (output / "qualified-patches.csv").write_text(
        (output / "qualified-owner/retail-word-patches.csv").read_text())
    report = {
        "function": FUNCTION,
        "source_installed": installed,
        "words": WORDS,
        "frame": FRAME,
        "natural_positional_differences": 4,
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
        "caller": caller_evidence(root),
        "game_data": data,
    }
    (output / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
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
