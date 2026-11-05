"""Qualify the object-follow update as direct exact C and a literal ELF delta."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_object_follow_update_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset, symbol_rows


FUNCTION,FILENAME,SOURCE = candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT = "conker/build/src/game/generated_188F90.c.o"
ASM = "conker/asm/188F90.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF,LINKER = "conker/build/conker.us.elf","conker/build/conker.ld"
ROM_IMAGE,REGISTRY = "conker/conker.us.bin","conker/asm/data/22FF90.rodata.s"
BUILD = "conker/build/game-object-follow-update-1515BFA8-match"
ENTRY,ROM,WORDS = candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,NATURAL_FRAME,RETAIL_FRAME = WORDS*4,0x18,0x18
RAW_SHA256 = "1a99704973315185196aac958b0c9161a53539fb9731329773fc41a2521791a1"
RETAIL_SHA256 = "3d4b93b8301d2b23626a7bc16a33000b90840454052c5b36efd36928998959dc"
BASELINE_ELF_SHA256 = "92b4ed1166612a791154a72a680449cbeafae6eb8ef320422f338c9e546e57db"
BINDINGS = RETAIL_BINDINGS = {
    0x010:[("R_MIPS_HI16","D_800BE9E4")],
    0x024:[("R_MIPS_LO16","D_800BE9E4")],
    0x090:[("R_MIPS_HI16","D_800BE9A8")],
    0x094:[("R_MIPS_LO16","D_800BE9A8")],
    0x0F8:[("R_MIPS_26","func_1516972C")],
}
PATCH_ROWS = ()
source_states = candidate.source_states


def complete_row(row):
    raise AssertionError("Object-follow update requires no guards")


def registry_evidence(root):
    image=(Path(root)/ROM_IMAGE).read_bytes()
    words=struct.unpack(">%dI"%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,word in enumerate(words) if word==0x0C000000|((ENTRY>>2)&0x03FFFFFF)]
    pointers=[i*4 for i,word in enumerate(words) if word==ENTRY]
    if calls or pointers!=[0x230990]: raise ValueError("Object-follow reference census changed")
    table=0x8008B4A8+0x32*0x34
    if table!=0x8008BED0 or struct.unpack_from(">I",image,0x22FF68+0x32*0x34)[0]!=ENTRY:
        raise ValueError("Object-follow descriptor slot changed")
    registry=(Path(root)/REGISTRY).read_text()
    if registry.count(".word func_1515BFA8")!=1: raise ValueError("Object-follow registry assembly changed")
    return {"direct_jal_calls":[],"aligned_pointer_literals":["0x230990"],
            "registry":"D_8008B4A8[0x32].unk0","descriptor_stride":0x34,
            "dispatcher":"func_151670C0: callback JALR at 0x15167170; record in A0, return ignored",
            "abi":"one writable object-follow record pointer; void callback"}


def strict_image(before,after,truth):
    expected=bytearray(before)
    at=elf_slot_offset(before,ENTRY,SIZE)
    expected[at:at+SIZE]=truth
    rows=[(offset,row) for offset,name,row,_ in symbol_rows(before) if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):
        raise ValueError("Object-follow predecessor symbol changed")
    struct.pack_into(">I",expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        differences=[i for i,(a,b) in enumerate(zip(expected,after)) if a!=b]
        raise ValueError("Object-follow literal ELF prediction differs: "+repr(differences[:20]))
    return sum(a!=b for a,b in zip(before,after))


def prepare(root,output=None):
    names=("candidate FUNCTION FILENAME SOURCE OBJECT ASM GUARDS ELF LINKER ROM_IMAGE "
           "REGISTRY BUILD ENTRY ROM WORDS SIZE NATURAL_FRAME RETAIL_FRAME RAW_SHA256 "
           "RETAIL_SHA256 BINDINGS RETAIL_BINDINGS PATCH_ROWS complete_row source_states "
           "registry_evidence").split()
    saved={name:getattr(harness,name) for name in names}
    try:
        for name in names: setattr(harness,name,globals()[name])
        result=harness.prepare(root,output or Path(root)/BUILD)
    finally:
        for name,value in saved.items(): setattr(harness,name,value)
    before=result["predecessor_elf"].read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256:
        raise ValueError("Object-follow frozen ELF predecessor changed")
    count=strict_image(before,result["qualified_elf"].read_bytes(),
                       (Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE])
    result["report"].update({"literal_full_image_prediction":True,"strict_changed_bytes":count})
    (Path(output or Path(root)/BUILD)/"qualification.json").write_text(json.dumps(result["report"],indent=2)+"\n")
    return result


if __name__=="__main__": print(json.dumps(prepare(candidate.ROOT)["report"],indent=2))
