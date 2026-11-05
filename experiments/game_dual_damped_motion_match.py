"""Qualify the direct leaf motion callback through its complete generated owner."""
import hashlib,json,re,struct
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_dual_damped_motion_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT='conker/build/src/game/generated_1C2C60.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/1C2C60.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,REGISTRY='conker/conker.us.bin','conker/asm/data/22E730.rodata.s'
BUILD='conker/build/game-dual-damped-motion-15197AB4-match'
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,SLOT_SIZE,NATURAL_FRAME,RETAIL_FRAME=264,264,0,0
RAW_SHA256='19c57bdc96df0444fbf19c2b1310f68711211f9745dc1375d4689860bce65c5f'
RETAIL_SHA256='6aafd82dc077210e6759995c00a872115d3ab6d0ebc368e2e4c5f4e97bca6053'
BASELINE_ELF_SHA256='62e5bfea14b052e47e4928f670c6895794b3b9c001a74d59f80906ff45419aae'
BINDINGS={0:[('R_MIPS_HI16','D_800BE9A4')],4:[('R_MIPS_LO16','D_800BE9A4')]}
RETAIL_BINDINGS=BINDINGS
PATCH_ROWS=()
source_states=candidate.source_states
def complete_row(row):raise ValueError('Direct dual damped motion has no patches')

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}
def original_bytes(root):return(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
def checked_payload(raw,bindings,truth):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=BINDINGS:raise ValueError('Dual damped motion natural body/bindings changed')
    if len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Dual damped motion retail body changed')
    expected=bytearray(truth)
    for at in BINDINGS:struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&0xFFFF0000)
    if raw!=bytes(expected):raise ValueError('Dual damped motion requires a correction')
    return raw,bindings
def checked_candidate(root,obj):return checked_payload(*function_blob(obj),original_bytes(root))

def registry_evidence(root):
    image=(Path(root)/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,w in enumerate(words)if w>>26 in(2,3)and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)]
    pointers=[i*4 for i,w in enumerate(words)if w==ENTRY]
    block=(Path(root)/REGISTRY).read_text().split('dlabel D_80089CB8\n',1)[1].split('enddlabel D_80089CB8',1)[0]
    entries=re.findall(r'\.word\s+(\w+)',block)
    if calls or pointers!=[0x22E7A0]or len(entries)!=42 or entries[10]!=FUNCTION:raise ValueError('Dual damped motion registration changed')
    return dict(direct_jump_calls=[],pointer_literals=['0x22E7A0'],catalog='D_80089CB8',slot=10,entries=42,
        abi='s32(DualDampedMotion15197AB4 *motion); return one',caller='func_1513CFE4 window 0x1513D034..0x1513D074')

def strict_image(before,after,truth):
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256 or len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Dual damped motion strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,f)for off,name,f,_ in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Dual damped motion predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:raise ValueError('Dual damped motion literal complete image prediction differs')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    names=('candidate FUNCTION FILENAME SOURCE OBJECT ASM GUARDS ELF LINKER ROM_IMAGE REGISTRY BUILD ENTRY ROM WORDS SIZE '
        'NATURAL_FRAME RETAIL_FRAME RAW_SHA256 RETAIL_SHA256 BINDINGS RETAIL_BINDINGS PATCH_ROWS complete_row source_states registry_evidence checked_candidate').split()
    with patch.multiple(harness,**{name:globals()[name]for name in names}):result=harness.prepare(root,output or Path(root)/BUILD)
    out=Path(output or Path(root)/BUILD);before=result['predecessor_elf'].read_bytes();after=result['qualified_elf'].read_bytes()
    delta=strict_image(before,after,original_bytes(root));raw_neighbors=same_functions(out/'predecessor-compact.o',result['qualified_compact'],(FUNCTION,))
    if normalized_pools(out/'predecessor-compact.o')!=normalized_pools(result['qualified_compact']):raise ValueError('Dual damped motion raw pools changed')
    result['report'].update(slot_words=66,alignment_words=0,frame=0,raw_neighbors=raw_neighbors,strict_changed_bytes=delta,literal_full_image_prediction=True)
    (out/'qualification.json').write_text(json.dumps(result['report'],indent=2)+'\n');return result
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
