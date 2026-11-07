"""Below-height effect callback with retained position and payload pointers."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-below-height-effect-15189EBC-match'
RODATA_SYMBOL=None
TARGETS=[{'function': 'func_15189EBC', 'source': 'conker/src/game/generated_1B6DB0.c', 'owner': 'generated_1B6DB0', 'object': 'conker/build/src/game/generated_1B6DB0.c.o', 'assembly': 'conker/asm/1B6DB0.s', 'entry': 353935036, 'rom': 1799020, 'words': 69, 'frame': 80, 'raw_sha256': '710feafe53e498e4c18b3f15a313bbcd18fcc2d6c44bff268b3702b0cf4503e9', 'bindings': {72: [('R_MIPS_26', 'func_150ADA68')], 80: [('R_MIPS_HI16', 'D_800A73A8')], 84: [('R_MIPS_LO16', 'D_800A73A8')], 164: [('R_MIPS_26', 'func_151D8E20')], 224: [('R_MIPS_26', 'func_151DBCBC')], 240: [('R_MIPS_HI16', 'D_800A73B0')], 244: [('R_MIPS_LO16', 'D_800A73B0')]}, 'patches': {0: (666763192, 666763184), 76: (2946629700, 2946629696), 92: (2409758788, 2409758784), 272: (666697800, 666697808)}}]
SUPPORT='typedef struct {\n    f32 x, y, z;\n    u8 retained0C[8];\n} BelowHeightPosition;\nextern f64 D_800A73A8;\nextern f32 D_800A73B0;\nf32 func_150ADA68(void);\nu8 func_151D8E20(void);\nvoid func_151DBCBC(u8, f32, s16, s32, void *, u8, s32);\n'
SELECTED='/* Emit an occasional below-height effect, then reset the captured payload. */\ns32 func_15189EBC(u8 *actor) {\n    BelowHeightPosition *positions = *(BelowHeightPosition **)(actor + 0x94);\n    u8 *payload = *(u8 **)(actor + 0x98);\n    f32 point[3];\n    s32 choice;\n    if (positions[(s8)actor[0x2D]].y < *(f32 *)(payload + 0x48)) {\n        if ((f64)func_150ADA68() < D_800A73A8) {\n            point[0] = positions[(s8)actor[0x2D]].x;\n            point[1] = *(f32 *)(payload + 0x48);\n            point[2] = positions[(s8)actor[0x2D]].z;\n            choice = func_151D8E20();\n            func_151DBCBC((u8)choice, *(f32 *)payload * 6.0f,\n                         payload[0x1B], 0, point, actor[0xC], actor[1]);\n        }\n        payload[0x20] = 4;\n        *(f32 *)(payload + 0x48) = D_800A73B0;\n    }\n    return 1;\n}'
def source_states(live,index=0):
    if index!=0:raise ValueError('One below-height callback')
    stub='s32 func_15189EBC() {\n    return 0;\n}'
    selected=SUPPORT+'\n'+SELECTED
    if live.count(stub)==1:
        if SUPPORT in live:raise ValueError('Partial height callback installation')
        return live,live.replace(stub,selected,1),False
    if live.count(selected)!=1:raise ValueError('Height callback source changed')
    return live.replace(selected,stub,1),live,True
