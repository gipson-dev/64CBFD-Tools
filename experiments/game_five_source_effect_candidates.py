"""Direct C five-source effect constructor with a partially defined descriptor."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_150DB518','generated_108320'
SOURCE,ASM='conker/src/game/generated_108320.c','conker/asm/108320.s'
BUILD='conker/build/game-five-source-effect-constructor-150DB518-match'
ENTRY,ROM,WORDS=0x150DB518,0x1089C8,70
OLD='s32 func_150DB518() {\n    return 0;\n}'
HEADERS='typedef struct EffectRequest150DB518 {\n    u8 kind, reserved01;\n    u16 mode;\n    s16 duration;\n    u8 reserved06[2];\n    s32 value;\n    u32 flags;\n    u8 red, green, blue, alpha;\n    u8 reserved14[0x2C];\n    u32 allocationFlags;\n    u8 first, second, reserved46[0x12];\n} EffectRequest150DB518;\ntypedef struct EffectSources150DB518 {\n    u8 reserved[0x110];\n    void *first, *second, *third, *fifth, *fourth;\n} EffectSources150DB518;\nvoid *func_1513D524(void *, u8, u8, u8, u8, u8, s32, u8, s32);\n'
SELECTED='/* Create a parameter-driven effect and retain its five live source pointers. */\nvoid func_150DB518(void *first, void *second, void *third, void *fourth,\n                   void *fifth, s16 duration, u8 channel, s32 context) {\n    EffectRequest150DB518 request;\n    EffectSources150DB518 *effect;\n\n    if (first && second && third && fourth && fifth && duration) {\n        /* Reserved descriptor bytes retain their original stack contents. */\n        request.kind = 0x17;\n        request.flags = 0x243A;\n        request.allocationFlags = 0x401;\n        request.first = 255;\n        request.value = 0;\n        request.duration = duration;\n        request.second = 255;\n        request.red = request.green = request.blue = 200;\n        request.alpha = 200;\n        request.mode = 0x401;\n        effect = func_1513D524(&request, 0, 10, 0, 8, 0, 20, channel, context);\n        if (effect) {\n            effect->first = first;\n            effect->second = second;\n            effect->third = third;\n            effect->fifth = fifth;\n            effect->fourth = fourth;\n        }\n    }\n}'
NEW=HEADERS+SELECTED
def source_states(live):
    if live.count(OLD)==1 and NEW not in live:return live,live.replace(OLD,NEW,1),False
    if live.count(NEW)==1 and OLD not in live:return live.replace(NEW,OLD,1),live,True
    raise ValueError('Five-source effect source state changed')
