"""Qualify func_15172E7C's actor channel event dispatch as direct C."""

from collections import Counter
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


FUNCTION = "func_15172E7C"
FILENAME = "generated_1A0100"
SOURCE = "conker/src/game/generated_1A0100.c"
DEPENDENT_SOURCE = "conker/src/game/generated_CDE80.c"
OBJECT = "conker/build/src/game/generated_1A0100.c.o"
DEPENDENT_OBJECT = "conker/build/src/game/generated_CDE80.c.o"
ASM = "conker/asm/1A0100.s"
DEPENDENT_ASM = "conker/asm/CDE80.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-actor-channel-event-15172E7C-match"
ENTRY, ROM, WORDS, FRAME = 0x15172E7C, 0x1A032C, 59, 0x30
SIZE = WORDS * 4
RAW_SHA256 = "57f33ce4c5998bb05227ce39e861c9a8ef5d2988c446f7964e79d6b7db077fb0"
RETAIL_SHA256 = "b38b606e8695b825862fb4a2a3e735f918629d2fb7ff8133ee25f73a0f790acd"
BINDINGS = {
    0x044: [("R_MIPS_HI16", "D_800DD2B0")],
    0x050: [("R_MIPS_HI16", "D_800BE9F0")],
    0x054: [("R_MIPS_LO16", "D_800DD2B0")],
    0x088: [("R_MIPS_26", "func_1517EE40")],
    0x0AC: [("R_MIPS_HI16", "D_800DD2C0")],
    0x0BC: [("R_MIPS_LO16", "D_800DD2C0")],
    0x0C0: [("R_MIPS_LO16", "D_800BE9F0")],
    0x0D0: [("R_MIPS_26", "func_15172D28")],
}
ORIGINAL = "s32 func_15172E7C() {\n    return 0;\n}"
OLD_DECLARATION = "s32 func_15172E7C(struct127 *, u8, s32);"
NEW_DECLARATION = "void func_15172E7C(struct127 *, s32, s32);"
SELECTED = """/* Route an actor's channel event through its active camera or fallback state. */
void func_15172E7C(struct127 *actor, s32 selector, s32 payload) {
    s32 channel = actor->unk127;

    if (actor->health != 0 &&
        (actor->unk31C == NULL || ((s8 *)actor->unk31C)[0x23] <= 0)) {
        if (actor->camera != NULL) {
            if (D_800DD2B0[channel] == -1) {
                func_1517EE40(0, 0, 0, 0xA, 1, channel);
                actor->unk2F8 |= 0x10;
                D_800DD2B0[channel] = selector;
                D_800DD2C0[channel] = payload;
            }
        } else if (selector == D_800BE9F0) {
            func_15172D28((u8 *)actor, payload);
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
            raise ValueError("Unexpected actor-channel diagnostic: " + line)
    return Counter(rows)


def source_states(live):
    include = '#include <ultra64.h>\n'
    include_with_structs = '#include <ultra64.h>\n#include "structs.h"\n'
    old_global = "extern u8 D_800BE9B4;\n"
    new_global = "extern u8 D_800BE9B4;\nextern s32 D_800BE9F0;\n"
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    if body == ORIGINAL:
        if live.count(include_with_structs) or live.count(new_global):
            raise ValueError("Actor channel predecessor preamble changed")
        qualified = live.replace(include, include_with_structs, 1)
        qualified = qualified.replace(old_global, new_global, 1)
        start2, end2 = function_span(qualified, FUNCTION)
        qualified = qualified[:start2] + SELECTED + qualified[end2:]
        return live, qualified, False
    if body == SELECTED.split("\n", 1)[1]:
        purpose = SELECTED.split("\n", 1)[0] + "\n"
        if live.count(include_with_structs) != 1 or live.count(new_global) != 1:
            raise ValueError("Installed actor channel preamble changed")
        predecessor = live.replace(include_with_structs, include, 1)
        predecessor = predecessor.replace(new_global, old_global, 1)
        start2, end2 = function_span(predecessor, FUNCTION)
        predecessor = predecessor[:start2] + ORIGINAL + predecessor[end2:]
        if predecessor.count(purpose) != 1:
            raise ValueError("Installed actor channel purpose comment changed")
        return predecessor.replace(purpose, "", 1), live, True
    raise ValueError("Actor channel source state changed")


def dependent_states(live):
    old_count = live.count(OLD_DECLARATION)
    new_count = live.count(NEW_DECLARATION)
    if (old_count, new_count) == (1, 0):
        return live, live.replace(OLD_DECLARATION, NEW_DECLARATION, 1), False
    if (old_count, new_count) == (0, 1):
        return live.replace(NEW_DECLARATION, OLD_DECLARATION, 1), live, True
    raise ValueError("Actor channel caller declaration state changed")


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Actor channel retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    for offset, rows in BINDINGS.items():
        word = struct.unpack_from(">I", data, offset)[0]
        if rows[0][0] == "R_MIPS_26":
            word = 0x0C000000
        else:
            word &= 0xFFFF0000
        struct.pack_into(">I", data, offset, word)
    return bytes(data)


def checked_candidate(obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Actor channel natural candidate changed")
    if bindings != BINDINGS:
        raise ValueError("Actor channel bindings changed")
    words = struct.unpack(">%dI" % WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Actor channel frame changed")
    return raw, bindings


def assemble_generated(root, output, compact, label, filename):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / (filename + ".c.s")
    asm = ASM if filename == FILENAME else DEPENDENT_ASM
    assembly.write_text(emit_padded_assembly(
        compact, root / asm, word_patches_path=root / GUARDS,
        filename=filename))
    obj = owner_dir / (filename + ".c.o")
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(root / "conker/include"), "-o", str(obj),
        str(assembly)], check=True, capture_output=True)
    return obj


def assemble_owner(root, output, compact, label):
    return assemble_generated(root, output, compact, label, FILENAME)


def link_image(root, output, owner, label):
    old = OBJECT.replace("conker/", "")
    new = str(owner.relative_to(root / "conker")).replace("\\", "/")
    linker = (root / LINKER).read_text()
    if linker.count(old) != 1:
        raise ValueError("Actor channel linker owner reference changed")
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
        raise ValueError("Actor channel predecessor symbol extent changed")
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
    predecessor_source, qualified_source, source_installed = source_states(
        (root / SOURCE).read_text())
    predecessor_dependent, qualified_dependent, dependent_installed = dependent_states(
        (root / DEPENDENT_SOURCE).read_text())
    if source_installed != dependent_installed:
        raise ValueError("Actor channel implementation and caller declaration disagree")

    predecessor_compact, before_diagnostics = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after_diagnostics = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostic_counts(before_diagnostics) != diagnostic_counts(after_diagnostics):
        raise ValueError("Actor channel owner diagnostics changed")
    raw, bindings = checked_candidate(qualified_compact)
    retail = retail_bytes(root)
    retail_object = retail_object_bytes(root)
    if raw != retail_object:
        raise ValueError("Actor channel natural C does not reproduce retail")

    old_dependent, old_dep_diagnostics = compile_owner(
        root, output, predecessor_dependent, "dependent-before")
    new_dependent, new_dep_diagnostics = compile_owner(
        root, output, qualified_dependent, "dependent-after")
    if diagnostic_counts(old_dep_diagnostics) != diagnostic_counts(new_dep_diagnostics):
        raise ValueError("Actor channel dependent diagnostics changed")
    dependent_neighbors = same_functions(old_dependent, new_dependent, ())
    if normalized_pools(old_dependent) != normalized_pools(new_dependent):
        raise ValueError("Actor channel declaration changed caller pools")
    old_dependent_padded = assemble_generated(
        root, output, old_dependent, "dependent-before-owner", "generated_CDE80")
    new_dependent_padded = assemble_generated(
        root, output, new_dependent, "dependent-after-owner", "generated_CDE80")
    if old_dependent_padded.read_bytes() != new_dependent_padded.read_bytes():
        raise ValueError("Actor channel declaration changed the padded caller object")
    if old_dependent_padded.read_bytes() != (root / DEPENDENT_OBJECT).read_bytes():
        raise ValueError("Actor channel dependent differs from production")

    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, "qualified-owner")
    expected_owner = qualified_owner if source_installed else predecessor_owner
    if expected_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Actor channel selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (retail_object, bindings):
        raise ValueError("Actor channel qualified owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Actor channel normalized pools changed")

    predecessor_elf = link_image(
        root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(
        root, output, qualified_owner, "qualified-image")
    current_elf = (root / ELF).read_bytes()
    expected_elf = qualified_elf if source_installed else predecessor_elf
    if expected_elf.read_bytes() != current_elf:
        raise ValueError("Actor channel selected image differs from production")
    if qualified_elf.read_bytes() != expected_image(
            predecessor_elf.read_bytes(), retail):
        raise ValueError("Actor channel qualified image differs from literal prediction")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Actor channel full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Actor channel protected data changed")

    (output / "proposed-owner.c").write_text(qualified_source)
    (output / "proposed-dependent.c").write_text(qualified_dependent)
    report = {
        "function": FUNCTION,
        "installed": source_installed,
        "words": WORDS,
        "slot_words": 61,
        "frame": FRAME,
        "natural_differences": 0,
        "guards": 0,
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
        "dependent_identical": True,
        "dependent_functions_fixed": dependent_neighbors,
        "game_data": data,
    }
    (output / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return report, predecessor_owner, qualified_owner, predecessor_elf, qualified_elf


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)[0], indent=2))
