"""Cleanup commands and alias-sensitive owner-reference exchange."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-reference-command-151347CC-match'
RODATA_SYMBOL=None
TARGETS=[dict(function='func_151347CC',source='conker/src/game_161520.c',owner='game_161520',object='conker/build/src/game_161520.c.o',assembly='conker/retail_layout.us.txt',entry=0x151347CC,rom=0x161C7C,words=73,frame=24,bindings={0x48:[('R_MIPS_26','func_1516972C')],0x94:[('R_MIPS_26','func_1516972C')],0xBC:[('R_MIPS_26','func_1516972C')]},patches={0x100:(0x54790005,0x57230005)})]
SELECTED='/* Handle owner cleanup requests and exchange the live owner reference. */\nvoid func_151347CC(struct102 *record, s32 *request, u8 command) {\n    s32 first;\n    s32 current;\n    if (command == 0 || command == 3) {\n        if (*(s32 *)((u8 *)record + 0x1C) == request[0] ||\n            *((u8 *)record + 0x18) == *((u8 *)request + 4)) {\n            func_1516972C(record);\n        }\n    } else if (command == 0x11) {\n        if (*((u8 *)record + 0x3D) == 5) {\n            if (*(s32 *)((u8 *)record + 0x1C) == request[0] ||\n                *((u8 *)record + 0x18) == *((u8 *)request + 4)) {\n                func_1516972C(record);\n            }\n        }\n    } else if (command == 0x16) {\n        if ((s32)request == *(s32 *)((u8 *)record + 0x1C)) {\n            func_1516972C(record);\n        }\n    } else if (command == 0x2D) {\n        first = request[0];\n        current = *(s32 *)((u8 *)record + 0x1C);\n        if (first == current) {\n            *(s32 *)((u8 *)record + 0x1C) = request[1];\n            *((u8 *)record + 0x18) = *((u8 *)request + 9);\n        } else {\n            if (current == request[1]) {\n                *(s32 *)((u8 *)record + 0x1C) = first;\n                *((u8 *)record + 0x18) = *((u8 *)request + 8);\n            }\n        }\n    }\n}'
STUB='/* Non-matching C placeholders for asm/nonmatchings/game_161520/func_151347CC.s. */\ns32 func_151347CC() {\n    return 0;\n}'
OLD_DECL='s32 func_151347CC();'
NEW_DECL='void func_151347CC(struct102 *record, s32 *request, u8 command);'
def source_states(live,index=0):
    if index!=0:raise ValueError('One reference command handler')
    if live.count(STUB)==1 and live.count(OLD_DECL)==1:
        return live,live.replace(STUB,SELECTED,1).replace(OLD_DECL,NEW_DECL,1),False
    if live.count(SELECTED)!=1 or live.count(NEW_DECL)!=1:raise ValueError('Reference handler source changed')
    return live.replace(SELECTED,STUB,1).replace(NEW_DECL,OLD_DECL,1),live,True
