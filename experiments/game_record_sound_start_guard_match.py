"""Qualify func_150A23E4's guarded record-sound-start retail match."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_record_sound_start_match as candidate
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, symbol_rows)
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
OBJECT = candidate.OBJECT
ASM = "conker/asm/CDE80.s"
ENTRY = candidate.ENTRY
ROM = candidate.ROM
RETAIL_WORDS = 55
CANDIDATE_WORDS = 54
RETAIL_SIZE = RETAIL_WORDS * 4
CANDIDATE_SIZE = CANDIDATE_WORDS * 4
FRAME = 0x40
BUILD = "conker/build/game-record-sound-start-150A23E4-guard-match"
RETAIL_SHA256 = "7dd86eaa37304feb641883029b5d159fcd7b46457b17f107522e4b13e2d5f375"
OFFSETS = (0x018, 0x0B8, 0x0BC, 0x0C0, 0x0C4, 0x0C8, 0x0CC,
           0x0D0, 0x0D4)
PATHS = {
    "source": SOURCE,
    "object": OBJECT,
    "elf": "conker/build/conker.us.elf",
    "linker": "conker/build/conker.ld",
    "guards": "conker/retail_word_patches.us.csv",
    "asm": ASM,
    "rom": "conker/conker.us.bin",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def retail_bytes(root):
    data = (root / PATHS["rom"]).read_bytes()[ROM:ROM + RETAIL_SIZE]
    if len(data) != RETAIL_SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Record sound-start retail slot changed")
    return data


def retail_object_payload(root):
    raw = bytearray(retail_bytes(root))
    if struct.unpack_from(">I", raw, 0x0AC)[0] != 0x0C003E99:
        raise ValueError("Record sound-start retail helper target changed")
    struct.pack_into(">I", raw, 0x0AC, 0x0C000000)
    return bytes(raw), candidate.BINDINGS


def compile_candidate(root, output):
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(
        root, output, candidate.HEADERS + candidate.SELECTED,
        "record-sound-start-guard-candidate")
    if diagnostics:
        raise ValueError("Record sound-start diagnostics changed: " + diagnostics)
    raw, bindings = candidate.checked_payload(*payload(obj, FUNCTION))
    words = struct.unpack(">%dI" % CANDIDATE_WORDS, raw)
    frame = next((0x10000 - (word & 0xFFFF) for word in words
                  if word >> 16 == 0x27BD and word & 0x8000), 0)
    if frame != FRAME:
        raise ValueError("Record sound-start candidate frame changed")
    return obj, raw, bindings


def relocation_text(bindings):
    return "-" if not bindings else ";".join(
        kind + ":" + symbol for kind, symbol in bindings)


def guard_rows(raw, bindings, retail_raw, retail_bindings):
    if bindings != retail_bindings:
        raise ValueError("Record sound-start relocation closure changed")
    raw_words = struct.unpack(">%dI" % CANDIDATE_WORDS, raw)
    retail_words = struct.unpack(">%dI" % RETAIL_WORDS, retail_raw)
    rows = []
    for index, word in enumerate(raw_words):
        offset = index * 4
        replacement = retail_words[index]
        insertion = retail_words[-1] if index == CANDIDATE_WORDS - 1 else None
        if word == replacement and insertion is None:
            continue
        expected_bindings = tuple(bindings.get(offset, ()))
        replacement_bindings = tuple(retail_bindings.get(offset, ()))
        rows.append({
            "filename": FILENAME,
            "function": FUNCTION,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % word,
            "replacement": "0x%08X" % replacement,
            "expected_relocations": relocation_text(expected_bindings),
            "replacement_relocations": relocation_text(replacement_bindings),
            "note": "Normalize closed record sound-start epilogue schedule",
            "insert_after": ("0x%08X" % insertion
                             if insertion is not None else ""),
            "insert_after_relocations": "-" if insertion is not None else "",
            "omit": "false",
        })
    if (tuple(int(row["offset"], 0) for row in rows) != OFFSETS or
            sum(bool(row["insert_after"]) for row in rows) != 1):
        raise ValueError("Record sound-start guard projection changed")
    return rows


def normalized_payload(raw, rows):
    by_offset = {int(row["offset"], 0): row for row in rows}
    output = []
    for index, word in enumerate(struct.unpack(">%dI" % CANDIDATE_WORDS, raw)):
        offset = index * 4
        row = by_offset.get(offset)
        if row:
            if word != int(row["expected"], 0):
                raise ValueError("Record sound-start expected guard word changed")
            word = int(row["replacement"], 0)
        output.append(word)
        if row and row["insert_after"]:
            output.append(int(row["insert_after"], 0))
    if len(output) != RETAIL_WORDS:
        raise ValueError("Record sound-start normalized extent changed")
    return struct.pack(">%dI" % RETAIL_WORDS, *output)


def suffix_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
    writer.writerows(rows)
    return stream.getvalue().encode("ascii")


def guard_manifests(before, rows):
    with io.StringIO(before.decode(), newline="") as stream:
        live = [row for row in csv.DictReader(stream)
                if row["function"] == FUNCTION]
    suffix = suffix_bytes(rows)
    if live:
        if live != rows or not before.endswith(suffix):
            raise ValueError("Installed record sound-start guards differ")
        return before[:-len(suffix)], before, True
    if not before.endswith((b"\n", b"\r")):
        raise ValueError("Guard table has no terminating newline")
    return before, before + suffix, False


def build_owner(root, output, source, guards, label):
    compact, diagnostics = compile_owner(root, output, source, label + "-compact")
    if diagnostics:
        raise ValueError("Record sound-start owner diagnostics changed: " + diagnostics)
    assembly = output / (label + ".s")
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=guards, filename=FILENAME))
    obj = output / (label + ".o")
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly)], check=True, capture_output=True, text=True)
    return obj


def link_owner(root, output, owner, label):
    old = OBJECT.replace("conker/", "")
    new = str(owner.relative_to(root / "conker")).replace("\\", "/")
    linker = (root / PATHS["linker"]).read_text()
    if linker.count(old) != 1:
        raise ValueError("Record sound-start linker owner reference changed")
    script = output / (label + ".ld")
    script.write_text(linker.replace(old, new))
    elf = output / (label + ".elf")
    map_path = output / (label + ".map")
    subprocess.run([
        "mips-linux-gnu-ld", "-T", str(script.relative_to(root / "conker")),
        "-Map", str(map_path.relative_to(root / "conker")), "-T",
        "undefined_syms.us.txt", "-T", "undefined_funcs.us.txt", "-T",
        "undefined_syms_auto.txt", "-T", "undefined_funcs_auto.txt",
        "--no-check-sections", "--no-warn-mismatch", "-o",
        str(elf.relative_to(root / "conker"))], cwd=root / "conker",
        check=True, capture_output=True, text=True)
    return elf


def expected_image(predecessor, retail):
    result = bytearray(predecessor)
    offset = elf_slot_offset(predecessor, ENTRY, RETAIL_SIZE)
    result[offset:offset + RETAIL_SIZE] = retail
    rows = [position for position, name, fields, _ in symbol_rows(predecessor)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and
            fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError("Record sound-start predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0] + 8, RETAIL_SIZE)
    return bytes(result)


def closure_audit(predecessor, qualified):
    old, _, old_addresses = load_elf_functions(
        str(predecessor), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified), "mips-linux-gnu-objdump")
    if set(old) != set(new) or old_addresses != new_addresses:
        raise ValueError("Record sound-start function inventory or addresses changed")
    changed = [name for name in new if old[name] != new[name]]
    if changed != [FUNCTION]:
        raise ValueError("Record sound-start executable closure changed: " +
                         repr(changed))
    return {"functions": len(new), "changed_bodies": changed,
            "all_addresses_fixed": True, "strict_exclusions": 0}


def prepare(root, output=None):
    root = Path(root).resolve()
    output = Path(output or root / BUILD).resolve()
    output.mkdir(parents=True, exist_ok=True)
    retail = retail_bytes(root)
    retail_raw, retail_bindings = retail_object_payload(root)
    candidate_obj, raw, bindings = compile_candidate(root, output)
    rows = guard_rows(raw, bindings, retail_raw, retail_bindings)
    if normalized_payload(raw, rows) != retail_raw:
        raise ValueError("Record sound-start guards do not reproduce retail")
    predecessor_guards, qualified_guards, guards_installed = guard_manifests(
        (root / PATHS["guards"]).read_bytes(), rows)
    predecessor_guards_path = output / "predecessor-guards.csv"
    qualified_guards_path = output / "qualified-guards.csv"
    predecessor_guards_path.write_bytes(predecessor_guards)
    qualified_guards_path.write_bytes(qualified_guards)
    predecessor_source, qualified_source, source_installed = candidate.source_states(
        (root / SOURCE).read_text())
    if guards_installed != source_installed:
        raise ValueError("Record sound-start source and guard states disagree")
    predecessor_owner = build_owner(
        root, output, predecessor_source, predecessor_guards_path,
        "predecessor-owner")
    qualified_owner = build_owner(
        root, output, qualified_source, qualified_guards_path,
        "qualified-owner")
    qualified_raw, qualified_bindings = payload(qualified_owner, FUNCTION)
    if (qualified_raw, qualified_bindings) != (retail_raw, retail_bindings):
        raise ValueError("Record sound-start qualified owner differs from retail")
    predecessor_elf = link_owner(
        root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_owner(root, output, qualified_owner, "qualified-image")
    predicted = expected_image(predecessor_elf.read_bytes(), retail)
    if qualified_elf.read_bytes() != predicted:
        raise ValueError("Record sound-start link differs from literal prediction")
    closure = closure_audit(predecessor_elf, qualified_elf)
    current = (root / PATHS["elf"]).read_bytes()
    if current == qualified_elf.read_bytes():
        image_installed = True
    elif current == predecessor_elf.read_bytes():
        image_installed = False
    else:
        raise ValueError("Record sound-start live image differs from qualified states")
    report = {
        "function": FUNCTION,
        "installed": source_installed,
        "image_installed": image_installed,
        "candidate_words": CANDIDATE_WORDS,
        "retail_words": RETAIL_WORDS,
        "candidate_frame": FRAME,
        "retail_frame": FRAME,
        "guards": len(rows),
        "replacements": len(rows),
        "insertions": sum(bool(row["insert_after"]) for row in rows),
        "relocations": sum(len(value) for value in bindings.values()),
        "candidate_sha256": digest(raw),
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
