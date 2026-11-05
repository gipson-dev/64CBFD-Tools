"""Qualify blended dual-point motion by a checked bijective float schedule."""

import hashlib
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_blended_dual_point_motion_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset, symbol_rows
from tools.experiments.game_linear_float_dataflow import derive


FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT="conker/build/src/game/generated_1BA1D0.c.o"
ASM="conker/asm/1BA1D0.s"
GUARDS="conker/retail_word_patches.us.csv"
ELF,LINKER="conker/build/conker.us.elf","conker/build/conker.ld"
ROM_IMAGE,REGISTRY="conker/conker.us.bin","conker/asm/data/22E730.rodata.s"
BUILD="conker/build/game-blended-dual-point-motion-1518EF54-match"
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,NATURAL_FRAME,RETAIL_FRAME=WORDS*4,0,0
RAW_SHA256="372ead169d7ac00cc7e2b1f15ccd5bc63a347bc54bfd4d12c0faf0e860476183"
RETAIL_SHA256="70987c31e8415b3c9469f2d012e7688647d09a6f3325ae27619e9b06fd234b80"
BASELINE_ELF_SHA256="29005e48a1f51044750259749b5f066abcc3f85ba0c05cd3d58147a281df94de"
STEP=0x800BE9A4
BINDINGS=RETAIL_BINDINGS={0:[("R_MIPS_HI16","D_800BE9A4")],4:[("R_MIPS_LO16","D_800BE9A4")]}
GUARD_WORDS=(
    (0x01C,0xC4840144,0xE4860140),
    (0x020,0xE4860140,0xC44A0000),
    (0x024,0xC44A0000,0xC4860144),
    (0x028,0x460A4482,0x460A4102),
    (0x02C,0xC4880148,0xC48A0148),
    (0x030,0x46004282,0x46043200),
    (0x034,0xC4880034,0x46005182),
    (0x038,0x46122180,0xC4840140),
    (0x03C,0xC4840140,0xE4880144),
    (0x040,0xE48A0148,0xC4880144),
    (0x044,0xE4860144,0xE4860148),
    (0x04C,0xC4920144,0xC48A0148),
    (0x050,0xC4860148,0xC4860034),
    (0x058,0xC4840038,0x24020001),
    (0x05C,0x24020001,0x46024382),
    (0x060,0x46029382,0xC4880038),
    (0x064,0x460C4280,0x46025402),
    (0x068,0x46023402,0x460C3100),
    (0x070,0x460E2480,0x460E4280),
    (0x074,0xE48A0034,0xC4880040),
    (0x078,0xC48A0040,0xE4840034),
    (0x07C,0xC4800034,0x46103100),
    (0x080,0xE4920038,0xE48A0038),
    (0x084,0x460C5100,0xC4860044),
    (0x088,0xC4920044,0x460C4280),
    (0x08C,0x46103200,0xE484003C),
    (0x090,0xE4840040,0xC4880048),
    (0x094,0xC4840040,0x460E3100),
    (0x098,0x460E9180,0xE48A0040),
    (0x09C,0xE488003C,0xC4860040),
    (0x0A0,0xC4880048,0xC4920034),
    (0x0A4,0x46002481,0x46104280),
    (0x0A8,0xE4860044,0xE4840044),
    (0x0AC,0xC486015C,0xC488015C),
    (0x0B0,0x46104280,0x46123101),
    (0x0B4,0xC4840044,0xE48A0048),
    (0x0B8,0x46069202,0xC4800038),
    (0x0C0,0xE48A0048,0x46082282),
    (0x0C4,0x46004280,0xC4840044),
    (0x0C8,0xC4800038,0x46002201),
    (0x0CC,0x46002481,0x460A9180),
    (0x0D0,0xE48A0040,0xE4860040),
    (0x0D4,0xC466004C,0xC46A004C),
    (0x0D8,0xC4840048,0x460A4182),
    (0x0DC,0x46069202,0xC4880048),
    (0x0E0,0x46022481,0x46024281),
    (0x0E4,0x46004280,0x46060100),
    (0x0E8,0xE48A0044,0xE4840044),
    (0x0F0,0x46069202,0x46065102),
    (0x0F4,0x46024280,0x46041200),
    (0x0F8,0xE48A0048,0xE4880048),
)
PATCH_ROWS=tuple(dict(offset="0x%03X"%at,expected="0x%08X"%old,replacement="0x%08X"%new)
                 for at,old,new in GUARD_WORDS)
