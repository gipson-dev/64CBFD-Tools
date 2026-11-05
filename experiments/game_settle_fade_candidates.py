"""Screen the wrapped position/spin and timed fade callback as semantic C."""

import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ROOT = Path(__file__).resolve().parents[2]
FUNCTION, OWNER = "func_1517A84C", "generated_1A7260"
SOURCE = "conker/src/game/generated_1A7260.c"
BUILD = "conker/build/game-settle-fade-candidates"
ENTRY, ROM, WORDS = 0x1517A84C, 0x1A7CFC, 67
PLACEHOLDER = "s32 func_1517A84C() {\n    return 0;\n}"
DECLARATIONS = """typedef struct {
    u8 retained00[0x90];
    s16 x, y, z;
    s16 angleX, angleY, angleZ;
    s8 spinX, spinY, spinZ;
    u8 retained9F;
    s16 speedX, speedY, speedZ;
    u16 timer;
    u8 retainedA8[8];
    s16 floorY;
    u8 retainedB2;
    u8 opacity;
} SettleFade1517A84C;
extern s32 D_800BE9E4;
void func_1516972C(void *);

"""
SELECTED = """/* Move and rotate the record until it lands, then fade and retire it. */
void func_1517A84C(SettleFade1517A84C *record) {
    s32 remaining = record->timer;

    if (remaining == 0) {
        record->x += record->speedX;
        record->y += record->speedY;
        record->z += record->speedZ;
        if (record->speedY > 0) {
            record->speedY--;
            if (record->speedY <= 0) {
                record->speedY = -3;
            }
        }
        remaining = record->y - record->floorY;
        if (remaining <= 0) {
            record->angleX = 90;
            record->angleZ = 0;
            record->timer = 60;
            record->y = record->floorY;
        } else {
            record->angleX += record->spinX;
            record->angleY += record->spinY;
            record->angleZ += record->spinZ;
        }
    } else {
        remaining = (s32)((u32)remaining - (u32)D_800BE9E4);
        if (remaining > 0) {
            record->timer = remaining;
            record->opacity = (s32)((u32)remaining << 8) / 60;
        } else {
            func_1516972C(record);
        }
    }
}"""


def source_states(live):
    marker = '#include <ultra64.h>\n'
    if live.count(PLACEHOLDER)==1:
        if DECLARATIONS in live or SELECTED in live or live.count(marker)!=1:
            raise ValueError("Settle/fade predecessor changed")
        qualified=live.replace(marker,marker+"\n"+DECLARATIONS,1).replace(PLACEHOLDER,SELECTED,1)
        return live,qualified,False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        predecessor=live.replace("\n"+DECLARATIONS,"",1).replace(SELECTED,PLACEHOLDER,1)
        return predecessor,live,True
    raise ValueError("Settle/fade source state changed")


def source_with(body):
    _,qualified,_=source_states((ROOT/SOURCE).read_text())
    return qualified.replace(SELECTED,body,1)


def compare(label="selected",body=SELECTED):
    output=ROOT/BUILD;output.mkdir(parents=True,exist_ok=True)
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
    return {"label":label,"words":len(words),"frame":(-words[0])&65535,
            "raw_sha256":hashlib.sha256(raw).hexdigest(),
            "retail_sha256":hashlib.sha256(retail).hexdigest(),
            "differences":differences,"diagnostics":diagnostics,
            "bindings":{at-start:rows for at,rows in relocations.items() if start<=at<start+size}}


if __name__=="__main__":print(json.dumps(compare(),indent=2))
