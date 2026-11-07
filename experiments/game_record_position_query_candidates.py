"""Position-initialized actor query and first matching record search."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_150A3194','generated_CDE80'
SOURCE='conker/src/game/generated_CDE80.c'
BUILD='conker/build/game-record-position-query-150A3194-match'
ENTRY,ROM,WORDS=0x150A3194,0xD0644,72
SELECTED='/* Find the first matching record accepted by the position query. */\nGeneratedCDE80Record *func_150A3194(s32 kind, s32 subtype, s32 x, s32 y, s32 z) {\n    u32 index;\n    struct127 query;\n    s32 offset;\n\n    query.x_position = x;\n    query.y_position = y;\n    query.z_position = z;\n    query.old_x_position = x;\n    query.unk180 = y;\n    query.old_y_position = y;\n    query.old_z_position = z;\n\n    for (index = 0, offset = 0; index < (u32)D_800D3094; index++, offset += 0x34) {\n        if ((((u8 *)D_800D3098)[offset + 0x14] == 0) &&\n            ((((u8 *)D_800D3098)[offset + 0x15] >> 2) == kind) &&\n            (((u8 *)D_800D3098)[offset + 0x17] == subtype)) {\n            if (func_150A1DA0(&query, offset + (s32)D_800D3098, 0) == 0) {\n                return (GeneratedCDE80Record *)(offset + (s32)D_800D3098);\n            }\n        }\n    }\n    return NULL;\n}'
PLACEHOLDER='s32 func_150A3194() {\n    return 0;\n}'

SUPPORT='typedef struct {\n    s16 origin0;\n    s16 origin1;\n    s16 origin2;\n    u8 pad6[0xF];\n    u8 flags;\n    u8 pad16;\n    u8 field17;\n    s32 field18;\n    s32 field1C;\n    s32 field20;\n    f32 coefficient0;\n    f32 scale;\n    f32 coefficient1;\n    f32 coefficient2;\n} GeneratedCDE80Record;\n\nextern GeneratedCDE80Record *D_800D3098;\nextern s32 D_800D3094;\n\ns32 func_150A1DA0(struct127 *, s32, s32);\n'

def source_states(live):
    if live.count(PLACEHOLDER)==1:
        if SELECTED in live:raise ValueError('Record query predecessor changed')
        return live,live.replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)!=1:raise ValueError('Record query source changed')
    return live.replace(SELECTED,PLACEHOLDER,1),live,True
