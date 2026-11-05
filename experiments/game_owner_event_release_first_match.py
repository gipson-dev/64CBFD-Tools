"""Qualify the release-first owner event callback and literal complete ELF delta."""

import hashlib
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_owner_event_release_first_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset, symbol_rows


FUNCTION, FILENAME, SOURCE = candidate.FUNCTION, candidate.OWNER, candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1BA1D0.c.o"
ASM, GUARDS = "conker/asm/1BA1D0.s", "conker/retail_word_patches.us.csv"
ELF, LINKER = "conker/build/conker.us.elf", "conker/build/conker.ld"
ROM_IMAGE, REGISTRY = "conker/conker.us.bin", "conker/asm/data/22EF80.rodata.s"
BUILD = "conker/build/game-owner-event-release-first-15191A84-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE, NATURAL_FRAME, RETAIL_FRAME = WORDS * 4, 0x28, 0x28
RAW_SHA256 = "99cdbf8e3c83c22f158ccd9a46f01f6c5413c5497a364809a35d05fd84b247bf"
RETAIL_SHA256 = "07179b29dafa7c76cef0c171e9446f2638dabd4d423aad0c696fe6bd03cb1395"
BASELINE_ELF_SHA256 = "b06f9a049b7b71c57625b6bc887eb75be0105090cb401be32323fda84cae9c2b"
BINDINGS = RETAIL_BINDINGS = {
    0x060: [("R_MIPS_26", "func_1516972C")],
    0x07C: [("R_MIPS_26", "func_1516972C")],
    0x0EC: [("R_MIPS_26", "func_15169850")],
}
GUARD_WORDS = (
    (0x020, 0x10410005, 0x8FAF002C),
    (0x024, 0x2401000E, 0x10410004),
    (0x028, 0x10410003, 0x2401000E),
    (0x02C, 0x24010050, 0x10410002),
    (0x030, 0x54410010, 0x24010050),
    (0x034, 0x2401004E, 0x1441000E),
    (0x038, 0x8FAE002C, 0x26060028),
    (0x03C, 0x8E180028, 0x8CCE0000),
    (0x040, 0x8DCF0000, 0x8DF80000),
    (0x044, 0x11F80006, 0x8FA8002C),
    (0x048, 0x00000000, 0x11D80005),
    (0x04C, 0x8FB9002C, 0x00000000),
    (0x050, 0x9209002C, 0x90D90004),
    (0x054, 0x93280004, 0x91090004),
    (0x058, 0x55090027, 0x57290027),
    (0x090, 0x14410012, 0x14410013),
    (0x094, 0x27A80030, 0x8FA4002C),
    (0x098, 0x8FAA002C, 0x8FAB002C),
    (0x09C, 0x8E0C0028, 0x26060028),
    (0x0A0, 0x8D4B0000, 0x8CCA0000),
    (0x0A4, 0x516C0007, 0x8D6C0000),
    (0x0A8, 0x9202000D, 0x8FAF002C),
    (0x0AC, 0x8FAD002C, 0x514C0006),
    (0x0B0, 0x920F002C, 0x9218000D),
    (0x0B4, 0x91AE0004, 0x90CD0004),
    (0x0B8, 0x55CF000F, 0x91EE0004),
    (0x0BC, 0x8FBF0024, 0x55AE000E),
    (0x0C0, 0x9202000D, 0x8FBF0024),
    (0x0C4, 0x24180064, 0x9218000D),
    (0x0C8, 0xA618000E, 0x24190064),
    (0x0CC, 0x34590001, 0xA619000E),
    (0x0D0, 0xA219000D, 0x37080001),
    (0x0D4, 0x10000008, 0xA208000D),
    (0x0D8, 0x8FBF0024, 0x10000007),
    (0x0DC, 0x8FA4002C, 0x8FBF0024),
    (0x0E0, 0x91050003, 0x26060028),
    (0x0E4, 0xAFB00010, 0x24C70004),
    (0x0E8, 0x26060028, 0x93A50033),
    (0x0F0, 0x2607002C, 0xAFB00010),
)
PATCH_ROWS = tuple(dict(offset="0x%03X" % at, expected="0x%08X" % old,
                        replacement="0x%08X" % new)
                   for at, old, new in GUARD_WORDS)