source_states=candidate.source_states


def complete_row(row):
    return {"filename":FILENAME,"function":FUNCTION,**row,
            "expected_relocations":"-","replacement_relocations":"-",
            "note":"Normalize checked blended-motion FPR roles and bijective independent schedule",
            "insert_after":"","insert_after_relocations":"","omit":"false"}


def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=BINDINGS:
        raise ValueError("Blended-motion natural words or bindings changed")
    if len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:
        raise ValueError("Blended-motion retail words changed")
    natural=list(struct.unpack(">65I",raw));retail=list(struct.unpack(">65I",truth))
    resolved=natural.copy();resolved[:2]=retail[:2]
    proof=derive(resolved,retail,[0x30000]+[STEP-at for at in range(0,0x160,4)])
    fitted=proof.pop("fitted_words")
    if proof["permutation"][:2]!=[0,1] or proof["changed_words"]!=51:
        raise ValueError("Blended-motion relocation slots or schedule extent changed")
    fitted[:2]=natural[:2]
    expected=[]
    for at,old,new in GUARD_WORDS:
        if natural[at//4]!=old or fitted[at//4]!=new:
            raise ValueError("Blended-motion derived guard changed")
        expected.append(at)
    if [i*4 for i,(a,b) in enumerate(zip(natural,fitted)) if a!=b]!=expected:
        raise ValueError("Blended-motion changed-word set differs")
    return struct.pack(">65I",*fitted),proof


def registry_evidence(root):
    image=(Path(root)/ROM_IMAGE).read_bytes()
    words=struct.unpack(">%dI"%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,word in enumerate(words) if word==(0x0C000000|((ENTRY>>2)&0x03FFFFFF))]
    pointers=[i*4 for i,word in enumerate(words) if word==ENTRY]
    block=(Path(root)/REGISTRY).read_text().split("dlabel D_80089CB8\n",1)[1].split("enddlabel D_80089CB8",1)[0]
    entries=re.findall(r"\.word\s+(\w+)",block)
    if calls or pointers!=[0x22E794] or len(entries)!=42 or entries[7]!=FUNCTION:
        raise ValueError("Blended-motion callback registration changed")
    return {"direct_jal_calls":[],"aligned_pointer_literals":["0x22E794"],
            "registry":"D_80089CB8[7]","table_entries":42,
            "abi":"one writable motion record in A0; signed return one in V0",
            "dispatcher":"func_1513CFE4 original window 0x1513D034..0x1513D074"}


def strict_image(before,after,truth):
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(offset,row) for offset,name,row,_ in symbol_rows(before) if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):
        raise ValueError("Blended-motion predecessor symbol changed")
    struct.pack_into(">I",expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        differences=[i for i,(a,b) in enumerate(zip(expected,after)) if a!=b]
        raise ValueError("Blended-motion literal ELF prediction differs: "+repr(differences[:20]))
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
        raise ValueError("Blended-motion frozen ELF predecessor changed")
    truth=(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
    # The inherited target globals are restored; parse this owner directly.
    from tools.pad_generated_object import parse_object
    text,functions,relocations=parse_object(result["qualified_compact"])
    info=functions[FUNCTION];start=info["value"]
    raw=text[start:start+SIZE]
    bindings={at-start:rows for at,rows in relocations.items() if start<=at<start+SIZE}
    fitted,proof=normalized(raw,bindings,truth)
    expected=bytearray(truth)
    for at in BINDINGS:
        word=struct.unpack_from(">I",expected,at)[0]&0xFFFF0000
        struct.pack_into(">I",expected,at,word)
    if fitted!=bytes(expected):raise ValueError("Blended-motion derived object differs from retail")
    count=strict_image(before,result["qualified_elf"].read_bytes(),truth)
    result["report"].update({"literal_full_image_prediction":True,"strict_changed_bytes":count,"dataflow":proof})
    (Path(output or Path(root)/BUILD)/"qualification.json").write_text(json.dumps(result["report"],indent=2)+"\n")
    return result


if __name__=="__main__":print(json.dumps(prepare(candidate.ROOT)["report"],indent=2))
