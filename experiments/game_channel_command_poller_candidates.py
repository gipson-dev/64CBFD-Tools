"""Queued actor-channel commands and the signed-count Init reader ABI."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15080228','generated_AD6B0'
SOURCE='conker/src/game/generated_AD6B0.c'
BUILD='conker/build/game-channel-command-poller-15080228-match'
ENTRY,ROM,WORDS=0x15080228,0xAD6D8,72
HEADER,INIT='conker/include/functions.h','conker/src/init_12560.c'
DECLARATION='extern u8 D_800D18D0;\nextern u8 D_800CC2D0[];\ns32 func_100126E8(u8 *, s32);\nvoid func_15080430(u8 *, s32, s32);\n'
SELECTED='/* Poll queued actor-channel commands and decode their seven-bit duration. */\nvoid func_15080228(void) {\n    u8 command[256];\n    s32 duration;\n\n    while (func_100126E8(command, sizeof(command)) != 0) {\n        if (command[0] == 0x4C) {\n            duration = command[4] & 0x7F;\n            duration = (command[5] & 0x7F) | (duration << 7);\n            duration = (command[6] & 0x7F) | (duration << 7);\n            duration = (command[7] & 0x7F) | (duration << 7);\n            duration /= 367;\n            if (duration == 0) {\n                duration = 20;\n            }\n            func_15080430(D_800CC2D0 + D_800D18D0 * 0x32C,\n                         command[3] - 1, duration);\n        }\n    }\n}'
PLACEHOLDER='s32 func_15080228() {\n    return 0;\n}'
OLD_INIT='void func_100126E8(s32 arg0, s32 arg1) {\n    func_15043CA4(&D_800427A0, arg0, arg1);\n}'
NEW_INIT='/* Receive one queued command and return its byte count. */\ns32 func_100126E8(u8 *output, s32 capacity) {\n    return func_15043CA4(&D_800427A0, output, capacity);\n}'
QUEUE_DECL='s32 func_15043CA4(struct105 *, u8 *, s32);\n'
OLD_PROTO='void func_100126E8(s32 arg0, s32 arg1);'
NEW_PROTO='s32 func_100126E8(u8 *output, s32 capacity);'

def source_states(live):
    marker='#include <ultra64.h>\n'
    if live.count(PLACEHOLDER)==1:
        if SELECTED in live or DECLARATION in live:raise ValueError('Packet poller predecessor changed')
        return live,live.replace(marker,marker+DECLARATION,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)!=1 or live.count(DECLARATION)!=1:raise ValueError('Packet poller source changed')
    return live.replace(marker+DECLARATION,marker,1).replace(SELECTED,PLACEHOLDER,1),live,True
def repaired_header(text):
    if text.count(OLD_PROTO)!=1 or NEW_PROTO in text:raise ValueError('Reader header predecessor changed')
    return text.replace(OLD_PROTO,NEW_PROTO,1)
def repaired_init(text):
    if text.count(OLD_INIT)!=1 or QUEUE_DECL in text:raise ValueError('Reader definition predecessor changed')
    return text.replace(OLD_INIT,NEW_INIT,1).replace('#include "variables.h"\n','#include "variables.h"\n'+QUEUE_DECL,1)
