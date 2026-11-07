"""Randomized effect forwarding with a live position pointer and RNG captures."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_151C5588','generated_1F2730'
SOURCE='conker/src/game/generated_1F2730.c'
BUILD='conker/build/game-random-effect-forwarder-151C5588-match'
ENTRY,ROM,WORDS=0x151C5588,0x1F2A38,71
DECLARATION='extern f32 D_800AAABC, D_800AAAC0, D_800AAAC4, D_800AAAC8;\nextern f32 D_800AAA90[3], D_800AAA9C[3];\nf32 func_150ADA68(void);\ns32 func_150ADA20(void);\nu8 *func_15102B38(u8 *, u8, f32 *, f32 *, f32 *, s16, u8, f32, f32 *, u8, s32, s16, u8, s32);\n'
PLACEHOLDER='s32 func_151C5588() {\n    return 0;\n}'
SELECTED='/* Submit an effect with randomized scale, type and angular parameters. */\nu8 *func_151C5588(u8 *owner, f32 *position, s16 duration, u8 priority, s32 parameter) {\n    f32 scale[2];\n    s32 random[2];\n\n    scale[1] = (func_150ADA68() * D_800AAABC + 604.0f) * D_800AAAC0;\n    scale[0] = (func_150ADA68() * 59.0f + 141.0f) * D_800AAAC4;\n    random[0] = func_150ADA20();\n    random[1] = func_150ADA20();\n    return func_15102B38(owner, 0, D_800AAA90, D_800AAA9C, scale,\n                         (random[0] & 3) + 6, 255,\n                         func_150ADA68() * 270.0f + D_800AAAC8,\n                         position, 255, 0, duration, priority, parameter);\n}'

def source_states(live):
    marker='#include "structs.h"\n'
    if live.count(PLACEHOLDER)==1:
        if SELECTED in live or DECLARATION in live:raise ValueError('Effect forwarder predecessor changed')
        return live,live.replace(marker,marker+DECLARATION,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)!=1 or live.count(DECLARATION)!=1:raise ValueError('Effect forwarder source changed')
    return live.replace(marker+DECLARATION,marker,1).replace(SELECTED,PLACEHOLDER,1),live,True
