"""Screen cosine phase motion with alternating half/full-period sound events."""
import hashlib,itertools,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1510ADD8','generated_137ED0'
SOURCE='conker/src/game/generated_137ED0.c'
BUILD='conker/build/game-cosine-phase-sound-candidates'
ENTRY,ROM,WORDS,SLOT_WORDS=0x1510ADD8,0x138288,66,66
PLACEHOLDER='s32 func_1510ADD8() {\n    return 0;\n}'
DECLARATIONS='''extern s32 D_800BE9E4;
extern f32 D_800A26B0, D_800A26B4, D_800A26B8;
f32 cosf(f32);
s32 func_15114D24(u8 *, s32, s32, s16, s16, s32);

'''
SELECTED='''/* Advance cosine motion and signal the alternating half/full-period crossings. */
void func_1510ADD8(u8 *state) {
    f32 value;
    f32 previous;

    *(f32 *)(state + 0x80) += D_800A26B0 * (f32)D_800BE9E4 / 60.0f;
    value = cosf(*(f32 *)(state + 0x80)) * 10.0f;
    previous = *(f32 *)state - value;
    *(f32 *)state = value;
    *(f32 *)(state + 0x60) = previous;
    if (*(s32 *)(state + 0x7C) == 0) {
        if (D_800A26B4 <= *(f32 *)(state + 0x80)) {
            *(s32 *)(state + 0x7C) = 1;
            func_15114D24(state, 0x4CA, 12000, 200, 1000, 4);
        }
    } else if (D_800A26B8 <= *(f32 *)(state + 0x80)) {
        previous = *(f32 *)(state + 0x80) - D_800A26B8;
        *(s32 *)(state + 0x7C) = 0;
        *(f32 *)(state + 0x80) = previous;
        func_15114D24(state, 0x4CB, 12000, 200, 1000, 4);
    }
}'''
def source_states(live):
    marker='#include <ultra64.h>\n\n'
    if live.count(PLACEHOLDER)==1 and SELECTED not in live and DECLARATIONS not in live:
        return live,live.replace(marker,marker+DECLARATIONS,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        return live.replace(DECLARATIONS,'',1).replace(SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Cosine phase/sound source state changed')
def source_with(body=SELECTED):return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)
def compare(label='selected',body=SELECTED):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);obj,diag=compile_owner(ROOT,out,source_with(body),label)
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    diffs=[dict(offset=i*4,ours=a,retail=b)for i,(a,b)in enumerate(itertools.zip_longest(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>%dI'%WORDS,truth),fillvalue=0))if a!=b]
    return dict(words=size//4,differences=diffs,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
     bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
if __name__=='__main__':print(json.dumps(compare(),indent=2))
