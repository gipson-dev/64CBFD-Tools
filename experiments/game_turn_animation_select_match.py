"""Qualify the turn-animation selector with checked GPR roles and regular-owner padding."""
import hashlib
import json
from pathlib import Path
import struct
import sys

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_turn_animation_select_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools import pad_generated_object
sys.modules.setdefault("pad_generated_object",pad_generated_object)
from tools.pad_c_object import emit_padded_assembly as pad_root_object

FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT="conker/build/src/game_83300.c.o"
ASM="conker/asm/nonmatchings/game_83300/func_15056A00.s"
GUARDS,ELF,LINKER="conker/retail_word_patches.us.csv","conker/build/conker.us.elf","conker/build/conker.ld"
ROM_IMAGE,REGISTRY="conker/conker.us.bin","conker/asm/nonmatchings/game_A28B0/func_15077F64.s"
BUILD="conker/build/game-turn-animation-select-15056A00-match"
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,NATURAL_FRAME,RETAIL_FRAME=WORDS*4,0,0
TABLE=0x80099A3C
RAW_SHA256="5f3efc4de35019ffbc1a7b23445006b36aae9193a89365dcd64d45194e5f2117"
RETAIL_SHA256="f29ce9ba3bd3c791599d4e88882e95126d8e1ab1f60f58656a05e7740ed99cfe"
BASELINE_ELF_SHA256="4dfa62fd6f26d30aa472519a5bf2422e45faa0b9f1ac7cd88018ef2638ab0c96"
BINDINGS=RETAIL_BINDINGS={0x10:[("R_MIPS_HI16","D_80099A3C")],0x14:[("R_MIPS_LO16","D_80099A3C")]}
# Original-register mappings apply once, from each definition through its last use.
ROLES=((0xA0,0xD8,7,5),(0xC0,0xE0,2,14),(0xD8,0xFC,5,13),
       (0xE0,0xE8,6,15),(0xE8,0xEC,13,25))
GUARD_WORDS=(
    (0x080,0x01E8C021,0x010FC021),
    (0x0A0,0x03023821,0x03022821),
    (0x0A4,0x90F90000,0x90B90000),
    (0x0C0,0x8C8200F4,0x8C8E00F4),
    (0x0D8,0x90E50000,0x90AD0000),
    (0x0E0,0x00413024,0x01C17824),
    (0x0E4,0xAC8600F4,0xAC8F00F4),
    (0x0E8,0x34CD0004,0x35F90004),
    (0x0EC,0xAC8D00F4,0xAC9900F4),
    (0x0FC,0xA4850244,0xA48D0244),
)
PATCH_ROWS=tuple(dict(offset="0x%03X"%at,expected="0x%08X"%old,replacement="0x%08X"%new)for at,old,new in GUARD_WORDS)
source_states=candidate.source_states

def complete_row(row):
    return {"filename":FILENAME,"function":FUNCTION,**row,"expected_relocations":"-","replacement_relocations":"-",
            "note":"Derive turn-animation GPR lifetimes and commutative row-address addition",
            "insert_after":"","insert_after_relocations":"","omit":"false"}

def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=BINDINGS:
        raise ValueError("Turn-animation natural body or bindings changed")
    if len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:
        raise ValueError("Turn-animation retail body changed")
    words=list(struct.unpack(">66I",raw));result=[]
    for i,word in enumerate(words):
        at=i*4;op,fn=word>>26,word&63
        mapping={old:new for lo,hi,old,new in ROLES if lo<=at<=hi};role=lambda r:mapping.get(r,r)
        rs,rt,rd=word>>21&31,word>>16&31,word>>11&31
        fitted=word
        if at==0x80:
            if (op,fn,rs,rt,rd)!=(0,33,15,8,24):raise ValueError("Turn row-address ADDU shape changed")
            fitted=(word&0xFC00FFFF)|(rt<<21)|(rs<<16)
        elif mapping:
            if op==0 and fn in(33,36):
                fitted=(word&0xFC0007FF)|(role(rs)<<21)|(role(rt)<<16)|(role(rd)<<11)
            elif op in(9,13,35,36,40,41,43):
                fitted=(word&0xFC00FFFF)|(role(rs)<<21)|(role(rt)<<16)
            elif op in(4,20):
                fitted=(word&0xFC00FFFF)|(role(rs)<<21)|(role(rt)<<16)
            elif op==57:
                fitted=(word&0xFC1FFFFF)|(role(rs)<<21) # SWC1's RT is a floating register.
            elif op==17 and rs==4:
                fitted=(word&0xFFE0FFFF)|(role(rt)<<16) # MTC1's RT is the GPR source.
            else:raise ValueError("Unexpected turn-animation role instruction")
        result.append(fitted)
    blob=struct.pack(">66I",*result)
    changes=[(i*4,a,b)for i,(a,b)in enumerate(zip(words,result))if a!=b]
    if changes!=list(GUARD_WORDS):raise ValueError("Turn-animation derived guards differ")
    expected=bytearray(truth)
    for at in BINDINGS:struct.pack_into(">I",expected,at,struct.unpack_from(">I",expected,at)[0]&0xFFFF0000)
    if blob!=bytes(expected):raise ValueError("Turn-animation fitted payload differs")
    return blob,{"instructions":66,"GPR_lifetimes":5,"commutative_ADDU_offsets":[0x80],
                 "changed_words":10,"schedule_changes":0,"inserted_or_omitted_instructions":0}

