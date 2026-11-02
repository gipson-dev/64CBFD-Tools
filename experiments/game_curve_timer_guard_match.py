"""Qualify func_15131DEC as a one-guard byte-exact C recovery."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_curve_timer_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset, symbol_rows
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly


FUNCTION = candidate.FUNCTION
FILENAME = candidate.OWNER
SOURCE = candidate.SOURCE
ASM = "conker/asm/15D730.s"
ENTRY = 0x15131DEC
ROM = candidate.ROM
SIZE = candidate.SIZE
WORDS = SIZE // 4
BUILD = "conker/build/game-curve-timer-15131DEC-guard-match"
RETAIL_SHA256 = "c83255773ddb4fd4113dbaa3632e7018ce47ce7dc401b60b358e971112cb3468"
CANDIDATE_RAW_SHA256 = "e0ec7b930f0399db0b848cdcbd234ff153a3b03cf1160dde404e6984d43cb1b4"
CANDIDATE_LINKED_SHA256 = "aadbeb831f2d7023849238973a0eacc407d6c95fc30f16349bd2dc640c344204"
BINDINGS = {
    0xBC: [("R_MIPS_HI16", "D_800BE9A4")],
    0xC4: [("R_MIPS_LO16", "D_800BE9A4")],
}
GUARD = (0x24, 0x46002302, 0x46040302)
PATHS = {
    "source": SOURCE,
    "object": "conker/build/src/game/generated_15D730.c.o",
    "elf": "conker/build/conker.us.elf",
    "linker": "conker/build/conker.ld",
    "guards": "conker/retail_word_patches.us.csv",
    "asm": ASM,
    "rom": "conker/conker.us.bin",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def retail_bytes(root):
    data = (root / PATHS["rom"]).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Curve-timer retail slot changed")
    return data


def compile_candidate(root, output):
    source, _ = candidate.production_source((root / SOURCE).read_text())
    obj, diagnostics = compile_owner(root, output, source, "guard-candidate")
    if diagnostics:
        raise ValueError("Curve-timer compiler diagnostics changed: " + diagnostics)
    raw, bindings = payload(obj, FUNCTION)
    if (len(raw), digest(raw), bindings) != (SIZE, CANDIDATE_RAW_SHA256, BINDINGS):
        raise ValueError("Curve-timer compiler payload changed")
    if digest(linked_payload(raw)) != CANDIDATE_LINKED_SHA256:
        raise ValueError("Curve-timer linked compiler payload changed")
    return obj, raw


def linked_payload(raw):
    result = bytearray(raw)
    struct.pack_into(">I", result, 0xBC, 0x3C01800C)
    struct.pack_into(">I", result, 0xC4, 0xC428E9A4)
    return bytes(result)


def guard_rows(raw, retail):
    expected_offset, expected_word, replacement = GUARD
    candidate_words = struct.unpack(">%dI" % WORDS, linked_payload(raw))
    retail_words = struct.unpack(">%dI" % WORDS, retail)
    differences = [(index * 4, actual, expected)
                   for index, (actual, expected) in enumerate(
                       zip(candidate_words, retail_words)) if actual != expected]
    if differences != [GUARD]:
        raise ValueError("Curve-timer compiler gap changed: " + repr(differences))
    return [{
        "filename": FILENAME,
        "function": FUNCTION,
        "offset": "0x%03X" % expected_offset,
        "expected": "0x%08X" % expected_word,
        "replacement": "0x%08X" % replacement,
        "expected_relocations": "-",
        "replacement_relocations": "-",
        "note": "Preserve retail commutative curve-timer MUL.S operand order",
        "insert_after": "",
        "insert_after_relocations": "",
        "omit": "false",
    }]


def normalized_payload(raw, rows):
    result = bytearray(linked_payload(raw))
    for row in rows:
        offset = int(row["offset"], 0)
        actual = struct.unpack_from(">I", result, offset)[0]
        if actual != int(row["expected"], 0):
            raise ValueError("Curve-timer expected guard word changed")
        struct.pack_into(">I", result, offset, int(row["replacement"], 0))
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
            raise ValueError("Installed curve-timer guard differs from qualification")
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
        raise ValueError("Installed curve-timer declaration state changed")
    predecessor = predecessor.replace(candidate.DECLARATIONS, "", 1)
    return predecessor, proposed, True


def build_owner(root, output, source, guards, label):
    compact, diagnostics = compile_owner(root, output, source, label + "-compact")
    if diagnostics:
        raise ValueError("Curve-timer owner diagnostics changed: " + diagnostics)
    assembly = output / (label + ".s")
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=guards, filename=FILENAME))
    obj = output / (label + ".o")
    subprocess.run(["mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly)], check=True, capture_output=True, text=True)
    return obj


def link_owner(root, output, owner, label):
    old = "build/src/game/generated_15D730.c.o"
    new = str(owner.relative_to(root / "conker")).replace("\\", "/")
    linker = (root / PATHS["linker"]).read_text()
    if linker.count(old) != 1:
        raise ValueError("Curve-timer linker owner reference changed")
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
    offset = elf_slot_offset(predecessor, ENTRY, SIZE)
    result[offset:offset + SIZE] = retail
    rows = [position for position, name, fields, _ in symbol_rows(predecessor)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError("Curve-timer predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0] + 8, SIZE)
    return bytes(result)


def closure_audit(predecessor, qualified):
    old, _, old_addresses = load_elf_functions(str(predecessor), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(str(qualified), "mips-linux-gnu-objdump")
    if set(old) != set(new) or old_addresses != new_addresses:
        raise ValueError("Curve-timer function inventory or addresses changed")
    changed = [name for name in new if old[name] != new[name]]
    if changed != [FUNCTION]:
        raise ValueError("Curve-timer executable closure changed: " + repr(changed))
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
        raise ValueError("Curve-timer guard does not reproduce retail")
    predecessor_guards, qualified_guards, guard_installed = guard_manifests(
        (root / PATHS["guards"]).read_bytes(), rows)
    predecessor_guards_path = output / "predecessor-guards.csv"
    qualified_guards_path = output / "qualified-guards.csv"
    predecessor_guards_path.write_bytes(predecessor_guards)
    qualified_guards_path.write_bytes(qualified_guards)
    predecessor_source, qualified_source, source_installed = source_states(
        (root / SOURCE).read_text())
    if guard_installed != source_installed:
        raise ValueError("Curve-timer source and guard installation state disagree")
    predecessor_owner = build_owner(root, output, predecessor_source,
                                    predecessor_guards_path, "predecessor-owner")
    qualified_owner = build_owner(root, output, qualified_source,
                                  qualified_guards_path, "qualified-owner")
    qualified_raw, qualified_bindings = payload(qualified_owner, FUNCTION)
    if linked_payload(qualified_raw) != retail or qualified_bindings != BINDINGS:
        raise ValueError("Curve-timer qualified owner differs from retail")
    predecessor_elf = link_owner(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_owner(root, output, qualified_owner, "qualified-image")
    predicted = output / "expected-qualified.elf"
    predicted.write_bytes(expected_image(predecessor_elf.read_bytes(), retail))
    if qualified_elf.read_bytes() != predicted.read_bytes():
        raise ValueError("Curve-timer private link differs from literal prediction")
    closure = closure_audit(predecessor_elf, qualified_elf)
    current = (root / PATHS["elf"]).read_bytes()
    if current == qualified_elf.read_bytes():
        image_installed = True
    elif current == predecessor_elf.read_bytes():
        image_installed = False
    else:
        raise ValueError("Curve-timer live image differs from qualified state")
    report = {
        "function": FUNCTION,
        "installed": source_installed,
        "image_installed": image_installed,
        "words": WORDS,
        "frame": 0,
        "guards": len(rows),
        "replacements": 1,
        "omissions": 0,
        "insertions": 0,
        "relocations": 2,
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
