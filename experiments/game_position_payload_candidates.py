"""Direct callback-position payload factory and its captured/live data."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-position-payload-151D0F60-match'
RODATA_SYMBOL=None
TARGETS=[{'function': 'func_151D0F60', 'source': 'conker/src/game/generated_1FA770.c', 'owner': 'generated_1FA770', 'object': 'conker/build/src/game/generated_1FA770.c.o', 'assembly': 'conker/asm/1FA770.s', 'entry': 354226016, 'rom': 2090000, 'words': 69, 'frame': 112, 'raw_sha256': '30dcb8a77bc13b6dee24a2b1a7d251e536ceabeedd13bae6e791758d57672bb1', 'bindings': {24: [('R_MIPS_HI16', 'D_8008FC30')], 40: [('R_MIPS_LO16', 'D_8008FC30')], 72: [('R_MIPS_HI16', 'D_800A5480')], 76: [('R_MIPS_LO16', 'D_800A5480')], 112: [('R_MIPS_HI16', 'D_800A5480')], 124: [('R_MIPS_LO16', 'D_800A5480')], 232: [('R_MIPS_26', 'func_15149130')], 252: [('R_MIPS_26', 'memcpy')]}, 'patches': {}}]
SUPPORT='typedef struct { f32 x, y, z; } PositionVector151D0F60;\ntypedef struct {\n    u8 *owner;\n    u8 ownerId;\n    s32 zero08;\n    PositionVector151D0F60 first, second, third;\n    f32 zero30;\n    u8 selector;\n} PositionPayload151D0F60;\nextern s32 (*D_8008FC30[])(u8 *, PositionVector151D0F60 *);\nextern PositionVector151D0F60 D_800A5480;\n'
SELECTED='/* Capture the position callback result and attach its duplicated payload. */\nvoid func_151D0F60(u8 *owner, u8 selector, u8 priority, s32 context) {\n    u8 *created;\n    PositionPayload151D0F60 payload;\n    payload.owner = owner;\n    payload.ownerId = owner[0x3B];\n    payload.zero08 = 0;\n    if (!D_8008FC30[selector](owner, &payload.second)) {\n        payload.second = D_800A5480;\n    }\n    payload.first = payload.second;\n    payload.third = D_800A5480;\n    payload.zero30 = 0.0f;\n    payload.selector = selector;\n    created = func_15149130(300, -1, 95, -1, 0, 72, 56, priority, context);\n    if (created != NULL) {\n        memcpy(created + 0x28, &payload, 56);\n    }\n}'

REPAIRS=[
('s32 func_151D10E4(u8 *, s32, u8);','s32 func_151D10E4(u8 *, void *, u8);'),
('''s32 func_151D1074(u8 *arg0, f32 *arg1) {
    arg1[0] = *(f32 *) (arg0 + 0x14);
    arg1[1] = *(f32 *) (arg0 + 0x180) + 8.0f;
    arg1[2] = *(f32 *) (arg0 + 0x1C);
    return 1;
}''','''s32 func_151D1074(u8 *owner, PositionVector151D0F60 *output) {
    output->x = *(f32 *)(owner + 0x14);
    output->y = *(f32 *)(owner + 0x180) + 8.0f;
    output->z = *(f32 *)(owner + 0x1C);
    return 1;
}'''),
('''void func_151D10A4(s32 arg0, s32 arg1) {
    func_151D10E4(arg0, arg1, 0);
}''','''/* Preserve the transform status returned through the position callback. */
s32 func_151D10A4(u8 *owner, PositionVector151D0F60 *output) {
    return func_151D10E4(owner, output, 0);
}'''),
('''void func_151D10C4(s32 arg0, s32 arg1) {
    func_151D10E4(arg0, arg1, 1);
}''','''/* Query the second transform row through the same callback ABI. */
s32 func_151D10C4(u8 *owner, PositionVector151D0F60 *output) {
    return func_151D10E4(owner, output, 1);
}'''),
('''s32 func_151D10E4(u8 *arg0, s32 arg1, u8 arg2) {
    s32 target;

    target = *(s32 *) (arg0 + 0x1D4);
    if (target == NULL) {
        return 0;
    }
    func_15143134(&D_800AAF9C[arg2], arg1, target);
    return 1;
}''','''s32 func_151D10E4(u8 *owner, void *output, u8 mode) {
    void *target;

    target = *(void **)(owner + 0x1D4);
    if (target == NULL) {
        return 0;
    }
    func_15143134(&D_800AAF9C[mode], output, target);
    return 1;
}''')]

def source_states(live,index=0):
    if index!=0:raise ValueError('One position-payload target')
    stub='s32 func_151D0F60() {\n    return 0;\n}';selected=SUPPORT+'\n'+SELECTED
    if live.count(stub)==1:
        if SUPPORT in live:raise ValueError('Partial payload installation')
        after=live.replace(stub,selected,1)
        for old,new in REPAIRS:
            if after.count(old)!=1:raise ValueError('Payload callback predecessor changed')
            after=after.replace(old,new,1)
        return live,after,False
    if live.count(selected)!=1:raise ValueError('Position payload source changed')
    before=live.replace(selected,stub,1)
    for old,new in REPAIRS:
        if before.count(new)!=1:raise ValueError('Payload callback repair changed')
        before=before.replace(new,old,1)
    return before,live,True
