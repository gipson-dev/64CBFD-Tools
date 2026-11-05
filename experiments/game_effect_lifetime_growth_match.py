"""Qualify ordered effect ramps by checked GPR lifetimes and one independent load move."""

import hashlib
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_effect_lifetime_growth_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset, symbol_rows


FUNCTION, FILENAME, SOURCE = candidate.FUNCTION, candidate.OWNER, candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1CC440.c.o"
ASM, GUARDS = "conker/asm/1CC440.s", "conker/retail_word_patches.us.csv"
ELF, LINKER = "conker/build/conker.us.elf", "conker/build/conker.ld"
ROM_IMAGE, REGISTRY = "conker/conker.us.bin", "conker/asm/data/22FF90.rodata.s"
BUILD = "conker/build/game-effect-lifetime-growth-151A25E0-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE, NATURAL_FRAME, RETAIL_FRAME = WORDS * 4, 0, 0
RAW_SHA256 = "dae35a0e353a29c2fb2970f4f190f710bad9716602819dd2d78fcd244e61f9a7"
RETAIL_SHA256 = "a7058300b6c0b1e2c82ae3e626a25356e5b78ffa99e8969ca7e2218dcc7004f5"
BASELINE_ELF_SHA256 = "557cd1685bfb53e29ce35d423d84c2ad62820bd56c4506c99c64910d3d3024b5"
STEP = 0x800BE9E4
BINDINGS = RETAIL_BINDINGS = {
    0x068: [("R_MIPS_HI16", "D_800BE9E4")],
    0x0A0: [("R_MIPS_LO16", "D_800BE9E4")],
}
# Each interval starts at the original role's definition and includes its last use.
ROLES = ((0x098,0x0CC,15,25), (0x0A4,0x0C4,11,13), (0x0A8,0x0C4,13,15),
         (0x0B4,0x0C4,5,12), (0x0B8,0x0C4,12,14), (0x0BC,0x0C4,14,24),
         (0x0D4,0x100,8,10), (0x0D8,0x0E0,24,8), (0x0DC,0x0E4,25,9),
         (0x0F4,0x100,9,11))
GUARD_WORDS = (
    (0x07C, 0x03030019, 0x00780019),
    (0x098, 0x844F0018, 0x84590018),
    (0x0A4, 0x848B0034, 0x848D0034),
    (0x0A8, 0x848D0036, 0x848F0036),
    (0x0B0, 0x84830038, 0x00006012),
    (0x0B4, 0x00002812, 0x01AC7021),
    (0x0B8, 0x01656021, 0x01ECC021),
    (0x0BC, 0x01A57021, 0xA48E0034),
    (0x0C0, 0xA48C0034, 0xA4980036),
    (0x0C4, 0xA48E0036, 0x84830038),
    (0x0C8, 0x844F0018, 0x84590018),
    (0x0CC, 0x006F082A, 0x0079082A),
    (0x0D4, 0x8448000E, 0x844A000E),
    (0x0D8, 0x8458001A, 0x8448001A),
    (0x0DC, 0x2419D8F1, 0x2409D8F1),
    (0x0E0, 0xA4980032, 0xA4880032),
    (0x0E4, 0xA4590018, 0xA4490018),
    (0x0EC, 0x8448000E, 0x844A000E),
    (0x0F0, 0x01030019, 0x006A0019),
    (0x0F4, 0x00004812, 0x00005812),
    (0x0F8, 0xA0890042, 0xA08B0042),
    (0x0FC, 0xA0890041, 0xA08B0041),
    (0x100, 0xA0890040, 0xA08B0040),
)
PATCH_ROWS = tuple(dict(offset="0x%03X" % at, expected="0x%08X" % old,
                        replacement="0x%08X" % new)
                   for at, old, new in GUARD_WORDS)
source_states = candidate.source_states


def complete_row(row):
    return {"filename": FILENAME, "function": FUNCTION, **row,
            "expected_relocations": "-", "replacement_relocations": "-",
            "note": "Derive effect ramp GPR lifetimes and independent timer-load schedule",
            "insert_after": "", "insert_after_relocations": "", "omit": "false"}


