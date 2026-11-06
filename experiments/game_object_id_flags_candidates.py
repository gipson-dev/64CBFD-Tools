"""State-one object ID classification with priority and first-match flags."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1503B840','generated_68C70'
SOURCE='conker/src/game/generated_68C70.c'
CALLER='conker/src/game_83300.c'
ENTRY,ROM,WORDS=0x1503B840,0x68CF0,71
BUILD='conker/build/game-object-id-flags-1503B840-match'
PLACEHOLDER='s32 func_1503B840() {\n    return 0;\n}'
DECLARATIONS='extern u16 D_8009877C, D_8009877E;\nextern u16 D_80098780[88], D_80098830[3], D_80098836[];\n'
SELECTED='''/* Set the ID-classification flag for objects in interaction state one. */
void func_1503B840(struct127 *object) {
    u16 *cursor;
    u16 *end;
    u32 identity;
    s32 index;

    if (object->interaction_state != 1) {
        return;
    }
    end = D_80098836;
    identity = object->unk84.uh;
    cursor = D_80098830;
    do {
        if (identity == *cursor++) {
            object->unk2FB |= 2;
            return;
        }
    } while ((u32)cursor < (u32)end);
    if (identity == D_8009877C) {
        object->unk2FB |= 1;
        return;
    }
    if (identity == D_8009877E) {
        object->unk2FB |= 1;
        return;
    }
    for (index = 0; index < 88; index++) {
        if (identity == D_80098780[index]) {
            object->unk2FB |= 1;
            return;
        }
    }
}'''
HEADER_OLD='/* Non-matching placeholders for the text-only asm slice asm/68C70.s. */'
HEADER_NEW='/* Recovered routines and remaining placeholders for asm/68C70.s. */'
def source_states(live):
    if live.count(PLACEHOLDER)==1 and DECLARATIONS not in live and live.count(HEADER_OLD)==1:return live,live.replace(PLACEHOLDER,DECLARATIONS+SELECTED,1).replace(HEADER_OLD,HEADER_NEW,1),False
    if live.count(DECLARATIONS+SELECTED)==1 and PLACEHOLDER not in live and live.count(HEADER_NEW)==1:return live.replace(DECLARATIONS+SELECTED,PLACEHOLDER,1).replace(HEADER_NEW,HEADER_OLD,1),live,True
    raise ValueError('Object ID flags source state changed')
CALLER_DECL='void func_1503B840(struct127 *);\n'
def caller_states(live):
    anchor='s32 func_15194FF4(struct127 *, struct127 *, s32);\n'
    if live.count(CALLER_DECL)==1:return live.replace(CALLER_DECL,'',1),live,True
    if CALLER_DECL not in live and live.count(anchor)==1:return live,live.replace(anchor,anchor+CALLER_DECL,1),False
    raise ValueError('Object ID flags caller declaration state changed')
