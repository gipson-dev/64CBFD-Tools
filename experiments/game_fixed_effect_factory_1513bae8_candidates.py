"""Fixed descriptor/payload constructor and preserved handle return."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-fixed-effect-factory-1513BAE8-match'
RODATA_SYMBOL=None
TARGETS=[{'function': 'func_1513BAE8', 'source': 'conker/src/game_168A90.c', 'owner': 'game_168A90', 'object': 'conker/build/src/game_168A90.c.o', 'assembly': 'conker/asm/nonmatchings/game_168A90/func_1513BAE8.s', 'entry': 353614568, 'rom': 1478552, 'words': 69, 'frame': 120, 'raw_sha256': 'a138487343daddcd2774f576d10fe102b8d64856d52e107747272d567226c6cc', 'bindings': {176: [('R_MIPS_26', 'func_1513B5E0')], 212: [('R_MIPS_26', 'func_1516972C')], 244: [('R_MIPS_26', 'memcpy')]}, 'patches': {240: (19341345, 15278113)}}]
SUPPORT='typedef struct {\n    u8 field0, field1, field2, pad3;\n    s16 field4;\n    u8 pad6[2];\n    s32 field8, fieldC, field10, field14, field18, field1C, field20;\n    u8 field24, field25, pad26[10];\n    s32 field30, field34;\n    u8 field38;\n} EffectDescriptor1513BAE8;\ntypedef struct { f32 value0, value4, value8, valueC, value10; } EffectPayload1513BAE8;\n'
SELECTED='/* Build the fixed effect and preserve its handle even on validation release. */\ns32 func_1513BAE8(void) {\n    u32 handle;\n    EffectDescriptor1513BAE8 descriptor;\n    EffectPayload1513BAE8 payload;\n    payload.value0 = 0.0f;\n    payload.value4 = 0.0f;\n    payload.valueC = 0.0f;\n    payload.value10 = 0.0f;\n    payload.value8 = 0.0f;\n    descriptor.field0 = 0;\n    descriptor.field1 = 2;\n    descriptor.field2 = 5;\n    descriptor.field4 = 300;\n    descriptor.field30 = 9;\n    descriptor.field34 = 430;\n    descriptor.field8 = 1;\n    descriptor.fieldC = 0x220205;\n    descriptor.field10 = 0x40600;\n    descriptor.field24 = 0;\n    descriptor.field25 = 0;\n    descriptor.field14 = 1;\n    descriptor.field18 = 54;\n    descriptor.field1C = 128;\n    descriptor.field20 = 32;\n    descriptor.field38 = 3;\n    handle = func_1513B5E0(&descriptor, 1, 20, 255, 1);\n    if (handle != 0) {\n        if (*(s32 *)(handle + 0x50) != 0x1180) {\n            func_1516972C((struct102 *)handle);\n        } else {\n            memcpy((void *)(handle + *(s32 *)(handle + 0x50) + 0xF8), &payload, 20);\n        }\n    }\n    return handle;\n}'
def source_states(live,index=0):
    if index!=0:raise ValueError('One fixed-effect target')
    role='/* Non-matching C placeholders for asm/nonmatchings/game_168A90/func_1513BAE8.s. */\n'
    stub='s32 func_1513BAE8() {\n    return 0;\n}';selected=SUPPORT+'\n'+SELECTED
    if live.count(role+stub)==1 and live.count('s32 func_1513BAE8();')==1:
        return live,live.replace(role+stub,selected,1).replace('s32 func_1513BAE8();','s32 func_1513BAE8(void);',1),False
    if live.count(selected)!=1 or live.count('s32 func_1513BAE8(void);')!=1:raise ValueError('Fixed effect source changed')
    return live.replace(selected,role+stub,1).replace('s32 func_1513BAE8(void);','s32 func_1513BAE8();',1),live,True
