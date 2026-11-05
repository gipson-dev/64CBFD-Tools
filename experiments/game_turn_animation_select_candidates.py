"""Screen the threshold/direction turn-animation selection and actor reset."""

import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.pad_generated_object import parse_object


ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15056A00','game_83300'
SOURCE='conker/src/game_83300.c'
BUILD='conker/build/game-turn-animation-select-candidates'
ENTRY,ROM,WORDS=0x15056A00,0x83EB0,66
PLACEHOLDER='s32 func_15056A00() {\n    return 0;\n}'
OLD_DECL='s32 func_15056A00();'
DECLARATIONS='void func_15056A00(void *, u8, u8);'
OLD_COMMENT='/* Non-matching C placeholders for asm/nonmatchings/game_83300/func_15056A00.s. */\n'
SELECTED='''/* Select a turn animation from magnitude thresholds and wrapped heading sign. */
void func_15056A00(void *inputActor, u8 magnitude, u8 row) {
    struct127 *actor = inputActor;
    struct TurnAnimationRow15056A00 { u8 bytes[10]; } *rows = (void *)D_80099A3C;
    u8 *table = (u8 *)D_80099A3C;
    u8 index = 0;
    u16 heading;
    u8 *entry;

    if (rows[row].bytes[7] < magnitude) {
        index = 5;
    } else if (rows[row].bytes[2] < magnitude) {
        index = 2;
    }
    heading = actor->unk76;
    if ((actor->unk78 - heading) & 0x8000) {
        index += 3;
    } else {
        index += 4;
    }
    entry = table + row * 10 + index;
    if (*entry != 0xFF) {
        u8 animation;
        s32 flags = actor->unkF4;

        actor->unk218 = (struct216 *)((u32)actor->unk218 - 5u);
        actor->unk21C = 20000;
        actor->unk223 = 13;
        actor->unk44 = 0.0f;
        animation = *entry;
        /* Retain both observed flag stores before aligning the actor headings. */
        *(volatile s32 *)&actor->unkF4 = flags & ~0xE;
        *(volatile s32 *)&actor->unkF4 = (flags & ~0xE) | 4;
        actor->unk78 = heading;
        actor->unk7A = heading;
        actor->unk138 = 0;
        actor->unk244 = animation;
    }
}'''


def source_states(live):
    if live.count(PLACEHOLDER)==1 and live.count(OLD_DECL)==1 and live.count(OLD_COMMENT)==1 and SELECTED not in live:
        return live,live.replace(OLD_DECL,DECLARATIONS,1).replace(OLD_COMMENT,'',1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1 and OLD_DECL not in live and OLD_COMMENT not in live:
        return live.replace(DECLARATIONS,OLD_DECL,1).replace(SELECTED,OLD_COMMENT+PLACEHOLDER,1),live,True
    raise ValueError('Turn-animation source state changed')


def source_with(body=SELECTED,declaration=DECLARATIONS):
    return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1).replace(DECLARATIONS,declaration,1)


def compare(label='selected',body=SELECTED,declaration=DECLARATIONS):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    obj,diagnostics=compile_owner(ROOT,out,source_with(body,declaration),label)
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
