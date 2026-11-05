"""Qualify the settle/fade callback with a literal complete-ELF prediction."""

import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_settle_fade_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset, symbol_rows


FUNCTION,FILENAME,SOURCE = candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1A7260.c.o"
ASM = "conker/asm/1A7260.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF,LINKER = "conker/build/conker.us.elf","conker/build/conker.ld"
ROM_IMAGE,REGISTRY = "conker/conker.us.bin","conker/asm/data/22FF90.rodata.s"
BUILD = "conker/build/game-settle-fade-1517A84C-match"
ENTRY,ROM,WORDS = candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,NATURAL_FRAME,RETAIL_FRAME = WORDS*4,0x18,0x18
RAW_SHA256 = "793790020a1a6eb1b48ee52a0d41593bc6d8d8996c9f751551e17c1a95f12420"
RETAIL_SHA256 = "de50604b8c75524b590f3806b3fa78c1889db3f1173778aa8171ff108524e722"
BASELINE_ELF_SHA256 = "b775949211d110993c2e819b0c15135c0e21f92b74bd8dac61f5996a4ff3fdbb"
BINDINGS = RETAIL_BINDINGS = {
    0x00C:[("R_MIPS_HI16","D_800BE9E4")],
    0x0CC:[("R_MIPS_LO16","D_800BE9E4")],
    0x0F4:[("R_MIPS_26","func_1516972C")],
}
PATCH_ROWS = ()
source_states = candidate.source_states


def complete_row(row):
    raise AssertionError("Settle/fade requires no guards")


def registry_evidence(root):
    image=(Path(root)/ROM_IMAGE).read_bytes()
    words=struct.unpack(">%dI"%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,word in enumerate(words) if word==(0x0C000000|((ENTRY>>2)&0x03FFFFFF))]
    pointers=[i*4 for i,word in enumerate(words) if word==ENTRY]
    if calls or pointers!=[0x23013C]:raise ValueError("Settle/fade reference census changed")
    if 0x8008B4A8+9*0x34!=0x8008B67C or struct.unpack_from(">I",image,0x22FF68+9*0x34)[0]!=ENTRY:
        raise ValueError("Settle/fade descriptor changed")
    if (Path(root)/REGISTRY).read_text().count(".word func_1517A84C")!=1:
        raise ValueError("Settle/fade registry assembly changed")
    return {"direct_jal_calls":[],"aligned_pointer_literals":["0x23013C"],
            "registry":"D_8008B4A8[9].unk0","descriptor_stride":0x34,
            "dispatcher":"func_151670C0: JALR at 0x15167170; record in A0, return ignored",
            "factory":"func_1517A644: category 9, allocation size 0xB8",
            "abi":"one writable settle/fade record pointer; void callback"}


def strict_image(before,after,truth):
    expected=bytearray(before)
    at=elf_slot_offset(before,ENTRY,SIZE)
    expected[at:at+SIZE]=truth
    rows=[(offset,row) for offset,name,row,_ in symbol_rows(before) if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):
        raise ValueError("Settle/fade predecessor symbol changed")
    struct.pack_into(">I",expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        differences=[i for i,(a,b) in enumerate(zip(expected,after)) if a!=b]
        raise ValueError("Settle/fade literal ELF prediction differs: "+repr(differences[:20]))
    return sum(a!=b for a,b in zip(before,after))


def prepare(root,output=None):
    names=("candidate FUNCTION FILENAME SOURCE OBJECT ASM GUARDS ELF LINKER ROM_IMAGE "
           "REGISTRY BUILD ENTRY ROM WORDS SIZE NATURAL_FRAME RETAIL_FRAME RAW_SHA256 "
           "RETAIL_SHA256 BINDINGS RETAIL_BINDINGS PATCH_ROWS complete_row source_states "
           "registry_evidence").split()
    saved={name:getattr(harness,name) for name in names}
    try:
        for name in names:setattr(harness,name,globals()[name])
        result=harness.prepare(root,output or Path(root)/BUILD)
    finally:
        for name,value in saved.items():setattr(harness,name,value)
    before=result["predecessor_elf"].read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256:
        raise ValueError("Settle/fade frozen ELF predecessor changed")
    count=strict_image(before,result["qualified_elf"].read_bytes(),
                       (Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE])
    result["report"].update({"literal_full_image_prediction":True,"strict_changed_bytes":count})
    (Path(output or Path(root)/BUILD)/"qualification.json").write_text(json.dumps(result["report"],indent=2)+"\n")
    return result


if __name__=="__main__":print(json.dumps(prepare(candidate.ROOT)["report"],indent=2))