def derive(raw):
    if len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != RAW_SHA256:
        raise ValueError("Effect growth natural instruction stream changed")
    words = list(struct.unpack(">67I", raw))
    fitted = []
    for index, word in enumerate(words):
        at = index * 4
        mapping = {old: new for lo, hi, old, new in ROLES if lo <= at <= hi}
        role = lambda r: mapping.get(r, r)
        op, fn = word >> 26, word & 63
        rs, rt, rd = word >> 21 & 31, word >> 16 & 31, word >> 11 & 31
        result = word
        if mapping:
            if op in (9, 33, 35, 40, 41):
                result = (word & 0xFC00FFFF) | (role(rs) << 21) | (role(rt) << 16)
            elif op == 0 and fn in (18, 25, 33, 42):
                result = (word & 0xFC0007FF) | (role(rs) << 21) | (role(rt) << 16) | (role(rd) << 11)
            elif op in (4, 20):
                result = (word & 0xFC00FFFF) | (role(rs) << 21) | (role(rt) << 16)
            else:
                raise ValueError("Unexpected instruction inside effect GPR lifetime")
        if at in (0x07C, 0x0F0):
            if result >> 26 or result & 0xFFFF != 25:
                raise ValueError("Effect commutative MULTU shape changed")
            left, right = result >> 21 & 31, result >> 16 & 31
            result = (result & 0xFC00FFFF) | (right << 21) | (left << 16)
        fitted.append(result)
    # Move only LH time,+0x38(A0) across MFLO, two ADDU and SH +0x34/+0x36.
    # The load address is disjoint from both stores for every record placement.
    if words[0x0B0//4] != 0x84830038:
        raise ValueError("Effect independent timer load changed")
    if [(words[i] >> 26, words[i] & 63) for i in range(0x0B4//4,0x0C8//4)] != [
            (0,18),(0,33),(0,33),(41,52),(41,54)]:
        raise ValueError("Effect crossed instruction inventory changed")
    permutation = list(range(WORDS))
    permutation[44:50] = [45,46,47,48,49,44]
    fitted = [fitted[i] for i in permutation]
    if sorted(permutation) != list(range(WORDS)):
        raise ValueError("Effect instruction permutation changed")
    result = struct.pack(">67I", *fitted)
    changes = [(at,struct.unpack_from(">I",raw,at)[0],struct.unpack_from(">I",result,at)[0])
               for at in range(0,SIZE,4) if raw[at:at+4] != result[at:at+4]]
    if changes != list(GUARD_WORDS):
        raise ValueError("Effect derived changed-word set differs")
    return result, {"instructions": WORDS, "roles": len(ROLES),
                    "permutation": permutation, "changed_words": len(changes),
                    "commutative_MULTU": [0x7C,0xF0],
                    "timer_load_moved": [0xB0,0xC4],
                    "crossed_store_offsets": [0x34,0x36], "timer_offset": 0x38,
                    "inserted_or_omitted_instructions": 0}


def normalized(raw, bindings, truth):
    if bindings != BINDINGS:
        raise ValueError("Effect growth bindings changed")
    if len(truth) != SIZE or hashlib.sha256(truth).hexdigest() != RETAIL_SHA256:
        raise ValueError("Effect growth retail body changed")
    fitted, proof = derive(raw)
    expected = bytearray(truth)
    for at in BINDINGS:
        struct.pack_into(">I", expected, at, struct.unpack_from(">I",expected,at)[0] & 0xFFFF0000)
    if fitted != bytes(expected):
        raise ValueError("Effect complete fitted body differs from retail")
    return fitted, proof


def registry_evidence(root):
    root = Path(root)
    image = (root / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image)//4),image[:len(image)&~3])
    calls = [i*4 for i,w in enumerate(words) if w == (0x0C000000|((ENTRY>>2)&0x03FFFFFF))]
    pointers = [i*4 for i,w in enumerate(words) if w == ENTRY]
    block = (root/REGISTRY).read_text().split("dlabel D_8008C9C8\n",1)[1].split("enddlabel D_8008C9C8",1)[0]
    entries = re.findall(r"\.word\s+(\w+)",block)
    if calls or pointers != [0x2314D4] or len(entries) != 22 or entries[19] != FUNCTION:
        raise ValueError("Effect growth registry changed")
    return {"direct_jal_calls": [], "aligned_pointer_literals": ["0x2314d4"],
            "registry": "D_8008C9C8[19]", "table_entries":22,
            "callers": ["func_15167E0C","func_15168870"],
            "abi": "one writable effect pointer in A0; void return"}


def strict_image(before, after, truth):
    expected = bytearray(before)
    at = elf_slot_offset(before,ENTRY,SIZE)
    expected[at:at+SIZE] = truth
    rows = [(offset,row) for offset,name,row,_ in symbol_rows(before) if name == FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3] != (ENTRY,12):
        raise ValueError("Effect growth predecessor symbol changed")
    struct.pack_into(">I",expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        raise ValueError("Effect growth literal whole ELF prediction differs")
    return sum(a!=b for a,b in zip(before,after))


def checked_candidate(root, obj):
    from tools.pad_generated_object import parse_object
    text, functions, relocations = parse_object(obj)
    info = functions[FUNCTION]
    start, size = info["value"], info["size"]
    if size != SIZE:
        raise ValueError("Effect growth natural extent changed")
    raw = text[start:start+size]
    bindings = {at-start: rows for at, rows in relocations.items() if start <= at < start+size}
    truth = (Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
    normalized(raw, bindings, truth)
    # This leaf opens with LH, not ADDIU SP. Its complete pinned stream has no frame.
    if any(word >> 16 == 0x27BD for word in struct.unpack(">67I", raw)):
        raise ValueError("Unexpected effect growth stack frame")
    return raw, bindings


def prepare(root, output=None):
    names = ("candidate FUNCTION FILENAME SOURCE OBJECT ASM GUARDS ELF LINKER ROM_IMAGE "
             "REGISTRY BUILD ENTRY ROM WORDS SIZE NATURAL_FRAME RETAIL_FRAME RAW_SHA256 "
             "RETAIL_SHA256 BINDINGS RETAIL_BINDINGS PATCH_ROWS complete_row source_states "
             "registry_evidence checked_candidate").split()
    saved = {name:getattr(harness,name) for name in names}
    try:
        for name in names:setattr(harness,name,globals()[name])
        result = harness.prepare(root,output or Path(root)/BUILD)
    finally:
        for name,value in saved.items():setattr(harness,name,value)
    before = result["predecessor_elf"].read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256:
        raise ValueError("Effect growth frozen predecessor ELF changed")
    truth = (Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
    from tools.pad_generated_object import parse_object
    text,functions,relocations = parse_object(result["qualified_compact"])
    start=functions[FUNCTION]["value"]
    raw=text[start:start+SIZE]
    bindings={at-start:rows for at,rows in relocations.items() if start<=at<start+SIZE}
    _,proof=normalized(raw,bindings,truth)
    count=strict_image(before,result["qualified_elf"].read_bytes(),truth)
    result["report"].update(literal_full_image_prediction=True,strict_changed_bytes=count,normalization=proof)
    (Path(output or Path(root)/BUILD)/"qualification.json").write_text(json.dumps(result["report"],indent=2)+"\n")
    return result


if __name__=="__main__":
    print(json.dumps(prepare(candidate.ROOT)["report"],indent=2))
