"""Typed actor spatial-query ABI and the ordered 25-actor scan."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15081574','generated_AE1D0'
SOURCE,ASM='conker/src/game/generated_AE1D0.c','conker/asm/AE1D0.s'
BUILD='conker/build/game-actor-type-query-15081574-match'
ENTRY,ROM,WORDS=0x15081574,0xaea24,68
SLOT_WORDS=71
OLD='s32 func_15081574() {\n    return 0;\n}'
HEADERS='#include "structs.h"\nextern u8 D_800CC2D0[], D_800D121C[], D_8009BD30[];\ns32 func_1508108C(u8 *);\n\n'
SELECTED='/* Find the first loaded actor of this type that passes the spatial query. */\ns32 func_15081574(struct127 *origin, f32 forwardOffset, f32 radius,\n    s32 *foundActorAddress, s32 queryMode, s32 actorType) {\n    u8 *actor;\n    s32 part;\n    s32 value;\n\n    *foundActorAddress = 0;\n    actor = D_800CC2D0;\n    do {\n        if (*(s32 *)actor != 0 && *(void **)(actor + 0x1D4) != NULL &&\n            actor[4] == actorType) {\n            part = func_1508108C(actor);\n            if (part != -1) {\n                value = func_15080D20((u8 *)origin, actor, D_8009BD30[part * 4 + 2],\n                    forwardOffset, radius, queryMode);\n                if (value != 0) {\n                    *foundActorAddress = (s32)actor;\n                    return value;\n                }\n            }\n        }\n        actor += 0x32C;\n    } while (actor != D_800D121C);\n    return 0;\n}'
HELPER_OLD='s32 func_15080D20() {\n    return 0;\n}'
HELPER_NEW='s32 func_15080D20(u8 *origin, u8 *target, s32 part, f32 forwardOffset, f32 radius, s32 queryMode) {\n    return 0;\n}'

def source_states(live):
    marker='#include <ultra64.h>\n'
    if live.count(OLD)==1 and live.count(HELPER_OLD)==1 and HEADERS not in live:
        new=live.replace(marker,marker+HEADERS,1).replace(HELPER_OLD,HELPER_NEW,1).replace(OLD,SELECTED,1)
        return live,new,False
    if live.count(SELECTED)==1 and live.count(HELPER_NEW)==1 and live.count(HEADERS)==1:
        return live.replace(HEADERS,'',1).replace(HELPER_NEW,HELPER_OLD,1).replace(SELECTED,OLD,1),live,True
    raise ValueError('Actor-query owner source changed')
