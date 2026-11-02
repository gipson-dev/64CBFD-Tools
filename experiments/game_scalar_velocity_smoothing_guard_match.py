"""Qualify the scalar position/velocity smoother's guarded retail match."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.experiments import game_scalar_velocity_smoothing_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset,
    symbol_rows,
)
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly


FUNCTION = candidate.FUNCTION
FILENAME = "generated_76A60"
SOURCE = candidate.SOURCE
ASM = candidate.ASM
ENTRY = candidate.ENTRY
ROM = candidate.ROM
RETAIL_WORDS = candidate.RETAIL_WORDS
CANDIDATE_WORDS = 55
RETAIL_SIZE = RETAIL_WORDS * 4
CANDIDATE_SIZE = CANDIDATE_WORDS * 4
RETAIL_FRAME = 24
CANDIDATE_FRAME = 16
OMIT_OFFSET = 0x08C
BUILD = "conker/build/game-scalar-velocity-smoothing-150495B0-guard-match"
RETAIL_SHA256 = candidate.RETAIL_SHA256
CANDIDATE_SHA256 = "0ab6c7e108330c06f91011f6e58ada22f91b06a5235ab1f1bd4ede4e72ac164f"
OFFSETS = (0x008, 0x038, 0x044, 0x048, 0x04C, 0x050, 0x058, 0x060,
    0x064, 0x068, 0x06C, 0x070, 0x074, 0x078, 0x07C, 0x080, 0x084,
    0x088, 0x08C, 0x0BC, 0x0C8, 0x0D0, 0x0D8)
PATHS = {
    "source": SOURCE,
    "object": "conker/build/src/game/generated_76A60.c.o",
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
        raise ValueError("Scalar smoother retail slot changed")
    return data


def compile_candidate(root, output):
    output.mkdir(parents=True, exist_ok=True)
    obj, diagnostics = compile_owner(root, output, candidate.SELECTED, "guard-candidate")
    if diagnostics:
        raise ValueError("Scalar smoother compiler diagnostics changed: " + diagnostics)
    raw, bindings = payload(obj, FUNCTION)
    if (len(raw), digest(raw), bindings) != (CANDIDATE_SIZE, CANDIDATE_SHA256, {}):
        raise ValueError("Scalar smoother compiler payload changed")
    words = struct.unpack(">%dI" % CANDIDATE_WORDS, raw)
    frame = next((0x10000 - (word & 0xFFFF) for word in words
                  if word >> 16 == 0x27BD and word & 0x8000), 0)
    if frame != CANDIDATE_FRAME:
        raise ValueError("Scalar smoother compiler frame changed")
    return obj, raw


def guard_rows(raw, retail):
    candidate_words = struct.unpack(">%dI" % CANDIDATE_WORDS, raw)
    retail_words = struct.unpack(">%dI" % RETAIL_WORDS, retail)
    rows = []
    retail_index = 0
    note = "Normalize scalar smoother frame, floating-register and local schedule allocation"
    for candidate_index, word in enumerate(candidate_words):
        offset = candidate_index * 4
        if offset == OMIT_OFFSET:
            if word != 0:
                raise ValueError("Scalar smoother omitted instruction is no longer nop")
            replacement = word
            omit = True
        else:
            replacement = retail_words[retail_index]
            retail_index += 1
            omit = False
            if word == replacement:
                continue
        rows.append({
            "filename": FILENAME,
            "function": FUNCTION,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % word,
            "replacement": "0x%08X" % replacement,
            "expected_relocations": "-",
            "replacement_relocations": "-",
            "note": note,
            "insert_after": "",
            "insert_after_relocations": "",
            "omit": "true" if omit else "false",
        })
    if retail_index != RETAIL_WORDS or tuple(int(row["offset"], 0) for row in rows) != OFFSETS:
        raise ValueError("Scalar smoother guard projection changed")
    return rows


def normalized_payload(raw, rows):
    by_offset = {int(row["offset"], 0): row for row in rows}
    output = []
    for index, word in enumerate(struct.unpack(">%dI" % CANDIDATE_WORDS, raw)):
        offset = index * 4
        row = by_offset.get(offset)
        if row:
            if word != int(row["expected"], 0):
                raise ValueError("Scalar smoother expected guard word changed")
            if row["omit"] == "true":
                continue
            word = int(row["replacement"], 0)
        output.append(word)
    if len(output) != RETAIL_WORDS:
        raise ValueError("Scalar smoother normalization extent changed")
    return struct.pack(">%dI" % RETAIL_WORDS, *output)


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
            raise ValueError("Installed scalar smoother guards differ from qualification")
        return before[:-len(suffix)], before, True
    if not before.endswith((b"\n", b"\r")):
        raise ValueError("Guard table has no terminating newline")
    return before, before + suffix, False


def source_states(source):
    proposed, installed = candidate.production_source(source)
    if installed:
        start, end = function_span(source, FUNCTION)
        predecessor = source[:start] + candidate.PLACEHOLDER + source[end:]
    else:
        predecessor = source
    return predecessor, proposed, installed


def build_owner(root, output, source, guards, label):
    compact, diagnostics = compile_owner(root, output, source, label + "-compact")
    if diagnostics:
        raise ValueError("Scalar smoother owner diagnostics changed: " + diagnostics)
    assembly = output / (label + ".s")
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=guards, filename=FILENAME))
    obj = output / (label + ".o")
    subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly)], check=True, capture_output=True, text=True)
    return obj


def link_owner(root, output, owner, label):
    old = "build/src/game/generated_76A60.c.o"
    new = str(owner.relative_to(root / "conker")).replace("\\", "/")
    linker = (root / PATHS["linker"]).read_text()
    if linker.count(old) != 1:
        raise ValueError("Scalar smoother linker owner reference changed")
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
    offset = elf_slot_offset(predecessor, ENTRY, RETAIL_SIZE)
    result[offset:offset + RETAIL_SIZE] = retail
    rows = [position for position, name, fields, _ in symbol_rows(predecessor)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError("Scalar smoother predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0] + 8, RETAIL_SIZE)
    return bytes(result)


def closure_audit(predecessor, qualified):
    old, _, old_addresses = load_elf_functions(str(predecessor), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(str(qualified), "mips-linux-gnu-objdump")
    if set(old) != set(new) or old_addresses != new_addresses:
        raise ValueError("Scalar smoother function inventory or addresses changed")
    changed = [name for name in new if old[name] != new[name]]
    if changed != [FUNCTION]:
        raise ValueError("Scalar smoother executable closure changed: " + repr(changed))
    return {"functions": len(new), "changed_bodies": changed,
            "all_addresses_fixed": True, "strict_exclusions": 0}


def prepare(root, output=None):
    root = Path(root).resolve()
    output = Path(output or root / BUILD).resolve()
    output.mkdir(parents=True, exist_ok=True)
    retail = retail_bytes(root)
    candidate_obj, raw = compile_candidate(root, output)
    rows = guard_rows(raw, retail)
    if normalized_payload(raw, rows) != retail:
        raise ValueError("Scalar smoother guards do not reproduce retail")
    predecessor_guards, qualified_guards, installed = guard_manifests(
        (root / PATHS["guards"]).read_bytes(), rows)
    predecessor_guards_path = output / "predecessor-guards.csv"
    qualified_guards_path = output / "qualified-guards.csv"
    predecessor_guards_path.write_bytes(predecessor_guards)
    qualified_guards_path.write_bytes(qualified_guards)
    predecessor_source, qualified_source, source_installed = source_states(
        (root / SOURCE).read_text())
    if installed != source_installed:
        raise ValueError("Scalar smoother source and guard installation state disagree")
    predecessor_owner = build_owner(root, output, predecessor_source,
                                    predecessor_guards_path, "predecessor-owner")
    qualified_owner = build_owner(root, output, qualified_source,
                                  qualified_guards_path, "qualified-owner")
    qualified_raw, qualified_bindings = payload(qualified_owner, FUNCTION)
    if qualified_raw != retail or qualified_bindings:
        raise ValueError("Scalar smoother qualified owner differs from retail")
    predecessor_elf = link_owner(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_owner(root, output, qualified_owner, "qualified-image")
    predicted = output / "expected-qualified.elf"
    predicted.write_bytes(expected_image(predecessor_elf.read_bytes(), retail))
    if qualified_elf.read_bytes() != predicted.read_bytes():
        raise ValueError("Scalar smoother private link differs from independent prediction")
    closure = closure_audit(predecessor_elf, qualified_elf)
    current = (root / PATHS["elf"]).read_bytes()
    expected_live = qualified_elf.read_bytes() if installed else predecessor_elf.read_bytes()
    if current != expected_live:
        raise ValueError("Scalar smoother live image differs from qualified state")
    report = {
        "function": FUNCTION,
        "installed": installed,
        "candidate_words": CANDIDATE_WORDS,
        "retail_words": RETAIL_WORDS,
        "candidate_frame": CANDIDATE_FRAME,
        "retail_frame": RETAIL_FRAME,
        "guards": len(rows),
        "replacements": sum(row["omit"] == "false" for row in rows),
        "omissions": sum(row["omit"] == "true" for row in rows),
        "insertions": 0,
        "relocations": 0,
        "candidate_sha256": digest(raw),
        "retail_sha256": digest(retail),
        "qualified_owner_sha256": digest(qualified_owner.read_bytes()),
        "predecessor_elf_sha256": digest(predecessor_elf.read_bytes()),
        "qualified_elf_sha256": digest(qualified_elf.read_bytes()),
        "closure": closure,
    }
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report, rows, candidate_obj, predecessor_owner, qualified_owner, predecessor_elf, qualified_elf


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
