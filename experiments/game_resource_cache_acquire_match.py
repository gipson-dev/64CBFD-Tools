"""Qualify resource cache acquisition with six checked private spill offsets."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_resource_cache_acquire_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset, symbol_rows
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools


FUNCTION,FILENAME,SOURCE = candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT = "conker/build/src/game/generated_1B9DB0.c.o"
ASM = "conker/asm/1B9DB0.s"
GUARDS = "conker/retail_word_patches.us.csv"
ELF,LINKER = "conker/build/conker.us.elf","conker/build/conker.ld"
ROM_IMAGE,REGISTRY = "conker/conker.us.bin","conker/asm/1B9DB0.s"
BUILD = "conker/build/game-resource-cache-acquire-1518C900-match"
ENTRY,ROM,WORDS = candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,NATURAL_FRAME,RETAIL_FRAME = WORDS*4,0x40,0x40
RAW_SHA256 = "1b1a539482abf273805508bba68d5ca94be9bd18c3e23cdc03be24296c81d1f6"
RETAIL_SHA256 = "7fc963b128273618962ba087ac5acb5ae9181126b3b34aedf08c44d9385ed053"
BASELINE_ELF_SHA256 = "b3eecf1336289ea865dfd089d311aa3730cecb90a44e50721ac74a4a3d28cfc4"
BINDINGS = RETAIL_BINDINGS = {
    0x014:[("R_MIPS_HI16","D_800DF7D0")],
    0x018:[("R_MIPS_LO16","D_800DF7D0")],
    0x028:[("R_MIPS_HI16","D_800E0148")],
    0x050:[("R_MIPS_26","func_1502B6BC")],
    0x070:[("R_MIPS_HI16","D_800DF9B8")],
    0x074:[("R_MIPS_LO16","D_800DF9B8")],
    0x09C:[("R_MIPS_26","func_1510CE60")],
    0x0A8:[("R_MIPS_26","func_15168E54")],
    0x0B8:[("R_MIPS_HI16","D_800E0148")],
    0x0C0:[("R_MIPS_LO16","D_800E0148")],
    0x0D8:[("R_MIPS_LO16","D_800E0148")],
}
GUARD_WORDS = ((0x054,0xAFA80034,0xAFA80038),(0x058,0x8FA80034,0x8FA80038),
    (0x08C,0xAFB90028,0xAFB9002C),(0x090,0xAFA80034,0xAFA80038),
    (0x0B0,0x8FAB0028,0x8FAB002C),(0x0B4,0x8FA80034,0x8FA80038))
PATCH_ROWS = tuple(dict(offset="0x%03X"%at,expected="0x%08X"%old,replacement="0x%08X"%new)
                   for at,old,new in GUARD_WORDS)
source_states = candidate.source_states
CALLS = (0xBD5EC,0xC0D30,0x182C90,0x19E1A8,0x19E548,0x19E834)
CALLER_SOURCE = "conker/src/game/generated_182C30.c"


def complete_row(row):
    return {"filename":FILENAME,"function":FUNCTION,**row,
            "expected_relocations":"-","replacement_relocations":"-",
            "note":"Normalize resource cache acquire private count/index spill homes",
            "insert_after":"","insert_after_relocations":"","omit":"false"}


def registry_evidence(root):
    image=(Path(root)/ROM_IMAGE).read_bytes()
    words=struct.unpack(">%dI"%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,word in enumerate(words) if word==(0x0C000000|((ENTRY>>2)&0x03FFFFFF))]
    pointers=[i*4 for i,word in enumerate(words) if word==ENTRY]
    if calls!=list(CALLS) or pointers:raise ValueError("Resource cache acquire caller census changed")
    return {"direct_jal_rom":["0x%X"%at for at in calls],"aligned_pointer_literals":[],
            "abi":"signed word kind in A0; resource data word or zero in V0",
            "callers":["0x%08X"%(at-0x2D4B0+0x15000000) for at in calls],
            "providers":"load category 9, retain textures, attach resource metadata"}


def strict_image(before,after,truth):
    expected=bytearray(before)
    at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(offset,row) for offset,name,row,_ in symbol_rows(before) if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):
        raise ValueError("Resource cache acquire predecessor symbol changed")
    struct.pack_into(">I",expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        differences=[i for i,(a,b) in enumerate(zip(expected,after)) if a!=b]
        raise ValueError("Resource cache acquire literal ELF prediction differs: "+repr(differences[:20]))
    return sum(a!=b for a,b in zip(before,after))


def qualify_caller_prototype(root,output):
    root,output=Path(root),Path(output)
    live=(root/CALLER_SOURCE).read_text()
    old,new="void func_1518C900(s32);","s32 func_1518C900(s32);"
    if live.count(old)==1 and new not in live:before,after=live,live.replace(old,new,1)
    elif live.count(new)==1 and old not in live:before,after=live.replace(new,old,1),live
    else:raise ValueError("Resource cache acquire caller prototype changed")
    objects=[];diagnostics=[]
    for label,source in (("before",before),("after",after)):
        compact,warning=compile_owner(root,output,source,"caller-"+label)
        diagnostics.append(warning)
        directory=output/("caller-"+label);directory.mkdir(parents=True,exist_ok=True)
        assembly,obj=directory/"generated_182C30.s",directory/"generated_182C30.o"
        assembly.write_text(emit_padded_assembly(compact,root/"conker/asm/182C30.s",
            word_patches_path=root/GUARDS,filename="generated_182C30"))
        subprocess.run(["mips-linux-gnu-as","-EB","-mtune=vr4300","-march=vr4300","-mabi=32",
            "-I",str(root/"conker/include"),"-o",str(obj),str(assembly)],check=True,capture_output=True)
        objects.append((compact,obj))
    if diagnostics[0]!=diagnostics[1]:raise ValueError("Caller prototype diagnostics changed")
    if parse_object(objects[0][0])!=parse_object(objects[1][0]) or normalized_pools(objects[0][0])!=normalized_pools(objects[1][0]):
        raise ValueError("Caller prototype code, bindings or pools changed")
    production=(root/"conker/build/src/game/generated_182C30.c.o").read_bytes()
    if any(obj.read_bytes()!=production for _,obj in objects):
        raise ValueError("Caller prototype padded owner differs from production")
    return {"source":CALLER_SOURCE,"functions":len(parse_object(objects[1][0])[1]),
            "padded_owner_byte_identical":True,"sha256":hashlib.sha256(production).hexdigest()}


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
        raise ValueError("Resource cache acquire frozen ELF predecessor changed")
    count=strict_image(before,result["qualified_elf"].read_bytes(),
                       (Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE])
    caller=qualify_caller_prototype(root,Path(output or Path(root)/BUILD))
    result["report"].update({"literal_full_image_prediction":True,"strict_changed_bytes":count,
                              "caller_prototype":caller})
    (Path(output or Path(root)/BUILD)/"qualification.json").write_text(json.dumps(result["report"],indent=2)+"\n")
    return result


if __name__=="__main__":print(json.dumps(prepare(candidate.ROOT)["report"],indent=2))
