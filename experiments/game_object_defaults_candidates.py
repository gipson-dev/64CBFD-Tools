"""Full object clear, ordered defaults, RNG byte and component initialization."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1505F188','game_83300'
SOURCE='conker/src/game_83300.c'
ENTRY,ROM,WORDS=0x1505F188,0x8C638,68
BUILD='conker/build/game-object-defaults-1505F188-match'
PLACEHOLDER='/* Non-matching C placeholders for asm/nonmatchings/game_83300/func_1505F188.s. */\ns32 func_1505F188(void *arg0) {\n    return 0;\n}'
DECLARATIONS='extern f32 D_8009962C, D_80099630;\n'
PROTOTYPE_BEFORE='s32 func_1505F188(void *arg0);'
PROTOTYPE_AFTER='void func_1505F188(struct127 *object);'
CALL_BEFORE='func_1505F188(&D_800D121C);'
CALL_AFTER='func_1505F188((struct127 *)&D_800D121C);'
SELECTED='''/* Clear the object and initialize defaults around the original helpers. */
void func_1505F188(struct127 *object) {
    u32 *cursor = (u32 *)object;
    u32 *end = (u32 *)((u8 *)object + 0x32C);
    f32 unit;
    f32 base;
    f32 gravity;
    while ((u32)cursor < (u32)end) {
        *cursor++ = 0;
    }
    unit = 1.0f;
    base = D_8009962C;
    ((u8 *)object)[0x2FD] = 2;
    *(s16 *)((u8 *)object + 0x38) = -10000;
    object->xz_scale = unit;
    object->y_scale = unit;
    object->unk118 = base;
    object->unk180 = base;
    gravity = D_80099630;
    ((u8 *)object)[0x1DC] = 255;
    object->unk127 = 255;
    object->unk84.uh = 65535;
    object->unk13F = 255;
    *(u8 **)((u8 *)object + 0x2C4) = (u8 *)object + 4;
    ((u8 *)object)[0x2C8] = 1;
    object->unk2C9 = 1;
    object->id = 255;
    object->unk2CB = 50;
    object->unk48 = unit;
    object->gravity = gravity;
    object->unk6E = (u32)func_150ADA20() % 50U + 50;
    func_150615DC(object);
    ((u8 *)object)[0x1DD] = 255;
    ((u8 *)object)[0x1DE] = 255;
    ((u8 *)object)[0x1DF] = 255;
    *(s16 *)((u8 *)object + 0x18C) = 0;
    *(s16 *)((u8 *)object + 0x18E) = 0;
    *(s16 *)((u8 *)object + 0x190) = 0;
    *(s16 *)((u8 *)object + 0x192) = 0;
    *(s16 *)((u8 *)object + 0x194) = 0;
    *(s16 *)((u8 *)object + 0x196) = 10;
    *(s16 *)((u8 *)object + 0x198) = 10;
    *(s16 *)((u8 *)object + 0x19A) = 0;
    *(s16 *)((u8 *)object + 0x19C) = 0;
}'''

def source_states(live):
    old,new=PLACEHOLDER,DECLARATIONS+SELECTED
    if live.count(old)==1 and new not in live and live.count(PROTOTYPE_BEFORE)==1 and live.count(CALL_BEFORE)==1:
        return live,live.replace(old,new,1).replace(PROTOTYPE_BEFORE,PROTOTYPE_AFTER,1).replace(CALL_BEFORE,CALL_AFTER,1),False
    if live.count(new)==1 and old not in live and live.count(PROTOTYPE_AFTER)==1 and live.count(CALL_AFTER)==1:
        return live.replace(new,old,1).replace(PROTOTYPE_AFTER,PROTOTYPE_BEFORE,1).replace(CALL_AFTER,CALL_BEFORE,1),live,True
    raise ValueError('Object defaults source/prototype/caller state changed')
