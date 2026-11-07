"""Reverse position queue drain and the renderer's ten-argument ABI."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1517D690','generated_1A89B0'
SOURCE='conker/src/game/generated_1A89B0.c'
BUILD='conker/build/game-position-queue-drain-1517D690-match'
ENTRY,ROM,WORDS=0x1517D690,0x1AAB40,72
SELECTED='/* Drain queued position draws in reverse order and preserve the allocation index. */\nGfx *func_1517D690(Gfx *displayList, u16 *pixels) {\n    u32 savedIndex;\n    PositionQueueEntry *entry;\n\n    savedIndex = D_800DDD58;\n    D_800DDD1C += 5;\n    if (D_800DDD1C >= 200) D_800DDD1C -= 200;\n    while (D_8008CEB0[0] != 0) {\n        D_8008CEB0[0]--;\n        if (pixels != NULL) {\n            entry = &D_800DDD28[D_8008CEB0[0]];\n            displayList = func_1517D074(displayList, entry->unk0, entry->unk2,\n                                      entry->unk4, entry->unkC,\n                                      (u16)entry->unk8, (u16)entry->unkA,\n                                      16, 32, pixels + entry->unk6 * 640);\n        }\n    }\n    D_800DDD58 = savedIndex;\n    return displayList;\n}'
SUPPORT='extern u32 D_800DDD58;\n'
PLACEHOLDER='s32 func_1517D690() {\n    return 0;\n}'
HELPER_PLACEHOLDER='s32 func_1517D074() {\n    return 0;\n}'
TYPED_HELPER='Gfx *func_1517D074(Gfx *displayList, s32 x, s32 y, s32 z, f32 angle,\n                       s32 halfWidth, s32 halfHeight, s32 textureWidth, s32 textureHeight,\n                       u16 *pixels) {\n    return 0;\n}'

def source_states(live):
    if live.count(PLACEHOLDER)==1:
        if SUPPORT in live or SELECTED in live or live.count(HELPER_PLACEHOLDER)!=1:raise ValueError('Queue predecessor changed')
        return live,live.replace('#include "structs.h"','#include "structs.h"\n'+SUPPORT,1).replace(HELPER_PLACEHOLDER,TYPED_HELPER,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)!=1 or live.count(SUPPORT)!=1 or live.count(TYPED_HELPER)!=1:raise ValueError('Queue source changed')
    return live.replace('#include "structs.h"\n'+SUPPORT,'#include "structs.h"',1).replace(TYPED_HELPER,HELPER_PLACEHOLDER,1).replace(SELECTED,PLACEHOLDER,1),live,True
