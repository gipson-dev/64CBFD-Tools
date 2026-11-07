"""Twelve damped records, signed lifetime, and the retail no-unroll owner profile."""
from pathlib import Path
from tools.experiments.game_active_record_lookup_match import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15187978','generated_1B1600'
SOURCE='conker/src/game/generated_1B1600.c'
BUILD='conker/build/game-damped-record-lifetime-15187978-match'
ENTRY,ROM,WORDS=0x15187978,0x1B4E28,72
FLAGS=('-O2','-g3','-Wo,-loopunroll,0')
SELECTED='/* Advance twelve damped records; release the buffer and actor after expiry. */\nvoid func_15187978(struct102 *input) {\n    TimedDampedEffect1B1600 *effect = (TimedDampedEffect1B1600 *)input;\n    DampedEffectRecord1B1600 *record;\n    s32 offset;\n\n    if (effect->age < 0) {\n        func_10004074(effect->records);\n        func_1516972C(input);\n    } else {\n        effect->age += (u32)D_800BE9E4;\n        if (effect->age > effect->lifetime) {\n            effect->age = -10;\n        } else if (effect->age >= 0) {\n            for (offset = 0; offset < 0x780; offset += 0xA0) {\n                record = (DampedEffectRecord1B1600 *)((u8 *)effect->records + offset);\n                if (record->elapsed < record->duration) {\n                    record->elapsed += (u32)D_800BE9E4;\n                    record = (DampedEffectRecord1B1600 *)((u8 *)effect->records + offset);\n                    if (record->elapsed > record->duration) {\n                        record->elapsed = record->duration;\n                        record = (DampedEffectRecord1B1600 *)((u8 *)effect->records + offset);\n                    }\n                    record->accumulated += record->baseIncrement -\n                        (record->baseIncrement / 3.0f) * record->elapsed / record->duration;\n                }\n            }\n        }\n    }\n}'
SUPPORT='#include "structs.h"\ntypedef struct {\n    u8 retained[0x8C];\n    f32 baseIncrement;\n    f32 accumulated;\n    s16 elapsed;\n    s16 duration;\n    u8 tail[8];\n} DampedEffectRecord1B1600;\ntypedef struct {\n    u8 retained[0xA4];\n    DampedEffectRecord1B1600 *records;\n    s16 age;\n    s16 lifetime;\n} TimedDampedEffect1B1600;\nextern s32 D_800BE9E4;\nvoid func_10004074(void *);\nvoid func_1516972C(struct102 *);\n'
PLACEHOLDER='s32 func_15187978() {\n    return 0;\n}'
MAKE_ANCHOR='$(BUILD_DIR)/$(SRC_DIR)/game/generated_E4070.c.o: RETAIL_RODATA_SYMBOL := jtbl_8009FD00_game\n'
MAKE_ADDITION='# Preserve the twelve-record effect loop without unrolling; all other owner bodies remain fixed.\n$(BUILD_DIR)/$(SRC_DIR)/game/generated_1B1600.c.o: OPT_FLAGS := -O2 -g3 -Wo,-loopunroll,0\n'

def source_states(live):
    if live.count(PLACEHOLDER)==1:
        if SUPPORT in live or SELECTED in live:raise ValueError('Damped effect predecessor changed')
        return live,live.replace('#include <ultra64.h>','#include <ultra64.h>\n'+SUPPORT,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)!=1 or live.count(SUPPORT)!=1:raise ValueError('Damped effect source changed')
    return live.replace('#include <ultra64.h>\n'+SUPPORT,'#include <ultra64.h>',1).replace(SELECTED,PLACEHOLDER,1),live,True

def make_states(live):
    if live.count(MAKE_ANCHOR)!=1:raise ValueError('Damped effect profile anchor changed')
    if MAKE_ADDITION in live:
        if live.count(MAKE_ADDITION)!=1:raise ValueError('Duplicated damped profile')
        return live.replace(MAKE_ADDITION,'',1),live,True
    if 'generated_1B1600.c.o: OPT_FLAGS' in live:raise ValueError('Foreign damped profile')
    return live,live.replace(MAKE_ANCHOR,MAKE_ANCHOR+MAKE_ADDITION,1),False
