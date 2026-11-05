"""Qualify the direct 66-word actor camera-position body and three alignment words."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch
from tools.experiments import game_actor_camera_position_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools

FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT='conker/build/src/game/generated_C98F0.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/C98F0.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
BUILD='conker/build/game-actor-camera-position-1509C8FC-match'
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,SLOT_SIZE=WORDS*4,candidate.SLOT_WORDS*4
RAW_SHA256='12c37669dabaa8f7c2ebc28cb84dbdd5fea06c617b62cdb1bdb9fd4a8d6f6a70'
RETAIL_SHA256='29607fc33920695bb0741b090816807d0b0acc1757ae5c788bfe24166e785188'
BASELINE_ELF_SHA256='1d56f2554e0bc910fcec5498bfc78a5fd72c7711832be629b2037987fef5a9f9'
BINDINGS={0x10:[('R_MIPS_26','func_1505EEF4')],0x20:[('R_MIPS_HI16','D_800DBFF0')],
          0x24:[('R_MIPS_LO16','D_800DBFF0')],0x98:[('R_MIPS_26','func_150221E8')],
          0xF0:[('R_MIPS_26','func_15022190')]}

def function_blob(obj):
    text,functions,relocs=parse_object(obj);f=functions[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in relocs.items()if start<=at<start+size}

def original_bytes(root):return(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]

def checked_candidate(root,obj):
    raw,bindings=function_blob(obj);truth=original_bytes(root)
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=BINDINGS:
        raise ValueError('Camera-position raw body or bindings changed')
    if hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Retail camera-position body changed')
    expected=bytearray(truth)
    for at,rows in BINDINGS.items():
        mask=0xFC000000 if rows[0][0]=='R_MIPS_26' else 0xFFFF0000
        struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&mask)
    if raw!=bytes(expected):raise ValueError('Camera-position requires a word correction')
    return raw,bindings

def strict_image(before,after,truth):
    if len(truth)!=SIZE:raise ValueError('Wrong camera-position body extent')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SLOT_SIZE)
    if before[at+SIZE:at+SLOT_SIZE]!=bytes(SLOT_SIZE-SIZE):raise ValueError('Predecessor alignment changed')
    expected[at:at+SIZE]=truth
    rows=[(off,f)for off,name,f,_ in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Predecessor camera-position symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:raise ValueError('Camera-position literal whole ELF prediction differs')
    return sum(a!=b for a,b in zip(before,after))

def registry_evidence(root):
    image=(Path(root)/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,w in enumerate(words)if w==(0x0C000000|((ENTRY>>2)&0x03FFFFFF))]
    pointers=[i*4 for i,w in enumerate(words)if w==ENTRY]
    if calls!=[0xC99AC,0xC9BD0]or pointers:raise ValueError('Camera-position caller census changed')
    return dict(direct_jal_calls=list(map(hex,calls)),aligned_pointer_literals=[],caller='func_1509C440',
                abi='s32 key, s32 alternate; void return; low 12-bit actor key and signed-16 coordinate outputs')

def assemble_owner(root,out,compact,label):
    path=out/(label+'.s');path.write_text(emit_padded_assembly(compact,root/ASM,word_patches_path=root/GUARDS,filename=FILENAME))
    obj=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(path)],check=True,capture_output=True)
    return obj

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True)
    before_source,after_source,installed=candidate.source_states((root/SOURCE).read_text())
    before_obj,before_diagnostics=candidate.compile_owner(root,out,before_source,'predecessor-compact')
    after_obj,after_diagnostics=candidate.compile_owner(root,out,after_source,'qualified-compact')
    if harness.diagnostics(before_diagnostics)!=harness.diagnostics(after_diagnostics):raise ValueError('Owner diagnostics changed')
    raw,bindings=checked_candidate(root,after_obj)
    before_owner=assemble_owner(root,out,before_obj,'predecessor-owner');after_owner=assemble_owner(root,out,after_obj,'qualified-owner')
    if (after_owner if installed else before_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Live owner changed')
    if function_blob(after_owner)!=(raw,bindings):raise ValueError('Padder changed direct camera-position body')
    raw_neighbors=same_functions(before_obj,after_obj,(FUNCTION,));neighbors=same_functions(before_owner,after_owner,(FUNCTION,))
    for a,b in((before_obj,after_obj),(before_owner,after_owner)):
        if normalized_pools(a)!=normalized_pools(b):raise ValueError('Owner pools changed')
    with patch.object(harness,'OBJECT',OBJECT),patch.object(harness,'LINKER',LINKER):
        before_elf=harness.link_image(root,out,before_owner,'predecessor-image')
        after_elf=harness.link_image(root,out,after_owner,'qualified-image')
    before,after=before_elf.read_bytes(),after_elf.read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256:raise ValueError('Predecessor ELF changed')
    if (after if installed else before)!=(root/ELF).read_bytes():raise ValueError('Live image changed')
    delta=strict_image(before,after,original_bytes(root))
    old,_,old_addresses=load_elf_functions(str(before_elf),'mips-linux-gnu-objdump')
    new,_,new_addresses=load_elf_functions(str(after_elf),'mips-linux-gnu-objdump')
    changed=[name for name in new if old[name]!=new[name]]
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SLOT_SIZE]
    if set(old)!=set(new)or old_addresses!=new_addresses or changed!=[FUNCTION]or new[FUNCTION]!=list(struct.unpack('>69I',truth)):
        raise ValueError('Full image function/address/69-word slot closure failed')
    data=audit_layout(after_elf,root/'conker')
    if not data['exact']or(data['bytes'],data['owner_count'],data['different_bytes'])!=(189088,720,0):raise ValueError('Protected Game data changed')
    report=dict(function=FUNCTION,source_installed=installed,words=WORDS,slot_words=69,alignment_words=3,frame=0x18,
        guards=0,relocations=len(bindings),neighbors=neighbors,raw_neighbors=raw_neighbors,raw_sha256=hashlib.sha256(raw).hexdigest(),
        retail_sha256=RETAIL_SHA256,qualified_owner_sha256=hashlib.sha256(after_owner.read_bytes()).hexdigest(),
        predecessor_elf_sha256=BASELINE_ELF_SHA256,qualified_elf_sha256=hashlib.sha256(after).hexdigest(),functions=len(new),
        changed_bodies=changed,all_addresses_fixed=True,strict_exclusions=0,strict_changed_bytes=delta,registry=registry_evidence(root),game_data=data)
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=before_owner,qualified_owner=after_owner,predecessor_elf=before_elf,
                qualified_elf=after_elf,qualified_compact=after_obj)

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
