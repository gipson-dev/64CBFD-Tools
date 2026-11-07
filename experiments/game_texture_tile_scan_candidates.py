"""Display-list texture selection and paired tile-size command counting."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15195868','generated_1C2C60'
SOURCE='conker/src/game/generated_1C2C60.c'
BUILD='conker/build/game-asset-command-block-15195868-match'
ENTRY,ROM,WORDS=0x15195868,0x1C2D18,71
DECLARATION='extern s32 D_800B0E58[7762];\n'
PLACEHOLDER='s32 func_15195868() {\n    return 0;\n}'
SELECTED='''/* Find a texture occurrence and count its paired tile-size commands. */
s32 func_15195868(u8 *displayList, s32 assetId, s32 occurrence, s32 *tileCount) {
    s32 index;
    s32 opcode;
    s32 next;
    s32 second;

    *tileCount = 0;
    index = -1;
    for (;;) {
        index++;
        while ((s8)G_SETTIMG != (opcode = *(s8 *)(displayList + (index << 3))) &&
               (s8)G_ENDDL != opcode) {
            index++;
        }
        if ((s8)G_ENDDL == opcode) {
            return -1;
        }
        if (D_800B0E58[assetId] == ((s32 *)displayList)[index * 2 + 1] || assetId == 0) {
            if (occurrence-- <= 0) {
                break;
            }
        }
    }
    assetId = (s8)opcode;
    while (assetId != (s8)G_SETTILESIZE) {
        index++;
        assetId = *(s8 *)(displayList + (index << 3));
    }
    next = index;
    do {
        *tileCount += 1;
        next++;
        assetId = *(s8 *)(displayList + (next << 3));
        next++;
        second = *(s8 *)(displayList + (next << 3));
    } while (assetId == (s8)G_SETTILE && second == (s8)G_SETTILESIZE);
    return index;
}'''

def source_states(live):
    marker='#include <ultra64.h>\n'
    if live.count(PLACEHOLDER)==1:
        if SELECTED in live or DECLARATION in live:raise ValueError('Texture scanner predecessor changed')
        return live,live.replace(marker,marker+DECLARATION,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)!=1 or live.count(DECLARATION)!=1:raise ValueError('Texture scanner source changed')
    before=live.replace(marker+DECLARATION,marker,1).replace(SELECTED,PLACEHOLDER,1)
    return before,live,True
