"""Screen semantic C for the object-follow position/velocity callback."""

import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ROOT = Path(__file__).resolve().parents[2]
FUNCTION, OWNER = "func_1515BFA8", "generated_188F90"
SOURCE = "conker/src/game/generated_188F90.c"
BUILD = "conker/build/game-object-follow-update-candidates"
ENTRY, ROM, WORDS = 0x1515BFA8, 0x189458, 68
PLACEHOLDER = "s32 func_1515BFA8() {\n    return 0;\n}"
DECLARATIONS = """typedef struct {
    u8 retained00[0x18];
    u8 *object;
    u8 objectId;
    u8 flags;
    s16 timer;
    struct17 current;
    struct17 previous;
    struct17 velocity;
} ObjectFollowUpdate1515BFA8;

extern f32 D_800BE9A8;

"""
SELECTED = """/* Track the live object's position and reverse displacement, or retire a stale record. */
void func_1515BFA8(ObjectFollowUpdate1515BFA8 *record) {
    s32 remove = 0;
    u8 *object;

    if ((record->flags & 1) != 0) {
        record->timer = (s16)((u32)record->timer - (u32)D_800BE9E4);
        if (record->timer < 0) {
            remove = 1;
        }
    }
    object = record->object;
    if (*(s32 *)object == 0 || record->objectId != object[0x3B]) {
        remove = 1;
    }
    if (remove == 0) {
        record->previous = record->current;
        object = record->object;
        record->current.unk0 = *(f32 *)(object + 0x14);
        record->current.unk4 = *(f32 *)(object + 0x18);
        record->current.unk8 = *(f32 *)(object + 0x1C);
        record->velocity.unk0 = (record->previous.unk0 - record->current.unk0) * D_800BE9A8;
        record->velocity.unk4 = (record->previous.unk4 - record->current.unk4) * D_800BE9A8;
        record->velocity.unk8 = (record->previous.unk8 - record->current.unk8) * D_800BE9A8;
    }
    if (remove != 0) {
        func_1516972C(record);
    }
}"""


def source_states(live):
    marker = '#include "structs.h"\n'
    if live.count(PLACEHOLDER)==1:
        if DECLARATIONS in live or SELECTED in live or live.count(marker)!=1:
            raise ValueError("Object-follow predecessor changed")
        qualified = live.replace(marker,marker+"\n"+DECLARATIONS,1).replace(PLACEHOLDER,SELECTED,1)
        return live,qualified,False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        predecessor=live.replace("\n"+DECLARATIONS,"",1).replace(SELECTED,PLACEHOLDER,1)
        return predecessor,live,True
    raise ValueError("Object-follow source state changed")


def source_with(body):
    _,qualified,_=source_states((ROOT/SOURCE).read_text())
    return qualified.replace(SELECTED,body,1)


def compare(label="selected",body=SELECTED):
    output=ROOT/BUILD
    output.mkdir(parents=True,exist_ok=True)
    obj,diagnostics=compile_owner(ROOT,output,source_with(body),label)
    text,functions,relocations=parse_object(obj)
    info=functions[FUNCTION];start,size=info["value"],info["size"]
    raw=text[start:start+size]
    linked,_=link_owner(ROOT,output,obj,OWNER)
    ours=linked[start:start+size]
    retail=(ROOT/"conker/conker.us.bin").read_bytes()[ROM:ROM+WORDS*4]
    words=struct.unpack(">%dI"%(len(ours)//4),ours)
    truth=struct.unpack(">%dI"%WORDS,retail)
    differences=[{"offset":i*4,"ours":a,"retail":b}
                 for i,(a,b) in enumerate(itertools.zip_longest(words,truth,fillvalue=0)) if a!=b]
    return {"label":label,"words":len(words),"frame":(-words[0])&0xFFFF,
            "raw_sha256":hashlib.sha256(raw).hexdigest(),
            "linked_sha256":hashlib.sha256(ours).hexdigest(),
            "retail_sha256":hashlib.sha256(retail).hexdigest(),
            "differences":differences,"diagnostics":diagnostics,
            "bindings":{at-start:rows for at,rows in relocations.items() if start<=at<start+size}}


if __name__=="__main__":
    print(json.dumps(compare(),indent=2))
