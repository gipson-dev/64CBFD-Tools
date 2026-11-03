"""Qualify func_151C61A0's fixed directional-effect submission as direct C."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.check_game_data_layout import audit_layout
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.game_four_head_lookup_match import diagnostics, payload
from tools.experiments.game_remaining_donor_candidates import (
    compile_owner, function_span)
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION = "func_151C61A0"
FILENAME = "generated_1F2730"
SOURCE = "conker/src/game/generated_1F2730.c"
OBJECT = "conker/build/src/game/generated_1F2730.c.o"
ASM = "conker/asm/1F2730.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
BUILD = "conker/build/game-direction-effect-config-submit-151C61A0-match"
ENTRY, ROM, WORDS, FRAME = 0x151C61A0, 0x1F3650, 60, 0x58
SIZE = WORDS * 4
CALL_ROM = 0x1643D4
SYMBOL = struct.Struct(">IIIBBH")
RAW_SHA256 = "e6298d9a9f6c45f5efac3d87599bcbf78cc1e69b349978f6d82d340e3711b892"
RETAIL_SHA256 = "02d5d9e1e55d07a109eb61896a630abfb17871806731a124081cbae8868802dc"
BINDINGS = {
    0x024: [("R_MIPS_HI16", "D_800AAAF4")],
    0x028: [("R_MIPS_LO16", "D_800AAAF4")],
    0x02C: [("R_MIPS_HI16", "D_800AAAF8")],
    0x030: [("R_MIPS_LO16", "D_800AAAF8")],
    0x034: [("R_MIPS_HI16", "D_800AAAFC")],
    0x038: [("R_MIPS_LO16", "D_800AAAFC")],
    0x0D8: [("R_MIPS_26", "func_15154684")],
}

ANCHOR = (
    "struct225 *func_151602C0(Header *, Header2 *, s32, s32, s32, s32, "
    "u8, u8, s32, u8, s32);\n")
DECLARATIONS = """
typedef struct {
    s16 countBase;
    s16 countRange;
    void *providerType;
    s16 private8;
    s16 secondAngleBase;
    s16 privateC;
    s16 secondAngleRange;
    f32 radiusBase;
    f32 radiusRange;
    f32 scaleBase;
    f32 scaleRange;
    f32 mode;
    u8 selectorBase;
    u8 selectorRange;
    s16 durationBase;
    s16 durationRange;
    u8 private2A[2];
    f32 timeBase;
    f32 timeRange;
    f32 opaqueChance;
    s32 requestValue;
} DirectionEffectConfig1F2730;

extern f32 D_800AAAF4;
extern f32 D_800AAAF8;
extern f32 D_800AAAFC;
void func_15154684(DirectionEffectConfig1F2730 *, s32, s32);
"""
STUB = "s32 func_151C61A0() {\n    return 0;\n}"
SELECTED = """/* Submit one fixed directional-effect configuration. */
void func_151C61A0(void *providerType, s32 requestValue, u8 channel, s32 owner) {
    DirectionEffectConfig1F2730 config;

    config.countBase = 10;
    config.countRange = 4;
    config.providerType = providerType;
    config.private8 = 0;
    config.privateC = 255;
    config.secondAngleBase = -24;
    config.secondAngleRange = 25;
    config.radiusBase = 5.0f;
    config.radiusRange = 7.0f;
    config.scaleBase = D_800AAAF4;
    config.scaleRange = D_800AAAF8;
    config.mode = D_800AAAFC;
    config.selectorBase = 190;
    config.selectorRange = 65;
    config.durationBase = 200;
    config.durationRange = 150;
    config.timeBase = 96.0f;
    config.timeRange = 109.0f;
    config.opaqueChance = 1.0f;
    config.requestValue = requestValue;
    func_15154684(&config, channel, owner);
}"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_states(live):
    start, end = function_span(live, FUNCTION)
    body = live[start:end]
    installed_body = SELECTED.split("\n", 1)[1]
    if body == STUB:
        if DECLARATIONS in live or SELECTED in live or live.count(ANCHOR) != 1:
            raise ValueError("Direction-config predecessor source changed")
        qualified = live.replace(ANCHOR, ANCHOR + DECLARATIONS, 1)
        qstart, qend = function_span(qualified, FUNCTION)
        qualified = qualified[:qstart] + SELECTED + qualified[qend:]
        return live, qualified, False
    if body == installed_body:
        if live.count(DECLARATIONS) != 1 or live.count(SELECTED) != 1:
            raise ValueError("Installed direction-config source changed")
        predecessor = live.replace(DECLARATIONS, "", 1)
        predecessor = predecessor.replace(SELECTED, STUB, 1)
        return predecessor, live, True
    raise ValueError("Direction-config source state changed")


