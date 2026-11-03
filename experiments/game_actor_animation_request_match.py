"""Qualify func_1507F54C's slot-selected actor animation request as direct C."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.check_game_data_layout import audit_layout
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.game_four_head_lookup_match import diagnostics, payload
from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span)
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = "func_1507F54C"
FILENAME = "generated_AC030"
SOURCE = "conker/src/game/generated_AC030.c"
OBJECT = "conker/build/src/game/generated_AC030.c.o"
ASM = "conker/asm/AC030.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-actor-animation-request-1507F54C-match"
ENTRY, ROM, WORDS, FRAME = 0x1507F54C, 0xAC9FC, 61, 0x28
SIZE = WORDS * 4
RAW_SHA256 = "aaac11ae0af6521e041ecea665bc5dca4dd3b84b857d97daca65f5a0aa3e7241"
RETAIL_SHA256 = "7780fc9e928d71998ded20a41b800f5048d3bfc22a5b875dfa069e1dcf13cc90"
BINDINGS = {
    0x040: [("R_MIPS_HI16", "D_800B85A4")],
    0x048: [("R_MIPS_LO16", "D_800B85A4")],
    0x0BC: [("R_MIPS_26", "func_1505E650")],
    0x0DC: [("R_MIPS_26", "func_1505E650")],
}

ANCHOR = "/* Non-matching placeholders for the text-only asm slice asm/AC030.s. */\n"
DECLARATIONS = """
extern u8 D_800B85A4[];
void func_1505E650(u8 *, u16, f32, f32, f32, f32, s32);
"""
STUB = "s32 func_1507F54C() {\n    return 0;\n}"
SELECTED = """/* Start the actor animation selected for its current slot. */
void func_1507F54C(u8 *actor) {
    s32 animation;

    if (actor[0x13C] >= 100) {
        switch (D_800B85A4[actor[0x13C] * 0x32C]) {
        case 0x57:
            animation = 0x115;
            break;
        case 0x8C:
            animation = 0x1A5;
            break;
        case 0xA8:
        case 0xA9:
            animation = 0x1AF;
            break;
        case 0x89:
        case 0xBA:
            animation = 0x1FA;
            break;
        default:
            animation = 0xD8;
            break;
        }
        func_1505E650(actor, animation, 1.0f, 4.0f, 0.0f, 0.0f, 0);
    } else {
        func_1505E650(actor, 0xF, 1.0f, 3.0f, 0.0f, 0.0f, 0);
    }
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    installed_body = SELECTED.split("\n", 1)[1]
    if body == STUB:
        if DECLARATIONS in live or SELECTED in live or live.count(ANCHOR) != 1:
            raise ValueError("Actor-animation-request predecessor source changed")
        qualified = live.replace(ANCHOR, ANCHOR + DECLARATIONS, 1)
        qstart, qend = function_span(qualified, FUNCTION)
        qualified = qualified[:qstart] + SELECTED + qualified[qend:]
        return live, qualified, False
    if body == installed_body:
        if live.count(DECLARATIONS) != 1 or live.count(SELECTED) != 1:
            raise ValueError("Installed actor-animation-request source changed")
        predecessor = live.replace(DECLARATIONS, "", 1)
        predecessor = predecessor.replace(SELECTED, STUB, 1)
        return predecessor, live, True
    raise ValueError("Actor-animation-request source state changed")


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Actor-animation-request retail bytes changed")
    return data


def retail_object_bytes(root):
    data = bytearray(retail_bytes(root))
    for offset, rows in BINDINGS.items():
        mask = 0xFC000000 if rows[0][0] == "R_MIPS_26" else 0xFFFF0000
        struct.pack_into(">I", data, offset,
                         struct.unpack_from(">I", data, offset)[0] & mask)
    return bytes(data)


def checked_candidate(root, obj):
    raw, bindings = payload(obj, FUNCTION)
    if len(raw) != SIZE or digest(raw) != RAW_SHA256:
        raise ValueError("Actor-animation-request natural candidate changed")
    if bindings != BINDINGS or raw != retail_object_bytes(root):
        raise ValueError("Actor-animation-request natural words or bindings changed")
    words = struct.unpack(">%dI" % WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Actor-animation-request frame changed")
    return raw, bindings


def assemble_owner(root, output, compact, label):
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    assembly = owner_dir / (FILENAME + ".c.s")
    assembly.write_text(emit_padded_assembly(
        compact, root / ASM, word_patches_path=root / GUARDS,
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
        raise ValueError("Actor-animation-request linker owner reference changed")
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


def expected_image(predecessor, retail):
    result = bytearray(predecessor)
    offset = elf_slot_offset(predecessor, ENTRY, SIZE)
    result[offset:offset + SIZE] = retail
    rows = [(at, fields) for at, name, fields, _ in symbol_rows(predecessor)
            if name == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 12):
        raise ValueError("Actor-animation-request predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0][0] + 8, SIZE)
    return bytes(result)


def check_image(predecessor, actual, retail):
    if actual != expected_image(predecessor, retail):
        raise ValueError("Actor-animation-request image differs from literal prediction")


def function_blob(obj, name):
    text, functions, relocations = parse_object(obj)
    info = functions[name]
    start, end = info["value"], info["value"] + info["size"]
    bindings = {offset - start: rows for offset, rows in relocations.items()
                if start <= offset < end}
    return text[start:end], bindings


def caller_evidence(root):
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    proof = {
        0xACE18: 0x908F013C,
        0xACE20: 0x29E10064,
        0xACE2C: jal,
        0xACE30: 0x00000000,
        0xACF14: 0x10000005,
        0xACF1C: jal,
        0xACF20: 0x00000000,
        0xACF24: 0x1000006A,
    }
    if calls != [0xACE2C, 0xACF1C] or pointers or any(
            struct.unpack_from(">I", image, at)[0] != word
            for at, word in proof.items()):
        raise ValueError("Actor-animation-request caller evidence changed")
    return {
        "caller": "func_1507F640", "direct_jal_calls": [hex(at) for at in calls],
        "aligned_pointer_literals": [],
        "result": "both call sites branch away without consuming v0",
    }


def prepare(root, output=None):
    root = Path(root).resolve()
    output = Path(output or root / BUILD).resolve()
    output.mkdir(parents=True, exist_ok=True)
    predecessor_source, qualified_source, installed = source_states(
        (root / SOURCE).read_text())
    predecessor_compact, before = compile_owner(
        root, output, predecessor_source, "predecessor-compact")
    qualified_compact, after = compile_owner(
        root, output, qualified_source, "qualified-compact")
    if diagnostics(before) != diagnostics(after):
        raise ValueError("Actor-animation-request owner diagnostics changed")
    raw, bindings = checked_candidate(root, qualified_compact)
    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, "qualified-owner")
    live_owner = qualified_owner if installed else predecessor_owner
    if live_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Actor-animation-request selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (
            retail_object_bytes(root), BINDINGS):
        raise ValueError("Actor-animation-request owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Actor-animation-request normalized pools changed")
    predecessor_elf = link_image(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    retail = retail_bytes(root)
    check_image(predecessor_elf.read_bytes(), qualified_elf.read_bytes(), retail)
    live_elf = (root / ELF).read_bytes()
    expected_live = qualified_elf if installed else predecessor_elf
    if live_elf != expected_live.read_bytes():
        raise ValueError("Actor-animation-request selected image differs from production")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Actor-animation-request full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Actor-animation-request protected data changed")
    (output / "proposed-owner.c").write_text(qualified_source)
    report = {
        "function": FUNCTION, "source_installed": installed,
        "words": WORDS, "frame": FRAME,
        "natural_positional_differences": 0, "guards": 0,
        "relocations": len(bindings), "neighbors": neighbors,
        "raw_sha256": digest(raw), "retail_sha256": digest(retail),
        "qualified_owner_sha256": digest(qualified_owner.read_bytes()),
        "predecessor_elf_sha256": digest(predecessor_elf.read_bytes()),
        "qualified_elf_sha256": digest(qualified_elf.read_bytes()),
        "functions": len(new), "changed_bodies": changed,
        "all_addresses_fixed": True, "strict_exclusions": 0,
        "caller": caller_evidence(root), "game_data": data,
    }
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report, predecessor_owner, qualified_owner, predecessor_elf, qualified_elf


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root)[0], indent=2))
