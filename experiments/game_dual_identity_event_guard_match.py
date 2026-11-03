"""Qualify func_151B5A9C's dual-identity event handler as guarded C."""

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


FUNCTION = "func_151B5A9C"
FILENAME = "generated_1E26F0"
SOURCE = "conker/src/game/generated_1E26F0.c"
OBJECT = "conker/build/src/game/generated_1E26F0.c.o"
ASM = "conker/asm/1E26F0.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-dual-identity-event-151B5A9C-guard-match"
ENTRY, ROM, NATURAL_WORDS, WORDS, FRAME = 0x151B5A9C, 0x1E2F4C, 63, 64, 0x18
SIZE = WORDS * 4
RAW_SHA256 = "31f88f922d0cd0587efc21a00a913c1ca5230f6779a79e612e018d4223dd3039"
RETAIL_SHA256 = "d81e4927955f1e633b95370b31158f7802ee4b6fca1ab5e9826d28ab7480f8c4"
RAW_BINDINGS = {0x0E4: [("R_MIPS_26", "func_1516972C")]}
RETAIL_BINDINGS = {0x0E8: [("R_MIPS_26", "func_1516972C")]}
GUARD_ROWS = (
    (0x018, 0x14C10022, 0x14C10023, None),
    (0x084, 0x10000019, 0x1000001A, None),
    (0x08C, 0x54860018, 0x54860019, None),
    (0x09C, 0x10000013, 0xA049058C, 0x10000014),
    (0x0A0, 0xA049058C, 0x8FBF0014, None),
)
ORIGINAL = "s32 func_151B5A9C() {\n    return 0;\n}"
TYPE_ANCHOR = "u8 *func_15083E90(u8);\n"
TYPES = """typedef struct {
    u8 pad0[0x580];
    s32 key0;
    u8 tag0;
    u8 pad585[3];
    s32 key1;
    u8 tag1;
} DualIdentityState151B5A9C;
typedef struct {
    u8 pad0[0x28];
    DualIdentityState151B5A9C identity;
} DualIdentityOwner151B5A9C;
typedef struct {
    s32 key0;
    s32 key1;
    u8 tag0;
    u8 tag1;
} DualIdentityEvent151B5A9C;
void func_1516972C(DualIdentityOwner151B5A9C *);

"""
SELECTED = """/* Replace matching identity pairs or release an owner on command zero. */
void func_151B5A9C(DualIdentityOwner151B5A9C *owner,
                       DualIdentityEvent151B5A9C *event, u8 command) {
    DualIdentityState151B5A9C *state = &owner->identity;
    s32 key;

    if (command == 0x2D) {
        if (state->key0 == event->key0) {
            state->key0 = event->key1;
            state->tag0 = event->tag1;
        } else if (state->key0 == event->key1) {
            state->key0 = event->key0;
            state->tag0 = event->tag0;
        }
        if (state->key1 == event->key0) {
            state->key1 = event->key1;
            state->tag1 = event->tag1;
        } else if (state->key1 == event->key1) {
            state->key1 = event->key0;
            state->tag1 = event->tag0;
        }
    } else if (command == 0) {
        key = event->key0;
        if (state->key0 == key || state->key1 == key ||
            ((u8 *)event)[4] == state->tag0 ||
            ((u8 *)event)[4] == state->tag1) {
            func_1516972C(owner);
        }
    }
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
            raise ValueError("Unexpected dual-identity diagnostic: " + line)
    return Counter(rows)


def source_states(live):
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    if body == ORIGINAL:
        if live.count(TYPES):
            raise ValueError("Dual-identity predecessor types changed")
        qualified = live.replace(TYPE_ANCHOR, TYPES + TYPE_ANCHOR, 1)
        start2, end2 = function_span(qualified, FUNCTION)
        qualified = qualified[:start2] + SELECTED + qualified[end2:]
        return live, qualified, False
    if body == SELECTED.split("\n", 1)[1]:
        purpose = SELECTED.split("\n", 1)[0] + "\n"
        if live.count(TYPES) != 1 or live.count(purpose) != 1:
            raise ValueError("Installed dual-identity source changed")
        predecessor = live.replace(TYPES, "", 1)
        start2, end2 = function_span(predecessor, FUNCTION)
        predecessor = predecessor[:start2] + ORIGINAL + predecessor[end2:]
        return predecessor.replace(purpose, "", 1), live, True
    raise ValueError("Dual-identity source state changed")


def proposed_guards(root, output):
    source = root / GUARDS
    destination = output / "proposed-guards.csv"
    with source.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if any(row["filename"] == FILENAME and row["function"] == FUNCTION
           for row in rows):
        raise ValueError("Dual-identity guards already exist in predecessor")
    for offset, expected, replacement, inserted in GUARD_ROWS:
        rows.append({
            "filename": FILENAME,
            "function": FUNCTION,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % expected,
            "replacement": "0x%08X" % replacement,
            "expected_relocations": "-",
            "replacement_relocations": "-",
            "note": "Normalize closed dual-identity event compiler schedule",
            "insert_after": "" if inserted is None else "0x%08X" % inserted,
            "insert_after_relocations": "" if inserted is None else "-",
            "omit": "false",
        })
    with destination.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames,
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return destination


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Dual-identity retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    struct.pack_into(">I", data, 0x0E8, 0x0C000000)
    return bytes(data)


def checked_candidate(obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != NATURAL_WORDS * 4 or digest(raw) != RAW_SHA256:
        raise ValueError("Dual-identity natural candidate changed")
    if bindings != RAW_BINDINGS:
        raise ValueError("Dual-identity natural binding changed")
    words = struct.unpack(">%dI" % NATURAL_WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Dual-identity frame changed")
    return raw, bindings


def assemble_owner(root, output, compact, guards, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / "generated_1E26F0.c.s"
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=guards,
        filename=FILENAME))
    obj = owner_dir / "generated_1E26F0.c.o"
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
        raise ValueError("Dual-identity linker owner reference changed")
    link_dir = output / label
    link_dir.mkdir(parents=True, exist_ok=True)
    script = link_dir / "conker.ld"
    script.write_text(linker.replace(old, new))
    elf = link_dir / "conker.us.elf"
    map_path = link_dir / "conker.us.map"
    subprocess.run([
        "mips-linux-gnu-ld", "-T", str(script.relative_to(root / "conker")),
        "-Map", str(map_path.relative_to(root / "conker")), "-T",
        "undefined_syms.us.txt", "-T", "undefined_funcs.us.txt", "-T",
        "undefined_syms_auto.txt", "-T", "undefined_funcs_auto.txt",
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
        raise ValueError("Dual-identity predecessor symbol extent changed")
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
    proposed = proposed_guards(root, output) if not installed else output / "proposed-guards.csv"
    predecessor_guards = root / GUARDS
    if installed:
        proposed.write_bytes((root / GUARDS).read_bytes())
        with predecessor_guards.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        selected_rows = [row for row in rows if row["filename"] == FILENAME and
                         row["function"] == FUNCTION]
        if len(selected_rows) != len(GUARD_ROWS):
            raise ValueError("Installed dual-identity guard set changed")
        # Reconstruct a predecessor table for strict before/after closure.
        with predecessor_guards.open(newline="") as stream:
            reader = csv.DictReader(stream)
            fieldnames = reader.fieldnames
            before_rows = [row for row in reader if not
                           (row["filename"] == FILENAME and
                            row["function"] == FUNCTION)]
        predecessor_guards = output / "predecessor-guards.csv"
        with predecessor_guards.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames,
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(before_rows)

    predecessor_compact, before_diagnostics = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after_diagnostics = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostic_counts(before_diagnostics) != diagnostic_counts(after_diagnostics):
        raise ValueError("Dual-identity owner diagnostics changed")
    checked_candidate(qualified_compact)

    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_guards,
        "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, proposed, "qualified-owner")
    expected_owner = qualified_owner if installed else predecessor_owner
    if expected_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Dual-identity selected owner differs from production")
    retail = retail_bytes(root)
    retail_object = retail_object_bytes(root)
    if function_blob(qualified_owner, FUNCTION) != (retail_object, RETAIL_BINDINGS):
        raise ValueError("Dual-identity guarded owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Dual-identity normalized pools changed")

    predecessor_elf = link_image(
        root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(
        root, output, qualified_owner, "qualified-image")
    current_elf = (root / ELF).read_bytes()
    expected_elf = qualified_elf if installed else predecessor_elf
    if expected_elf.read_bytes() != current_elf:
        raise ValueError("Dual-identity selected image differs from production")
    if qualified_elf.read_bytes() != expected_image(
            predecessor_elf.read_bytes(), retail):
        raise ValueError("Dual-identity qualified image differs from literal prediction")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Dual-identity full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Dual-identity protected data changed")

    (output / "proposed-owner.c").write_text(qualified_source)
    report = {
        "function": FUNCTION,
        "installed": installed,
        "natural_words": NATURAL_WORDS,
        "words": WORDS,
        "slot_words": 65,
        "frame": FRAME,
        "guards": len(GUARD_ROWS),
        "insertions": 1,
        "relocations": len(RETAIL_BINDINGS),
        "neighbors": neighbors,
        "raw_sha256": RAW_SHA256,
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
