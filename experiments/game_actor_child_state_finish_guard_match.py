"""Qualify func_1507FEA0's actor child-state finisher as guarded C."""

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


FUNCTION = "func_1507FEA0"
FILENAME = "generated_AC030"
SOURCE = "conker/src/game/generated_AC030.c"
OBJECT = "conker/build/src/game/generated_AC030.c.o"
ASM = "conker/asm/AC030.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-actor-child-state-finish-1507FEA0-guard-match"
ENTRY, ROM, WORDS, FRAME = 0x1507FEA0, 0xAD350, 61, 0x18
SIZE = WORDS * 4
RAW_SHA256 = "02e668794fb1544bd1de43b0f509c7a19dc6e00b20a3d07c883e16235a6a6c20"
RETAIL_SHA256 = "5dbd06b4cd858bf4b29bf073a48425e792f2b3f0e5fcb38b8f3871e1b028db1b"
RAW_BINDINGS = {
    0x02C: [("R_MIPS_HI16", "D_800C35EA")],
    0x050: [("R_MIPS_LO16", "D_800C35EA")],
    0x058: [("R_MIPS_HI16", "D_800BE9E4")],
    0x05C: [("R_MIPS_LO16", "D_800BE9E4")],
    0x0A0: [("R_MIPS_HI16", "D_800BE9E4")],
    0x0AC: [("R_MIPS_LO16", "D_800BE9E4")],
    0x0C8: [("R_MIPS_26", "func_1507FF94")],
    0x0DC: [("R_MIPS_26", "func_1507FC2C")],
}
RETAIL_BINDINGS = {
    0x030: [("R_MIPS_HI16", "D_800C35EA")],
    0x050: [("R_MIPS_LO16", "D_800C35EA")],
    0x058: [("R_MIPS_HI16", "D_800BE9E4")],
    0x05C: [("R_MIPS_LO16", "D_800BE9E4")],
    0x0A0: [("R_MIPS_HI16", "D_800BE9E4")],
    0x0AC: [("R_MIPS_LO16", "D_800BE9E4")],
    0x0C8: [("R_MIPS_26", "func_1507FF94")],
    0x0DC: [("R_MIPS_26", "func_1507FC2C")],
}
GUARD_ROWS = (
    (0x028, 0x90C2013A, 0x90C3013A, "-", "-"),
    (0x02C, 0x3C190000, 0x24A20058, "R_MIPS_HI16:D_800C35EA", "-"),
    (0x030, 0x10400002, 0x3C190000, "-", "R_MIPS_HI16:D_800C35EA"),
    (0x034, 0x244FFFFF, 0x10600002, "-", "-"),
    (0x038, 0xA0CF013A, 0x246FFFFF, "-", "-"),
    (0x03C, 0x24A20058, 0xA0CF013A, "-", "-"),
    (0x060, 0x94440002, 0x94450002, "-", "-"),
    (0x068, 0x01034823, 0x01032023, "-", "-"),
    (0x06C, 0x0089082A, 0x00A4082A, "-", "-"),
    (0x074, 0x00835021, 0x00A34821, "-", "-"),
    (0x078, 0xA44A0002, 0xA4490002, "-", "-"),
    (0x0BC, 0x00435823, 0x00435023, "-", "-"),
    (0x0C4, 0xA4AB0066, 0xA4AA0066, "-", "-"),
    (0x0D4, 0x8CC5031C, 0x8CCB031C, "-", "-"),
    (0x0D8, 0xA4A00066, 0xA5600066, "-", "-"),
)
ORIGINAL = "s32 func_1507FEA0() {\n    return 0;\n}"
DECLARATION_ANCHOR = "extern s32 D_800BE9F0;\n"
DECLARATIONS = """extern s32 D_800BE9E4;
extern u8 D_800C35EA;
void func_1507FF94(u8 *);
"""
SELECTED = """/* Advance or reset an actor's child state, then finish its update. */
void func_1507FEA0(u8 *actor) {
    u8 *child = *(u8 **)(actor + 0x31C);
    u8 *state = child + 0x58;
    u8 countdown;
    s32 timer;
    s32 tick;
    u16 count;

    if (child == NULL || actor[0x127] == 0xFF) {
        return;
    }
    countdown = actor[0x13A];
    if (countdown != 0) {
        actor[0x13A] = countdown - 1;
    }
    if (state[0] == 1 && D_800C35EA != 1) {
        tick = D_800BE9E4;
        count = *(u16 *)(state + 2);
        if (count < 0xFFFF - tick) {
            *(u16 *)(state + 2) = count + tick;
        }
    } else {
        *(u16 *)(state + 2) = 0;
        state[4] = 0;
        state[5] = 0;
        state[0xC] = 0;
        state[0xD] = 0;
    }
    child = *(u8 **)(actor + 0x31C);
    timer = *(s16 *)(child + 0x66);
    if (timer != 0) {
        tick = D_800BE9E4;
        if (tick < timer) {
            *(s16 *)(child + 0x66) = timer - tick;
        } else {
            func_1507FF94(actor);
            child = *(u8 **)(actor + 0x31C);
            *(s16 *)(child + 0x66) = 0;
        }
    }
    func_1507FC2C(actor);
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
            raise ValueError("Unexpected child-state diagnostic: " + line)
    return Counter(rows)


def source_states(live):
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    purpose = SELECTED.split("\n", 1)[0] + "\n"
    if body == ORIGINAL:
        if live.count(DECLARATIONS) or live.count(purpose):
            raise ValueError("Child-state predecessor declarations changed")
        if live.count(DECLARATION_ANCHOR) != 1:
            raise ValueError("Child-state declaration anchor changed")
        qualified = live.replace(
            DECLARATION_ANCHOR, DECLARATION_ANCHOR + DECLARATIONS, 1)
        start2, end2 = function_span(qualified, FUNCTION)
        qualified = qualified[:start2] + SELECTED + qualified[end2:]
        return live, qualified, False
    if body == SELECTED.split("\n", 1)[1]:
        if live.count(DECLARATIONS) != 1 or live.count(purpose) != 1:
            raise ValueError("Installed child-state source changed")
        predecessor = live.replace(DECLARATIONS, "", 1)
        start2, end2 = function_span(predecessor, FUNCTION)
        predecessor = predecessor[:start2] + ORIGINAL + predecessor[end2:]
        return predecessor.replace(purpose, "", 1), live, True
    raise ValueError("Child-state source state changed")


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
            raise ValueError("Installed child-state guard set changed")
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
        raise ValueError("Child-state guards already exist in predecessor")
    for offset, expected, replacement, expected_relocs, replacement_relocs in GUARD_ROWS:
        rows.append({
            "filename": FILENAME,
            "function": FUNCTION,
            "offset": "0x%03X" % offset,
            "expected": "0x%08X" % expected,
            "replacement": "0x%08X" % replacement,
            "expected_relocations": expected_relocs,
            "replacement_relocations": replacement_relocs,
            "note": "Normalize actor child-state finisher compiler allocation and schedule",
            "insert_after": "",
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
        raise ValueError("Child-state retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    for offset, bindings in RETAIL_BINDINGS.items():
        word = struct.unpack_from(">I", data, offset)[0]
        if bindings[0][0] == "R_MIPS_26":
            word &= 0xFC000000
        else:
            word &= 0xFFFF0000
        struct.pack_into(">I", data, offset, word)
    return bytes(data)


def checked_candidate(obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Child-state natural candidate changed: %d %s" %
                         (len(raw), digest(raw)))
    if bindings != RAW_BINDINGS:
        raise ValueError("Child-state natural bindings changed")
    words = struct.unpack(">%dI" % WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Child-state frame changed")
    return raw, bindings


def assemble_owner(root, output, compact, guards, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=guards,
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
        raise ValueError("Child-state linker owner reference changed")
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
        raise ValueError("Child-state predecessor symbol extent changed")
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
        raise ValueError("Child-state owner diagnostics changed")
    raw, bindings = checked_candidate(qualified_compact)
    natural_differences = sum(
        left != right for left, right in zip(
            struct.unpack(">%dI" % WORDS, raw),
            struct.unpack(">%dI" % WORDS, retail_object_bytes(root))))
    if natural_differences != len(GUARD_ROWS):
        raise ValueError("Child-state natural difference count changed")

    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, predecessor_guards,
        "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, proposed, "qualified-owner")
    expected_owner = qualified_owner if installed else predecessor_owner
    if expected_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Child-state selected owner differs from production")
    retail = retail_bytes(root)
    retail_object = retail_object_bytes(root)
    if function_blob(qualified_owner, FUNCTION) != (retail_object, RETAIL_BINDINGS):
        raise ValueError("Child-state guarded owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Child-state normalized pools changed")

    predecessor_elf = link_image(
        root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(
        root, output, qualified_owner, "qualified-image")
    expected_elf = qualified_elf if installed else predecessor_elf
    if expected_elf.read_bytes() != (root / ELF).read_bytes():
        raise ValueError("Child-state selected image differs from production")
    if qualified_elf.read_bytes() != expected_image(
            predecessor_elf.read_bytes(), retail):
        raise ValueError("Child-state qualified image differs from literal prediction")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Child-state full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Child-state protected data changed")

    (output / "proposed-owner.c").write_text(qualified_source)
    report = {
        "function": FUNCTION,
        "installed": installed,
        "words": WORDS,
        "slot_words": WORDS,
        "frame": FRAME,
        "natural_differences": natural_differences,
        "guards": len(GUARD_ROWS),
        "insertions": 0,
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
