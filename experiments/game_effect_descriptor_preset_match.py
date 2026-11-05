"""Qualify the complete func_150D64E8 preset as direct exact C."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_effect_descriptor_preset_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness


FUNCTION, FILENAME, SOURCE = candidate.FUNCTION, candidate.OWNER, candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1028F0.c.o"
ASM = "conker/asm/1028F0.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF = "conker/build/conker.us.elf"
LINKER = "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = ASM
BUILD = "conker/build/game-effect-descriptor-preset-150D64E8-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE = WORDS * 4
NATURAL_FRAME = RETAIL_FRAME = 0
RAW_SHA256 = "34338181599fa21ee599fb9d25b68ee51208b437819d83fe6f983b9a82addd9d"
RETAIL_SHA256 = "1f121928a2a24315de766cdea26184984c3fe753588d4297dcc12187cbd9312e"
BINDINGS = RETAIL_BINDINGS = {
    0x018: [("R_MIPS_HI16", "D_800A0AB8")],
    0x01C: [("R_MIPS_LO16", "D_800A0AB8")],
    0x020: [("R_MIPS_HI16", "D_800A0ABC")],
    0x02C: [("R_MIPS_LO16", "D_800A0ABC")],
    0x030: [("R_MIPS_HI16", "D_800A0AC0")],
    0x03C: [("R_MIPS_LO16", "D_800A0AC0")],
    0x070: [("R_MIPS_HI16", "D_800A0AC4")],
    0x08C: [("R_MIPS_LO16", "D_800A0AC4")],
    0x098: [("R_MIPS_HI16", "D_800A0AC8")],
    0x0A4: [("R_MIPS_LO16", "D_800A0AC8")],
    0x0C4: [("R_MIPS_HI16", "D_80082FA0")],
    0x0CC: [("R_MIPS_LO16", "D_80082FA0")],
    0x0D0: [("R_MIPS_HI16", "D_8008FD8C")],
    0x0E4: [("R_MIPS_LO16", "D_8008FD8C")],
}
PATCH_ROWS = ()
source_states = candidate.source_states


def complete_row(row):
    raise AssertionError("The effect preset emits directly without guards")


def checked_candidate(root, obj):
    raw, bindings = harness.function_blob(obj)
    if (len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or
            bindings != BINDINGS or raw != harness.retail_object_bytes(root)):
        raise ValueError("Effect preset natural body or bindings changed")
    return raw, bindings


def registry_evidence(root):
    image = (Path(root) / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF)
    calls = [index * 4 for index, word in enumerate(words) if word == jal]
    pointers = [index * 4 for index, word in enumerate(words) if word == ENTRY]
    if calls or pointers:
        raise ValueError("Effect preset reference census changed")
    return {
        "direct_jal_calls": [], "aligned_pointer_literals": [], "registry": None,
        "abi": "two writable pointers inferred from the complete routine: descriptor and auxiliary float; void return",
        "limit": "No static JAL or aligned-pointer reference in the decompressed image; computed or external reachability remains unknown",
    }


def strict_image(before, after, truth):
    """Predict the code, target extent, and three closed GNU symbol rotations."""
    result = bytearray(before)
    shoff = struct.unpack_from(">I", before, 0x20)[0]
    shentsize, shnum = struct.unpack_from(">HH", before, 0x2E)
    matches = []
    for index in range(shnum):
        header = shoff + index * shentsize
        _, kind, flags, address, offset, size = struct.unpack_from(">6I", before, header)
        if kind == 1 and flags & 4 and address <= ENTRY and ENTRY + SIZE <= address + size:
            matches.append(offset + ENTRY - address)
    if len(matches) != 1:
        raise ValueError("Effect preset executable span changed")
    offset = matches[0]
    result[offset:offset + SIZE] = truth
    headers = [struct.unpack_from(">10I", before, shoff + i * shentsize)
               for i in range(shnum)]
    symtabs = [header for header in headers if header[1] == 2]
    if len(symtabs) != 1:
        raise ValueError("Effect preset symbol table changed")
    symtab = symtabs[0]
    strings_header = headers[symtab[6]]
    string_at = strings_header[4]
    strings = before[string_at:string_at + strings_header[5]]
    records = []
    for index in range(symtab[5] // 16):
        item = struct.unpack_from(">IIIBBH", before, symtab[4] + index * 16)
        name = strings[item[0]:].split(b"\0", 1)[0].decode()
        records.append((name, item))
    indices = {name: index for index, (name, _) in enumerate(records)}
    for first, second in (("D_800A0AC8", "D_8009EC34"),
                          ("func_15192308", "D_8009E5D4"),
                          ("D_8008B374", "D_8009E5D0")):
        index = indices[first]
        if records[index + 1][0] != second:
            raise ValueError("Effect preset closed symbol group changed")
        first_item, second_item = records[index][1], records[index + 1][1]
        start = first_item[0]
        old_names = (first + "\0" + second + "\0").encode()
        if strings[start:start + len(old_names)] != old_names:
            raise ValueError("Effect preset closed string group changed")
        result[string_at + start:string_at + start + len(old_names)] = (
            second + "\0" + first + "\0").encode()
        struct.pack_into(">IIIBBH", result, symtab[4] + index * 16,
                         start, *second_item[1:])
        struct.pack_into(">IIIBBH", result, symtab[4] + (index + 1) * 16,
                         start + len(second) + 1, *first_item[1:])
    target = indices[FUNCTION]
    if records[target][1][1:3] != (ENTRY, 12):
        raise ValueError("Effect preset predecessor symbol extent changed")
    struct.pack_into(">I", result, symtab[4] + target * 16 + 8, SIZE)
    if bytes(result) != after:
        differences = [i for i, (a, b) in enumerate(zip(result, after)) if a != b]
        raise ValueError("Effect preset unexpected full-image differences: " + repr(differences[:20]))
    return sum(a != b for a, b in zip(before, after))


def prepare(root, output=None):
    names = (
        "candidate FUNCTION FILENAME SOURCE OBJECT ASM GUARDS ELF LINKER ROM_IMAGE "
        "REGISTRY BUILD ENTRY ROM WORDS SIZE NATURAL_FRAME RETAIL_FRAME RAW_SHA256 "
        "RETAIL_SHA256 BINDINGS RETAIL_BINDINGS PATCH_ROWS complete_row source_states "
        "registry_evidence checked_candidate"
    ).split()
    saved = {name: getattr(harness, name) for name in names}
    try:
        for name in names:
            setattr(harness, name, globals()[name])
        result = harness.prepare(root, output or Path(root) / BUILD)
    finally:
        for name, value in saved.items():
            setattr(harness, name, value)
    truth = (Path(root) / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    changed = strict_image(result["predecessor_elf"].read_bytes(),
                           result["qualified_elf"].read_bytes(), truth)
    report = result["report"]
    report.update({"strict_changed_bytes": changed, "literal_full_image_prediction": True})
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(prepare(candidate.ROOT)["report"], indent=2))
