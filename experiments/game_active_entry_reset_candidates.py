"""Direct active-entry reset loop with naturally retained O32 owner home."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-active-entry-reset-15191400-match'
RODATA_SYMBOL=None
TARGETS=[{'function': 'func_15191400', 'source': 'conker/src/game/generated_1BA1D0.c', 'owner': 'generated_1BA1D0', 'object': 'conker/build/src/game/generated_1BA1D0.c.o', 'assembly': 'conker/asm/1BA1D0.s', 'entry': 353965056, 'rom': 1829040, 'words': 72, 'frame': 64, 'raw_sha256': '05a334797359731f8010c06d68d0f1db934211dbb4771ace48eb33d60cfbf367', 'bindings': {48: [('R_MIPS_HI16', 'D_800A9D40')], 52: [('R_MIPS_LO16', 'D_800A9D40')], 144: [('R_MIPS_26', 'func_1513F680')], 152: [('R_MIPS_26', 'func_150ADA20')], 240: [('R_MIPS_26', 'bzero')]}, 'patches': {}}]
SUPPORT='typedef struct {\n    u8 *actor;\n    u8 retained04[8];\n} ActiveResetEntry15191400;\ntypedef struct {\n    s16 base, range;\n    u8 retained04[16];\n} ActiveResetPreset15191400;\ntypedef struct {\n    u8 retained00[0x1C];\n    f32 value1C;\n    s32 state20;\n    ActiveResetEntry15191400 *entries;\n} ActiveResetOwner15191400;\nextern ActiveResetPreset15191400 D_800A9D40[];\nvoid func_1513F680(struct171 *, u8, u8, u8, u8);\n'
SELECTED='/* Reset active entries, reseed their live actor timers, then clear the owner list. */\nvoid func_15191400(ActiveResetOwner15191400 *owner) {\n    ActiveResetEntry15191400 *entry;\n    ActiveResetPreset15191400 *preset;\n    s32 index;\n    u32 random;\n    u8 *state;\n\n    owner->value1C = 0.0f;\n    owner->state20 = 0;\n    entry = owner->entries;\n    for (index = 0; index < 60; index++, entry++) {\n        if (entry->actor != NULL) {\n            state = entry->actor + 0x110;\n            preset = &D_800A9D40[state[0x20]];\n            *(f32 *)(state + 0) = 0.0f;\n            *(f32 *)(state + 4) = 0.0f;\n            *(f32 *)(state + 8) = 0.0f;\n            func_1513F680((struct171 *)entry->actor, 13, 18, 0, 13);\n            random = (u32)func_150ADA20();\n            *(s16 *)(entry->actor + 0x1C) = random % (preset->range + 1U) + preset->base;\n            *(u32 *)(entry->actor + 0x58) |= 1;\n        }\n    }\n    bzero(owner->entries, 0x2D0);\n}'

def source_states(live,index=0):
    if index!=0:raise ValueError('One active-entry reset target')
    stub='s32 func_15191400() {\n    return 0;\n}'
    anchor='/* Non-matching placeholders for the text-only asm slice asm/1BA1D0.s. */'
    changes=[('s32 func_15191400();','void func_15191400(ActiveResetOwner15191400 *);'),
             ('s32 func_15190840(s32 arg0)','s32 func_15190840(u8 *arg0)'),
             ('s32 func_1519086C(s32 arg0)','s32 func_1519086C(u8 *arg0)'),
             ('func_15191400(arg0);','func_15191400((ActiveResetOwner15191400 *)arg0);')]
    installed=SELECTED in live
    if installed:
        if live.count(SELECTED)!=1 or live.count(SUPPORT)!=1:raise ValueError('Partial reset installation')
        before=live.replace(SELECTED,stub,1).replace(SUPPORT+'\n'+anchor,anchor,1)
        for a,b in changes:before=before.replace(b,a)
        after=live
    else:
        if live.count(stub)!=1 or SUPPORT in live:raise ValueError('Reset source changed')
        before=live;after=live.replace(stub,SELECTED,1).replace(anchor,SUPPORT+'\n'+anchor,1)
        for a,b in changes:after=after.replace(a,b)
    return before,after,installed
