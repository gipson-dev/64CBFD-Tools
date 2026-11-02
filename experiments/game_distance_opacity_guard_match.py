"""Qualify func_15179CB0 as a one-guard byte-exact C recovery."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_distance_opacity_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset, symbol_rows
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
ASM = "conker/asm/1A6360.s"
ENTRY = 0x15179CB0
ROM = candidate.ROM
BODY_SIZE = 0xF8
SLOT_SIZE = candidate.SIZE
WORDS = SLOT_SIZE // 4
BUILD = "conker/build/game-distance-opacity-15179CB0-guard-match"
RETAIL_SHA256 = "7ab3e37f5ec40fea045320a042a94c4045ba39338defb1cdb4113e631aa2c823"
CANDIDATE_RAW_SHA256 = "3ccd9207905b3a5d2cf18c30f0070c0936503e7f363c15c073e862c536a5eb7a"
CANDIDATE_LINKED_SHA256 = "4ea50c1839b7cea994c29fb54ba5d3eab2d43cd62dc0746032d566d157527015"
BINDINGS = {
    0x008: [("R_MIPS_HI16", "D_800DBFF0")],
    0x010: [("R_MIPS_LO16", "D_800DBFF0")],
}
RELOCATED_WORDS = {
    0x008: 0x3C02800E,
    0x010: 0x8C42BFF0,
}
GUARDS = ((0x060, 0x46080282, 0x46004282),)
PATHS = {
    "source": SOURCE,
    "object": "conker/build/src/game/generated_1A6360.c.o",
    "elf": "conker/build/conker.us.elf",
    "linker": "conker/build/conker.ld",
    "guards": "conker/retail_word_patches.us.csv",
    "asm": ASM,
    "rom": "conker/conker.us.bin",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def retail_slot(root):
    data = (root / PATHS["rom"]).read_bytes()[ROM:ROM + SLOT_SIZE]
    if len(data) != SLOT_SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Distance-opacity retail slot changed")
    if data[BODY_SIZE:] != b"\0" * (SLOT_SIZE - BODY_SIZE):
        raise ValueError("Distance-opacity retail owner tail changed")
    return data


def linked_payload(raw):
    result = bytearray(raw)
    for offset, word in RELOCATED_WORDS.items():
        struct.pack_into(">I", result, offset, word)
    return bytes(result)


def compile_candidate(root, output):
    source, _ = candidate.production_source((root / SOURCE).read_text())
    obj, diagnostics = compile_owner(root, output, source, "guard-candidate")
    if diagnostics:
        raise ValueError("Distance-opacity compiler diagnostics changed: " + diagnostics)
    raw, bindings = payload(obj, FUNCTION)
    if (len(raw), digest(raw), bindings) != (BODY_SIZE, CANDIDATE_RAW_SHA256, BINDINGS):
        raise ValueError("Distance-opacity compiler payload changed")
    if digest(linked_payload(raw)) != CANDIDATE_LINKED_SHA256:
        raise ValueError("Distance-opacity linked compiler payload changed")
    return obj, raw


def guard_rows(raw, retail):
    candidate_words = struct.unpack(">%dI" % (BODY_SIZE // 4), linked_payload(raw))
    retail_words = struct.unpack(">%dI" % (BODY_SIZE // 4), retail[:BODY_SIZE])
    differences = [(index * 4, actual, expected)
                   for index, (actual, expected) in enumerate(
                       zip(candidate_words, retail_words)) if actual != expected]
    if differences != list(GUARDS):
        raise ValueError("Distance-opacity compiler gap changed: " + repr(differences))
    return [{
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": "0x%03X" % offset,
        "expected": "0x%08X" % expected,
        "replacement": "0x%08X" % replacement,
        "expected_relocations": "-",
        "replacement_relocations": "-",
        "note": "Preserve retail commutative distance-scale MUL.S operand order",
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    } for offset, expected, replacement in GUARDS]


def normalized_slot(raw, rows):
    result = bytearray(linked_payload(raw))
    for row in rows:
        offset = int(row["offset"], 0)
        actual = struct.unpack_from(">I", result, offset)[0]
        if actual != int(row["expected"], 0):
            raise ValueError("Distance-opacity expected guard word changed")
        struct.pack_into(">I", result, offset, int(row["replacement"], 0))
    result.extend(b"\0" * (SLOT_SIZE - len(result)))
    return bytes(result)


def suffix_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
    writer.writerows(rows)
    return stream.getvalue().encode("ascii")


def guard_manifests(before, rows):
    with io.StringIO(before.decode(), newline="") as stream:
        live = [row for row in csv.DictReader(stream) if row["function"] == FUNCTION]
    suffix = suffix_bytes(rows)
    if live:
        if live != rows or not before.endswith(suffix):
            raise ValueError("Installed distance-opacity guard differs from qualification")
        return before[:-len(suffix)], before, True
    if not before.endswith((b"\n", b"\r")):
        raise ValueError("Guard table has no terminating newline")
    return before, before + suffix, False


def source_states(source):
    proposed, installed = candidate.production_source(source)
    if not installed:
        return source, proposed, False
    start, end = function_span(source, FUNCTION)
    predecessor = source[:start] + candidate.PLACEHOLDER + source[end:]
    if predecessor.count(candidate.DECLARATIONS) != 1:
        raise ValueError("Installed distance-opacity declaration state changed")
    predecessor = predecessor.replace(candidate.DECLARATIONS, "", 1)
    return predecessor, proposed, True


def build_owner(root, output, source, guards, label):
    compact, diagnostics = compile_owner(root, output, source, label + "-compact")
    if diagnostics:
        raise ValueError("Distance-opacity owner diagnostics changed: " + diagnostics)
    assembly = output / (label + ".s")
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=guards, filename=FILENAME))
    obj = output / (label + ".o")
    subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly)], check=True, capture_output=True, text=True)
    return obj


def link_owner(root, output, owner, label):
    old = "build/src/game/generated_1A6360.c.o"
    new = str(owner.relative_to(root / "conker")).replace("\\", "/")
    linker = (root / PATHS["linker"]).read_text()
    if linker.count(old) != 1:
        raise ValueError("Distance-opacity linker owner reference changed")
    script = output / (label + ".ld")
    script.write_text(linker.replace(old, new))
    elf = output / (label + ".elf")
    map_path = output / (label + ".map")
    subprocess.run(["mips-linux-gnu-ld", "-T", str(script.relative_to(root / "conker")),
        "-Map", str(map_path.relative_to(root / "conker")), "-T", "undefined_syms.us.txt",
        "-T", "undefined_funcs.us.txt", "-T", "undefined_syms_auto.txt", "-T",
        "undefined_funcs_auto.txt", "--no-check-sections", "--no-warn-mismatch", "-o",
        str(elf.relative_to(root / "conker"))], cwd=root / "conker", check=True,
        capture_output=True, text=True)
    return elf


def expected_image(predecessor, retail):
    result = bytearray(predecessor)
    offset = elf_slot_offset(predecessor, ENTRY, SLOT_SIZE)
    result[offset:offset + SLOT_SIZE] = retail
    rows = [position for position, name, fields, _ in symbol_rows(predecessor)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError("Distance-opacity predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0] + 8, BODY_SIZE)
    return bytes(result)


def closure_audit(predecessor, qualified):
    old, _, old_addresses = load_elf_functions(str(predecessor), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(str(qualified), "mips-linux-gnu-objdump")
    if set(old) != set(new) or old_addresses != new_addresses:
        raise ValueError("Distance-opacity function inventory or addresses changed")
    changed = [name for name in new if old[name] != new[name]]
    if changed != [FUNCTION]:
        raise ValueError("Distance-opacity executable closure changed: " + repr(changed))
    return {"functions": len(new), "changed_bodies": changed,
            "all_addresses_fixed": True, "strict_exclusions": 0}


def prepare(root, output=None):
    root = Path(root).resolve()
    output = Path(output or root / BUILD).resolve()
    output.mkdir(parents=True, exist_ok=True)
    retail = retail_slot(root)
    candidate_obj, raw = compile_candidate(root, output)
    rows = guard_rows(raw, retail)
    if normalized_slot(raw, rows) != retail:
        raise ValueError("Distance-opacity guard does not reproduce retail slot")
    predecessor_guards, qualified_guards, guard_installed = guard_manifests(
        (root / PATHS["guards"]).read_bytes(), rows)
    predecessor_guards_path = output / "predecessor-guards.csv"
    qualified_guards_path = output / "qualified-guards.csv"
    predecessor_guards_path.write_bytes(predecessor_guards)
    qualified_guards_path.write_bytes(qualified_guards)
    predecessor_source, qualified_source, source_installed = source_states(
        (root / SOURCE).read_text())
    if guard_installed != source_installed:
        raise ValueError("Distance-opacity source and guard installation state disagree")
    predecessor_owner = build_owner(root, output, predecessor_source,
                                    predecessor_guards_path, "predecessor-owner")
    qualified_owner = build_owner(root, output, qualified_source,
                                  qualified_guards_path, "qualified-owner")
    qualified_raw, qualified_bindings = payload(qualified_owner, FUNCTION)
    if (normalized_slot(qualified_raw, []) != retail or
            qualified_bindings != BINDINGS):
        raise ValueError("Distance-opacity qualified owner differs from retail")
    predecessor_elf = link_owner(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_owner(root, output, qualified_owner, "qualified-image")
    predicted = output / "expected-qualified.elf"
    predicted.write_bytes(expected_image(predecessor_elf.read_bytes(), retail))
    if qualified_elf.read_bytes() != predicted.read_bytes():
        raise ValueError("Distance-opacity private link differs from literal prediction")
    closure = closure_audit(predecessor_elf, qualified_elf)
    current = (root / PATHS["elf"]).read_bytes()
    if current == qualified_elf.read_bytes():
        image_installed = True
    elif current == predecessor_elf.read_bytes():
        image_installed = False
    else:
        raise ValueError("Distance-opacity live image differs from qualified state")
    report = {
        "function": FUNCTION,
        "installed": source_installed,
        "image_installed": image_installed,
        "words": WORDS,
        "body_words": BODY_SIZE // 4,
        "tail_words": (SLOT_SIZE - BODY_SIZE) // 4,
        "frame": 0,
        "guards": len(rows),
        "replacements": len(rows),
        "omissions": 0,
        "insertions": 0,
        "relocations": len(BINDINGS),
        "candidate_raw_sha256": digest(raw),
        "candidate_linked_sha256": digest(linked_payload(raw)),
        "retail_sha256": digest(retail),
        "qualified_owner_sha256": digest(qualified_owner.read_bytes()),
        "predecessor_elf_sha256": digest(predecessor_elf.read_bytes()),
        "qualified_elf_sha256": digest(qualified_elf.read_bytes()),
        "closure": closure,
    }
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return (report, rows, candidate_obj, predecessor_owner, qualified_owner,
            predecessor_elf, qualified_elf)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-root", type=Path,
                        default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report, *_ = prepare(args.consumer_root, args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
