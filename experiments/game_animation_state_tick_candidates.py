"""Screen signed-rate animation phase updates and optional per-state callbacks."""
import hashlib,itertools,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15167B44','game_1944C0'
SOURCE='conker/src/game_1944C0.c'
BUILD='conker/build/game-animation-state-tick-candidates'
ENTRY,ROM,WORDS,SLOT_WORDS=0x15167B44,0x194FF4,69,69
PLACEHOLDER='''/* Non-matching C placeholders for asm/nonmatchings/game_1944C0/func_15167B44.s. */
s32 func_15167B44() {
    return 0;
}'''
SELECTED='''/* Apply the optional update callback, rate countdown and wrapped animation phase. */
void func_15167B44(u8 *state) {
    s32 rate;
    s32 remaining;
    s32 cost;

    if (state[0x24] != 0) {
        D_8008CA20[state[0x24]](state);
    }
    rate = *(s8 *)(state + 0x22);
    if (rate > 0) {
        remaining = state[0x23];
        if (rate < remaining) {
            state[0x23] = remaining - rate;
        } else {
            *(s16 *)(state + 0x14) = (*(u8 **)(state + 0x10))[4] << 8;
        }
    } else if (rate < 0) {
        cost = -rate;
        if (*(s16 *)(state + 0x14) / 256 >= (*(u8 **)(state + 0x10))[4] - 1) {
            remaining = state[0x23];
            if (cost < remaining) {
                state[0x23] = remaining - cost;
                *(s16 *)(state + 0x14) -= *(s16 *)(state + 0x16);
            }
        }
    }
    *(s16 *)(state + 0x14) += *(s16 *)(state + 0x16);
    if (*(s16 *)(state + 0x14) / 256 >= (*(u8 **)(state + 0x10))[4]) {
        func_1516972C((struct102 *)state);
    }
}'''

def source_states(live):
    old='s32 func_15167B44();';new='void func_15167B44(u8 *state);'
    if live.count(PLACEHOLDER)==1 and live.count(old)==1 and SELECTED not in live:
        return live,live.replace(old,new,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(new)==1 and PLACEHOLDER not in live:
        return live.replace(new,old,1).replace(SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Animation state tick source state changed')
def source_with(body=SELECTED):return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)

def compare(label='selected',body=SELECTED):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);obj,diag=compile_owner(ROOT,out,source_with(body),label)
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    differences=[dict(offset=i*4,ours=a,retail=b)for i,(a,b)in enumerate(itertools.zip_longest(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>%dI'%WORDS,truth),fillvalue=0))if a!=b]
    return dict(words=size//4,differences=differences,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
        bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
if __name__=='__main__':print(json.dumps(compare(),indent=2))
