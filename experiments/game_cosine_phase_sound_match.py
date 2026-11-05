"""Qualify cosine/sound motion with closed FPR roles and two adjacent read loads."""
import hashlib,json,struct,re
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_cosine_phase_sound_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT='conker/build/src/game/generated_137ED0.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/137ED0.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,REGISTRY='conker/conker.us.bin','conker/asm/data/22D710.rodata.s'
BUILD='conker/build/game-cosine-phase-sound-1510ADD8-match'
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,NATURAL_FRAME,RETAIL_FRAME=264,32,32
RAW_SHA256='c3e4ed0649d8b692013b56f80caf5c403fc132706cf962a98ebec3b1eb29da6a'
RETAIL_SHA256='c2112e688fd2b7156e8d496c079d8c3dc2d536b3a45d7632174c8ea8553da526'
BASELINE_ELF_SHA256='4a421a1bed2aab994b0ed564b673113dddcba2262cafd4aa4480e58fea16397f'
BINDINGS={0x8:[('R_MIPS_HI16','D_800BE9E4')],0xC:[('R_MIPS_LO16','D_800BE9E4')],
 0x10:[('R_MIPS_HI16','D_800A26B0')],0x14:[('R_MIPS_LO16','D_800A26B0')],0x40:[('R_MIPS_26','cosf')],
 0x54:[('R_MIPS_HI16','D_800A26B8')],0x74:[('R_MIPS_HI16','D_800A26B4')],0x78:[('R_MIPS_LO16','D_800A26B4')],
 0xA8:[('R_MIPS_26','func_15114D24')],0xBC:[('R_MIPS_LO16','D_800A26B8')],0xF0:[('R_MIPS_26','func_15114D24')]}
RETAIL_BINDINGS={**{at:rows for at,rows in BINDINGS.items()if at!=0xBC},0xB8:BINDINGS[0xBC]}
ROLES=((0x64,0x70,12,16),(0x78,0x88,6,18),(0x7C,0x88,16,6),(0xD8,0xE8,12,4))
GUARD_WORDS=((0x64,0x46025301,0x46025401),(0x70,0xE48C0060,0xE4900060),
 (0x78,0xC4260000,0xC4320000),(0x7C,0xC4900080,0xC4860080),(0x88,0x4610303E,0x4606903E),
 (0xB8,0xC4800080,0xC4220000),(0xBC,0xC4220000,0xC4800080),
 (0xD8,0x46020301,0x46020101),(0xE8,0xE48C0080,0xE4840080))
PATCH_ROWS=tuple(dict(offset='0x%03X'%at,expected='0x%08X'%a,replacement='0x%08X'%b)for at,a,b in GUARD_WORDS)
source_states=candidate.source_states
def complete_row(row):
    at=int(row['offset'],0)
    def binding(rows):return '|'.join(kind+':'+symbol for kind,symbol in rows)or '-'
    return dict(filename=FILENAME,function=FUNCTION,**row,expected_relocations=binding(BINDINGS.get(at,[])),
        replacement_relocations=binding(RETAIL_BINDINGS.get(at,[])),note='Derive closed cosine-motion FPR roles and adjacent phase/period reads',
        insert_after='',insert_after_relocations='',omit='false')
def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=BINDINGS:raise ValueError('Cosine phase/sound natural body or bindings changed')
    if len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Cosine phase/sound retail body changed')
    words=list(struct.unpack('>66I',raw));result=[]
    for i,w in enumerate(words):
        at=i*4;mapping={a:b for lo,hi,a,b in ROLES if lo<=at<=hi};role=lambda r:mapping.get(r,r)
        op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        out=w
        if mapping:
            if op in(49,57):out=(w&0xFFE0FFFF)|(role(rt)<<16)
            elif op==17 and fmt==16 and fn in(1,62):out=(w&0xFFE0003F)|(role(rt)<<16)|(role(fs)<<11)|(role(fd)<<6)
            elif op in(4,5,9,20,21,43)or(op==17 and fmt==8):pass
            else:raise ValueError('Unexpected instruction within cosine FPR lifetime')
        result.append(out)
    # These are two independent reads, with different destination FPRs and
    # unchanged address GPRs. Even coincident addresses have no intervening write.
    if words[46:48]!=[0xC4800080,0xC4220000]:raise ValueError('Adjacent cosine read preimage changed')
    result[46:48]=result[47:45:-1]
    fitted=struct.pack('>66I',*result)
    if[(i*4,a,b)for i,(a,b)in enumerate(zip(words,result))if a!=b]!=list(GUARD_WORDS):raise ValueError('Cosine derived rows changed')
    expected=bytearray(truth)
    for at,rows in RETAIL_BINDINGS.items():
        mask=0xFC000000 if rows[0][0]=='R_MIPS_26'else 0xFFFF0000
        struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&mask)
    if fitted!=bytes(expected):raise ValueError('Complete fitted cosine body differs')
    return fitted,dict(FPR_lifetimes=4,adjacent_read_swap=[0xB8,0xBC],instructions=66,changed_words=9,inserted_or_omitted_instructions=0)
