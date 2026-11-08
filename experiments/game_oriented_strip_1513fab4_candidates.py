"""Unmatched oriented-strip C study. No normalization or installation command."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-oriented-strip-1513FAB4-study'
SOURCE='conker/src/game_169510.c'
FUNCTION='func_1513FAB4'
ENTRY,ROM,WORDS,FRAME=0x1513FAB4,0x16CF64,336,152
RAW_SHA256='99ccd0b08050604207ed8535f5b300d4a4decb6275c1e87f89d3db40db9ef672'
CANDIDATE = r'''
/* Build a quad along the actor displacement, facing the selected viewer. */
Vtx *func_1513FAB4(u8 *actor, u8 alternateOrder, f32 *scale, s16 view) {
    extern f32 sqrtf(f32);
    extern f32 *func_15144B34(s32);
    extern void func_150AD8B0(f32 *, f32 *, f32 *);
    f32 width, length, endX, endY, endZ;
    f32 side[3], eyeDelta[3], heightDelta[3];
    f32 *viewer;
    struct {
        Vtx *first;
        Vtx *cursor;
    } scratch;
    u8 fresh;

    func_151D5D60(actor + 0x100, view, 0x40, &scratch.cursor, &fresh);
    scratch.first = scratch.cursor;
    if (scratch.cursor != NULL) {
        if (fresh) {
            memcpy(*(u8 **)(actor + 0x100 + view * 4), actor + 0xC0, 0x40);
            memcpy(*(u8 **)(actor + 0x100 + view * 4) + 0x40, actor + 0xC0, 0x40);
        }
    } else {
        return NULL;
    }
    viewer = func_15144B34(view);
    width = *(f32 *)(actor + 0x2C) * scale[0];
    length = *(f32 *)(actor + 0x30) * scale[1];
    heightDelta[0] = *(f32 *)(actor + 0x40) - *(f32 *)(actor + 0x34);
    heightDelta[1] = *(f32 *)(actor + 0x44) - *(f32 *)(actor + 0x38);
    heightDelta[2] = *(f32 *)(actor + 0x48) - *(f32 *)(actor + 0x3C);
    heightDelta[0] *= length;
    heightDelta[1] *= length;
    heightDelta[2] *= length;
    endX = *(f32 *)(actor + 0x34) + heightDelta[0];
    endY = *(f32 *)(actor + 0x38) + heightDelta[1];
    endZ = *(f32 *)(actor + 0x3C) + heightDelta[2];
    eyeDelta[0] = (*(f32 *)(actor + 0x34) + heightDelta[0] * 0.5f) - viewer[0];
    eyeDelta[1] = (*(f32 *)(actor + 0x38) + heightDelta[1] * 0.5f) - viewer[1];
    eyeDelta[2] = (*(f32 *)(actor + 0x3C) + heightDelta[2] * 0.5f) - viewer[2];
    func_150AD8B0(heightDelta, eyeDelta, side);
    length = (side[0] * side[0] + side[1] * side[1]) + side[2] * side[2];
    if (length != 0.0f) {
        length = width / sqrtf(length);
        side[0] *= length;
        side[1] *= length;
        side[2] *= length;
    } else {
        side[0] = side[1] = side[2] = 0.0f;
    }
    /* Both orders traverse the same corners, starting at different corners. */
    if (alternateOrder) {
        scratch.cursor->v.ob[0] = (s32)(*(f32 *)(actor + 0x34) + side[0]);
        scratch.cursor->v.ob[1] = (s32)(*(f32 *)(actor + 0x38) + side[1]);
        scratch.cursor->v.ob[2] = (s32)(*(f32 *)(actor + 0x3C) + side[2]);
        scratch.cursor->v.flag = 0;
        scratch.cursor++;
        scratch.cursor->v.ob[0] = (s32)(*(f32 *)(actor + 0x34) - side[0]);
        scratch.cursor->v.ob[1] = (s32)(*(f32 *)(actor + 0x38) - side[1]);
        scratch.cursor->v.ob[2] = (s32)(*(f32 *)(actor + 0x3C) - side[2]);
        scratch.cursor->v.flag = 0;
        scratch.cursor++;
        scratch.cursor->v.flag = 0;
        scratch.cursor->v.ob[0] = (s32)(endX - side[0]);
        scratch.cursor->v.ob[1] = (s32)(endY - side[1]);
        scratch.cursor->v.ob[2] = (s32)(endZ - side[2]);
        scratch.cursor++;
        scratch.cursor->v.flag = 0;
        scratch.cursor->v.ob[0] = (s32)(endX + side[0]);
        scratch.cursor->v.ob[1] = (s32)(endY + side[1]);
        scratch.cursor->v.ob[2] = (s32)(endZ + side[2]);
    } else {
        scratch.cursor->v.ob[0] = (s32)(*(f32 *)(actor + 0x34) - side[0]);
        scratch.cursor->v.ob[1] = (s32)(*(f32 *)(actor + 0x38) - side[1]);
        scratch.cursor->v.ob[2] = (s32)(*(f32 *)(actor + 0x3C) - side[2]);
        scratch.cursor->v.flag = 0;
        scratch.cursor++;
        scratch.cursor->v.ob[0] = (s32)(endX - side[0]);
        scratch.cursor->v.ob[1] = (s32)(endY - side[1]);
        scratch.cursor->v.flag = 0;
        scratch.cursor->v.ob[2] = (s32)(endZ - side[2]);
        scratch.cursor++;
        scratch.cursor->v.ob[0] = (s32)(endX + side[0]);
        scratch.cursor->v.ob[1] = (s32)(endY + side[1]);
        scratch.cursor->v.ob[2] = (s32)(endZ + side[2]);
        scratch.cursor->v.flag = 0;
        scratch.cursor++;
        scratch.cursor->v.ob[0] = (s32)(*(f32 *)(actor + 0x34) + side[0]);
        scratch.cursor->v.ob[1] = (s32)(*(f32 *)(actor + 0x38) + side[1]);
        scratch.cursor->v.ob[2] = (s32)(*(f32 *)(actor + 0x3C) + side[2]);
        scratch.cursor->v.flag = 0;
    }
    return scratch.first;
}
'''.strip()
STUB='/* Non-matching C placeholders for asm/nonmatchings/game_169510/func_1513FAB4.s. */\ns32 func_1513FAB4(s32 arg0, s32 arg1, s32 arg2, s32 arg3) {\n    return 0;\n}'
OLD_PROTO='s32 func_1513FAB4(s32 arg0, s32 arg1, s32 arg2, s32 arg3);'
NEW_PROTO='Vtx *func_1513FAB4(u8 *actor, u8 alternateOrder, f32 *scale, s16 view);'
WRAPPERS=[('void func_1513FA2C(struct210 *arg0, s16 arg1) {\n    f32 tmp[2];\n\n    tmp[0] = 1.0f;\n    tmp[1] = 1.0f;\n    func_1513FAB4(arg0, 0, tmp, arg1);\n}', 'Vtx *func_1513FA2C(struct210 *actor, s16 view) {\n    f32 scale[2];\n\n    scale[0] = 1.0f;\n    scale[1] = 1.0f;\n    return func_1513FAB4((u8 *)actor, 0, scale, view);\n}'), ('void func_1513FA70(struct210 *arg0, s16 arg1) {\n    f32 tmp[2];\n\n    tmp[0] = 1.0f;\n    tmp[1] = 1.0f;\n    func_1513FAB4(arg0, 1, tmp, arg1);\n}', 'Vtx *func_1513FA70(struct210 *actor, s16 view) {\n    f32 scale[2];\n\n    scale[0] = 1.0f;\n    scale[1] = 1.0f;\n    return func_1513FAB4((u8 *)actor, 1, scale, view);\n}')]

def source_states(live):
    installed=CANDIDATE in live
    before,after=(live,live) if not installed else (live.replace(CANDIDATE,STUB,1).replace(NEW_PROTO,OLD_PROTO,1),live)
    if installed:
        for old,new in WRAPPERS:
            if before.count(new)!=1:raise ValueError('Study wrapper changed')
            before=before.replace(new,old,1)
    if before.count(STUB)!=1 or before.count(OLD_PROTO)!=1:raise ValueError('Study source changed')
    after=before.replace(STUB,CANDIDATE,1).replace(OLD_PROTO,NEW_PROTO,1)
    for old,new in WRAPPERS:
        if after.count(old)!=1:raise ValueError('Study predecessor wrapper changed')
        after=after.replace(old,new,1)
    if installed and after!=live:raise ValueError('Study round trip changed')
    return before,after,installed
