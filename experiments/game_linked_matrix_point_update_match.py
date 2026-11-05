"""Qualify func_15107E48 with a closed eight-byte frame/home normalization."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_linked_matrix_point_update_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset, symbol_rows


FUNCTION, FILENAME, SOURCE = candidate.FUNCTION, candidate.OWNER, candidate.SOURCE
OBJECT = "conker/build/src/game/generated_133190.c.o"
ASM = "conker/asm/133190.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF, LINKER = "conker/build/conker.us.elf", "conker/build/conker.ld"
ROM_IMAGE = "conker/conker.us.bin"
REGISTRY = "conker/asm/data/22D6D0.rodata.s"
BUILD = "conker/build/game-linked-matrix-point-update-15107E48-match"
ENTRY, ROM, WORDS = candidate.ENTRY, candidate.ROM, candidate.WORDS
SIZE, NATURAL_FRAME, RETAIL_FRAME = WORDS * 4, 0x40, 0x38
RAW_SHA256 = "de00ee337d85f828445303335f3f5e5ded1d1ce6319368537e9994f27ef63458"
RETAIL_SHA256 = "ef64e458318375bb187a475212933fb615d2177827550c56a14a5f23d7d49143"
BASELINE_ELF_SHA256 = "1bf15eaf5cd81203aac76f30c50e7bd0819b1c99c1e279807502036e280ca388"
BINDINGS = RETAIL_BINDINGS = {
    0x08C: [("R_MIPS_26", "func_15107F54")],
    0x0EC: [("R_MIPS_26", "func_15107AE0")],
}
GUARD_WORDS = (
    (0x000, 0x27BDFFC0, 0x27BDFFC8),
    (0x014, 0xAFA50044, 0xAFA5003C),
    (0x048, 0x8FA80044, 0x8FA8003C),
    (0x068, 0x27A9002C, 0x27A90024),
    (0x094, 0xC7A4002C, 0xC7A40024),
    (0x09C, 0xC7A80030, 0xC7A80028),
    (0x0A8, 0x8FAD0044, 0x8FAD003C),
    (0x0C0, 0xC7B00034, 0xC7B0002C),
    (0x108, 0x27BD0040, 0x27BD0038),
)
PATCH_ROWS = tuple(dict(offset="0x%03X" % offset,
                        expected="0x%08X" % expected,
                        replacement="0x%08X" % replacement)
                   for offset, expected, replacement in GUARD_WORDS)
source_states = candidate.source_states


def complete_row(row):
    return {"filename":FILENAME,"function":FUNCTION, **row,
            "expected_relocations":"-","replacement_relocations":"-",
            "note":"Normalize linked-matrix point callback frame and snapshot homes",
            "insert_after":"","insert_after_relocations":"","omit":"false"}


def assemble_owner(root, output, compact, rows, fields, label):
    # This owner already binds its fractional-point pool explicitly in Make.
    from tools.experiments.game_linked_actor_point_update_match import assemble_owner as inherited
    owner_dir = output / label
    owner_dir.mkdir(parents=True, exist_ok=True)
    patches = owner_dir / "retail-word-patches.csv"
    harness.write_patches(patches, fields, rows)
    return inherited(root, output, compact, label, patches)


def registry_evidence(root):
    image = (Path(root) / ROM_IMAGE).read_bytes()
    words = struct.unpack(">%dI" % (len(image) // 4), image[:len(image) & ~3])
    calls = [index*4 for index,word in enumerate(words)
             if word == 0x0C000000 | ((ENTRY>>2)&0x03FFFFFF)]
    pointers = [index*4 for index,word in enumerate(words) if word == ENTRY]
    registry = (Path(root) / REGISTRY).read_text()
    block = registry.split("dlabel D_80088C10\n",1)[1].split("enddlabel D_80088C10",1)[0]
    entries = [line.split(".word",1)[1].strip() for line in block.splitlines() if ".word" in line]
    if calls or pointers != [0x22D6D4] or entries != ["func_15107924",FUNCTION]:
        raise ValueError("Linked matrix point registry changed")
    return {"direct_jal_calls":[],"aligned_pointer_literals":["0x22d6d4"],
            "registry":"D_80088C10[1]",
            "abi":"owner pointer and changed-byte pointer; false for invalid actor/identity/matrix, otherwise true",
            "dispatcher":"func_1510608C at 0x151060C8: JALR with owner in A0 and local changed byte in A1"}


def strict_image(before, after, truth):
    expected = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    expected[at:at+SIZE] = truth
    rows = [(offset, row) for offset,name,row,_ in symbol_rows(before) if name == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY,12):
        raise ValueError("Linked matrix point predecessor symbol changed")
    struct.pack_into(">I",expected,rows[0][0]+8,SIZE)
    if bytes(expected) != after:
        differences = [i for i,(a,b) in enumerate(zip(expected,after)) if a != b]
        raise ValueError("Linked matrix point literal image differs: " + repr(differences[:20]))
    return sum(a!=b for a,b in zip(before,after))


def prepare(root, output=None):
    names = ("candidate FUNCTION FILENAME SOURCE OBJECT ASM GUARDS ELF LINKER ROM_IMAGE "
             "REGISTRY BUILD ENTRY ROM WORDS SIZE NATURAL_FRAME RETAIL_FRAME RAW_SHA256 "
             "RETAIL_SHA256 BINDINGS RETAIL_BINDINGS PATCH_ROWS complete_row source_states "
             "registry_evidence assemble_owner").split()
    saved = {name:getattr(harness,name) for name in names}
    try:
        for name in names: setattr(harness,name,globals()[name])
        result = harness.prepare(root, output or Path(root)/BUILD)
    finally:
        for name,value in saved.items(): setattr(harness,name,value)
    truth = (Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
    if hashlib.sha256(result["predecessor_elf"].read_bytes()).hexdigest() != BASELINE_ELF_SHA256:
        raise ValueError("Linked matrix point frozen whole-image predecessor changed")
    count = strict_image(result["predecessor_elf"].read_bytes(),
                         result["qualified_elf"].read_bytes(),truth)
    result["report"].update({"literal_full_image_prediction":True,"strict_changed_bytes":count})
    (Path(output or Path(root)/BUILD)/"qualification.json").write_text(json.dumps(result["report"],indent=2)+"\n")
    return result


if __name__ == "__main__":
    print(json.dumps(prepare(candidate.ROOT)["report"],indent=2))
