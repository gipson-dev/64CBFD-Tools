"""Byte-phase coordinates and wrapped sine scale with the original saved payload."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1515A11C','generated_185560'
SOURCE='conker/src/game/generated_185560.c'
BUILD='conker/build/game-phase-motion-callback-1515A11C-match'
ENTRY,ROM,WORDS=0x1515A11C,0x1875CC,71
OLD='s32 func_1515A11C() {\n    return 0;\n}'
TYPES='typedef struct {\n    f32 center;\n    u8 firstPhase, secondPhase;\n    s8 firstVelocity, secondVelocity;\n    f32 firstRadius, secondRadius;\n    f32 scale[3];\n    f32 phase, rate;\n} MotionPayload1515A11C;\nf32 func_151423D8(u8);\nf32 func_15144B68(f32);\nf32 sinf(f32);\nextern f32 D_800BE9A4;\n'
SELECTED='/* Advance two byte oscillators and the shared floating scale phase. */\ns32 func_1515A11C(u8 *owner, u8 *workspace) {\n    MotionPayload1515A11C *motion;\n    f32 first;\n    f32 second;\n    f32 scale;\n\n    owner[0xAC] += (u32)(s32)*(s8 *)(owner + 0xAE) * (u32)D_800BE9E4;\n    owner[0xAD] += (u32)(s32)*(s8 *)(owner + 0xAF) * (u32)D_800BE9E4;\n    motion = (MotionPayload1515A11C *)(owner + 0xA8);\n    first = func_151423D8((u8)(motion->firstPhase - 64));\n    second = func_151423D8((u8)(motion->secondPhase - 64));\n    *(f32 *)(owner + 0x38) = motion->center + motion->firstRadius * first;\n    *(f32 *)(owner + 0x3C) = motion->center + motion->secondRadius * second;\n    motion->phase += motion->rate * D_800BE9A4;\n    motion->phase = func_15144B68(motion->phase);\n    scale = sinf(motion->phase);\n    *(f32 *)(owner + 0x4C) = motion->scale[0] * scale;\n    *(f32 *)(owner + 0x50) = motion->scale[1] * scale;\n    *(f32 *)(owner + 0x54) = motion->scale[2] * scale;\n    return 1;\n}'

def source_states(live):
    marker='#include <string.h>\n'+TYPES
    if live.count(OLD)==1 and SELECTED not in live and marker not in live:
        return live,live.replace('#include <string.h>','#include <string.h>\n'+TYPES,1).replace(OLD,SELECTED,1),False
    if live.count(SELECTED)==1 and OLD not in live and live.count(marker)==1:
        return live.replace(SELECTED,OLD,1).replace(marker,'#include <string.h>',1),live,True
    raise ValueError('Phase-motion owner source changed')
