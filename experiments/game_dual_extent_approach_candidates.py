"""Direct extent interpolation callback with byte flags and the typed SDK setter."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_damped_motion_snapshot import diagnostics
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1514A380','generated_176A00'
SOURCE,ASM='conker/src/game/generated_176A00.c','conker/asm/176A00.s'
BUILD='conker/build/game-dual-extent-approach-1514A380-match'
ENTRY,ROM,WORDS=0x1514A380,0x177830,70
OLD='s32 func_1514A380() {\n    return 0;\n}'
DECLARATIONS='#include "structs.h"\nextern f32 D_800A57A0, D_800A57A4, D_800A57A8, D_800A57AC;\nvoid func_1513F680(struct171 *, u8, u8, u8, u8);\n'
SELECTED='/* Approach both target extents, then select the settled update callback. */\ns32 func_1514A380(u8 *owner) {\n    s32 complete = 1;\n    u8 *payload = owner + 0x110;\n\n    if ((owner[0x74] & 2) == 0) {\n        *(f32 *)(owner + 0x2C) +=\n            (*(f32 *)(payload + 8) - *(f32 *)(owner + 0x2C)) * D_800A57A0;\n        if (*(f32 *)(payload + 8) * D_800A57A4 < *(f32 *)(owner + 0x2C)) {\n            owner[0x74] |= 2;\n        } else {\n            complete = 0;\n        }\n    }\n    if ((owner[0x74] & 8) == 0) {\n        *(f32 *)(owner + 0x30) +=\n            (*(f32 *)(payload + 0x18) - *(f32 *)(owner + 0x30)) * D_800A57A8;\n        if (*(f32 *)(payload + 0x18) * D_800A57AC < *(f32 *)(owner + 0x30)) {\n            owner[0x74] |= 8;\n        } else {\n            complete = 0;\n        }\n    }\n    if (complete) {\n        func_1513F680((struct171 *)owner, owner[0x70], 4, owner[0x72], owner[0x73]);\n    }\n    return 1;\n}'
def source_states(live):
    marker='#include <ultra64.h>\n'
    if live.count(OLD)==1 and DECLARATIONS not in live:
        return live,live.replace(marker,marker+DECLARATIONS,1).replace(OLD,SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(DECLARATIONS)==1:
        return live.replace(DECLARATIONS,'',1).replace(SELECTED,OLD,1),live,True
    raise ValueError('Extent-approach source state changed')
