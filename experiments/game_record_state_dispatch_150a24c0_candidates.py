"""Record state service call and its captured arguments/live result update."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-record-state-dispatch-150A24C0-match'
RODATA_SYMBOL=None
TARGETS=[{'function': 'func_150A24C0', 'source': 'conker/src/game/generated_CDE80.c', 'owner': 'generated_CDE80', 'object': 'conker/build/src/game/generated_CDE80.c.o', 'assembly': 'conker/asm/CDE80.s', 'entry': 352986304, 'rom': 850288, 'words': 69, 'frame': 64, 'raw_sha256': 'ad30e0c1334440dc880b251fc5f6c9b945ac40bc46e3a48d56483a80a8fbbec0', 'bindings': {156: [('R_MIPS_26', 'func_15183290')]}, 'patches': {48: (2450325527, 2449604631), 68: (2450325527, 2449604631), 96: (2248933378, 2249785346), 108: (2947350544, 2946629648), 112: (2249064454, 2248998918), 116: (2410610756, 2410545220), 120: (821625087, 821559551), 124: (704768, 680192), 128: (52443173, 50346021), 148: (26748961, 53225505), 152: (2947416084, 2947350548), 160: (2947481624, 2947416088), 176: (2451046423, 2450456599), 184: (182784, 180736), 188: (1392574481, 1373700113), 196: (2383282204, 2383151132), 204: (925696240, 924385520), 208: (29456420, 25258020), 212: (28295205, 53309477), 220: (2920808476, 2920153116), 232: (8398885, 8392741), 236: (604307458, 604110850), 244: (6408228, 6387748), 248: (52785189, 31637541), 252: (2920153116, 2920808476)}}]
RECORD_VIEW='typedef struct {\n    s16 origin0;\n    s16 origin1;\n    s16 origin2;\n    u8 pad6[0xF];\n    u8 flags;\n    u8 pad16;\n    u8 field17;\n    s32 field18;\n    s32 field1C;\n    s32 field20;\n    f32 coefficient0;\n    f32 scale;\n    f32 coefficient1;\n    f32 coefficient2;\n} GeneratedCDE80Record;'
SUPPORT='s32 func_15183290(s32,s32,s32,u8,s32,s32,s32,s32,s32,s32,s32);\n'
SELECTED='/* Submit eligible records, then publish the live service result or phase floor. */\nvoid func_150A24C0(GeneratedCDE80Record *record, s32 selector) {\n    u32 state;\n    s32 result;\n    s32 property;\n    s16 parameter18;\n    u8 parameter1A, parameter1C, parameter1D;\n    s32 parameter20;\n    s16 secondOrigin;\n    u8 *bytes = (u8 *)record;\n    if (selector != 255) {\n        state = (u32)record->field1C;\n        if ((state & 255) == 0 || record->field17 == 9) {\n            property = record->field18;\n            parameter18 = *(s16 *)(bytes + 0x18);\n            parameter1A = bytes[0x1A];\n            parameter1C = bytes[0x1C];\n            parameter1D = bytes[0x1D];\n            parameter20 = record->field20;\n            secondOrigin = record->origin1;\n            result = func_15183290(record->origin0,\n                secondOrigin + (parameter1D << 4), record->origin2,\n                property & 255, record->field17,\n                *(s16 *)(bytes + 6), selector, parameter18,\n                parameter1A, parameter1C, parameter20);\n            if (result != -1 && record->field17 != 9) {\n                record->field1C = (((u32)result << 8) | 0xF0) |\n                    ((u32)record->field1C & 0xFFFF0000);\n            }\n        } else {\n            result = (s32)(state & 255);\n            if (result < 2) result = 2;\n            record->field1C = (state & 0xFFFFFF00) | (u32)result;\n        }\n    }\n}'

def source_states(live,index=0):
    if index!=0:raise ValueError('One record-state target')
    stub='s32 func_150A24C0() {\n    return 0;\n}';selected=SUPPORT+'\n'+SELECTED
    if live.count(stub)==1:
        if SUPPORT in live:raise ValueError('Partial record-state installation')
        return live,live.replace(stub,selected,1),False
    if live.count(selected)!=1:raise ValueError('Record-state source changed')
    return live.replace(selected,stub,1),live,True