def checked_candidate(root,obj):
    from tools.pad_generated_object import parse_object
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:rows for at,rows in rs.items()if f['value']<=at<f['value']+f['size']}
    normalized(raw,bindings,(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]);return raw,bindings
def registry_evidence(root):
    image=(Path(root)/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,w in enumerate(words)if w>>26 in(2,3)and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)]
    pointers=[i*4 for i,w in enumerate(words)if w==ENTRY]
    block=(Path(root)/REGISTRY).read_text().split('dlabel D_80088C90\n')[1].split('enddlabel D_80088C90')[0]
    entries=re.findall(r'\.word\s+(\w+)',block)
    if calls or pointers!=[0x22D984]or entries[47*3:48*3]!=[FUNCTION,'0x00000000','0x00000000']:raise ValueError('Cosine phase/sound registry changed')
    return dict(direct_jump_calls=[],pointer_literals=['0x22d984'],table='D_80088C90',row=47,stride=12,abi='void(u8 *state)',caller_sites=['0x15113EE8','0x15113FC0'])
def strict_image(before,after,truth):
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,f)for off,name,f,_ in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Cosine phase/sound predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    # Referencing the phase-rate constant rotates one five-name ld hash bucket.
    # Reconstruct complete records and strings only from the pinned predecessor.
    names=('D_800A26B0','D_800A1128','D_800AAA78','D_800AA9A8','D_8009CC28')
    values=(0x800A26B0,0x800A1128,0x800AAA78,0x800AA9A8,0x8009CC28)
    syms={name:(off,f,string)for off,name,f,string in symbol_rows(before)}
    group=[syms[name]for name in names]
    for index,(off,fields,string)in enumerate(group):
        if off!=0x2B450C+16*index or fields[1:]!=(values[index],0,16,0,65521)or before[string:string+11]!=names[index].encode()+b'\0':
            raise ValueError('Cosine phase/sound symbol bucket changed')
        source=(index+1)%5
        struct.pack_into('>IIIBBH',expected,off,fields[0],*group[source][1][1:])
        expected[string:string+11]=names[source].encode()+b'\0'
    if bytes(expected)!=after:raise ValueError('Cosine phase/sound whole ELF prediction differs')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    names=('candidate FUNCTION FILENAME SOURCE OBJECT ASM GUARDS ELF LINKER ROM_IMAGE REGISTRY BUILD ENTRY ROM WORDS SIZE '
        'NATURAL_FRAME RETAIL_FRAME RAW_SHA256 RETAIL_SHA256 BINDINGS RETAIL_BINDINGS PATCH_ROWS complete_row source_states registry_evidence checked_candidate').split()
    with patch.multiple(harness,**{name:globals()[name]for name in names}):result=harness.prepare(root,output or Path(root)/BUILD)
    before=result['predecessor_elf'].read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256:raise ValueError('Cosine phase/sound predecessor image changed')
    truth=(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];raw,bindings=checked_candidate(root,result['qualified_compact'])
    _,proof=normalized(raw,bindings,truth);delta=strict_image(before,result['qualified_elf'].read_bytes(),truth)
    result['report'].update(normalization=proof,literal_full_image_prediction=True,strict_changed_bytes=delta)
    (Path(output or Path(root)/BUILD)/'qualification.json').write_text(json.dumps(result['report'],indent=2)+'\n');return result
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
