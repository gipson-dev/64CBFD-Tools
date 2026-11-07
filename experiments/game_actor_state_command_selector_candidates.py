"""Actor-state command selection and its local record-base pointer ABI."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15080500','generated_AD9B0'
SOURCE='conker/src/game/generated_AD9B0.c'
BUILD='conker/build/game-actor-state-command-selector-15080500-match'
ENTRY,ROM,WORDS=0x15080500,0xAD9B0,72
SELECTED='/* Select an actor-state command while honoring protected status bytes. */\nvoid func_15080500(struct127 *actor, struct178 *record, s32 secondary, s32 command) {\n    if ((actor != NULL) && (actor->interaction_state != 0) && (actor->unk127 != 0xFF)) {\n        if ((command == 0x2B) || (command == 0x2C)) {\n            D_800D1940 = command;\n            D_800D199C = (u8 *)record;\n            command = 0x2A;\n        } else if (func_15080738(command)) {\n            D_800D1940 = command;\n            if (!(D_800D2E60[command >> 3] & (1 << (command & 7)))) {\n                command = 0x1A;\n            }\n        }\n        if (secondary == 0) {\n            if (!(((u8 *)actor->unk31C)[0x74] & 0x80)) {\n                ((u8 *)actor->unk31C)[0x74] = command;\n            }\n        } else {\n            if (!(((u8 *)actor->unk31C)[0x75] & 0x80)) {\n                ((u8 *)actor->unk31C)[0x75] = command;\n                ((u8 *)actor->unk31C)[0x7A] = record - D_800D3098;\n            }\n        }\n    }\n}'
DECLARATION='s32 func_15080738(s32);\n'
INCLUDE='/* This owner reads the retail record-base pointer, not the legacy array type. */\n#define D_800D3098 D_800D3098_legacy_array\n#include "variables.h"\n#undef D_800D3098\nextern struct178 *D_800D3098;'
PLACEHOLDER='s32 func_15080500() {\n    return 0;\n}'

def source_states(live):
    old='#include "variables.h"';marker='extern u8 D_800BE580[];'
    if live.count(PLACEHOLDER)==1:
        if SELECTED in live or INCLUDE in live or DECLARATION in live:raise ValueError('State command predecessor changed')
        return live,live.replace(PLACEHOLDER,SELECTED,1).replace(old,INCLUDE,1).replace(marker,DECLARATION+marker,1),False
    if live.count(SELECTED)!=1 or live.count(INCLUDE)!=1 or live.count(DECLARATION)!=1:raise ValueError('State command source changed')
    return live.replace(SELECTED,PLACEHOLDER,1).replace(INCLUDE,old,1).replace(DECLARATION,'',1),live,True
