"""Eight-argument preset table payload and explicit caller ABI."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_151623F4','game_18D770'
SOURCE='conker/src/game_18D770.c'
BUILD='conker/build/game-selector-table-payload-151623F4-match'
ENTRY,ROM,WORDS=0x151623F4,0x18F8A4,71
TYPES='typedef struct {\n    struct17 base;\n    struct17 amplitude;\n    f32 phase;\n    f32 rate;\n} SelectorPayload151623F4;\n'
SELECTED='/* Build a 32-byte payload from one of the three preset table rows. */\nstruct225 *func_151623F4(struct226 *actor, u8 selector, u8 flags, u8 headerId,\n                       s8 kind, s16 lifetime, u8 priority, s32 userData) {\n    SelectorPayload151623F4 payload;\n    Header header;\n    struct225 *result;\n\n    if (selector >= 3) {\n        return 0;\n    }\n    payload.base = *(struct17 *)D_800A670C[selector];\n    payload.amplitude = *(struct17 *)D_800A6730[selector];\n    payload.phase = 0.0f;\n    payload.rate = D_800A6754[selector];\n    header.unk0 = headerId;\n    header.unk1 = kind;\n    header.unk2 = lifetime;\n    header.unk4 = flags;\n    result = func_1516037C(&header, actor, sizeof(payload), priority, userData);\n    if (result != 0) {\n        memcpy((u8 *)result + 0x18, &payload, sizeof(payload));\n    }\n    return result;\n}'
PROTOTYPE='struct225 *func_151623F4(struct226 *, u8, u8, u8, s8, s16, u8, s32);'
STEPS={'conker/src/game_18D770.c': [('#include "variables.h"', '#include "variables.h"\ntypedef struct {\n    struct17 base;\n    struct17 amplitude;\n    f32 phase;\n    f32 rate;\n} SelectorPayload151623F4;\n'), ('s32 func_151623F4();', 'struct225 *func_151623F4(struct226 *, u8, u8, u8, s8, s16, u8, s32);'), ('// help.\n/* Non-matching C placeholders for asm/nonmatchings/game_18D770/func_151623F4.s. */\ns32 func_151623F4() {\n    return 0;\n}', '/* Build a 32-byte payload from one of the three preset table rows. */\nstruct225 *func_151623F4(struct226 *actor, u8 selector, u8 flags, u8 headerId,\n                       s8 kind, s16 lifetime, u8 priority, s32 userData) {\n    SelectorPayload151623F4 payload;\n    Header header;\n    struct225 *result;\n\n    if (selector >= 3) {\n        return 0;\n    }\n    payload.base = *(struct17 *)D_800A670C[selector];\n    payload.amplitude = *(struct17 *)D_800A6730[selector];\n    payload.phase = 0.0f;\n    payload.rate = D_800A6754[selector];\n    header.unk0 = headerId;\n    header.unk1 = kind;\n    header.unk2 = lifetime;\n    header.unk4 = flags;\n    result = func_1516037C(&header, actor, sizeof(payload), priority, userData);\n    if (result != 0) {\n        memcpy((u8 *)result + 0x18, &payload, sizeof(payload));\n    }\n    return result;\n}')], 'conker/src/game_36680.c': [('#include "variables.h"', '#include "variables.h"\n\nstruct225 *func_151623F4(struct226 *, u8, u8, u8, s8, s16, u8, s32);'), ('    func_151623F4(arg0,', '    func_151623F4((struct226 *)arg0,')]}
SOURCES=tuple(STEPS)
def source_states(live,name=SOURCE):
    installed=PROTOTYPE in live;before=live
    if installed:
        for old,new in reversed(STEPS[name]):
            count=2 if old.startswith('    func_')else 1
            if before.count(new)!=count:raise ValueError('Installed selector source differs: '+name)
            before=before.replace(new,old)
    after=before
    for old,new in STEPS[name]:
        count=2 if old.startswith('    func_')else 1
        if after.count(old)!=count:raise ValueError('Predecessor selector source differs: '+name)
        after=after.replace(old,new)
    if installed and after!=live:raise ValueError('Selector source reversal failed: '+name)
    return before,after,installed
