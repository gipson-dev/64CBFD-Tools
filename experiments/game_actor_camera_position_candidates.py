"""Screen actor-key camera-position forwarding without editing production source."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object

ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1509C8FC','generated_C98F0'
SOURCE='conker/src/game/generated_C98F0.c'
BUILD='conker/build/game-actor-camera-position-candidates'
ENTRY,ROM,WORDS=0x1509C8FC,0xC9DAC,66
SLOT_WORDS=69
PLACEHOLDER='s32 func_1509C8FC() {\n    return 0;\n}'
DECLARATIONS='''#include "structs.h"

extern struct108 *D_800DBFF0;
struct127 *func_1505EEF4(s32);
void func_15022190(s16, s16, s16, f32);
void func_150221E8(s16, s16, s16, f32);

'''
SELECTED='''/* Forward an actor's position with the selected camera heading plus 180 degrees. */
void func_1509C8FC(s32 key, s32 alternate) {
    struct127 *actor = func_1505EEF4(key & 0xFFF);
    f32 heading;

    if (actor != NULL) {
        if (D_800DBFF0->unk2C & 0x100) {
            heading = *(f32 *)((u8 *)D_800DBFF0 + 0x760);
        } else {
            heading = D_800DBFF0->unk37C;
        }
        if (alternate) {
            func_150221E8((s16)(s32)actor->x_position, (s16)(s32)actor->y_position,
                          (s16)(s32)actor->z_position, heading + 180.0f);
        } else {
            func_15022190((s16)(s32)actor->x_position, (s16)(s32)actor->y_position,
                          (s16)(s32)actor->z_position, heading + 180.0f);
        }
    }
}'''

def source_states(live):
    marker='#include <ultra64.h>\n\n'
    if live.count(PLACEHOLDER)==1 and DECLARATIONS not in live and SELECTED not in live:
        return live,live.replace(marker,marker+DECLARATIONS,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        return live.replace(DECLARATIONS,'',1).replace(SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Actor camera-position source state changed')

def source_with(body=SELECTED):
    return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)

def compare(label='selected',body=SELECTED):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    obj,diagnostics=compile_owner(ROOT,out,source_with(body),label)
    text,functions,relocations=parse_object(obj);info=functions[FUNCTION]
    start,size=info['value'],info['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size]
    truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    differences=[dict(offset=i*4,ours=a,retail=b)for i,(a,b)in enumerate(itertools.zip_longest(
        struct.unpack('>%dI'%(size//4),ours),struct.unpack('>%dI'%WORDS,truth),fillvalue=0))if a!=b]
    return dict(label=label,words=size//4,differences=differences,raw_sha256=hashlib.sha256(raw).hexdigest(),
        retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diagnostics,
        bindings={at-start:rows for at,rows in relocations.items()if start<=at<start+size})

if __name__=='__main__':print(json.dumps(compare(),indent=2))
