"""Screen point/height interval effect forwarding and its unsigned tag conversion."""
import hashlib,itertools,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_150EB090','generated_118400'
SOURCE='conker/src/game/generated_118400.c'
BUILD='conker/build/game-point-interval-effect-candidates'
ENTRY,ROM,WORDS,SLOT_WORDS=0x150EB090,0x118540,73,76
PLACEHOLDER='s32 func_150EB090() {\n    return 0;\n}'
OLD_TYPE='typedef struct HeightResult71820 HeightResult71820;'
RESULT_TYPE='''typedef struct HeightResult71820 {
    f32 height;
    s16 vertices[9];
    s16 pad16;
    u32 metadata;
    u8 flags;
    u8 state;
    u16 pad1E;
    s32 value;
} HeightResult71820;'''
DECLARATIONS='''extern f32 D_800A1470, D_800A1474;
void func_15141F78(u8, u8 *, f32, u8, f32 *, u8);

'''
SELECTED='''/* Emit a point/height-interval effect using the live actor tag and requested scale. */
void func_150EB090(u8 *actor, s32 mode, s32 amount) {
    f32 position[3];
    HeightResult71820 result;

    if (*(s32 *)(actor + 0x1D4) == 0) return;
    if (func_150EAF50(position, actor, &result, mode) != 0) {
        func_15141F78(10, (u8 *)&result, (f32)amount * D_800A1470,
                      (u8)(u32)(*(f32 *)(actor + 0x40) * D_800A1474), position, mode);
    }
}'''
def source_states(live):
    marker='#include <ultra64.h>\n\n'
    if live.count(PLACEHOLDER)==1 and live.count(OLD_TYPE)==1 and SELECTED not in live and DECLARATIONS not in live:
        return live,live.replace(OLD_TYPE,RESULT_TYPE,1).replace(marker,marker+DECLARATIONS,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(RESULT_TYPE)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        return live.replace(RESULT_TYPE,OLD_TYPE,1).replace(DECLARATIONS,'',1).replace(SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Point-interval effect source state changed')
def source_with(body=SELECTED):return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)
def compare(label='selected',body=SELECTED):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    obj,diagnostics=compile_owner(ROOT,out,source_with(body),label)
    text,functions,relocations=parse_object(obj);info=functions[FUNCTION];start,size=info['value'],info['size']
    raw=text[start:start+size];linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size]
    truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    differences=[dict(offset=i*4,ours=a,retail=b)for i,(a,b)in enumerate(itertools.zip_longest(
        struct.unpack('>%dI'%(size//4),ours),struct.unpack('>%dI'%WORDS,truth),fillvalue=0))if a!=b]
    return dict(words=size//4,differences=differences,raw_sha256=hashlib.sha256(raw).hexdigest(),
        retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diagnostics,
        bindings={at-start:r for at,r in relocations.items()if start<=at<start+size})
if __name__=='__main__':print(json.dumps(compare(),indent=2))
