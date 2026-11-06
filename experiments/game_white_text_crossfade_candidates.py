"""White text crossfade with a signed countdown and retained owner homes."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_150D0534','generated_FC5F0'
SOURCE='conker/src/game/generated_FC5F0.c'
BUILD='conker/build/game-text-crossfade-150D0534-match'
ENTRY,ROM,WORDS=0x150d0534,0xfd9e4,70
OLD='s32 func_150D0534() {\n    return 0;\n}'
SELECTED='/* Crossfade the current and previous white text buffers. */\ns32 func_150D0534(u8 *owner) {\n    s8 *count;\n    u8 opacity;\n    u8 inverse;\n    /* The second descriptor is captured before its color-provider call. */\n    TextDescriptorFC5F0 *firstText;\n    TextDescriptorFC5F0 *secondText;\n\n    count = (s8 *)((TextDescriptorFC5F0 *)((((u8 **)&owner)[0]) + 0x28))->payload;\n    if (((((u8 **)&owner)[0])[0x30] & 1) != 0) {\n        *count = 20;\n    }\n    if (*count > 0) {\n        opacity = *count * 12;\n        inverse = 255 - opacity;\n        *count = (u8)((u32)*count - (u32)D_800BE9E4);\n    }\n    else {\n        inverse = 255;\n        opacity = 0;\n    }\n    if (inverse != 0) {\n        func_1504332C(255, 255, 255, inverse);\n        firstText = (TextDescriptorFC5F0 *)((((u8 **)&owner)[0]) + 0x28);\n        func_15042D94(20, 20, 128, (s32)firstText->buffers[firstText->index]);\n    }\n    if (opacity) {\n        secondText = (TextDescriptorFC5F0 *)((((u8 **)&owner)[0]) + 0x28);\n        func_1504332C(255, 255, 255, opacity);\n        func_15042D94(20, 20, 128, (s32)secondText->buffers[secondText->index ^ 1]);\n    }\n    return 1;\n}'

def source_states(live):
    if live.count(OLD)==1 and SELECTED not in live:return live,live.replace(OLD,SELECTED,1),False
    if live.count(SELECTED)==1 and OLD not in live:return live.replace(SELECTED,OLD,1),live,True
    raise ValueError('White crossfade owner source changed')
