"""Direct SDK resource draw; portable shift contract uses view indices0..31."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-view-resource-draw-1513B83C-match'
TARGETS=[{'function': 'func_1513B83C', 'source': 'conker/src/game_168A90.c', 'owner': 'game_168A90', 'object': 'conker/build/src/game_168A90.c.o', 'assembly': 'conker/asm/nonmatchings/game_168A90/func_1513B83C.s', 'entry': 353613884, 'rom': 1477868, 'words': 75, 'frame': 32, 'raw_sha256': 'a186ae6d8427b7f23bf8288edc5a2058a219905745eb37fd328b47e12c17b710', 'bindings': {104: [('R_MIPS_HI16', 'D_80089C28')], 112: [('R_MIPS_LO16', 'D_80089C28')], 156: [('R_MIPS_HI16', 'D_800BE9C0')], 160: [('R_MIPS_LO16', 'D_800BE9C0')]}}]
SELECTED="/* Submit the resource's three graphics commands after per-view filtering. */\nGfx *func_1513B83C(Gfx *displayList, u8 *resource, s16 view) {\n    s8 callbackIndex;\n\n    if ((resource[0x10] & 2) != 0 &&\n        (resource[0x49] & (1U << view)) == 0) {\n        return displayList;\n    }\n    callbackIndex = *(s8 *)(resource + 0x12);\n    if (callbackIndex != -1 && D_80089C28[callbackIndex](resource, view) == 0) {\n        return displayList;\n    }\n    gSPMatrix(displayList++, (Mtx *)(resource + 0x78 + ((u32)D_800BE9C0 << 6)),\n              G_MTX_MODELVIEW | G_MTX_LOAD | G_MTX_NOPUSH);\n    gSPSegment(displayList++, 1,\n               *(u32 *)(resource + 0x58 + ((u32)D_800BE9C0 << 4) + (s32)view * 4));\n    gSPDisplayList(displayList++, *(Gfx **)(resource + 0x54));\n    return displayList;\n}"

def source_states(live,index=0):
    if index!=0:raise ValueError('One view resource draw target')
    stub='/* Non-matching C placeholders for asm/nonmatchings/game_168A90/func_1513B83C.s. */\ns32 func_1513B83C() {\n    return 0;\n}'
    old='s32 func_1513B83C();';new='Gfx *func_1513B83C(Gfx *displayList, u8 *resource, s16 view);'
    prior='extern s32 (*D_80089C18[])(u8 *);';current=prior+'\nextern s32 (*D_80089C28[])(u8 *, s16);'
    if live.count(stub)==1 and live.count(old)==1 and current not in live:return live,live.replace(stub,SELECTED,1).replace(old,new,1).replace(prior,current,1),False
    if live.count(SELECTED)!=1 or live.count(new)!=1 or live.count(current)!=1:raise ValueError('View resource source changed')
    return live.replace(SELECTED,stub,1).replace(new,old,1).replace(current,prior,1),live,True
