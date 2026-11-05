"""Screen lazy resource-cache acquisition and saturating retain count as C."""

import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ROOT = Path(__file__).resolve().parents[2]
FUNCTION, OWNER = "func_1518C900", "generated_1B9DB0"
SOURCE = "conker/src/game/generated_1B9DB0.c"
BUILD = "conker/build/game-resource-cache-acquire-candidates"
ENTRY, ROM, WORDS = 0x1518C900, 0x1B9DB0, 65
PLACEHOLDER = "s32 func_1518C900() {\n    return 0;\n}"
DECLARATIONS = """void *func_1502B6BC(s32 *, s32, s32 *, s32, ...);
s32 func_1510CE60(void *, s32, s32, s32, s32 *);
void func_15168E54(void *, void *);

"""
SELECTED = """/* Load a cached resource on first use and retain its saturating byte count. */
s32 func_1518C900(s32 kind) {
    s32 *resource;
    u8 *count = &D_800DF7D0[kind];

    if (*count == 0) {
        resource = func_1502B6BC(NULL, 0, NULL, 2, 9, kind);
        if (resource == NULL) {
            return 0;
        }
        func_1510CE60((void *)resource[0], 0, 1, 0x3E,
                      (s32 *)&D_800DF9B8[kind]);
        func_15168E54((void *)resource[0], resource);
        D_800E0148[kind] = resource;
    } else {
        resource = D_800E0148[kind];
    }
    if (*count != 0xFF) {
        (*count)++;
    }
    return resource[0];
}"""


def source_states(live):
    marker = 'void func_100043B4(s32 *, u32);\n'
    if live.count(PLACEHOLDER)==1:
        if DECLARATIONS in live or SELECTED in live or live.count(marker)!=1:
            raise ValueError("Resource cache acquire predecessor changed")
        qualified=live.replace(marker,marker+"\n"+DECLARATIONS,1).replace(PLACEHOLDER,SELECTED,1)
        return live,qualified,False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        predecessor=live.replace("\n"+DECLARATIONS,"",1).replace(SELECTED,PLACEHOLDER,1)
        return predecessor,live,True
    raise ValueError("Resource cache acquire source state changed")


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
