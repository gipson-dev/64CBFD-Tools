"""Live linked-key events and the optional actor callback."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15133588','generated_15F680'
SOURCE='conker/src/game/generated_15F680.c'
BUILD='conker/build/game-linked-event-callback-15133588-match'
ENTRY,ROM,WORDS=0x15133588,0x160A38,72
SELECTED="/* Update linked event keys and dispatch the owner's optional callback. */\nvoid func_15133588(u8 *owner, u8 *pair, u8 event) {\n    u32 first;\n    u32 current;\n    s32 selector = event;\n    s32 index;\n    LinkedEventCallback15F680 callback;\n\n    if ((event == 0x1B) && (*(u16 *)(owner + 0x66) == 0x22)) {\n        func_151B9660(owner);\n    }\n    if (selector == 0x2D) {\n        first = *(u32 *)pair;\n        current = *(u32 *)(owner + 0x7C);\n        if (first == current) {\n            *(u32 *)(owner + 0x7C) = *(u32 *)(pair + 4);\n            owner[0x80] = pair[9];\n        } else if (*(u32 *)(pair + 4) == current) {\n            *(u32 *)(owner + 0x7C) = first;\n            owner[0x80] = pair[8];\n        }\n    } else if (selector == 0) {\n        first = *(u32 *)pair;\n        if ((first == *(u32 *)(owner + 0x7C)) || (owner[0x80] == pair[4])) {\n            *(u32 *)(owner + 0x7C) = 0;\n            owner[0x80] = 0;\n        }\n    }\n    index = (*(u32 *)(owner + 0x60) & 0x100) ? owner[0x68] : 0;\n    callback = D_800899F8[index];\n    if (callback != NULL) {\n        callback(owner, pair, event);\n    }\n}"
SUPPORT='typedef void (*LinkedEventCallback15F680)(u8 *, u8 *, u8);\nextern LinkedEventCallback15F680 D_800899F8[];\nvoid func_151B9660(u8 *);\n'
PLACEHOLDER='s32 func_15133588() {\n    return 0;\n}'
def source_states(live):
    if live.count(PLACEHOLDER)==1:
        if SUPPORT in live or SELECTED in live:raise ValueError('Linked event predecessor changed')
        after=live.replace('#include <ultra64.h>','#include <ultra64.h>\n'+SUPPORT,1).replace(PLACEHOLDER,SELECTED,1)
        return live,after,False
    if live.count(SELECTED)!=1 or live.count(SUPPORT)!=1:raise ValueError('Linked event source changed')
    return live.replace('#include <ultra64.h>\n'+SUPPORT,'#include <ultra64.h>',1).replace(SELECTED,PLACEHOLDER,1),live,True
