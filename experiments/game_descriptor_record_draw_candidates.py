"""Matrix batch draw: captured byte fields and live actor/matrix pointers."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_151897A4','generated_1B5CC0'
SOURCE='conker/src/game/generated_1B5CC0.c'
BUILD='conker/build/game-descriptor-record-draw-151897A4-match'
ENTRY,ROM,WORDS=0x151897A4,0x1B6C54,71
PREFIX='#include <ultra64.h>\ntypedef struct {\n    u8 retained0, stride, count, step;\n    u32 retained4;\n    Mtx *records;\n    u32 retainedC;\n    u8 *descriptor;\n} DescriptorDraw151897A4;\nextern u8 D_800BE9C0;\nGfx *func_151137D4(Gfx *, u8 *, Mtx *, s32, s32, s32);\n\n'
SELECTED='/* Draw matrix records with a temporary opacity ramp, then restore opacity. */\nGfx *func_151897A4(Gfx *cursor, DescriptorDraw151897A4 *draw, s16 viewIndex) {\n    s32 index;\n    s32 opacity;\n    u32 current;\n    u8 count;\n    s32 increment;\n    Gfx *next;\n    u8 step;\n    s32 start;\n    s32 savedOpacity;\n    s32 initialCount;\n\n    initialCount = draw->count;\n    if (initialCount == 0) {\n        return cursor;\n    }\n    start = D_800BE9C0 * draw->stride;\n    current = start;\n    step = draw->step;\n    opacity = step * 96;\n    index = 0;\n    savedOpacity = draw->descriptor[0x8A];\n    increment = step << 5;\n    count = initialCount;\n    if (initialCount > 0) {\n        do {\n            draw->descriptor[0x8A] = opacity >> 8;\n            next = func_151137D4(cursor, draw->descriptor,\n                                (Mtx *)((u8 *)draw->records + (current << 6)), viewIndex, 0, 0);\n            index++;\n            opacity += increment;\n            current++;\n            cursor = next;\n        } while (index != count);\n    }\n    draw->descriptor[0x8A] = savedOpacity;\n    return cursor;\n}'
STEPS=[('#include <ultra64.h>', '#include <ultra64.h>\ntypedef struct {\n    u8 retained0, stride, count, step;\n    u32 retained4;\n    Mtx *records;\n    u32 retainedC;\n    u8 *descriptor;\n} DescriptorDraw151897A4;\nextern u8 D_800BE9C0;\nGfx *func_151137D4(Gfx *, u8 *, Mtx *, s32, s32, s32);\n'), ('s32 func_151897A4() {\n    return 0;\n}', '/* Draw matrix records with a temporary opacity ramp, then restore opacity. */\nGfx *func_151897A4(Gfx *cursor, DescriptorDraw151897A4 *draw, s16 viewIndex) {\n    s32 index;\n    s32 opacity;\n    u32 current;\n    u8 count;\n    s32 increment;\n    Gfx *next;\n    u8 step;\n    s32 start;\n    s32 savedOpacity;\n    s32 initialCount;\n\n    initialCount = draw->count;\n    if (initialCount == 0) {\n        return cursor;\n    }\n    start = D_800BE9C0 * draw->stride;\n    current = start;\n    step = draw->step;\n    opacity = step * 96;\n    index = 0;\n    savedOpacity = draw->descriptor[0x8A];\n    increment = step << 5;\n    count = initialCount;\n    if (initialCount > 0) {\n        do {\n            draw->descriptor[0x8A] = opacity >> 8;\n            next = func_151137D4(cursor, draw->descriptor,\n                                (Mtx *)((u8 *)draw->records + (current << 6)), viewIndex, 0, 0);\n            index++;\n            opacity += increment;\n            current++;\n            cursor = next;\n        } while (index != count);\n    }\n    draw->descriptor[0x8A] = savedOpacity;\n    return cursor;\n}')]
def source_states(live):
    installed=SELECTED in live;before=live
    if installed:
        for old,new in reversed(STEPS):
            if before.count(new)!=1:raise ValueError('Installed matrix batch source differs')
            before=before.replace(new,old,1)
    after=before
    for old,new in STEPS:
        if after.count(old)!=1:raise ValueError('Predecessor matrix batch source differs')
        after=after.replace(old,new,1)
    if installed and after!=live:raise ValueError('Matrix batch source reversal failed')
    return before,after,installed