def emit_padded_assembly(obj,asm,word_patches_path=None,filename=None):
    if filename!=FILENAME:raise ValueError("Turn-animation padder owner changed")
    return pad_root_object(obj,candidate.ROOT/"conker/retail_layout.us.txt",filename,word_patches_path=word_patches_path)

def checked_candidate(root,obj):
    text,functions,relocations=pad_generated_object.parse_object(obj);info=functions[FUNCTION]
    start,size=info["value"],info["size"];raw=text[start:start+size]
    bindings={at-start:rows for at,rows in relocations.items()if start<=at<start+size}
    normalized(raw,bindings,(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE])
    if any(w>>16==0x27BD for w in struct.unpack(">66I",raw)):raise ValueError("Unexpected turn-animation frame")
    return raw,bindings

def registry_evidence(root):
    image=(Path(root)/ROM_IMAGE).read_bytes();words=struct.unpack(">%dI"%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,w in enumerate(words)if w==(0x0C000000|((ENTRY>>2)&0x03FFFFFF))]
    pointers=[i*4 for i,w in enumerate(words)if w==ENTRY]
    if calls!=[0x8528C,0xA550C]or pointers:raise ValueError("Turn-animation caller census changed: "+repr((calls,pointers)))
    return {"direct_jal_calls":list(map(hex,calls)),"aligned_pointer_literals":[],
            "callers":["func_15056B08","func_15077F64"],"abi":"actor pointer, unsigned byte magnitude, unsigned byte row; void return"}

def strict_image(before,after,truth):
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,f)for off,name,f,_ in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError("Turn-animation predecessor symbol changed")
    struct.pack_into(">I",expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        differences=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError("Turn-animation literal ELF prediction differs: "+repr(differences[:20]))
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    names=("candidate FUNCTION FILENAME SOURCE OBJECT ASM GUARDS ELF LINKER ROM_IMAGE REGISTRY BUILD ENTRY ROM WORDS SIZE "
           "NATURAL_FRAME RETAIL_FRAME RAW_SHA256 RETAIL_SHA256 BINDINGS RETAIL_BINDINGS PATCH_ROWS complete_row source_states "
           "registry_evidence checked_candidate emit_padded_assembly").split()
    saved={name:getattr(harness,name)for name in names}
    try:
        for name in names:setattr(harness,name,globals()[name])
        result=harness.prepare(root,output or Path(root)/BUILD)
    finally:
        for name,value in saved.items():setattr(harness,name,value)
    before=result["predecessor_elf"].read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256:raise ValueError("Turn-animation predecessor ELF changed")
    truth=(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
    raw,bindings=checked_candidate(root,result["qualified_compact"])
    _,proof=normalized(raw,bindings,truth)
    count=strict_image(before,result["qualified_elf"].read_bytes(),truth)
    result["report"].update(literal_full_image_prediction=True,strict_changed_bytes=count,normalization=proof,regular_owner_padder=True)
    (Path(output or Path(root)/BUILD)/"qualification.json").write_text(json.dumps(result["report"],indent=2)+"\n")
    return result

if __name__=="__main__":print(json.dumps(prepare(candidate.ROOT)["report"],indent=2))
