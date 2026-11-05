"""Screen the live sequence catch-up loop and slot-zero transition."""
import hashlib,itertools,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1501E2F8','generated_49D30'
SOURCE='conker/src/game/generated_49D30.c'
BUILD='conker/build/game-sequence-catchup-candidates'
ENTRY,ROM,WORDS=0x1501E2F8,0x4B7A8,66
PLACEHOLDER='s32 func_1501E2F8() {\n    return 0;\n}'
DECLARATIONS='s32 func_1501E400();\n\n'
SELECTED='''/* Catch up an active sequence, rechecking slot zero after each full pass. */
void func_1501E2F8(s32 slot) {
    for (;;) {
        if (D_800C35EA[slot] != 1) break;
        if (D_800C35B0[slot] < D_800C3640[slot]) break;
        if (D_800C3C8C == 0) {
            func_1501E81C(0, slot);
            if (D_800C35EA[slot] != 1) break;
            func_1501E400(0);
            slot = 0;
            func_150242F8(1, 0);
            func_1501EC38(0);
            func_150242F8(0, 0);
            func_15020EC4(0);
        } else {
            D_800C3C8C = 2;
            break;
        }
    }
}'''

def source_states(live):
    if live.count(PLACEHOLDER)==1 and SELECTED not in live and DECLARATIONS not in live:
        return live,live.replace(PLACEHOLDER,DECLARATIONS+SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        return live.replace(DECLARATIONS+SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Sequence catch-up source state changed')

def source_with(body=SELECTED):return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)

def compare(label='selected',body=SELECTED):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);obj,diag=compile_owner(ROOT,out,source_with(body),label)
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    diffs=[dict(offset=i*4,ours=a,retail=b)for i,(a,b)in enumerate(itertools.zip_longest(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>%dI'%WORDS,truth),fillvalue=0))if a!=b]
    return dict(words=size//4,differences=diffs,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
        bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
if __name__=='__main__':print(json.dumps(compare(),indent=2))
