"""Complete point-effect descriptor with the original early-return shape."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15146A98','generated_173D40'
SOURCE='conker/src/game/generated_173D40.c'
BUILD='conker/build/game-owner-effect-descriptor-15146A98-match'
ENTRY,ROM,WORDS=0x15146A98,0x173F48,72
SELECTED="/* Submit the point effect using the attached actor's selected position. */\nvoid func_15146A98(u8 *actor, s32 context, s32 unused) {\n    EffectPoint173D40 position;\n    PointEffectDescriptor173D40 descriptor;\n\n    if (*(u32 *)(actor + 0x1D4) == 0) return;\n    func_15146890(&position.x, actor, (HeightResult71820 *)0, (u8)context);\n    descriptor.countBase = 5;\n    descriptor.countRange = 22;\n    descriptor.position = position;\n    descriptor.field14 = D_800A5708;\n    descriptor.field18 = D_800A570C;\n    descriptor.minimum1C = 0;\n    descriptor.range1E = 255;\n    descriptor.minimum20 = -20;\n    descriptor.range22 = 14;\n    descriptor.field24 = 6.0f;\n    descriptor.field28 = 3.0f;\n    descriptor.field2C = D_800A5710;\n    descriptor.field30 = D_800A5714;\n    descriptor.field34 = D_800A5718;\n    descriptor.field38 = D_800A571C;\n    descriptor.mode = 3;\n    descriptor.value3E = 25;\n    descriptor.value40 = 25;\n    func_15150F90(&descriptor, 0, 255, 1);\n}"
SUPPORT='typedef struct { f32 x, y, z; } EffectPoint173D40;\ntypedef struct {\n    s32 countBase;\n    s32 countRange;\n    EffectPoint173D40 position;\n    f32 field14;\n    f32 field18;\n    s16 minimum1C;\n    s16 range1E;\n    s16 minimum20;\n    s16 range22;\n    f32 field24;\n    f32 field28;\n    f32 field2C;\n    f32 field30;\n    f32 field34;\n    f32 field38;\n    u8 mode;\n    u8 reserved3D;\n    s16 value3E;\n    s16 value40;\n    u8 reserved42[2];\n} PointEffectDescriptor173D40;\nextern f32 D_800A5708, D_800A570C, D_800A5710, D_800A5714, D_800A5718, D_800A571C;\nvoid func_15150F90(PointEffectDescriptor173D40 *, u8, u8, s32);\n'
PLACEHOLDER='s32 func_15146A98() {\n    return 0;\n}'
def source_states(live):
    if live.count(PLACEHOLDER)==1:
        if SUPPORT in live or SELECTED in live:raise ValueError('Point descriptor predecessor changed')
        return live,live.replace('#include <ultra64.h>','#include <ultra64.h>\n'+SUPPORT,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)!=1 or live.count(SUPPORT)!=1:raise ValueError('Point descriptor source changed')
    return live.replace('#include <ultra64.h>\n'+SUPPORT,'#include <ultra64.h>',1).replace(SELECTED,PLACEHOLDER,1),live,True
