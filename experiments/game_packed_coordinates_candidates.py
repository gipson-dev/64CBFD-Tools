"""Two packed 12-bit command coordinates with strict single-wrap arithmetic."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15062D10','game_83300'
SOURCE='conker/src/game_83300.c'
ENTRY,ROM,WORDS=0x15062D10,0x901C0,69
BUILD='conker/build/game-packed-coordinates-15062D10-match'
PLACEHOLDER='/* Non-matching C placeholders for asm/nonmatchings/game_83300/func_15062D10.s. */\ns32 func_15062D10() {\n    return 0;\n}'
DECLARATIONS='extern s32 **D_800C4488[];\n'
PROTOTYPE_BEFORE='s32 func_15062D10();'
PROTOTYPE_AFTER='void func_15062D10(s32, s32, s32, s32, s32, s32);'
SELECTED='''/* Update packed coordinates with the original strict single-wrap tests. */
void func_15062D10(s32 slot, s32 entry, s32 dx, s32 dy, s32 bank, s32 absolute) {
    s32 *command;
    s32 first;
    s32 *entryHome = &entry;
    s32 width;
    s32 height;
    s32 x;
    s32 y;
    if ((&D_800D19A0)[slot] == 0) {
        return;
    }
    command = D_800C4488[slot][bank] + *entryHome * 2;
    width = ((command[1] >> 12) & 0xFFF) + 2;
    height = (command[1] & 0xFFF) + 2;
    first = command[0];
    if (absolute != 0) {
        x = dx & 0xFFF;
    } else {
        x = (s32)((u32)((first >> 12) & 0xFFF) + (u32)dx);
        if (width < x) {
            x -= width;
        } else if (x < 0) {
            x += width;
        }
    }
    if (absolute != 0) {
        y = dy & 0xFFF;
    } else {
        y = (s32)((u32)(first & 0xFFF) + (u32)dy);
        if (height < y) {
            y -= height;
        } else if (y < 0) {
            y += height;
        }
    }
    first = (first & 0xFF000000) | (y & 0xFFF);
    command[0] = first | ((x & 0xFFF) << 12);
}'''

def source_states(live):
    old,new=PLACEHOLDER,DECLARATIONS+SELECTED
    if live.count(old)==1 and new not in live and live.count(PROTOTYPE_BEFORE)==1:
        return live,live.replace(old,new,1).replace(PROTOTYPE_BEFORE,PROTOTYPE_AFTER,1),False
    if live.count(new)==1 and old not in live and live.count(PROTOTYPE_AFTER)==1:
        return live.replace(new,old,1).replace(PROTOTYPE_AFTER,PROTOTYPE_BEFORE,1),live,True
    raise ValueError('Packed coordinate source/interface state changed')
