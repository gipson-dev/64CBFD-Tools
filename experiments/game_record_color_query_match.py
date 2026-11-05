"""Qualify direct packed-record color extraction and live fallback byte copies."""
import hashlib,json,struct
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_color_query_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT='conker/build/src/game/generated_18A8F0.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/18A8F0.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,REGISTRY='conker/conker.us.bin','conker/asm/18A8F0.s'
BUILD='conker/build/game-record-color-query-1515E43C-match'
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,SLOT_SIZE,NATURAL_FRAME,RETAIL_FRAME=264,264,32,32
RAW_SHA256='d054a96fa4add2cb132003f47826802017ab23b8cab7e2708f0a2252ef0789cb'
RETAIL_SHA256='71f1c40a6bb036aed83d69b19cf8fd675f6b9d16112a4789e78f834fee4d0c69'
BASELINE_ELF_SHA256='fbec38e46735bda7ddea0c9f35d6664febae8668b86d8b9cf786e55491b63257'
BINDINGS={0xC:[('R_MIPS_HI16','D_800DCD84')],0x10:[('R_MIPS_LO16','D_800DCD84')],0x18:[('R_MIPS_26','func_1515EB84')],
0x94:[('R_MIPS_HI16','D_800DCD24')],0x98:[('R_MIPS_LO16','D_800DCD24')],
0xA4:[('R_MIPS_HI16','D_800DCD28')],0xB0:[('R_MIPS_LO16','D_800DCD28')],
0xB4:[('R_MIPS_HI16','D_800DCD3C')],0xE4:[('R_MIPS_LO16','D_800DCD3C')],
0xC0:[('R_MIPS_HI16','D_800DCD3D')],0xF0:[('R_MIPS_LO16','D_800DCD3D')]}
RETAIL_BINDINGS=BINDINGS
PATCH_ROWS=()
source_states=candidate.source_states
def complete_row(row):raise ValueError('Direct record color query has no patches')

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}
def original_bytes(root):return(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]

def checked_payload(raw,bindings,truth):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=BINDINGS:raise ValueError('Record color query natural body/bindings changed')
    if len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Record color query retail body changed')
    expected=bytearray(truth)
    for at,rows in BINDINGS.items():
        mask=0xFC000000 if rows[0][0]=='R_MIPS_26'else 0xFFFF0000
        struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&mask)
    if raw!=bytes(expected):raise ValueError('Record color query requires a correction')
    return raw,bindings
def checked_candidate(root,obj):return checked_payload(*function_blob(obj),original_bytes(root))

def registry_evidence(root):
    image=(Path(root)/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,w in enumerate(words)if w>>26 in(2,3)and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)]
    pointers=[i*4 for i,w in enumerate(words)if w==ENTRY]
    if calls!=[0x18AE50,0x18B810]or pointers:raise ValueError('Record color query caller census changed')
    return dict(direct_calls=calls,pointers=pointers,abi='void(s32 x,y,z,unused,u8 *primary,*secondary,*secondaryExtra,*primaryExtra)',output_lengths=[3,3,1,1])

def strict_image(before,after,truth):
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256 or len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Record color query strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,f)for off,name,f,_ in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Record color query predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:raise ValueError('Record color query literal whole image prediction differs')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    names=('candidate FUNCTION FILENAME SOURCE OBJECT ASM GUARDS ELF LINKER ROM_IMAGE REGISTRY BUILD ENTRY ROM WORDS SIZE '
        'NATURAL_FRAME RETAIL_FRAME RAW_SHA256 RETAIL_SHA256 BINDINGS RETAIL_BINDINGS PATCH_ROWS complete_row source_states registry_evidence checked_candidate').split()
    with patch.multiple(harness,**{name:globals()[name]for name in names}):result=harness.prepare(root,output or Path(root)/BUILD)
    out=Path(output or Path(root)/BUILD);before=result['predecessor_elf'].read_bytes();after=result['qualified_elf'].read_bytes()
    delta=strict_image(before,after,original_bytes(root));raw_neighbors=same_functions(out/'predecessor-compact.o',result['qualified_compact'],(FUNCTION,))
    if normalized_pools(out/'predecessor-compact.o')!=normalized_pools(result['qualified_compact']):raise ValueError('Record color query raw pools changed')
    result['report'].update(slot_words=66,alignment_words=0,frame=32,raw_neighbors=raw_neighbors,strict_changed_bytes=delta,literal_full_image_prediction=True)
    (out/'qualification.json').write_text(json.dumps(result['report'],indent=2)+'\n');return result

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