source_states = candidate.source_states


def complete_row(row):
    return {"filename": FILENAME, "function": FUNCTION, **row,
            "expected_relocations": "-", "replacement_relocations": "-",
            "note": "Normalize release-first owner-event address materialization and compiler schedule",
            "insert_after": "", "insert_after_relocations": "", "omit": "false"}


def normalized(raw, bindings, truth):
    if len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings != BINDINGS:
        raise ValueError("Release-first natural body or bindings changed")
    if len(truth) != SIZE or hashlib.sha256(truth).hexdigest() != RETAIL_SHA256:
        raise ValueError("Release-first retail body changed")
    result = bytearray(raw)
    for at, old, new in GUARD_WORDS:
        if struct.unpack_from(">I", result, at)[0] != old:
            raise ValueError("Release-first guard preimage changed")
        struct.pack_into(">I", result, at, new)
    expected = bytearray(truth)
    for at in RETAIL_BINDINGS:
        struct.pack_into(">I", expected, at, 0x0C000000)
    if result != expected:
        raise ValueError("Release-first complete normalized body differs")
    return bytes(result)


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    calls = [i * 4 for i, word in enumerate(words) if word == (0x0C000000 | ((ENTRY >> 2) & 0x03FFFFFF))]
    pointers = [i * 4 for i, word in enumerate(words) if word == ENTRY]
    block = (root / REGISTRY).read_text().split("dlabel D_8008A8D8\n", 1)[1].split(
        "enddlabel D_8008A8D8", 1)[0]
    entries = re.findall(r"\.word\s+(\w+)", block)
    if calls or pointers != [0x22F3B8] or len(entries) != 74 or entries[8] != FUNCTION:
        raise ValueError("Release-first callback registry changed")
    return {"direct_jal_calls": [], "aligned_pointer_literals": ["0x22f3b8"],
            "registry": "D_8008A8D8[8]", "table_entries": 74,
            "dispatcher": "func_15149434",
            "abi": "record pointer, event pointer, low command byte; void return"}


def strict_image(before, after, truth):
    expected = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    expected[at:at + SIZE] = truth
    rows = [(offset, row) for offset, name, row, _ in symbol_rows(before) if name == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 12):
        raise ValueError("Release-first predecessor symbol changed")
    struct.pack_into(">I", expected, rows[0][0] + 8, SIZE)
    if bytes(expected) != after:
        raise ValueError("Release-first literal whole ELF prediction differs")
    return sum(a != b for a, b in zip(before, after))


def prepare(root, output=None):
    names = ("candidate FUNCTION FILENAME SOURCE OBJECT ASM GUARDS ELF LINKER ROM_IMAGE "
             "REGISTRY BUILD ENTRY ROM WORDS SIZE NATURAL_FRAME RETAIL_FRAME RAW_SHA256 "
             "RETAIL_SHA256 BINDINGS RETAIL_BINDINGS PATCH_ROWS complete_row source_states "
             "registry_evidence").split()
    saved = {name: getattr(harness, name) for name in names}
    try:
        for name in names:
            setattr(harness, name, globals()[name])
        result = harness.prepare(root, output or Path(root) / BUILD)
    finally:
        for name, value in saved.items():
            setattr(harness, name, value)
    before = result["predecessor_elf"].read_bytes()
    if hashlib.sha256(before).hexdigest() != BASELINE_ELF_SHA256:
        raise ValueError("Release-first frozen predecessor ELF changed")
    truth = (Path(root) / ROM_IMAGE).read_bytes()[ROM:ROM + SIZE]
    from tools.pad_generated_object import parse_object
    text, functions, relocations = parse_object(result["qualified_compact"])
    info = functions[FUNCTION]
    start = info["value"]
    raw = text[start:start + SIZE]
    bindings = {at - start: rows for at, rows in relocations.items() if start <= at < start + SIZE}
    normalized(raw, bindings, truth)
    count = strict_image(before, result["qualified_elf"].read_bytes(), truth)
    result["report"].update(literal_full_image_prediction=True, strict_changed_bytes=count)
    (Path(output or Path(root) / BUILD) / "qualification.json").write_text(
        json.dumps(result["report"], indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(prepare(candidate.ROOT)["report"], indent=2))
