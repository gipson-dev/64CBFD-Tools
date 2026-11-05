"""Screen packed record colors and fallback defaults with ordered byte stores."""
import hashlib,itertools,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1515E43C','generated_18A8F0'
SOURCE='conker/src/game/generated_18A8F0.c'
BUILD='conker/build/game-record-color-query-candidates'
ENTRY,ROM,WORDS,SLOT_WORDS=0x1515E43C,0x18B8EC,66,66
PLACEHOLDER='s32 func_1515E43C() {\n    return 0;\n}'
DECLARATIONS='''extern LinkedNode *D_800DCD84;
extern u8 D_800DCD24[], D_800DCD28[];
extern u8 D_800DCD3C, D_800DCD3D;
u8 *func_1515EB84(s32, s32, s32, s32, LinkedNode *);

'''
SELECTED='''/* Resolve packed record colors or copy the live default colors in byte order. */
void func_1515E43C(s32 x, s32 y, s32 z, s32 unused,
                   u8 *primary, u8 *secondary, u8 *secondaryExtra, u8 *primaryExtra) {
    u8 *record = func_1515EB84(x, y, z, 0, D_800DCD84);

    if (record != 0) {
        primary[0] = (*(u32 *)(record + 0x18)) & 0xFF;
        primary[1] = (*(u32 *)(record + 0x18) >> 8) & 0xFF;
        primary[2] = (*(u32 *)(record + 0x18) >> 16) & 0xFF;
        secondary[0] = (*(u32 *)(record + 0x1C)) & 0xFF;
        secondary[1] = (*(u32 *)(record + 0x1C) >> 8) & 0xFF;
        secondary[2] = (*(u32 *)(record + 0x1C) >> 16) & 0xFF;
        *secondaryExtra = (*(u32 *)(record + 0x1C) >> 24) & 0xFF;
        *primaryExtra = (*(u32 *)(record + 0x18) >> 24) & 0xFF;
    } else {
        primary[0] = D_800DCD24[0];
        primary[1] = D_800DCD24[1];
        primary[2] = D_800DCD24[2];
        secondary[0] = D_800DCD28[0];
        secondary[1] = D_800DCD28[1];
        secondary[2] = D_800DCD28[2];
        *secondaryExtra = D_800DCD3C;
        *primaryExtra = D_800DCD3D;
    }
}'''

def source_states(live):
    marker='/* Non-matching placeholders for the text-only asm slice asm/18A8F0.s. */'
    if live.count(PLACEHOLDER)==1 and SELECTED not in live and DECLARATIONS not in live:
        return live,live.replace(marker,DECLARATIONS+marker,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        return live.replace(DECLARATIONS,'',1).replace(SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Record color query source state changed')

def source_with(body=SELECTED):return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)

def compare(label='selected',body=SELECTED):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    obj,diag=compile_owner(ROOT,out,source_with(body),label);text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    differences=[dict(offset=i*4,ours=a,retail=b)for i,(a,b)in enumerate(itertools.zip_longest(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>%dI'%WORDS,truth),fillvalue=0))if a!=b]
    return dict(words=size//4,differences=differences,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
        bindings={at-start:r for at,r in rs.items()if start<=at<start+size})

if __name__=='__main__':print(json.dumps(compare(),indent=2))
