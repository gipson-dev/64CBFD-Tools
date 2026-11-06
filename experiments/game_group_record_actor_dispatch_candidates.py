"""Enabled group records, actor lookup and retained live count semantics."""
from pathlib import Path
from tools.experiments.game_grouped_actor_dispatch_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15022528','generated_49D30'
SOURCE,ASM='conker/src/game/generated_49D30.c','conker/asm/49D30.s'
BUILD='conker/build/game-group-record-actor-dispatch-15022528-match'
ENTRY,ROM,WORDS=0x15022528,0x4f9d8,70
OLD='s32 func_15022528() {\n    return 0;\n}'
HEADERS='typedef struct GroupActorRecord15022528 {\n    u16 kind;\n    u8 actorId;\n    u8 reserved03[5];\n} GroupActorRecord15022528;\n'
SELECTED='/* Dispatch enabled type-two records; refresh the count after processing a descriptor. */\nvoid func_15022528(s32 group) {\n    s32 index;\n    s32 count;\n    u8 *actor;\n    GroupActorRecord15022528 *record;\n    count = D_800C363A[group];\n    for (index = 0; index < count; index++) {\n        if (D_800C35D0[group][index] && D_800C35C8[group][index]) {\n            record = (GroupActorRecord15022528 *)(D_800C35F0[group] + index * 8);\n            if (record->kind == 2) {\n                actor = func_15083E90(record->actorId);\n                if (actor != NULL) {\n                    func_1502178C(actor, group, index);\n                }\n            }\n            count = D_800C363A[group];\n        }\n    }\n}\n'
NEW=HEADERS+SELECTED

def source_states(live):
    old_decl='s32 func_15022528();'
    new_decl='void func_15022528(s32);'
    if live.count(OLD)==1 and live.count(old_decl)==1 and NEW not in live:
        return live,live.replace(OLD,NEW,1).replace(old_decl,new_decl,1),False
    if live.count(NEW)==1 and live.count(new_decl)==1 and OLD not in live:
        return live.replace(NEW,OLD,1).replace(new_decl,old_decl,1),live,True
    raise ValueError('Group-record owner source changed')
