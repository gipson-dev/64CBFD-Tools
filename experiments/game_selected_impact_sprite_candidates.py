"""Selected impact sprite and its subsequent randomized effect submission."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-selected-impact-sprite-1518C69C-match'
TARGETS=[{'function': 'func_1518C69C', 'source': 'conker/src/game/generated_1B8F40.c', 'owner': 'generated_1B8F40', 'object': 'conker/build/src/game/generated_1B8F40.c.o', 'assembly': 'conker/asm/1B8F40.s', 'entry': 353945244, 'rom': 1809228, 'words': 109, 'frame': 248, 'raw_frame': 256, 'raw_sha256': '71fe177f77821ea1906b0c4c0462f3b5947c454e67bab7258b292f899c77969d', 'bindings': {144: [('R_MIPS_26', 'func_150ADA20')], 232: [('R_MIPS_26', 'func_1516865C')], 248: [('R_MIPS_26', 'func_15168800')], 328: [('R_MIPS_26', 'func_151D8E20')], 336: [('R_MIPS_26', 'func_150ADA68')], 404: [('R_MIPS_26', 'func_151DBCBC')]}, 'patches': {0: (666763008, 666763016), 16: (2946826500, 2946826492), 20: (2946892040, 2946892032), 24: (2946957580, 2946957572), 40: (3349676304, 3349676296), 80: (52645921, 7950369), 120: (31703073, 7323681), 188: (2746024178, 2813067490), 192: (2746089712, 2746024178), 196: (2813264104, 2746089712), 200: (2745172209, 2813264104), 204: (2813067492, 2745172209), 212: (2813067490, 2813067492), 268: (2706964512, 604241940), 272: (2181759021, 2706964512), 276: (604241940, 2181759021), 280: (3349545232, 3349545224), 292: (25389089, 7104545), 320: (31703073, 7323681), 396: (2410086676, 2410086668), 424: (666697984, 666697976)}}]
SUPPORT='u8 func_151D8E20(void);\nf32 func_150ADA68(void);\nvoid func_151DBCBC(u8, f32, s16, s32, void *, u8, s32);\n'
SELECTED='/* Emit the impact sprite and submit a randomized effect at the updated position. */\ns32 func_1518C69C(u8 *actor, f32 previousX, f32 previousY, f32 previousZ,\n                  f32 height, void *context) {\n    s32 heightInt;\n    SelectedVertexSprite descriptor;\n    u8 *owner = *(u8 **)(actor + 0x98);\n    u8 *positions = *(u8 **)(actor + 0x94);\n    u8 selector;\n    f32 position[3];\n    f32 magnitude;\n    descriptor.value80 = 0;\n    descriptor.value8A = 0x100;\n    descriptor.x = (s32)*(f32 *)(positions + *(s8 *)(actor + 0x2D) * 20);\n    descriptor.y = heightInt = (s32)height;\n    descriptor.z = (s32)*(f32 *)(positions + *(s8 *)(actor + 0x2D) * 20 + 8);\n    descriptor.lifetime = (u32)func_150ADA20() % 21 + 35;\n    descriptor.tag = -1;\n    descriptor.textureIndex = 18;\n    descriptor.flags = 12;\n    descriptor.mode = 0;\n    descriptor.remaining = descriptor.lifetime;\n    descriptor.initialHeight = heightInt;\n    func_1516865C(&descriptor, 255, 255, 255, 255);\n    func_15168800(&descriptor, actor[0xC], actor[1]);\n    owner[0x20] = 4;\n    position[0] = *(f32 *)(positions + *(s8 *)(actor + 0x2D) * 20);\n    position[1] = height;\n    position[2] = *(f32 *)(positions + *(s8 *)(actor + 0x2D) * 20 + 8);\n    selector = func_151D8E20();\n    magnitude = func_150ADA68() * 40.0f + 100.0f;\n    func_151DBCBC(selector, magnitude, 255,\n                  (s32)context, position, actor[0xC], actor[1]);\n    return 1;\n}'

def source_states(live,index=0):
    if index!=0:raise ValueError('Only one impact-sprite owner')
    stub='s32 func_1518C69C() {\n    return 0;\n}'
    anchor='void *func_15168800(void *, u8, s32);'
    support=anchor+'\n'+SUPPORT
    if live.count(stub)==1:
        if live.count(anchor)!=1 or SELECTED in live or SUPPORT in live:raise ValueError('Impact sprite predecessor changed')
        return live,live.replace(anchor,support,1).replace(stub,SELECTED,1),False
    if live.count(SELECTED)!=1 or live.count(support)!=1:raise ValueError('Impact sprite recovery changed')
    return live.replace(support,anchor,1).replace(SELECTED,stub,1),live,True
