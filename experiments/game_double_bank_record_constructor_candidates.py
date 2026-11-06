"""Direct two-bank constructor using SDK vertices and a bounded optional tail."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_damped_motion_snapshot import diagnostics
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1510D970','generated_13AE20'
SOURCE,ASM='conker/src/game/generated_13AE20.c','conker/asm/13AE20.s'
BUILD='conker/build/game-double-bank-record-constructor-1510D970-match'
ENTRY,ROM,WORDS=0x1510D970,0x13AE20,69
OLD='s32 func_1510D970() {\n    return 0;\n}'
HEADERS='void *func_15167A68(s32, s32, s32, s32, u8, u8);\n'
SELECTED='/* Allocate two quad-coordinate banks and optional signed-halfword state. */\nvoid *func_1510D970(s32 kind, void *owner, s32 mode, s32 flags, s32 variant) {\n    u8 *record;\n    s32 bytes = 0x128;\n    s32 i;\n\n    if (flags & 1) {\n        bytes = 0x13A;\n    }\n    record = func_15167A68(0x4B, 0, bytes, 1, 0xFF, 1);\n    if (record != NULL) {\n        /* Each bank contains four vertex flags and texture-coordinate pairs. */\n        for (i = 0; i < 2; i++) {\n            ((Vtx *)(record + i * 0x40 + 0x90))[0].v.flag = 0;\n            ((Vtx *)(record + i * 0x40 + 0x90))[0].v.tc[0] = 0x800;\n            ((Vtx *)(record + i * 0x40 + 0x90))[0].v.tc[1] = 0;\n            ((Vtx *)(record + i * 0x40 + 0x90))[1].v.flag = 0;\n            ((Vtx *)(record + i * 0x40 + 0x90))[1].v.tc[0] = 0;\n            ((Vtx *)(record + i * 0x40 + 0x90))[1].v.tc[1] = 0;\n            ((Vtx *)(record + i * 0x40 + 0x90))[2].v.flag = 0;\n            ((Vtx *)(record + i * 0x40 + 0x90))[2].v.tc[0] = 0;\n            ((Vtx *)(record + i * 0x40 + 0x90))[2].v.tc[1] = 0x800;\n            ((Vtx *)(record + i * 0x40 + 0x90))[3].v.flag = 0;\n            ((Vtx *)(record + i * 0x40 + 0x90))[3].v.tc[0] = 0x800;\n            ((Vtx *)(record + i * 0x40 + 0x90))[3].v.tc[1] = 0x800;\n        }\n        record[0x120] = kind;\n        *(void **)(record + 0x110) = owner;\n        record[0x121] = mode;\n        record[0x124] = variant;\n        if (flags & 1) {\n            for (i = 0; i < 9; i++) {\n                ((s16 *)(record + 0x128))[i] = 0x7FFF;\n            }\n        }\n    }\n    return record;\n}'
NEW=HEADERS+SELECTED

def source_states(live):
    if live.count(OLD)==1 and NEW not in live:return live,live.replace(OLD,NEW,1),False
    if live.count(NEW)==1 and OLD not in live:return live.replace(NEW,OLD,1),live,True
    raise ValueError('Two-bank constructor source state changed')