def retail_bytes(root):
    data = (root / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    if len(data) != SIZE or digest(data) != RETAIL_SHA256:
        raise ValueError("Direction-config retail bytes changed")
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
        raise ValueError("Direction-config natural candidate changed")
    if bindings != BINDINGS or raw != retail_object_bytes(root):
        raise ValueError("Direction-config natural words or bindings changed")
    words = struct.unpack(">%dI" % WORDS, raw)
    if ((-words[0]) & 0xFFFF) != FRAME:
        raise ValueError("Direction-config frame changed")
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
        raise ValueError("Direction-config linker owner reference changed")
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
        raise ValueError("Direction-config predecessor symbol extent changed")
    struct.pack_into(">I", result, rows[0][0] + 8, SIZE)
    # The owner's first D_800AAAF8 reference rotates one closed GNU-ld hash
    # bucket. Preserve the semantic symbol records while reproducing that
    # deterministic five-name .symtab/.strtab cycle exactly.
    entries = {name: (at, fields, string_at)
               for at, name, fields, string_at in symbol_rows(predecessor)}
    names = ("D_800AAAF8", "D_800A113C", "D_8009CC3C",
             "D_8009E63C", "func_15155FD4")
    slots = [entries[name] for name in names]
    if any(slots[index + 1][0] != slots[index][0] + SYMBOL.size
           for index in range(len(slots) - 1)):
        raise ValueError("Direction-config symbol cycle slots changed")
    old_literals = [name.encode() + b"\0" for name in names]
    string_start = slots[0][2]
    if predecessor[string_start:string_start + sum(map(len, old_literals))] != b"".join(old_literals):
        raise ValueError("Direction-config symbol cycle strings changed")
    strings_base = string_start - slots[0][1][0]
    new_names = names[1:] + names[:1]
    cursor = string_start
    for slot, source_name, literal in zip(slots, new_names,
                                          [name.encode() + b"\0" for name in new_names]):
        fields = list(entries[source_name][1])
        fields[0] = cursor - strings_base
        SYMBOL.pack_into(result, slot[0], *fields)
        result[cursor:cursor + len(literal)] = literal
        cursor += len(literal)
    return bytes(result)


def check_image(predecessor, actual, retail):
    if actual != expected_image(predecessor, retail):
        raise ValueError("Direction-config image differs from literal prediction")


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
        0x1643C8: 0x27A400AC,
        0x1643CC: 0x27A5007C,
        0x1643D0: 0x93A600D3,
        0x1643D4: jal,
        0x1643D8: 0x8FA700D4,
    }
    if calls != [CALL_ROM] or pointers or any(
            struct.unpack_from(">I", image, at)[0] != word
            for at, word in proof.items()):
        raise ValueError("Direction-config caller evidence changed")
    return {
        "caller": "func_15136C3C", "caller_owner": "game_161520",
        "call_rom": hex(CALL_ROM), "direct_jal_calls": [hex(at) for at in calls],
        "aligned_pointer_literals": [],
        "arguments": ["SP+0xAC provider", "SP+0x7C request",
                      "low byte at SP+0xD3", "owner at SP+0xD4"],
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
        raise ValueError("Direction-config owner diagnostics changed")
    raw, bindings = checked_candidate(root, qualified_compact)
    predecessor_owner = assemble_owner(
        root, output, predecessor_compact, "predecessor-owner")
    qualified_owner = assemble_owner(
        root, output, qualified_compact, "qualified-owner")
    live_owner = qualified_owner if installed else predecessor_owner
    if live_owner.read_bytes() != (root / OBJECT).read_bytes():
        raise ValueError("Direction-config selected owner differs from production")
    if function_blob(qualified_owner, FUNCTION) != (
            retail_object_bytes(root), BINDINGS):
        raise ValueError("Direction-config owner differs from retail")
    neighbors = same_functions(predecessor_owner, qualified_owner, (FUNCTION,))
    if normalized_pools(predecessor_owner) != normalized_pools(qualified_owner):
        raise ValueError("Direction-config normalized pools changed")
    predecessor_elf = link_image(root, output, predecessor_owner, "predecessor-image")
    qualified_elf = link_image(root, output, qualified_owner, "qualified-image")
    retail = retail_bytes(root)
    check_image(predecessor_elf.read_bytes(), qualified_elf.read_bytes(), retail)
    live_elf = (root / ELF).read_bytes()
    if live_elf == qualified_elf.read_bytes():
        image_state = "qualified"
    elif live_elf == predecessor_elf.read_bytes():
        image_state = "predecessor"
    else:
        raise ValueError("Direction-config live image is neither qualified nor predecessor")
    old, _, old_addresses = load_elf_functions(
        str(predecessor_elf), "mips-linux-gnu-objdump")
    new, _, new_addresses = load_elf_functions(
        str(qualified_elf), "mips-linux-gnu-objdump")
    changed = [name for name in new if old[name] != new[name]]
    if set(old) != set(new) or old_addresses != new_addresses or changed != [FUNCTION]:
        raise ValueError("Direction-config full-image closure changed: " + repr(changed))
    data = audit_layout(qualified_elf, root / "conker")
    if not data["exact"] or data["bytes"] != 189088 or data["owner_count"] != 720:
        raise ValueError("Direction-config protected data changed")
    (output / "proposed-owner.c").write_text(qualified_source)
    report = {
        "function": FUNCTION, "source_installed": installed,
        "live_image_state": image_state, "words": WORDS, "frame": FRAME,
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
