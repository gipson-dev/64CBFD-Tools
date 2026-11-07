"""Cached direction and basis preparation with live flag reloads."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1514F6E8','generated_17CAF0'
SOURCE='conker/src/game/generated_17CAF0.c'
BUILD='conker/build/game-cached-vector-basis-1514F6E8-match'
ENTRY,ROM,WORDS=0x1514F6E8,0x17CB98,72
SELECTED='/* Prepare and cache the scaled direction and its two basis vectors. */\ns32 func_1514F6E8(void *input) {\n    CachedVectorBasis17CAF0 *state = input;\n\n    if (!(state->flags & 1)) {\n        if (!func_15145128(&state->direction, &state->direction, NULL, NULL)) return 0;\n        state->direction.unk0 *= 1000.0f;\n        state->direction.unk4 *= 1000.0f;\n        state->direction.unk8 *= 1000.0f;\n        state->flags |= 1;\n    }\n    if (!(state->flags & 2)) {\n        if (!func_15146078(&state->direction, &state->tangent, &state->bitangent)) return 0;\n        state->flags |= 6;\n    }\n    if (!(state->flags & 4)) {\n        if (!func_15145128(&state->tangent, &state->tangent, NULL, NULL)) return 0;\n        if (!func_15145128(&state->bitangent, &state->bitangent, NULL, NULL)) return 0;\n        state->flags |= 4;\n    }\n    return 1;\n}'
SUPPORT='#include "structs.h"\ntypedef struct {\n    u8 flags;\n    u8 reserved[3];\n    struct17 direction;\n    struct17 tangent;\n    struct17 bitangent;\n    f32 radius;\n} CachedVectorBasis17CAF0;\ns32 func_15145128(struct17 *, struct17 *, f32 *, f32 *);\ns32 func_15146078(struct17 *, struct17 *, struct17 *);\n'
PLACEHOLDER='s32 func_1514F6E8() {\n    return 0;\n}'
def source_states(live):
    if live.count(PLACEHOLDER)==1:
        if SUPPORT in live or SELECTED in live:raise ValueError('Basis predecessor changed')
        return live,live.replace('#include <ultra64.h>','#include <ultra64.h>\n'+SUPPORT,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)!=1 or live.count(SUPPORT)!=1:raise ValueError('Basis source changed')
    return live.replace('#include <ultra64.h>\n'+SUPPORT,'#include <ultra64.h>',1).replace(SELECTED,PLACEHOLDER,1),live,True
