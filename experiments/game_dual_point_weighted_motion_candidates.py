"""Damped dual-point motion with a saved weight and first-point blend anchors."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_damped_motion_snapshot import diagnostics
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1514A594','generated_176A00'
SOURCE,ASM='conker/src/game/generated_176A00.c','conker/asm/176A00.s'
BUILD='conker/build/game-dual-point-motion-1514A594-match'
ENTRY,ROM,WORDS=0x1514A594,0x177A44,67
OLD='s32 func_1514A594() {\n    return 0;\n}'
SELECTED='/* Integrate two points, then blend the second toward the first. */\ns32 func_1514A594(u8 *owner) {\n    f32 *record = (f32 *)owner;\n    f32 dx, yComponent, zComponent;\n    f32 weight;\n    f32 firstX;\n\n    *(f32 *)(owner + 0x130) *= *(f32 *)(owner + 0x140);\n    *(f32 *)(owner + 0x134) += *(f32 *)(owner + 0x13C) * D_800BE9A4;\n    *(f32 *)(owner + 0x138) *= *(f32 *)(owner + 0x140);\n    dx = record[0x130 / 4] * D_800BE9A4;\n    yComponent = record[0x134 / 4] * D_800BE9A4;\n    zComponent = record[0x138 / 4] * D_800BE9A4;\n    record[0x34 / 4] += dx;\n    record[0x38 / 4] += yComponent;\n    record[0x3C / 4] += zComponent;\n    record[0x40 / 4] += dx;\n    record[0x44 / 4] += yComponent;\n    record[0x48 / 4] += zComponent;\n    firstX = record[0x34 / 4];\n    weight = record[0x54 / 4];\n    /* The finished Y/Z steps can now hold the first-point coordinates. */\n    yComponent = record[0x38 / 4];\n    zComponent = record[0x3C / 4];\n    record[0x40 / 4] = firstX + (record[0x40 / 4] - firstX) * weight;\n    record[0x44 / 4] = yComponent + (record[0x44 / 4] - yComponent) * weight;\n    record[0x48 / 4] = zComponent + (record[0x48 / 4] - zComponent) * weight;\n    return 1;\n}'
def source_states(live):
    if live.count(OLD)==1:return live,live.replace(OLD,SELECTED,1),False
    if live.count(SELECTED)==1:return live.replace(SELECTED,OLD,1),live,True
    raise ValueError('Weighted dual-point motion source changed')
