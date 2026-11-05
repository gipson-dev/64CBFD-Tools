"""Screen the two damped velocity triples and independently integrated points."""
import hashlib,itertools,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15197AB4','generated_1C2C60'
SOURCE='conker/src/game/generated_1C2C60.c'
BUILD='conker/build/game-dual-damped-motion-candidates'
ENTRY,ROM,WORDS,SLOT_WORDS=0x15197AB4,0x1C4F64,66,66
PLACEHOLDER='s32 func_15197AB4() {\n    return 0;\n}'
DECLARATIONS='''typedef struct {
    u8 retained00[0x34];
    f32 position[3];
    f32 endPoint[3];
    u8 retained4C[0xF4];
    f32 velocity[3];
    f32 endVelocity[3];
    f32 verticalAcceleration;
    f32 damping;
    f32 endDamping;
} DualDampedMotion15197AB4;
extern f32 D_800BE9A4;

'''
SELECTED='''/* Damp and accelerate each velocity triple, then advance its own point. */
s32 func_15197AB4(DualDampedMotion15197AB4 *motion) {
    f32 damping = motion->damping;
    f32 acceleration = motion->verticalAcceleration;
    f32 endDamping = motion->endDamping;

    motion->velocity[0] *= damping;
    motion->velocity[1] += acceleration * D_800BE9A4;
    motion->velocity[2] *= damping;
    motion->endVelocity[0] *= endDamping;
    motion->endVelocity[1] += acceleration * D_800BE9A4;
    motion->endVelocity[2] *= endDamping;
    motion->position[0] += motion->velocity[0] * D_800BE9A4;
    motion->position[1] += motion->velocity[1] * D_800BE9A4;
    motion->position[2] += motion->velocity[2] * D_800BE9A4;
    motion->endPoint[0] += motion->endVelocity[0] * D_800BE9A4;
    motion->endPoint[1] += motion->endVelocity[1] * D_800BE9A4;
    motion->endPoint[2] += motion->endVelocity[2] * D_800BE9A4;
    return 1;
}'''

def source_states(live):
    marker='/* Non-matching placeholders for the text-only asm slice asm/1C2C60.s. */'
    if live.count(PLACEHOLDER)==1 and SELECTED not in live and DECLARATIONS not in live:
        return live,live.replace(marker,DECLARATIONS+marker,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        return live.replace(DECLARATIONS,'',1).replace(SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Dual damped motion source state changed')

def source_with(body=SELECTED):return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)

def compare(label='selected',body=SELECTED):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);obj,diag=compile_owner(ROOT,out,source_with(body),label)
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    differences=[dict(offset=i*4,ours=a,retail=b)for i,(a,b)in enumerate(itertools.zip_longest(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>%dI'%WORDS,truth),fillvalue=0))if a!=b]
    return dict(words=size//4,differences=differences,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
        bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
if __name__=='__main__':print(json.dumps(compare(),indent=2))
