"""Actor bounds, signed height-entry selection and ordered event dispatch."""
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_151CE51C','generated_1FA770'
SOURCE,ASM='conker/src/game/generated_1FA770.c','conker/asm/1FA770.s'
BUILD='conker/build/game-event-height-threshold-151CE51C-match'
ENTRY,ROM,WORDS=0x151CE51C,0x1FB9CC,70
OLD='s32 func_151CE51C() {\n    return 0;\n}'
HEADERS='typedef struct HeightEntry151CE51C { u8 prefix[4]; f32 height; u8 rest[20]; } HeightEntry151CE51C;\ntypedef struct HeightOwner151CE51C {\n    u8 prefix[0x1E]; u16 flags; u8 pad20[5]; u8 count25; u8 pad26[6];\n    s8 count, current, previous; u8 pad2F[0x65]; HeightEntry151CE51C *entries;\n} HeightOwner151CE51C;\nvoid *func_151CE634(void *);\nvoid func_1515C1A0(struct127 *, struct17 *, f32 *, f32 *);\ns32 func_1505D024(struct127 *, s32, u16, s32);\n'
SELECTED='/* Dispatch the event when the actor reaches the selected height boundary. */\nvoid func_151CE51C(struct127 *actor, u8 *event) {\n    struct17 position;\n    f32 radius;\n    f32 height;\n    HeightOwner151CE51C *owner;\n    s32 index;\n    HeightEntry151CE51C *entries;\n    f32 boundary;\n    f32 limit;\n    f32 centerY;\n    f32 extent;\n    s32 command;\n    owner = func_151CE634(*(void **)(event + 0x18));\n    if (owner != NULL) {\n        func_1515C1A0(actor, &position, &radius, &height);\n        if (owner->flags & 8) {\n            if (owner->count > 0) {\n                index = owner->previous - 1;\n                if (index < 0) index = owner->count25 - 1;\n                centerY = position.unk4;\n                extent = height;\n                boundary = centerY - extent;\n                entries = owner->entries;\n                limit = entries[index].height;\n                command = 0x60019;\n                if (boundary <= limit) {\n                    func_1505D024(actor, command, 0, -1);\n                }\n            }\n        } else {\n            if (owner->count > 0) {\n                centerY = position.unk4;\n                extent = height;\n                boundary = centerY + extent;\n                entries = owner->entries;\n                limit = entries[owner->current].height;\n                command = 0x60019;\n                if (limit <= boundary) {\n                    func_1505D024(actor, command, 0, -1);\n                }\n            }\n        }\n    }\n}\n'
NEW=HEADERS+SELECTED
def source_states(live):
    if live.count(OLD)==1 and NEW not in live:return live,live.replace(OLD,NEW,1),False
    if live.count(NEW)==1 and OLD not in live:return live.replace(NEW,OLD,1),live,True
    raise ValueError('Height-threshold owner source changed')
