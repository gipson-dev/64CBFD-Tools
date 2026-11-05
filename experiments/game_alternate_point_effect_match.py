"""Qualify alternate point effects and one closed saved-mode stack lifetime."""
import hashlib,json,re,struct
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_alternate_point_effect_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT='conker/build/src/game/generated_173D40.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/173D40.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,REGISTRY='conker/conker.us.bin','conker/asm/data/22EB40.rodata.s'
BUILD='conker/build/game-alternate-point-effect-15146D60-match'
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,SLOT_SIZE,NATURAL_FRAME,RETAIL_FRAME=292,292,88,88
RAW_SHA256='bc4108e0ebcb78c2c5c2066836ebed1b8ba02f29e918a4ef76bcfba09e6b5022'
RETAIL_SHA256='cfdedfd0303caa2072e57265adf78596f9fda86aad4930e4aaab63e5db7e8919'
BASELINE_ELF_SHA256='743cca9727fe79f2058b52f709599e21ee5ea32a28647a72ba8582124f89b95a'
BINDINGS={0x30:[('R_MIPS_26','func_15146890')],0x44:[('R_MIPS_HI16','D_800A5728')],0x48:[('R_MIPS_LO16','D_800A5728')],
0x54:[('R_MIPS_HI16','D_800A572C')],0x58:[('R_MIPS_LO16','D_800A572C')],0x10C:[('R_MIPS_26','func_15141F78')]}
RETAIL_BINDINGS=BINDINGS
GUARD_WORDS=((0x34,0xAFA70020,0xAFA70024),(0xF8,0x8FAB0020,0x8FAB0024))
PATCH_ROWS=tuple(dict(offset='0x%03X'%at,expected='0x%08X'%a,replacement='0x%08X'%b)for at,a,b in GUARD_WORDS)
source_states=candidate.source_states

def complete_row(row):return dict(filename=FILENAME,function=FUNCTION,**row,expected_relocations='-',replacement_relocations='-',
    note='Derive closed saved-mode stack lifetime from SP+0x20 to retail SP+0x24',insert_after='',insert_after_relocations='',omit='false')

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}

def original_bytes(root):return(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]

def checked_payload(raw,bindings,truth):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=BINDINGS:raise ValueError('Alternate effect natural body/bindings changed')
    if len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Alternate effect retail body changed')
    words=list(struct.unpack('>73I',raw));changed=[]
    for i,w in enumerate(words):
        op,base,imm=w>>26,w>>21&31,w&65535
        if base==29 and imm==0x20 and op in(35,43):words[i]=(w&0xFFFF0000)|0x24;changed.append((i*4,w,words[i]))
    if changed!=list(GUARD_WORDS):raise ValueError('Alternate effect saved-mode accesses changed')
    expected=bytearray(truth)
    for at,rows in BINDINGS.items():
        mask=0xFC000000 if rows[0][0]=='R_MIPS_26'else 0xFFFF0000
        struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&mask)
    if struct.pack('>73I',*words)!=bytes(expected):raise ValueError('Complete alternate effect fitted body differs')
    return raw,bindings

def checked_candidate(root,obj):return checked_payload(*function_blob(obj),original_bytes(root))

def registry_evidence(root):
    image=(Path(root)/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,w in enumerate(words)if w>>26 in(2,3)and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)]
    pointers=[i*4 for i,w in enumerate(words)if w==ENTRY]
    block=(Path(root)/REGISTRY).read_text().split('dlabel D_8008A0B4\n')[1].split('enddlabel D_8008A0B4')[0]
    entries=re.findall(r'\.word\s+(\w+)',block)
    if calls or pointers!=[0x22EB8C]or entries[6:8]!=[FUNCTION,'0x00000055']or len(entries)!=43:raise ValueError('Alternate effect callback registry changed')
    return dict(direct_jump_calls=[],pointer_literals=['0x22eb8c'],table='D_8008A0B4',index=3,count=85,dispatch='func_15141A7C',abi='void(u8 *actor, s32 mode, s32 amount)')

def strict_image(before,after,truth):
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256 or len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Alternate effect strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,f)for off,name,f,_ in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Alternate effect predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    symbols={name:(off,f,string)for off,name,f,string in symbol_rows(before)}
    names=('D_800A572C','D_800A142C');a,b=(symbols[name]for name in names)
    if(a[0],b[0])!=(0x2C34CC,0x2C34DC)or a[1][1:]!=(0x800A572C,0,16,0,65521)or b[1][1:]!=(0x800A142C,0,16,0,65521):raise ValueError('Alternate effect predecessor symbol pair changed')
    for destination,source,name in((a,b,names[1]),(b,a,names[0])):
        off,fields,string=destination
        if before[string:string+11]!=names[0 if destination==a else 1].encode()+b'\0':raise ValueError('Alternate effect predecessor name changed')
        struct.pack_into('>IIIBBH',expected,off,fields[0],*source[1][1:]);expected[string:string+11]=name.encode()+b'\0'
    if bytes(expected)!=after:raise ValueError('Alternate effect literal complete image prediction differs')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    names=('candidate FUNCTION FILENAME SOURCE OBJECT ASM GUARDS ELF LINKER ROM_IMAGE REGISTRY BUILD ENTRY ROM WORDS SIZE '
        'NATURAL_FRAME RETAIL_FRAME RAW_SHA256 RETAIL_SHA256 BINDINGS RETAIL_BINDINGS PATCH_ROWS complete_row source_states registry_evidence checked_candidate').split()
    with patch.multiple(harness,**{name:globals()[name]for name in names}):result=harness.prepare(root,output or Path(root)/BUILD)
    before=result['predecessor_elf'].read_bytes();after=result['qualified_elf'].read_bytes();delta=strict_image(before,after,original_bytes(root))
    out=Path(output or Path(root)/BUILD)
    raw_neighbors=same_functions(out/'predecessor-compact.o',result['qualified_compact'],(FUNCTION,))
    if normalized_pools(out/'predecessor-compact.o')!=normalized_pools(result['qualified_compact']):raise ValueError('Alternate effect raw pools changed')
    result['report'].update(slot_words=73,alignment_words=0,frame=88,raw_neighbors=raw_neighbors,strict_changed_bytes=delta,literal_full_image_prediction=True,
        normalization=dict(saved_mode_offsets=[0x20,0x24],closed_accesses=2,inserted_or_omitted_instructions=0))
    (out/'qualification.json').write_text(json.dumps(result['report'],indent=2)+'\n');return result

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
