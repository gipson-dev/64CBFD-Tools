"""Complete semantic resource texture-phase and scroll update."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-resource-scroll-update-1513BEB0-match'
TARGETS=[{'function': 'func_1513BEB0', 'source': 'conker/src/game_168A90.c', 'owner': 'game_168A90', 'object': 'conker/build/src/game_168A90.c.o', 'assembly': 'conker/asm/nonmatchings/game_168A90/func_1513BEB0.s', 'entry': 353615536, 'rom': 1479520, 'words': 107, 'frame': 32, 'raw_sha256': '4a4ba11a3e841ea72a071ed7acfc02ebc6438762659b6099d5f678befc9b3d5c', 'bindings': {12: [('R_MIPS_HI16', 'D_800A4A84')], 16: [('R_MIPS_LO16', 'D_800A4A84')], 20: [('R_MIPS_HI16', 'D_800BE9A4')], 24: [('R_MIPS_LO16', 'D_800BE9A4')], 56: [('R_MIPS_26', 'func_15144B68')], 68: [('R_MIPS_HI16', 'D_800A4A88')], 72: [('R_MIPS_LO16', 'D_800A4A88')], 76: [('R_MIPS_HI16', 'D_800BE9A4')], 80: [('R_MIPS_LO16', 'D_800BE9A4')], 100: [('R_MIPS_26', 'sinf')], 116: [('R_MIPS_HI16', 'D_800BE9A4')], 120: [('R_MIPS_LO16', 'D_800BE9A4')], 108: [('R_MIPS_HI16', 'D_800A4A8C')], 112: [('R_MIPS_LO16', 'D_800A4A8C')], 128: [('R_MIPS_HI16', 'D_800A4A90')], 144: [('R_MIPS_LO16', 'D_800A4A90')], 148: [('R_MIPS_HI16', 'D_800A4A94')], 172: [('R_MIPS_LO16', 'D_800A4A94')], 188: [('R_MIPS_26', 'func_15144B68')], 200: [('R_MIPS_26', 'func_15144B68')]}}]
SELECTED='/* Advance texture phases and retain both inclusive 0..4096 scrolls. */\ns32 func_1513BEB0(u8 *resource) {\n    f32 *payload;\n    payload = (f32 *)(resource + *(u32 *)(resource + 0x50) + 0xF8);\n    payload[2] += D_800A4A84 * D_800BE9A4;\n    payload[2] = func_15144B68(payload[2]);\n    payload[0] += D_800A4A88 * D_800BE9A4;\n    payload[1] = sinf(payload[2]) * D_800A4A8C;\n    payload[3] += D_800A4A90 * D_800BE9A4;\n    payload[4] += D_800A4A94 * D_800BE9A4;\n    payload[3] = func_15144B68(payload[3]);\n    payload[4] = func_15144B68(payload[4]);\n    while (payload[0] > 4096.0f) payload[0] -= 4096.0f;\n    while (payload[0] < 0.0f) payload[0] += 4096.0f;\n    while (payload[1] > 4096.0f) payload[1] -= 4096.0f;\n    while (payload[1] < 0.0f) payload[1] += 4096.0f;\n    return 1;\n}'
DECLARATIONS='extern f32 D_800A4A84, D_800A4A88, D_800A4A8C, D_800A4A90, D_800A4A94;\n'

def source_states(live,index=0):
    if index!=0:raise ValueError('One resource scroll update')
    stub='/* Non-matching C placeholders for asm/nonmatchings/game_168A90/func_1513BEB0.s. */\ns32 func_1513BEB0() {\n    return 0;\n}'
    old='s32 func_1513BEB0();';new='s32 func_1513BEB0(u8 *resource);'
    marker='/* Generated placeholder declarations. */';added=DECLARATIONS+'\n'+marker
    if live.count(stub)==1 and live.count(old)==1:
        return live,live.replace(stub,SELECTED,1).replace(old,new,1).replace(marker,added,1),False
    if live.count(SELECTED)!=1 or live.count(new)!=1 or live.count(added)!=1:raise ValueError('Resource scroll source changed')
    return live.replace(SELECTED,stub,1).replace(new,old,1).replace(added,marker,1),live,True
