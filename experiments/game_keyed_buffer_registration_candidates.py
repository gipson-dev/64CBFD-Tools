"""Keyed registration and shared node layout; reproducible complete-owner states."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_damped_motion_snapshot import diagnostics
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1518894C','generated_1B5CC0'
SOURCE,ASM='conker/src/game/generated_1B5CC0.c','conker/asm/1B5CC0.s'
BUILD='conker/build/game-keyed-buffer-registration-1518894C-match'
ENTRY,ROM,WORDS=0x1518894C,0x1B5DFC,67
OLD='s32 func_1518894C() {\n    return 0;\n}\n\ntypedef struct ListNode15188A58 ListNode15188A58;\n\nstruct ListNode15188A58 {\n    u8 pad0[0xC];\n    ListNode15188A58 *next;\n};'
HEADERS='typedef struct ListNode15188A58 ListNode15188A58;\n\nstruct ListNode15188A58 {\n    u8 active, kind, cleared, recordSize;\n    u8 mode, retained05;\n    s16 timer;\n    u8 *buffer;\n    ListNode15188A58 *next;\n    s32 key;\n};\nextern ListNode15188A58 *D_800DF7CC;\ns32 allocate_memory(s32, s32, s32, s32);\n/* The matched helper receives its head through the existing node-pointer view. */\nvoid func_15188A58(ListNode15188A58 *, ListNode15188A58 *);\n'
SELECTED='/* Extend the first matching timer, or allocate and append its cleared buffer. */\nvoid func_1518894C(s32 key, s32 timer, s32 mode) {\n    ListNode15188A58 *node = D_800DF7CC;\n    u8 *buffer;\n\n    if (node != NULL) {\n        do {\n            if (key == node->key) {\n                if (node->timer < timer) {\n                    node->timer = timer;\n                }\n                node->mode = mode;\n                return;\n            }\n            node = node->next;\n        } while (node != NULL);\n    }\n    node = (ListNode15188A58 *)allocate_memory(sizeof(*node), 1, 0, 0);\n    if (node == NULL) {\n        return;\n    }\n    buffer = (u8 *)allocate_memory(0x180, 1, 1, 0);\n    if (buffer == NULL) {\n        func_10004074(node);\n        return;\n    }\n    node->active = 1;\n    node->kind = 3;\n    node->cleared = 0;\n    node->recordSize = 20;\n    node->mode = mode;\n    node->timer = timer;\n    node->buffer = buffer;\n    node->key = key;\n    bzero(buffer, 0x180);\n    func_15188A58(node, (ListNode15188A58 *)&D_800DF7CC);\n}'
NEW=HEADERS+SELECTED

def source_states(live):
    if live.count(OLD)==1 and NEW not in live:return live,live.replace(OLD,NEW,1),False
    if live.count(NEW)==1 and OLD not in live:return live.replace(NEW,OLD,1),live,True
    raise ValueError('Keyed registration source state changed')
