"""Screen the damped dual-point motion callback with live endpoint blending."""

import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ROOT = Path(__file__).resolve().parents[2]
FUNCTION, OWNER = "func_1518EF54", "generated_1BA1D0"
SOURCE = "conker/src/game/generated_1BA1D0.c"
BUILD = "conker/build/game-blended-dual-point-motion-candidates"
ENTRY, ROM, WORDS = 0x1518EF54, 0x1BC404, 65
PLACEHOLDER = "s32 func_1518EF54() {\n    return 0;\n}"
DECLARATIONS = """typedef struct {
    u8 retained00[0x34];
    f32 position[3];
    f32 endPoint[3];
    u8 retained4C[0xF4];
    f32 velocity[3];
    f32 verticalAcceleration;
    f32 damping;
    u8 retained154[8];
    f32 blend;
} BlendedDualPointMotion1518EF54;

"""
SELECTED = """/* Advance both damped points, then blend the endpoint toward the position. */
s32 func_1518EF54(BlendedDualPointMotion1518EF54 *motion) {
    struct BlendedPointPayload1518EF54 {
        u8 retained00[0x4C];
        f32 blend;
    } *payload = (void *)((u8 *)motion + 0x110);
    f32 damping = motion->damping;
    f32 step;
    f32 dx, dy, dz;

    motion->velocity[0] *= damping;
    motion->velocity[1] += motion->verticalAcceleration * D_800BE9A4;
    motion->velocity[2] *= damping;
    step = D_800BE9A4;
    dx = motion->velocity[0] * step;
    dy = motion->velocity[1] * step;
    dz = motion->velocity[2] * step;
    motion->position[0] += dx;
    motion->position[1] += dy;
    motion->position[2] += dz;
    motion->endPoint[0] += dx;
    motion->endPoint[1] += dy;
    motion->endPoint[2] += dz;
    motion->endPoint[0] = motion->position[0] + (motion->endPoint[0] - motion->position[0]) * motion->blend;
    motion->endPoint[1] = motion->position[1] + (motion->endPoint[1] - motion->position[1]) * payload->blend;
    motion->endPoint[2] = motion->position[2] + (motion->endPoint[2] - motion->position[2]) * payload->blend;
    return 1;
}"""


def source_states(live):
    marker = '#include "structs.h"\n'
    if live.count(PLACEHOLDER)==1:
        if DECLARATIONS in live or SELECTED in live or live.count(marker)!=1:
            raise ValueError("Blended dual-point motion predecessor changed")
        qualified=live.replace(marker,marker+"\n"+DECLARATIONS,1).replace(PLACEHOLDER,SELECTED,1)
        return live,qualified,False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        predecessor=live.replace("\n"+DECLARATIONS,"",1).replace(SELECTED,PLACEHOLDER,1)
        return predecessor,live,True
    raise ValueError("Blended dual-point motion source state changed")


def source_with(body,declarations=DECLARATIONS):
    _,qualified,_=source_states((ROOT/SOURCE).read_text())
    return qualified.replace(SELECTED,body,1).replace(DECLARATIONS,declarations,1)


def compare(label="selected",body=SELECTED,declarations=DECLARATIONS):
    output=ROOT/BUILD;output.mkdir(parents=True,exist_ok=True)
    obj,diagnostics=compile_owner(ROOT,output,source_with(body,declarations),label)
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
    return {"label":label,"words":len(words),"differences":differences,
            "raw_sha256":hashlib.sha256(raw).hexdigest(),
            "retail_sha256":hashlib.sha256(retail).hexdigest(),"diagnostics":diagnostics,
            "bindings":{at-start:rows for at,rows in relocations.items() if start<=at<start+size}}


if __name__=="__main__":print(json.dumps(compare(),indent=2))
